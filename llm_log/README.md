# AI interaction record status

The assignment requires full prompts/responses, actual team member, tool/model and dates for **every** interaction, including setup and reporting. AGENTS.md records prospective instructions; it does not establish that automatic logging was configured at the beginning.

This repository includes an append-only index of organization, verification and
publication sessions in [LOG.md](LOG.md). Full visible records are retained in
the ignored private course archive. Exact model/member details that are unavailable are marked unknown. It does not contain a complete earlier chat export, and no missing transcript has been fabricated.

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
| Teammates' AI sessions (heat-1, heat-2), including the "21 recovered local sessions" mentioned in a review | operators of heat-1, heat-2 | **Missing here.** Each member must export their own (see below) |

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
