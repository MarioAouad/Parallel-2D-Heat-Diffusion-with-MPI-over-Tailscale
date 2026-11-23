#!/usr/bin/env python3
"""Collect an interrupted Part 4 study and read-only guest diagnostics.

Standalone: copy this file into /tmp on the launching VM; do not pull a new
revision into an interrupted campaign. No solver, MPI job or benchmark is run.
The returned archive contains private host/network records; share privately.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import tarfile


PARENT_WARNING = re.compile(
    r"\[[^\]\r\n]+:\d+\] plm:rsh: Warning: setpgid\((\d+),\1\) "
    r"failed in parent with errno=Permission denied\(13\)"
)


def execute(command, timeout=30):
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return dict(command=command, returncode=result.returncode,
                    stdout=result.stdout, stderr=result.stderr)
    except (OSError, subprocess.TimeoutExpired) as error:
        return dict(command=command, error=str(error))


def warning_kind(text):
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return 'empty'
    return ('openmpi-parent-setpgid-only' if all(PARENT_WARNING.fullmatch(s) for s in lines)
            else 'other-diagnostic-needs-review')


def review_run(folder):
    state = json.loads((folder/'state.json').read_text())['completed']
    raw = []
    parse_errors = []
    for number, line in enumerate((folder/'raw_runs.jsonl').read_text().splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw.append(json.loads(line))
        except (ValueError, TypeError) as error:
            parse_errors.append(dict(line=number, error=str(error)))
    used = {value['run_id'] for value in state.values()}
    attention = []
    for record in raw:
        task = record.get('task_id', '')
        diagnostic = record.get('stderr', '')
        # Calibration's expected progress is not a launcher warning.
        if record.get('returncode') != 0 or record['run_id'] not in used or (
                task.startswith(('baseline:', 'strong:', 'weak:', 'placement:')) and diagnostic.strip()):
            attention.append(dict(run_id=record['run_id'], task_id=task,
                                  returncode=record.get('returncode'),
                                  selected_checkpoint=record['run_id'] in used,
                                  diagnostic_kind=warning_kind(diagnostic),
                                  stderr=diagnostic, stdout=record.get('stdout', ''),
                                  wall_seconds=record.get('wall_seconds')))
    heat = [value for value in state.values() if 'experiment' in value]
    return dict(completed_heat_measurements=len(heat),
                completed_calibration_sweeps=sum(key.startswith('calibration:') for key in state),
                completed_placement_probes=sum(key.startswith('placement:') for key in state),
                raw_invocations=len(raw), raw_parse_errors=parse_errors,
                nonzero_exit_attempts=sum(record.get('returncode') != 0 for record in raw),
                unselected_attempts=sum(record['run_id'] not in used for record in raw),
                attempts_requiring_review=attention,
                note='A warning-only rejected attempt has exit code zero and is not counted as a nonzero-exit failure. '
                     'This collector classifies messages; it never accepts a measurement or edits a checkpoint.')


def guest_program(repo, peers, include_network=True):
    # Pass arguments as data, rather than interpolating them into shell code.
    settings = dict(repo=str(repo), peers=peers, network=include_network)
    return '''import hashlib,json,pathlib,subprocess,datetime
settings=json.loads(SETTINGS)
repo=pathlib.Path(settings['repo'])
def run(command,timeout=30):
    try:
        p=subprocess.run(command,capture_output=True,text=True,timeout=timeout,cwd=repo)
        return dict(command=command,returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
    except (OSError,subprocess.TimeoutExpired) as e:
        return dict(command=command,error=str(e))
commands=[['hostname'],['date','-u','--iso-8601=seconds'],['nproc'],['lscpu'],
          ['free','-b'],['vmstat','1','3'],['ps','-eo','pid,comm,pcpu,pmem','--sort=-pcpu'],
          ['mpirun','--version'],['ompi_info','--param','plm','rsh','--level','9'],
          ['git','rev-parse','HEAD'],['git','status','--short'],
          ['ip','-s','link','show','tailscale0'],['ss','-s'],['dmesg','--level=err,warn']]
results=[run(command) for command in commands]
if settings['network']:
    results.extend(run(command,45) for command in
                   [['tailscale','status'],['tailscale','netcheck']])
    for peer in settings['peers']:
        results.append(run(['tailscale','ping','--c','3','--timeout','5s',peer],30))
files={}
for name in ['/proc/meminfo','/proc/pressure/cpu','/proc/pressure/memory','/proc/pressure/io']:
    try: files[name]=pathlib.Path(name).read_text()
    except OSError as e: files[name]=str(e)
hashes={}
for name in SOURCE_PATHS+['build/heat','build/heat_mpi','build/heat_blocks','build/mpi_pingpong']:
    try: hashes[name]=hashlib.sha256((repo/name).read_bytes()).hexdigest()
    except OSError as e: hashes[name]=str(e)
print(json.dumps(dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     observations=results,proc_files=files,sha256=hashes)))
'''.replace('SETTINGS', repr(json.dumps(settings))).replace('SOURCE_PATHS', repr([
        'part1/heat_serial.cpp', 'part2/heat_mpi.cpp', 'part3/heat_blocks.cpp',
        'part0/04-pingpong/mpi_pingpong.cpp', 'part4/common.py',
        'part4/run_experiments.py', 'part4/analyze.py', 'part4/verify_results.py']))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2)+'\n', encoding='utf-8')


def collect(run_folder, include_network=True):
    folder = Path(run_folder).resolve()
    if folder.is_symlink() or not all((folder/name).is_file() for name in ('metadata.json', 'state.json', 'raw_runs.jsonl')):
        raise ValueError('Supply the original run folder containing metadata.json, state.json and raw_runs.jsonl')
    # Find the repo from this run, independent of where this standalone file lives.
    repo = next((parent for parent in folder.parents
                 if (parent/'part0/config/hosts').is_file() and (parent/'part4/run_experiments.py').is_file()), None)
    if repo is None:
        raise ValueError('Cannot locate repository/configured hostfile above the run folder')
    if not folder.is_relative_to((repo/'part4/results/runs').resolve()):
        raise ValueError('Expected an unreviewed folder under part4/results/runs')
    meta = json.loads((folder/'metadata.json').read_text())
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = repo/'output'/('part4-diagnostic-'+stamp)
    out.mkdir(parents=True, exist_ok=False)
    print('Collecting into:', out, flush=True)
    # Copy original evidence before any probes. Symlinks are never followed.
    evidence = out/'original-run'/folder.name
    evidence.parent.mkdir()
    shutil.copytree(folder, evidence, symlinks=True)
    for link in evidence.rglob('*'):
        if link.is_symlink():
            raise ValueError('Unexpected symlink in run evidence; inspect manually')
    logs = out/'session-logs'
    logs.mkdir()
    for path in folder.parent.glob(folder.name+'-session-*.log'):
        if path.is_file() and not path.is_symlink():
            shutil.copy2(path, logs/path.name)
    review = review_run(evidence)
    write_json(out/'run-review.json', review)
    print('Saved measurements:', review['completed_heat_measurements'],
          'calibrations:', review['completed_calibration_sweeps'], flush=True)
    for attempt in review['attempts_requiring_review']:
        print('REVIEW', attempt['task_id'], 'exit=', attempt['returncode'],
              attempt['diagnostic_kind'], '\n'+attempt['stderr'], flush=True)
    configured = [line.split() for line in (repo/'part0/config/hosts').read_text().splitlines()
                  if line.strip() and not line.lstrip().startswith('#')]
    if len(configured) != 3:
        raise ValueError('Expected exactly three configured hosts')
    local = execute(['tailscale', 'ip', '-4'])
    write_json(out/'local-tailscale-address.json', local)
    address = local.get('stdout', '').strip()
    for index, fields in enumerate(configured):
        host = fields[0]
        code = guest_program(repo, [entry[0] for entry in configured if entry[0] != host], include_network)
        command = ['python3', '-c', code]
        if host != address:
            command = ['ssh', '-o', 'BatchMode=yes', '-o', 'StrictHostKeyChecking=yes',
                       '-o', 'ConnectTimeout=10', 'mpi@'+host, shlex.join(command)]
        # Up to ~2 min per guest; every individual network command is bounded.
        print('Checking guest', index+1, '(read-only; may take about two minutes)', flush=True)
        result = execute(command, 180)
        if result.get('returncode') == 0:
            try:
                payload = json.loads(result['stdout'])
            except ValueError:
                payload = result
        else:
            payload = result
        write_json(out/f'guest-{index+1}.json', payload)
    write_json(out/'diagnostic-metadata.json', dict(
        utc=datetime.now(timezone.utc).isoformat(), run_folder=str(folder),
        recorded_revision=meta.get('revision'), saved_status=meta.get('status'),
        network_checks=include_network,
        limitations='Post-interruption snapshots cannot establish memory pressure or network routes during earlier measurements. '
                    'Failed/missing commands are retained, not treated as successful checks. No MPI launches or solver runs performed. '
                    'Original measurement/checkpoint files remain untouched. Archive contains private endpoints.'))
    manifest = []
    for path in sorted(out.rglob('*')):
        if path.is_file():
            manifest.append(dict(file=path.relative_to(out).as_posix(), bytes=path.stat().st_size,
                                 sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    write_json(out/'diagnostic-manifest.json', manifest)
    archive = out.with_suffix('.tar.gz')
    with tarfile.open(archive, 'w:gz') as tar:
        tar.add(out, arcname=out.name)
    print('DIAGNOSTIC BUNDLE (share privately):', archive, flush=True)
    return archive


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path, help='Original interrupted run folder; read only')
    parser.add_argument('--no-network', action='store_true', help='Skip active Tailscale status/netcheck/ping probes')
    args = parser.parse_args()
    collect(args.run, include_network=not args.no_network)


if __name__ == '__main__':
    main()
