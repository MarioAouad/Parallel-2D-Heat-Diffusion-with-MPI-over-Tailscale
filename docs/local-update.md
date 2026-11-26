# Git and VM workflow

A commit saves a version locally, a push publishes it to GitHub, and a pull
receives it in another checkout. The published Parts 0/1 delivery includes the
reviewed Ubuntu study, analysis, checklist and written background solutions.

## Receive updates on Ubuntu

On heat-1 as `mpi`:

```bash
cd /home/mpi/heat-project-repo
git status --short
git pull --ff-only origin main
make serial
make verify-setup
make verify-results
make verify-part1-results
```

If local changes block the pull, preserve them and resolve the conflict before
continuing. Do not discard work to force an update. The three verification
targets inspect archived evidence without collecting new measurements.

`make check-serial` runs solver correctness checks. `make verify-part1` creates
a fresh timestamped study if needed. The completed study is already in Git;
rerunning it is optional.

For cluster work, update every VM to the same commit and run `make` on each.
Keep the checkout at `/home/mpi/heat-project-repo` on all three.
Git transfers source; each VM compiles its own executables.

## Save and publish later changes

In the repository on the computer where you edited the files:

```bash
git status --short
git diff
git add <reviewed-file-or-folder>
git diff --cached --stat
git diff --cached
git commit -m "Describe the completed change"
git push origin main
```

Replace the angle-bracket placeholder with the paths you reviewed. Include the
corresponding interaction-log entry. Keep private configuration, original transfer
archives, full private conversations and generated binaries out of public commits;
the ignore rules cover their documented locations.

Wait for a successful push before pulling on the VMs. Current source and delivery
files come from Git; old local transfer bundles are historical artifacts.
Parts 2 and 3 are implemented. Use the [Parts 2/3 rerun guide](parts2-3-rerun.md)
for remote updates, fresh retained-field evidence, P=8 and the return bundle.
For a separate performance run, follow the [Part 4 VM instructions](../part4/RUN.md). The updater builds the solvers and the ping-pong calibration program.
