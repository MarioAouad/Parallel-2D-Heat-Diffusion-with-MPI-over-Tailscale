#!/usr/bin/env python3
"""Publish a verified public copy and derive review tables without new MPI work."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil
import statistics
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'part4'))
import common as C
import verify_results as V


def rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def prepare(source, destination):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    V.verify_study(source)
    if destination.exists():
        raise ValueError('Destination exists; never overwrite a reviewed study')
    destination.mkdir(parents=True)
    original_manifest = json.loads((source/'manifest.json').read_text())
    redactions = []
    for item in original_manifest['published_files']:
        relative = Path(item['file'])
        if relative.is_absolute() or '..' in relative.parts or 'private' in relative.parts:
            raise ValueError('Unsafe public manifest entry')
        target = destination/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source/relative, target)
    raw_path = destination/'raw_runs.jsonl'
    raw = [json.loads(line) for line in raw_path.read_text().splitlines()]
    for record in raw:
        if record['task_id'].startswith('network:'):
            # Tailscale account columns can remain after hostname/IP sanitizing.
            # Restrict this additional redaction to network stdout, never MPI
            # commands, numerical output, timings, stderr or checkpoint values.
            old = record['stdout']
            record['stdout'], count = re.subn(r'(?<!\S)[\w.%+\-]+@[\w.\-]*', '[account]', old)
            if count:
                redactions.append(dict(run_id=record['run_id'], account_tokens=count))
    raw_path.write_text(''.join(json.dumps(record, allow_nan=False)+'\n' for record in raw), encoding='utf-8')
    C.manifest(destination)
    checked = V.verify_study(destination)
    changes = []
    for item in original_manifest['published_files']:
        original = source/item['file']; public = destination/item['file']
        if original.read_bytes() != public.read_bytes():
            changes.append(dict(file=item['file'], original_sha256=C.sha(original),
                                public_sha256=C.sha(public)))
    if [item['file'] for item in changes] != ['raw_runs.jsonl']:
        raise ValueError('Unexpected evidence change: '+repr(changes))
    measurements = rows(destination/'measurements.csv')
    summary = rows(destination/'analysis/summary.csv')
    predictions = rows(destination/'analysis/predictions.csv')
    state = json.loads((destination/'state.json').read_text())['completed']
    selected = {value['run_id'] for value in state.values()}
    groups = defaultdict(list)
    for measurement in measurements:
        groups[tuple(measurement[k] for k in ('experiment','host','decomp','mapping','P','N'))].append(measurement)
    assert len(groups) == 143 and all(len(g) == 3 for g in groups.values())
    for key, group in groups.items():
        expected = statistics.median(float(r['seconds_per_step']) for r in group)
        stored = next(r for r in summary if tuple(r[k] for k in ('experiment','host','decomp','mapping','P','N')) == key)
        assert expected == float(stored['median_seconds_per_step'])
    strong = [r for r in predictions if r['experiment'] == 'strong']
    comparisons = []
    for mapping in ('node','slot'):
        for P in (4,8):
            for N in (512,2048,8192):
                pair = {r['decomp']:r for r in strong if r['mapping']==mapping and int(r['P'])==P and int(r['N'])==N}
                winner = lambda field: min(pair, key=lambda layout: float(pair[layout][field]))
                comparisons.append(dict(mapping=mapping, P=P, N=N,
                    strips_s=float(pair['strips']['measured_s_per_step']), blocks_s=float(pair['blocks']['measured_s_per_step']),
                    predicted_winner=winner('model_total_s_per_step'), measured_winner=winner('measured_s_per_step'),
                    strips_model_s=float(pair['strips']['model_total_s_per_step']), blocks_model_s=float(pair['blocks']['model_total_s_per_step'])))
    best = [min((r for r in strong if int(r['N'])==N), key=lambda r:float(r['measured_s_per_step'])) for N in (512,2048,8192)]
    cross = [r for r in strong if int(next(s['nodes'] for s in summary if all(s[k]==r[k] for k in ('experiment','decomp','mapping','P','N'))))>1]
    spread = max(summary, key=lambda r:float(r['max_seconds_per_step'])/float(r['min_seconds_per_step']))
    rejected = [r for r in raw if r['run_id'] not in selected]
    review = dict(verification=checked, measurement_counts=dict(Counter(r['experiment'] for r in measurements)),
        configurations=len(groups), repetitions_per_configuration=3, raw_invocations=len(raw),
        raw_checkpoint_references=len(state), rejected_attempts=len(rejected),
        warning_only_rejected_attempts=sum(r['returncode']==0 for r in rejected),
        nonzero_exit_rejected_attempts=sum(r['returncode']!=0 for r in rejected),
        best_strong=best, cross_vm_measured_speedups=sum(float(r['speedup_or_weak_efficiency'])>1 for r in cross),
        cross_vm_strong_configurations=len(cross),
        model_layout_agreements=sum(r['predicted_winner']==r['measured_winner'] for r in comparisons),
        layout_comparisons=len(comparisons), worst_spread=dict(spread,
            max_over_min=float(spread['max_seconds_per_step'])/float(spread['min_seconds_per_step'])),
        privacy=dict(network_records_redacted=len(redactions), account_tokens_redacted=sum(r['account_tokens'] for r in redactions),
                     changed_public_files=changes, original_manifest_sha256=C.sha(source/'manifest.json'),
                     public_manifest_sha256=C.sha(destination/'manifest.json'),
                     policy='Only network stdout account identifiers redacted. Raw measured summaries, stderr, commands, '
                            'CSV values, figures, metadata and checkpoints unchanged; new public manifest. Original bundle private.'))
    C.write_json(ROOT/'part4/review.json', review)
    C.write_csv(ROOT/'part4/layout-comparison.csv', comparisons)
    print(json.dumps(review, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    prepare(args.source, args.destination)
