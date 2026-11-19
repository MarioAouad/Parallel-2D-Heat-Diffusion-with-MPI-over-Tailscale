# Written numerical-method task solutions

The existing [solutions PDF](Methode_Numerique_Tasks_Solutions.pdf) is included
with editable LaTeX, tables, figures, experimental source and saved numerical
results. All 25 required task numbers are present, together with optional
Task 6.5 (26 tasks total). The PDF is 32 pages and acknowledges AI assistance.
Its content and original source files were prepared earlier; this delivery
copies them without inventing team-member identities or earlier logging history.

`PROVENANCE.json` records original/public file hashes. One raw-output text file
replaces the old absolute Windows workspace prefix with BACKGROUND_WORKDIR;
its numerical result lines are unchanged. Exact originals remain privately
preserved. Temporary LaTeX build files, executables and reproducible binary
snapshots are excluded from Git.

## Use the correct solver

The final project reference is [part1/heat_serial.cpp](../../part1/heat_serial.cpp)
with its documented named options and Cases 1/2/V. The small positional-argument
solver under this folder's `experiments/` is the original helper for background
Tasks 6.7 and 7.2. It remains here to reproduce that earlier document; use the
Part 1 program for project simulations and subsequent MPI comparisons.

## Rebuild the written PDF

With pdfLaTeX installed, in this folder:

```bash
pdflatex -interaction=nonstopmode -halt-on-error Methode_Numerique_Tasks_Solutions.tex
pdflatex -interaction=nonstopmode -halt-on-error Methode_Numerique_Tasks_Solutions.tex
```

This uses the archived tables/figures. To rerun the numerical experiments,
first make a separate reproduction copy, so archived evidence is preserved:

```bash
copy="$HOME/heat-background-reproduction-$(date -u +%Y%m%dT%H%M%SZ)"
cp -a docs/background-solutions "$copy"
cd "$copy"
g++ -std=c++17 -O3 -ffp-contract=off experiments/heat_serial.cpp -o experiments/heat_serial
python3 experiments/run_experiments.py
```

Python needs NumPy and Matplotlib. Compile the PDF in that copy afterward if
you want a regenerated document. ORIGINAL_README.md retains the earlier
instructions for provenance; use the separate-copy procedure above for reruns.

The background solutions are a separate written deliverable, not the final
ten-page MPI project report. Preserve complete private AI interaction records
and add actual team identification as required for the final course hand-in.
