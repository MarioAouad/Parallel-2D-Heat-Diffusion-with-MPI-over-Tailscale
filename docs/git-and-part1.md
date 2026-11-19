# Save the checkpoint and begin Part 1

Make one checkpoint before the Ubuntu serial study. The current working copy
already contains the completed Part 0 records and the Part 1 serial solver, so
the commit records both. Only the coordinator needs to push these local changes.

| Action | Meaning |
| --- | --- |
| Commit | Save a named version in the local Windows Git repository |
| Push | Upload the committed version to GitHub |
| Pull | Bring the GitHub version into a VM checkout |

## 1. Windows: choose the files

Open PowerShell in the repository folder containing Makefile, part0 and part1.

```powershell
git status --short
git add .
git diff --cached --stat
```

The staged files should contain code, guides, public interaction index and
reviewed public results. The checked ignore policy excludes build artifacts,
private originals/transcripts/configuration, transfer archives and reproducible
binary fields. Both Part 1 Python files belong in the commit. Complete private
course records still belong in the private hand-in, even though excluded from
public GitHub publication.

## 2. Windows: save and upload

After reviewing the staged file list:

```powershell
git commit -m "Complete Part 0 and add serial heat solver"
git push origin main
```

Wait for push success before pulling on a VM. If a command fails, retain its
output and resolve that error first. These instructions do not themselves
perform a commit or publication.

## 3. Heat-1 Ubuntu: receive and compile

Part 1 uses a single process on one VM; the other team members need not run the
same serial study simultaneously. On heat-1 as mpi:

```bash
cd /home/mpi/heat-project-repo
git status --short
git pull --ff-only origin main
make serial
```

The pull receives the committed source. The build compiles C++17 locally into
build/heat; a Windows executable is not transferred through Git. If Git reports
local source changes that prevent the pull, preserve that output and resolve it
before continuing. The private local cluster configuration remains ignored.

## 4. Heat-1 Ubuntu: one small verification run

```bash
./build/heat --decomp serial --case V --N 16 --r 0.2 --T 0.05
```

V uses a known exact solution for comparison. N=16 means 16 intervals along
each direction, so the full stored grid has 17 by 17 nodes. r=0.2 gives a stable
time step, and T=0.05 is the final simulated time. Expect steps=64 and small
nonzero errors: roughly err_inf=0.00166337 and err_l2=0.000831685. This is a
finite-difference approximation; the later convergence study checks how the
errors shrink when the grid is refined.

Inspect this output and understand initialization and the two-buffer update
before proceeding through the [full serial correctness/study guide](../part1/README.md).
