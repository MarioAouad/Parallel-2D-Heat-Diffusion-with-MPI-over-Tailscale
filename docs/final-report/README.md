# Final CPU/MPI report

The [final report](final-report.pdf) contains ten main pages and three
appendices. It presents the numerical method, convergence, MPI verification,
scaling results, model and team contributions. The archived
[Part 4 study](../../part4/results/2026-11-24-cluster/) supplies the measured data.

## Rebuild

Use Python with NumPy, Matplotlib, ReportLab and pypdf. Install Arial on Windows
or DejaVu Sans on Linux.

```bash
python3 docs/final-report/build_figures.py
python3 docs/final-report/build_report.py
make verify-delivery
```

Run the commands from the repository root. The builders read the archived
results. They regenerate the compact report figures and append the three
original strong-scaling plots. The report builder checks the ten-page limit
for the main body.

## Show the live heat maps

Start with the [hand-in guide](../deliverables.md#live-demonstration). A second
invocation can demonstrate a different layout, grid size and rank count:

```bash
python3 scripts/run-demo.py --run --N 48 --P 6 --steps 40 --decomp strips
```

The helper prints the new `output/demo-…/cases.png` path. Open it on the
launching VM or copy it to the presentation computer. The folder contains
private run details, so share the heat map and keep the raw record internal.
The [archived Case 1 and 2 heat maps](../../part3/results/2026-11-21-retained-cluster/cases.png)
are available for rehearsal.
