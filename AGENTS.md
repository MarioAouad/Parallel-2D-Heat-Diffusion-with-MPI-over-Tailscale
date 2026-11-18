# Course interaction records

These project instructions were added during the compliance review on
18 November 2026. They do not claim that earlier interactions were logged.

For future interactions working in this project:

1. Preserve the complete visible user prompts and assistant responses, not
   summaries, in llm_log. Include progress responses when available.
2. Append a session entry to llm_log/LOG.md with actual date and time, team
   member, tool and exact model when known, full prompts and responses, and
   files created or modified with verified line ranges. Mark unknown metadata
   honestly rather than guessing it.
3. Never edit or delete an existing log entry. Add corrections as new entries.
4. Save the original full chat/session export in llm_log/raw when available.
   An index entry or this file does not substitute for that export.
5. Before any requested commit, include the corresponding interaction record
   with the code changes. Do not commit or publish without user authorization.
6. Do not record hidden reasoning or copy private credential/key files.
   Keep raw conversation records containing private material in the team's
   private course submission rather than publishing them accidentally.

Earlier setup and programming sessions still require a complete export or
verbatim copy, including the model/member/date metadata required by the
assignment. This instruction file guides agents; it is not an installed
automatic capture hook. Check the saved transcript after each session.


## This organized public repository

Keep the numbered Part 0 reading path. Do not implement later solvers merely
because they are listed as future requirements. Explain code and timing choices.
Measured CSVs are immutable evidence; new experiments go in separate run folders.
Retain complete private raw transcripts in the private course hand-in. Publish
only copies without credentials, and disclose any redaction or missing history.
Never claim a logging pipeline existed earlier without actual evidence.
