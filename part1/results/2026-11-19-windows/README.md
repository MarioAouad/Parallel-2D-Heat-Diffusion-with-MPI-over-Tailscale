# Reviewed local serial study

Generated on 19 November 2026 with the final Part 1 interface, on Windows x86_64.
Compiler: MSYS2 GCC 13.2.0. Build command, from the repository root:

```text
g++ -std=c++17 -O2 -ffp-contract=off -Wall -Wextra -Wpedantic part1/heat_serial.cpp -o build/heat.exe
python part1/verify_serial.py --exe build/heat.exe
python part1/run_experiments.py --exe build/heat.exe --out part1/results/2026-11-19-windows
```

All six correctness test groups passed. The study checked the full grid against
the independent discrete sine eigenmode and recovered the expected second-order
accuracy. Both stable cases respected [0,1]; the r=0.2625 experiment developed
growing checkerboard oscillations. The PNG figures were visually inspected.

`convergence.csv` and `instability.csv` are computed evidence. `raw_runs.json`
stores every command, stdout, stderr and return status. `metadata.json` records
the source hash and platform. Generated binary files are full little-endian grid
snapshots, without headers. They are kept locally and ignored by Git; rerunning
the experiment script recreates them. The image panels may have different colour scales.

This directory is preserved. Generate new experiments in a new output directory.
Timings here are incidental local values, not controlled VM performance data.
