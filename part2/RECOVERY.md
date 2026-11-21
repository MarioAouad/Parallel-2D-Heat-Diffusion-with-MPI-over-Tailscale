# Part 2 evidence recovery and remaining records

**Current review, 21 November 2026:** The [new retained-field cluster study](results/2026-11-21-retained-cluster/) passes strict verification: 84/84 exact comparisons, 109 retained fields, all three VMs represented. The missing-original-fields gap is closed by this new run; old archives remain record-only. Earlier dates and open-gap descriptions below refer to the historical archive, not the current delivery.


The heat solver has no known numerical or halo-exchange defect from the review.
Its C++ source and the dated cluster measurements are unchanged. The fixes concern
the written explanation and how experiments retain and verify evidence.

## Original 19 November run

The archived study records 84 successful byte comparisons across two/three VMs.
Its binary fields were omitted. Its original runner also deleted the 84 parallel
comparison fields after comparing them; a transferred folder may therefore contain
only serial references and the two figure pairs. Do not claim that those references
alone recover all the original comparisons. Do not regenerate fields and insert
them into the old archive as though they were original measurements.

Current verification of that legacy archive checks hashes, unchanged solver sources,
complete parameter coverage, CSV/raw summary consistency, V error norms, figure
summaries, debug transcripts and machine counts. It explicitly reports that it
cannot repeat the byte comparisons. The dated archive and its manifest stay intact.

## Close the binary-field gap

If an original full run folder exists on heat-3, preserve it separately first.
The run path was `~/heat-project-repo/part2/results/runs/20261119T184915639127Z`.
Keep originals and their provenance; do not merge files into the immutable archive.

To produce a complete new comparison archive, synchronize the updated repository
onto each VM, then build on **each** VM:

```bash
cd ~/heat-project-repo
make serial strips
```

Both parallel runners now check the configured slots against each guest's actual
`nproc`, use `--nooversubscribe` in cluster mode, and record the checked counts.
Part 2 reads the current allocation rather than assuming six slots.

On **one** launching VM with the existing private cluster configuration:

```bash
cd ~/heat-project-repo
make check-strips
python3 part2/run_experiments.py --cluster
# Substitute the timestamp printed by the preceding command:
python3 part2/verify_results.py --data part2/results/runs/<timestamp> --require-fields
```

Every new run retains all 109 original binary files for the default study (21
comparison references, 84 parallel results and four figure fields). It writes 86
verified field pairs (84 CSV comparison rows plus two figure pairs). Filenames and
hashes are in `compare.csv`; every field is also in the manifest. The verifier
reads the original files again, checks hashes, sizes, boundaries, extrema and V norms,
and compares each serial/parallel pair byte for byte. A missing or changed file fails.
Source and launcher-executable hashes are captured; the latter do not independently
attest the executable installed on every remote VM. Each VM must still build the
same synchronized source with the documented flags.

Copy the **entire** new folder, including `fields/`, to a new reviewed
`part2/results/<new-date-or-label>-cluster/` directory after inspection. Do not
overwrite `2026-11-19-cluster`. The ignore policy permits binary fields in these
reviewed cluster archives and continues to ignore temporary `results/runs/` data.

This run is needed to close the missing-original-fields gap, not to fix a known
solver error. The existing archived results continue to support checkpoint C2.
The live demonstration and Part 4 performance study are separate requirements.

## AI history

Local Codex session recovery saved 21 snapshots containing 411 visible user/assistant
messages in `llm_log/private/recovered/2026-11-19-part2-fixes/`. Each session has
source/output SHA-256 hashes, timestamps, tool metadata and recorded model IDs when
available. The recovery filters out internal reasoning, system/developer messages
and tool calls. These are visible-message snapshots, not unfiltered original exports;
compaction, missing attachments and the active session's capture time are disclosed.

Two heat-3 Claude Code sessions are now exported by the pulled changes. They do
not establish complete earlier history. Owners still need to supply the missing
earlier and teammate conversations with actual member/model/date metadata. A
recovery script cannot manufacture missing interactions or establish that logging
existed at the start. See the current [logging status](../llm_log/README.md).
