# AI interaction record status

The assignment requires full prompts/responses, actual team member, tool/model and dates for **every** interaction, including setup and reporting. AGENTS.md records prospective instructions; it does not establish that automatic logging was configured at the beginning.

This repository includes an append-only index of organization, verification and
publication sessions in [LOG.md](LOG.md). Full visible records are retained in
the ignored private course archive. Exact model/member details that are unavailable are marked unknown. No missing transcript has been fabricated.

## Recovered local sessions

The Part 2 fixes recovered **21 local Codex session snapshots, 411 visible messages**
under `private/recovered/2026-11-19-part2-fixes/`. The private manifest records the
source snapshot hash, exported-message hash, timestamps, recorded model IDs and
any compaction/malformed-record counts. Only user and visible assistant content is
exported; internal reasoning, tool calls and system/developer prompts are excluded.
Image references are preserved where present; unavailable attachment files cannot
be reconstructed. The active chat is captured only up to its snapshot time.

These recovered records reduce the gap; they do not establish completeness across
other tools, computers or missing/compacted history. Earlier Claude Code and teammate
sessions still require their owners' complete visible exports and actual metadata.

To capture another immutable snapshot on a teammate's computer:

```bash
python3 llm_log/recover_sessions.py --source /path/to/.codex/sessions --workspace /path/to/course-workspace --member "Actual team member"
```

The script creates a new private directory and refuses to overwrite an existing
one. Include the private recovery folders in the private course hand-in; Git ignores
them deliberately. The original source session files remain untouched.

Earlier private local records and full exports may contain disclosed credentials. Keep the complete records in a private course hand-in. A redacted public copy is useful for safe sharing but cannot be represented as the complete required private transcript. The public log and README alone do not close this course-compliance item.

For future sessions, preserve the visible full prompt and all full responses, including progress updates; append rather than replace entries, include actual metadata and verified file ranges, and commit the log with code. Save actual raw exports when supported. Do not store hidden reasoning or private key files.

## Session exports (status 20 November 2026)

Public, redacted transcripts are in [sessions/](sessions/), written by
[export_sessions.py](export_sessions.py). The unchanged raw JSONL files stay in the
git-ignored `llm_log/private/raw/` and belong in the private course hand-in.

| Source | Member | Status |
| --- | --- | --- |
| Claude Code, session `bc7486c7` (19 Nov, Part 0 explanation PDF) | operator of heat-3 | Exported: [transcript](sessions/2026-11-19-bc7486c7.md) + raw |
| Claude Code, session `0cf186f8` (19–20 Nov: Parts 0–3, cluster runs, Part 2 field fix) | operator of heat-3 | Exported as of 20 Nov: [transcript](sessions/2026-11-19-0cf186f8.md) + raw. **Re-export when the session ends**: the file is still growing |
| Earlier Claude conversations on heat-3's PC (setup, Parts 0–1, before 19 Nov) | operator of heat-3 | **Missing.** None is stored on this PC under `~/.claude/projects` for this repository. If they happened on claude.ai, export them from Settings → Privacy → Export data |
| Local Codex recovery snapshots | Actual member identity still to be supplied | 21 snapshots / 411 visible messages are present in this checkout under the private recovery path above; these do not establish all-member completeness |
| Remaining teammates' AI sessions (heat-1, heat-2) | operators of heat-1, heat-2 | Completeness is unverified; each member must supply their own missing full records (see below) |

The heat-3 PC also holds two Claude Code sessions in which its operator studied MPI lecture
slides. They are course study, not project work, and were not exported. One unrelated
session (not about this course) was also left out.

### How each team member exports their own sessions

- **Claude Code:** sessions are JSONL files in `~/.claude/projects/<folder>/` (Windows:
  `%USERPROFILE%\.claude\projects`). The folder name is the project path with separators
  replaced by `-`. From the repository root, run
  `python3 llm_log/export_sessions.py --member "operator of node heat-N" --redact <hostname>=heatN <files>`,
  read the output, and commit only `llm_log/sessions/`.
- **claude.ai (web or desktop chat):** Settings → Privacy → Export data. The archive is
  emailed. Keep it in the private hand-in, and quote only the project conversations.
- **ChatGPT:** Settings → Data controls → Export data.
- **Codex CLI:** sessions are in `~/.codex/sessions/` (JSONL). Keep them in the private
  hand-in.

An export that cannot be found must be listed as missing. Never reconstruct it from memory.


## Final-delivery recovery, 24 November 2026 local time

The latest immutable local recovery snapshot is
`private/recovered/20261123T224902038169Z/`: **24 session snapshots / 657 visible
messages**, attributed to Mario Aouad, whose identity was confirmed by the user.
These overlap earlier recoveries and must not be added together as unique counts.
Each snapshot records available model IDs, source hashes and compaction limits.
Current-turn visible records are retained separately because an active-chat
snapshot does not include messages created after capture. No hidden reasoning,
source tool calls or system/developer messages were exported by the recovery tool.

Mario Aouad confirmed the other team members as Mohamad Farchoukh and Bassem Haddad
and stated that all three worked across all project areas. This dated correction
supplies current identity/contribution information; older append-only entries
marked unknown are preserved. It does not identify unrelated or missing old chats.
The public index and private supplement still cannot certify completeness of the
other members' earlier sessions; each owner must verify and add their full exports.
