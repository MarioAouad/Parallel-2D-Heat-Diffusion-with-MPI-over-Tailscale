# Receive the published Parts 0/1 delivery on Ubuntu

The preferred handoff is Git. The published delivery includes the reviewed
Ubuntu Part 1 results, numerical analysis, delivery checklist and written
background solutions. On heat-1 as mpi:

```bash
cd /home/mpi/heat-project-repo
git status --short
git pull --ff-only origin main
make serial
make verify-setup
make verify-results
make verify-part1-results
```

The three verification targets inspect preserved evidence without collecting
new measurements. `make check-serial` runs the solver correctness checks;
`make verify-part1` creates a fresh timestamped numerical study if needed.

The [Part 1 delivery checklist](../part1/DELIVERY.md) and
[analysis](../part1/ANALYSIS.md) explain what has been verified. Parts 0/1 are
technically complete. The next implementation stage is Part 2 strips.

Earlier source tarballs are retained locally as historical handoff artifacts.
Use Git for the current delivery, including the newly archived Ubuntu files.
Private cluster configuration, full original archives and private course
transcripts remain outside public GitHub publication. Retain complete private
records for the course hand-in.
