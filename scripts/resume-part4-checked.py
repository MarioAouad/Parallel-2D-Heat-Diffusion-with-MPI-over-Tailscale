#!/usr/bin/env python3
"""Resume a frozen Part 4 campaign; bounded retries for one known MPI warning.

Copy this standalone helper to /tmp on the launcher. No Git pull, solver change,
stderr filtering, checkpoint editing or source-hash override is performed. Each
warning attempt stays rejected by the original runner and retained in raw history.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys


PARENT_WARNING = re.compile(
    r"\[[^\]\r\n]+:\d+\] plm:rsh: Warning: setpgid\((\d+),\1\) "
    r"failed in parent with errno=Permission denied\(13\)"
)


def read_raw(folder):
    records = [json.loads(line) for line in (folder/'raw_runs.jsonl').read_text().splitlines()
               if line.strip()]
    if [record['run_id'] for record in records] != list(range(1, len(records)+1)):
        raise ValueError('Raw invocation sequence is not contiguous; inspect manually')
    return records


def frozen_common(repo, meta):
    # Check before importing. Never rewrite the recorded source hashes/revision.
    for name, expected in meta['sources'].items():
        if hashlib.sha256((repo/name).read_bytes()).hexdigest() != expected:
            raise ValueError('Campaign source changed: '+name+'; keep campaigns separate')
    sys.path.insert(0, str(repo/'part4'))
    spec = importlib.util.spec_from_file_location('part4_frozen_common', repo/'part4/common.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if set(meta['sources']) != set(module.SOURCES):
        raise ValueError('Source inventory differs from frozen campaign')
    return module


def retry_reason(before, after, folder, meta, common):
    """Return a task only for a newly rejected heat invocation with this warning.

    The helper never makes this invocation a completed measurement. A subsequent
    clean retry must pass all original runner and final-verifier checks.
    """
    if len(after) <= len(before) or after[:len(before)] != before:
        return None
    record = after[-1]
    if record.get('returncode') != 0 or not record.get('command') or record['command'][0] != 'mpirun':
        return None
    diagnostic = record.get('stderr', '').strip().splitlines()
    if not diagnostic or not all(PARENT_WARNING.fullmatch(line) for line in diagnostic):
        return None
    slots = [host['slots'] for host in meta['hosts']]
    tasks = {task['id']: task for task in common.design(meta['parameters'], slots)}
    task = tasks.get(record['task_id'])
    if task is None or task['experiment'] not in ('strong', 'weak'):
        return None
    state = json.loads((folder/'state.json').read_text())['completed']
    if task['id'] in state:
        return None
    probe = state.get(f"placement:{task['mapping']}:{task['P']}")
    if not probe:
        return None
    try:
        parsed = common.parse_summary(record['stdout'], task, meta['parameters'],
                                      len(set(probe['rank_hosts'])))
        wall = record['wall_seconds']
        if not math.isfinite(wall) or wall < parsed['total_s']*(1-1e-8):
            return None
    except (KeyError, ValueError, TypeError):
        return None
    return task['id']


def append_event(path, event, **fields):
    record = dict(utc=datetime.now(timezone.utc).isoformat(), event=event, **fields)
    with path.open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(record, allow_nan=False)+'\n')
        stream.flush()
        os.fsync(stream.fileno())


def launch(command, logfile):
    # Tee outside the run folder, where the existing packager already finds logs.
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, bufsize=1) as process:
        try:
            for line in process.stdout:
                print(line, end='', flush=True)
                logfile.write(line)
                logfile.flush()
            return process.wait()
        except BaseException:
            # Do not automatically retry a user interruption or broken terminal.
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
            raise


def supervise(folder, notes, per_task=3, total_limit=32, executor=launch):
    folder = Path(folder).resolve()
    repo = next((parent for parent in folder.parents
                 if (parent/'part4/run_experiments.py').is_file()
                 and (parent/'scripts/run-part4.sh').is_file()), None)
    if repo is None or not folder.is_relative_to((repo/'part4/results/runs').resolve()):
        raise ValueError('Use an original unreviewed campaign under part4/results/runs')
    if per_task < 0 or total_limit < 0 or not notes.strip():
        raise ValueError('Supply actual conditions and nonnegative retry limits')
    meta = json.loads((folder/'metadata.json').read_text())
    if meta.get('mode') != 'cluster':
        raise ValueError('Expected an actual cluster campaign')
    common = frozen_common(repo, meta)
    private = folder/'private'
    private.mkdir(exist_ok=True)
    # A distinct supervisor lock prevents two retry loops taking turns on one run.
    import fcntl
    with (private/'resume-supervisor.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        journal = private/'resume-supervisor.jsonl'
        policy = (f'Exact Open MPI parent setpgid Permission denied(13) warning-only '
                  f'heat attempts are retried at most {per_task} times per task and '
                  f'{total_limit} times in this supervised session; all attempts retained. ')
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
        log = folder.parent/(folder.name+'-session-supervised-'+stamp+'.log')
        append_event(journal, 'start', per_task_retry_limit=per_task,
                     total_retry_limit=total_limit, policy=policy, conditions=notes,
                     helper_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())
        counts = Counter()
        total = 0
        with log.open('x', encoding='utf-8') as logfile:
            logfile.write(policy+'\nConditions: '+notes+'\n')
            while True:
                before = read_raw(folder)
                # Original runner repeats preflight (revision, sources, binaries,
                # MPI, capacity, idle cluster), honors lock and skips checkpoints.
                command = [sys.executable, '-u', str(repo/'part4/run_experiments.py'),
                           '--run', '--resume', str(folder), '--notes', policy+notes]
                append_event(journal, 'launch', starting_raw_count=len(before))
                status = executor(command, logfile)
                after = read_raw(folder)
                append_event(journal, 'runner_exit', returncode=status,
                             ending_raw_count=len(after))
                if status == 0:
                    append_event(journal, 'verified_runner_completed', automatic_retries=total)
                    break
                task = retry_reason(before, after, folder, meta, common) if status > 0 else None
                if task is None or counts[task] >= per_task or total >= total_limit:
                    append_event(journal, 'stopped_for_review', task_id=task,
                                 automatic_retries=total, returncode=status)
                    print('STOPPED: no eligible warning retry, or retry limit reached. '
                          'Original records preserved; send the last output.', flush=True)
                    if len(after) > len(before):
                        print('LAST INVOCATION:', after[-1].get('task_id'),
                              'EXIT CODE:', after[-1].get('returncode'), flush=True)
                        print('RETAINED STDERR:\n'+after[-1].get('stderr', ''), flush=True)
                    return status if 0 < status <= 255 else 1
                counts[task] += 1
                total += 1
                append_event(journal, 'retry_exact_parent_warning', task_id=task,
                             rejected_run_id=after[-1]['run_id'], task_retry=counts[task],
                             total_retries=total)
                message = (f'SUPERVISED RETRY {total}/{total_limit}: {task}; exact parent '
                           'setpgid warning only. Rejected attempt retained; completed tasks skipped.')
                print(message, flush=True)
                logfile.write(message+'\n')
                logfile.flush()
        # Journal/log are settled before tar reads them. The original packager
        # performs strict offline verification and includes private history/logs.
        return subprocess.run(['bash', str(repo/'scripts/run-part4.sh'),
                               'package', str(folder)]).returncode


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--notes', required=True, help='Actual current power/load/Wi-Fi conditions')
    parser.add_argument('--max-retries-per-task', type=int, default=3)
    parser.add_argument('--max-total-retries', type=int, default=32)
    args = parser.parse_args()
    if os.name != 'posix':
        parser.error('Run as mpi on the Ubuntu launcher; this helper does not run on Windows')
    raise SystemExit(supervise(args.run, args.notes, args.max_retries_per_task,
                               args.max_total_retries))


if __name__ == '__main__':
    main()
