# Copy this local source update to heat-1

For the Git workflow, first [commit and push on Windows, then pull on heat-1](git-and-part1.md).
The steps below are the source-bundle alternative for changes not yet published.
The source bundle `heat-project-update-20261119-v3.tar.gz` contains the
updated Makefile, public documentation/setup evidence, and Part 1 sources and
reviewed numerical results. It excludes `.git`, compiled programs, private
configuration, private course transcripts and reproducible `.bin` snapshots.
Reviewed CSVs, plots and raw command JSON remain included. A hash manifest is inside it.

On Windows, open the `Parallel_Programming` project folder in PowerShell, then:

```powershell
scp -P 2222 .\output\heat-project-update-20261119-v3.tar.gz mpi@127.0.0.1:/home/mpi/
```

Enter the Ubuntu mpi user's password if prompted. On **heat-1 Ubuntu**:

```bash
cd /home/mpi/heat-project-repo
tar -xzf /home/mpi/heat-project-update-20261119-v3.tar.gz -C /home/mpi/heat-project-repo
make serial
make check-serial
make verify-part1
./build/heat --decomp serial --case V --N 64 --r 0.2 --T 0.05
```

The extraction applies source/documentation updates to this checkout. The
private `cluster.local.sh`, existing compiled files and old measurements are
not package targets. Build the native Ubuntu executable locally; the Windows
executable is not included. The new verification run gets a separate timestamped
folder under `part1/results/runs/`. Keep that folder for the checkpoint.

The [Part 0 technical checklist](part0-closeout.md) is now complete: the final
recheck passes all SSH directions and six-rank hello. This bundle includes the
new public evidence and updated verifier, while retaining the failed snapshot.
The next step is the Part 1 Ubuntu study shown above.

The complete private course transcripts remain in the Windows repository's
ignored `llm_log/private/` tree and must be included in the private hand-in.
