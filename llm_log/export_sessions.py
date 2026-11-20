"""Export Claude Code sessions for the course AI-interaction record.

For each session JSONL this writes:
  - an unchanged copy to llm_log/private/raw/ (git-ignored: for the private hand-in);
  - a redacted, readable transcript to llm_log/sessions/<date>-<id>.md (public).

The transcript keeps every user prompt and every visible assistant message in order,
plus a one-line note for each tool call. It leaves out hidden reasoning (AGENTS.md
rule 6), tool outputs and harness system reminders, and collapses skill instructions
that the tool loads to one line.

Usage, from the repository root:
  python3 llm_log/export_sessions.py --member "operator of node heat-1" \\
      --redact my-laptop-name=heat1 --redact my-account=<user> \\
      ~/.claude/projects/<project-folder>/<session-id>.jsonl [...]

Claude Code keeps one JSONL per session in ~/.claude/projects/<folder>/ (on Windows,
%USERPROFILE%\\.claude\\projects). Email addresses, Tailscale 100.x addresses and the user
name in home-directory paths are always redacted. Pass --redact for device hostnames,
account names or anything else private, then read the output before committing.
"""
import argparse
import hashlib
import json
import re
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
REDACT = [
    (re.compile(r'[A-Za-z0-9._%+-]+@(?!anthropic\.com)[A-Za-z0-9.-]+\.[a-z]{2,}'), '<email>'),
    (re.compile(r'\b100\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'), '<tailscale-ip>'),
    (re.compile(r'([A-Za-z]:[\\/]+Users[\\/]+)[^\\/\s"\'<]+'), r'\1<user>'),
    (re.compile(r'(/[a-z]/Users/|/home/(?!mpi\b))[^/\s"\'<]+'), r'\1<user>'),
]
REMINDER = re.compile(r'<system-reminder>.*?</system-reminder>', re.S)


def clean(text):
    text = REMINDER.sub('', text)
    for pattern, repl in REDACT:
        text = pattern.sub(repl, text)
    return text.strip()


def user_text(content):
    if isinstance(content, str):
        return content
    parts = []
    for c in content or []:
        if not isinstance(c, dict) or c.get('type') == 'tool_result':
            continue
        if c.get('type') == 'text':
            parts.append(c.get('text', ''))
        elif c.get('type') == 'image':
            parts.append('[image attached]')
    return '\n'.join(p for p in parts if p)


def export(src, member):
    sid = src.stem
    raw_dir = REPO/'llm_log'/'private'/'raw'
    raw_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, raw_dir/src.name)
    digest = hashlib.sha256(src.read_bytes()).hexdigest()

    entries, first, last, models, version = [], None, None, set(), None
    for line in src.open(encoding='utf-8'):
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        ts = d.get('timestamp')
        if ts:
            first = first or ts
            last = ts
        version = version or d.get('version')
        msg = d.get('message') or {}
        if d.get('type') == 'user':
            text = clean(user_text(msg.get('content')))
            if not text:
                continue
            if d.get('isMeta') or text.startswith('Base directory for this skill'):
                entries.append((ts, 'tool', 'skill instructions loaded by the tool (not typed by the '
                                'user): ' + text.splitlines()[0][:120]))
            elif d.get('isCompactSummary'):
                entries.append((ts, 'Context summary (written automatically when the conversation '
                                'was compacted)', text))
            else:
                entries.append((ts, 'User', text))
        elif d.get('type') == 'assistant':
            if msg.get('model') and not msg['model'].startswith('<'):
                models.add(msg['model'])
            for c in msg.get('content') or []:
                if c.get('type') == 'text' and clean(c.get('text', '')):
                    entries.append((ts, 'Assistant', clean(c['text'])))
                elif c.get('type') == 'tool_use':
                    inp = c.get('input') or {}
                    what = (inp.get('description') or inp.get('file_path') or inp.get('pattern')
                            or inp.get('action') or inp.get('skill') or '')
                    entries.append((ts, 'tool', clean(f"{c.get('name')}: {what}")))
    if not first:
        raise SystemExit(f'{src}: no timestamped messages')

    out_dir = REPO/'llm_log'/'sessions'
    out_dir.mkdir(exist_ok=True)
    name = f'{first[:10]}-{sid[:8]}.md'
    lines = [f'# Claude Code session {sid}', '',
             '| Field | Value |', '| --- | --- |',
             f'| Team member | {member} |',
             f'| Tool | Claude Code {version or "(version unknown)"}, as recorded in the session file |',
             f'| Model(s) | {", ".join(sorted(models)) or "unknown"} |',
             f'| First / last message (UTC) | {first} / {last} |',
             f'| Raw export | `llm_log/private/raw/{src.name}` (git-ignored; private hand-in), '
             f'SHA-256 `{digest}` |',
             '', '**What this copy contains.** Every user prompt and every visible assistant message,',
             'in order, plus a one-line note for each tool call. It leaves out hidden reasoning',
             '(AGENTS.md rule 6), tool outputs and harness system reminders. Redacted: email',
             'addresses, Tailscale addresses, home-directory user names and the strings given',
             'with `--redact` (device hostnames are written as their heatN alias). Attached',
             'screenshots appear as `[image attached]`. The raw export is the complete record.', '']
    counts = {'User': 0, 'Assistant': 0, 'tool': 0}
    for ts, label, text in entries:
        counts[label] = counts.get(label, 0)+1
        if label == 'tool':
            lines.append(f'- *{ts[11:19]} tool* - {text}')
        else:
            lines += ['', f'## {label} - {ts}', '', text, '']
    (out_dir/name).write_text('\n'.join(lines)+'\n', encoding='utf-8', newline='\n')
    print(f"{sid[:8]}: {counts['User']} user prompts, {counts['Assistant']} assistant messages, "
          f"{counts['tool']} tool notes -> llm_log/sessions/{name}; raw SHA-256 {digest[:16]}...")


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('sessions', nargs='+', type=Path, help='session .jsonl files')
    parser.add_argument('--member', required=True, help='e.g. "operator of node heat-1"')
    parser.add_argument('--redact', action='append', default=[], metavar='TEXT=REPLACEMENT',
                        help='case-insensitive literal to replace (repeatable)')
    args = parser.parse_args()
    for item in args.redact:
        text, _, repl = item.partition('=')
        REDACT.insert(0, (re.compile(re.escape(text), re.I), repl or '<redacted>'))
    for src in args.sessions:
        export(src.resolve(), args.member)


if __name__ == '__main__':
    main()
