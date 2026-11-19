# Part 0: understand the cluster before the heat solver

## What changes at each step?

1. **Setup:** Ubuntu gives us the same Linux software environment on all three computers. Tailscale gives each VM a reachable private address across different homes.
2. **Connectivity:** `tailscale ping` checks an overlay path and reports direct/relay observations. Ordinary SSH checks that a remote shell starts without passwords or host-key prompts.
3. **Hostname launch:** `mpirun` starts six independent instances of the ordinary `hostname` utility. Two hostnames per VM demonstrate launch/placement. This is not yet a program calling MPI message routines.
4. **MPI hello:** six copies of our C++ program initialize MPI, discover their rank/size/host, and perform a collective sum. A shared `rank_sum=15` checks actual MPI communication.
5. **Ping-pong:** exactly two copies exchange buffers back and forth. We measure average round-trip time at each payload size. Three local baselines and all three VM pairs isolate configurations.
6. **Analysis:** a normal Python process reads saved CSVs, checks them, fits a communication-cost model and draws plots. The VMs need not be connected while analyzing archived data.

These are different questions. A reachable VM may still reject SSH. Working SSH may still leave MPI advertising an unreachable NAT address. A successful MPI message can still be expensive. A communication benchmark does not prove a heat solver's numerical correctness.

## What is parallel right now?

`mpirun` starts processes, each with its own variables and memory. All execute the same program; `MPI_Comm_rank` tells each which branch to take. Hello has six ranks; ping-pong has two. We have **not split a temperature grid** yet. The later strip/block solvers will give different subsets of that grid to different ranks.

## Coordinator versus workers

The coordinator is whichever VM runs the launcher. It asks SSH to start remote processes and saves their forwarded output. Rank zero is the first application endpoint selected by a benchmark case; it can be on another VM. For `heat2-heat3`, heat-1 coordinates while the timed buffers travel between heat-2 and heat-3. That is why all result files can reside on heat-1 even when heat-1 did not carry the timed payload.

## What is already demonstrated?

Part 0 technical work is complete. Three timestamped inventories, all six directed
SSH connections, six-process hostname placement, and a successful six-rank MPI
hello are verified. The fresh hello on 19 November at 15:34:24 UTC confirms the
organized checkout can run across the three VMs. The original full-run export
contains successful ping-pong logs and correct hosts for all six configurations.
The [closeout record](../docs/part0-closeout.md) keeps the earlier failed checks
and the subsequent successful recheck, rather than replacing the history.

The archived CSVs reproduce the communication analysis. Hardware/version and
terminal evidence are now also recorded. Complete earlier AI transcripts remain
a separate private course-submission requirement.

Continue with [setup](00-cluster-setup/README.md), then follow the numbered folders. For the assignment status, use [deliverables](../docs/deliverables.md).
