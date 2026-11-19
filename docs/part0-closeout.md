# Part 0 closeout: evidence reviewed on 19 November 2026

## Current status: Part 0 technical work complete

The final recheck closes both earlier problems. Heat-2's 15:30:12 UTC capture
passes SSH to both peers. The 15:34:24 UTC MPI hello has ranks 0-5, size=6 and
rank_sum=15, two ranks per VM. With the earlier four SSH successes, three
inventories, hostname placement and six measured ping-pong sweeps, all Part 0
technical requirements are demonstrated. The next task is Part 1 on Ubuntu.

Public recheck records and hashes are in
`part0/results/setup/2026-11-19-recheck/`. The original tar.gz is retained
privately. Both archives preserve the old failures; current status uses the
latest timestamped capture for each check, including a failure if it is latest.

```bash
make verify-setup
make verify-results
```

Both pass. To reproduce the initial failure assessment, use
`python3 part0/05-analysis/verify_setup.py --initial-only` (expected exit 1).
The repair/collection steps below document the completed process; no repeat
of them or the hours-long full benchmark is required to begin Part 1.

## Initial archive: historical failures, now repaired

The supplied archive contains all eight requested text files. It is intact, but
**the saved checks do not yet pass the complete Part 0 setup checklist**.
Original bytes are retained in the ignored private course archive. Public copies
under `part0/results/setup/2026-11-19/` replace network identifiers and the third
node's real hostname; their manifest records original and public SHA-256 hashes.

| Check | Saved result |
| --- | --- |
| Three VM inventories | PASS: Ubuntu 24.04.5, Open MPI 4.1.6, two vCPUs each; timestamped records on all nodes |
| SSH from heat-1 to heat-2 and heat-3 | PASS |
| SSH from heat-3 to heat-1 and heat-2 | PASS |
| SSH from heat-2 to heat-1 and heat-3 | FAIL: unknown ED25519 host keys rejected by strict checking |
| Six-process hostname | PASS: each VM appears twice |
| Six-rank MPI hello | FAIL at 14:46:55 UTC: third VM could not enter `/home/mpi/heat-project-repo`; two ranks failed to start |
| Original ping-pong study | PASS: all six original sweeps / 132 rows remain verified |

The third VM's inventory/connectivity capture was later, at 14:51:47 UTC. It is
possible that its checkout was prepared after the failed hello run. The later
successful hello now closes that item; the old failure is kept.
Successful `hostname` launch does not prove an application working directory or
MPI executable exists: `hostname` is a system command.

## 1. Record host keys on heat-2

On **heat-1 and heat-3**, run in Ubuntu and share each fingerprint with the owner
of heat-2 through your existing team communication:

```bash
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

On **heat-2**, run:

```bash
cd /home/mpi/heat-project-repo
source part0/config/cluster.sh
ssh "$MPI_USER@$HEAT1_IP" 'hostname; whoami'
ssh "$MPI_USER@$HEAT3_IP" 'hostname; whoami'
```

Compare the displayed fingerprints with the values from the destination VMs,
then accept each matching host key. A login by hostname may have been accepted
previously while the IP address used by the scripts is still unknown to SSH.
If a password is required, install heat-2's existing public key with
`ssh-copy-id "$MPI_USER@$HEAT1_IP"` and/or the corresponding HEAT3_IP command.
Then repeat the ordinary SSH commands and confirm they need no password.

## 2. Ensure the same checkout path on all VMs

On **each VM as mpi**, including heat-3:

```bash
cd /home/mpi
if [ ! -d /home/mpi/heat-project-repo ]; then
    git clone https://github.com/MarioAouad/Parallel-2D-Heat-Diffusion-with-MPI-over-Tailscale.git /home/mpi/heat-project-repo
fi
cd /home/mpi/heat-project-repo
make
pwd
test -x build/mpi_hello && echo 'MPI hello executable ready'
```

The final two checks must show `/home/mpi/heat-project-repo` and the ready message.
If an existing directory is inaccessible, inspect `ls -ld /home/mpi/heat-project-repo`
before making ownership changes. This clone obtains the currently published
code; the Part 1 changes prepared locally in this review are distributed in the
separate update bundle, not assumed to exist on GitHub.

## 3. Save fresh checks

Run on **each VM**. Configure `part0/config/cluster.local.sh` first if it is missing.

```bash
cd /home/mpi/heat-project-repo
set -o pipefail
mkdir -p ~/heat-evidence
stamp=$(date -u +%Y%m%dT%H%M%SZ)
bash part0/01-connectivity/check_cluster.sh 2>&1 |
    tee "$HOME/heat-evidence/connectivity-$(hostname)-$stamp.txt"
```

After every directed SSH check succeeds, run **only on heat-1**, with all VMs ready:

```bash
cd /home/mpi/heat-project-repo
set -o pipefail
stamp=$(date -u +%Y%m%dT%H%M%SZ)
bash part0/03-mpi-hello/run_hello.sh 2>&1 |
    tee "$HOME/heat-evidence/hello-$stamp.txt"
```

Require six lines with ranks 0 through 5, `size=6`, `rank_sum=15`, and two ranks
on each VM. Collect the new text files as before and export a new archive named
`heat-part0-recheck.tar.gz`. Keep the earlier failed records and original full
ping-pong study. No new hours-long full benchmark is needed to fix these errors.

## 4. Collect and send the new results

Only the new heat-2 connectivity and heat-1 hello records are needed to check
the outstanding failures. On **heat-1 Ubuntu**, after saving the new hello:

```bash
cd /home/mpi/heat-project-repo
source part0/config/cluster.sh
review="$HOME/heat-recheck-$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$review/heat-1" "$review/heat-2"
cp "$HOME"/heat-evidence/hello-*.txt "$review/heat-1/"
scp "$MPI_USER@$HEAT2_IP:/home/mpi/heat-evidence/connectivity-*.txt" "$review/heat-2/"
tar -czf "$HOME/heat-part0-recheck.tar.gz" -C "$review" .
```

This keeps old and new timestamped captures. After both file-copy commands
succeed, download the archive in **Windows PowerShell on the heat-1 laptop**:

```powershell
scp -P 2222 mpi@127.0.0.1:/home/mpi/heat-part0-recheck.tar.gz "$env:USERPROFILE\Downloads\"
```

Tell the assistant that `heat-part0-recheck.tar.gz` is in Downloads; it can be
read locally. Keep the original evidence archive as well. A successful recheck
must show the two previously failed SSH directions and all six MPI hello ranks.

## Route interpretation and remaining course work

The new probes show direct connectivity for heat-1 to heat-2 at that observation;
the other five directed probes report DERP. SSH still succeeds in four directions.
Relay operation explains a route observation, not an SSH host-key error or an
unavailable directory. These observations do not change the routes recorded
during the 17 November performance runs.

`python3 part0/05-analysis/verify_setup.py --initial-only` assesses this original
eight-file snapshot and deliberately exits 1. Default verification instead
checks all preserved records and assesses the latest captures, which now pass.
The fresh success is additional evidence, not a substitution into the old record.

The local repository now includes the Part 1 serial implementation and its
Windows correctness study. Repeat that study on Ubuntu for your checkpoint.
C1 also needs the written numerical-method tasks. Complete earlier AI histories,
team contributions and the final report remain course-submission items.
