# Final CPU/MPI report and presentation

[final-report.pdf](final-report.pdf) is **ten main pages plus three original
vector-plot appendices**, within the assignment's ten-page-plus-appendices limit.
It names Mario Aouad, Mohamad Farchoukh and Bassem Haddad and records their stated
shared contributions. It covers Parts 0-4; optional GPU/CUDA is omitted.

The measured campaign is [archived publicly](../../part4/results/2026-11-24-cluster/)
with [review provenance](../../part4/review.json). Original measured summaries,
CSV values and figures are unchanged. Private endpoint/account-bearing originals
and complete visible AI records belong in the private course hand-in.

## Rebuild the report offline

Use Python with NumPy, Matplotlib, ReportLab and pypdf, plus Arial (Windows) or
DejaVu Sans (Linux). The report source is [build_report.py](build_report.py);
the compact plots are produced by [build_figures.py](build_figures.py).

```bash
python3 docs/final-report/build_figures.py
python3 docs/final-report/build_report.py
make verify-delivery
```

No VM runs are launched by these commands. Report construction refuses a main
body other than ten pages. Page 10 includes actual shared contributions and
source/evidence qualifications. Full strong-scaling plot PDFs are appended
without changing the archived originals.

## Existing Case 1/2 evidence versus a live presentation

There already are actual three-VM runs and heat maps in
[Part 3 cases.png](../../part3/results/2026-11-21-retained-cluster/cases.png), with
the exact serial/blocks fields retained in that study. Part 2 also retains its
Case 1/2 fields and heat maps. No new full correctness or performance study is
needed to recreate technical evidence for those cases.

The assignment additionally requires a **ten-minute live presentation**, on the
measurement network, running Cases 1 and 2 across at least three VMs, showing a
heat map/animation and changing N/P on request. Existing run records do not
certify whether the team has already presented this to the instructor.

After the final files are published, synchronize the same clean revision on all
three guests and build with `make`. From heat-1:

```bash
# Preview only, no SSH/MPI launched:
python3 scripts/run-demo.py --N 32 --P 3 --steps 40 --decomp blocks

# Explicit live demonstration, once on heat-1:
python3 scripts/run-demo.py --run --N 32 --P 3 --steps 40 --decomp blocks

# Example requested change: N and P, or choose strips:
python3 scripts/run-demo.py --run --N 48 --P 6 --steps 40 --decomp strips
```

The helper reuses the original checked MPI launcher and transport. It verifies
three-guest participation, compares each Case 1/2 field byte-for-byte with a fresh
serial reference and writes a heat map and private raw record to a new ignored
`output/demo-TIMESTAMP/` folder. The default is deliberately a small demo, not a
new benchmark. It has been checked offline; a fresh live demo was not performed
by the assistant during report generation.

Open the printed `cases.png` on the launcher's desktop, or copy it to Windows
with the already configured localhost SSH port and show it there. For a headless
guest, substitute the actual printed folder in Windows PowerShell:

```powershell
scp -P 2222 "mpi@127.0.0.1:/home/mpi/heat-project-repo/output/demo-ACTUAL_TIMESTAMP/cases.png" "$env:USERPROFILE\Downloads"
```

Suggested ten minutes: two minutes for the method/stability, two for ownership
and halos, three for both live cases and a changed N/P, two for the measured
curves/model/network limitation, and one for reproducibility/team questions.
Every member must be ready to explain every code section and report sentence.

## Remaining hand-in actions

Use [the current checklist](../deliverables.md). The report and technical evidence
are ready. Present the live demo if still pending, confirm all three members'
full visible AI histories/metadata, read the report together and submit the
required artifacts. The private supplement is deliberately labelled incomplete
with respect to historical all-member AI coverage; no absent conversations or
earlier automatic logging pipeline is invented.
