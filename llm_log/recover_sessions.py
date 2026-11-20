"""Recover visible Codex messages from local JSONL session snapshots.

Exports only user messages and assistant commentary/final text. It never exports
analysis, reasoning items, tool calls, system/developer prompts or credentials files.
The output must stay in llm_log/private; historical messages may contain private data.
It does not reconstruct missing chats, attachments no longer present, or identities.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def extract(snapshot, workspace):
    records, meta, models, compacted = [], {}, set(), 0
    malformed = 0
    for number, line in enumerate(snapshot.decode('utf-8').splitlines(), 1):
        try:
            item = json.loads(line)
        except ValueError:
            malformed += 1
            continue
        payload = item.get('payload', {})
        if item.get('type') == 'session_meta':
            meta = {k: payload.get(k) for k in ['id', 'timestamp', 'cwd', 'originator', 'model_provider']}
        elif item.get('type') == 'turn_context' and payload.get('model'):
            models.add(payload['model'])
        elif item.get('type') == 'compacted':
            compacted += 1
        elif item.get('type') == 'response_item' and payload.get('type') == 'message':
            role, channel = payload.get('role'), payload.get('channel')
            if role not in ('user', 'assistant') or (role == 'assistant' and channel not in (None, 'commentary', 'final')):
                continue
            # Keep complete visible content blocks, including image references where present.
            content = [block for block in payload.get('content', [])
                       if block.get('type') in ('input_text', 'output_text', 'text', 'input_image', 'image_url')]
            if content:
                records.append(dict(source_line=number, timestamp=item.get('timestamp'),
                                    role=role, channel=channel, content=content))
    cwd = str(meta.get('cwd') or '').replace('\\', '/').rstrip('/').casefold()
    base = str(workspace).replace('\\', '/').rstrip('/').casefold()
    if cwd != base and not cwd.startswith(base+'/'):
        return None
    return dict(metadata=meta, models=sorted(models), visible_messages=records,
                compaction_events=compacted, malformed_lines=malformed)


def recover(source, workspace, out, member='unknown (not supplied)'):
    out = out.resolve()
    if not out.is_relative_to((HERE/'private').resolve()):
        raise ValueError('Recovery output must be inside llm_log/private')
    if not source.is_dir():
        raise ValueError('Session source directory is missing')
    out.mkdir(parents=True, exist_ok=False)
    manifest = []
    for path in sorted(source.rglob('*.jsonl')):
        snapshot = path.read_bytes()
        result = extract(snapshot, workspace)
        if result is None or not result['visible_messages']:
            continue
        stem = path.stem
        output = out/(stem+'.visible.jsonl')
        output.write_text(''.join(json.dumps(record, ensure_ascii=False)+'\n'
                                  for record in result.pop('visible_messages')), encoding='utf-8')
        data = output.read_bytes()
        count = len(data.splitlines())
        manifest.append(dict(file=output.name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest(),
                             source_file=str(path), source_snapshot_bytes=len(snapshot),
                             source_snapshot_sha256=hashlib.sha256(snapshot).hexdigest(),
                             visible_message_count=count, team_member=member, **result))
    index = dict(captured_utc=datetime.now(timezone.utc).isoformat(), sessions=manifest,
                 limitations=['Filtered visible-message snapshots, not full unfiltered session exports.',
                              'Other tools, other computers, unavailable attachments and missing/compacted history are not recovered.',
                              'The active chat is captured only through the snapshot time; retain its later messages separately.'])
    (out/'manifest.json').write_text(json.dumps(index, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    return len(manifest), sum(s['visible_message_count'] for s in manifest)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True, help='local Codex sessions directory')
    parser.add_argument('--workspace', type=Path, required=True, help='include sessions whose recorded cwd is here or below')
    parser.add_argument('--out', type=Path, help='new directory inside llm_log/private')
    parser.add_argument('--member', default='unknown (not supplied)', help='actual team member, if known')
    args = parser.parse_args()
    out = args.out or HERE/'private'/'recovered'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    count, messages = recover(args.source, args.workspace, out, args.member)
    print(f'Recovered {count} session snapshots, {messages} complete visible message records into {out}')
    print('Other tools/computers and missing history still need their original exports; see manifest.json.')


if __name__ == '__main__':
    main()
