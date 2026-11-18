# 3. MPI hello: our first application communication

## Build and run

Run `make` on each VM in the same absolute checkout path, then on one coordinator:

```bash
bash part0/03-mpi-hello/run_hello.sh
```

`mpi_hello.cpp` is the heavily commented version of the successful earlier program. Comments do not change its executable statements. The new launcher uses `build/mpi_hello`; the historical flat-directory executable was `/home/mpi/heat-project/mpi_hello`.

## Follow one process

1. `mpirun` creates six separate processes across the three VMs. All execute `main`.
2. `MPI_Init` initializes MPI inside each already started process.
3. `MPI_Comm_rank` writes its rank, `MPI_Comm_size` writes 6, and `MPI_Get_processor_name` identifies its VM.
4. Each process contributes its own rank to `MPI_Allreduce` with `MPI_SUM`.
5. Every process receives the sum `0+1+2+3+4+5 = 15` and prints it.
6. Every process calls `MPI_Finalize` and exits.

Observed placement with the two-slot order:

| VM | Ranks | Local memory |
| --- | --- | --- |
| heat-1 | 0, 1 | two separate sets of variables |
| heat-2 | 2, 3 | two separate sets of variables |
| heat-3 | 4, 5 | two separate sets of variables |

Each output line should contain `size=6` and `rank_sum=15`, with ranks 0..5 appearing once. The historical output did so. Output lines may arrive in any order.

## How much communication is this?

The Allreduce count argument is **1 integer element per process**. It is not a request for one byte, one Internet packet, or one remote machine. MPI chooses the collective algorithm, which may use several internal messages. We cannot infer an exact network packet count just from the six processes. Printing and runtime startup also have overhead.

This is a functional check, not a latency/bandwidth benchmark. It confirms a real MPI operation produces the expected result; it does not validate temperature calculations or show that adding processes makes a solver faster.

No grid is divided here. Allreduce combines small scalar values. Later decompositions will partition temperature cells and exchange boundary data.

Next: [the ping-pong benchmark](../04-pingpong/README.md).
