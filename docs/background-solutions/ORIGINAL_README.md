# Numerical Methods for the Heat Equation: worked solutions

This folder answers only the tasks in `heat_numerics_background-1.pdf`, as requested. It contains all 25 required tasks and optional Task 6.5 (26 tasks total). The MPI implementation, cluster setup, and cluster-performance report are outside this document.

## Contents

- `Methode_Numerique_Tasks_Solutions.pdf`: compiled document.
- `Methode_Numerique_Tasks_Solutions.tex`: main LaTeX source; supporting explanations are in `solutions_*.tex`.
- `experiments/heat_serial.cpp`: actual full-grid serial C++17 solver used for Tasks 6.7 and 7.2.
- `experiments/run_experiments.py`: reproduces the numerical experiments, plots, CSVs, and LaTeX table inputs.
- `results/`: raw output, numerical CSV tables, and double-precision binary heat fields.
- `figures/`: vector PDF plots used in the document, plus PNG previews.
- `tables/`: generated LaTeX tables.

## Reproduce the experiments

Requires a C++17 compiler and Python with NumPy and Matplotlib.

Linux/macOS, from this folder:

```sh
g++ -std=c++17 -O3 -ffp-contract=off experiments/heat_serial.cpp -o experiments/heat_serial
python3 experiments/run_experiments.py
```

Windows PowerShell, from this folder:

```powershell
g++ -std=c++17 -O3 -ffp-contract=off experiments/heat_serial.cpp -o experiments/heat_serial.exe
python experiments/run_experiments.py
```

The Python script independently checks the full-grid verification error against the exact discrete sine-mode amplitude and checks both error-norm normalizations. The full-grid solution, not the modal formula, supplies the reported convergence table. Round-off data are direct double-precision quotients, and their last digits can vary with the platform's math library.

## Compile the report

```sh
pdflatex -interaction=nonstopmode -halt-on-error Methode_Numerique_Tasks_Solutions.tex
pdflatex -interaction=nonstopmode -halt-on-error Methode_Numerique_Tasks_Solutions.tex
```

For Overleaf, upload all TeX files plus the `figures/` and `tables/` directories, and select `Methode_Numerique_Tasks_Solutions.tex` as the main document. The entire source archive can also be uploaded. Use pdfLaTeX.

## Before submitting

Add your name/team details if your professor requires them. The document acknowledges AI assistance. Section 12 of the supplied project specification requires the **complete prompts and responses**, team-member identity, tool/model, and date/time in a separate `llm_log/` submission. Export this complete conversation and include it with your course submission; the assistance acknowledgement is not a replacement for those logs. This document does not claim that a complete conversation export has already been created or that the remaining MPI project has been completed.

No real cluster timings or MPI results are claimed in this report. The requested numerical-method experiments were run locally.
