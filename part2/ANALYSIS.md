# Part 2: strip decomposition, correctness argument and expected cost

## Outcome and provenance

**Status: implementation complete; cluster evidence pending.** No Part 2 result has
been recorded yet. The [results index](results/README.md) will link the reviewed C2
study once it has been run on the VMs. Until then, this document gives only the design,
the correctness argument and a *model prediction* built from the archived Part 0 and
Part 1 measurements. It contains no measured Part 2 numbers.

Before any MPI run, the decomposition logic was checked by an exact Python emulation
of the row split, ghost layout, two-shift exchange and gather. It produced 96/96 fields
byte-identical to an emulated serial loop (Cases 1, 2, V; N = 3–24; P = 1–7, including
uneven strips). This emulation is not evidence about the C++ or the MPI library.

## Decomposition

The (N+1)×(N+1) grid keeps its row-major layout. The N−1 interior rows are cut into
P contiguous strips (assignment section 6.1):

$$
n_p=\left\lfloor\frac{N-1}{P}\right\rfloor+[\,p<(N-1)\bmod P\,],\qquad
j^{\text{first}}_p = 1+p\left\lfloor\frac{N-1}{P}\right\rfloor+\min\bigl(p,(N-1)\bmod P\bigr).
$$

Rank p stores n<sub>p</sub>+2 rows: its owned rows plus one ghost row below and above.
For rank 0 and rank P−1 the outer ghost row *is* the plate's Dirichlet row (j=0 or
j=N). It is filled once and never overwritten, because the matching neighbour is
`MPI_PROC_NULL`. The run's `decomposition.png` figure shows the layout for
N=9, P=3 (strips of 3, 3, 2 rows) and N=10, P=4 (3, 2, 2, 2).

## Why the output is bit-for-bit identical to serial

The explicit update for an interior node,

$$
u^{n+1}_{i,j}=u^n_{i,j}+r\left(\bigl((u^n_{i-1,j}+u^n_{i+1,j})+u^n_{i,j-1}\bigr)+u^n_{i,j+1}-4u^n_{i,j}\right),
$$

reads only level-n values from the node and its four neighbours. After the halo
exchange, every rank holds exactly those level-n values for each of its owned nodes:

- the nodes in its own rows;
- the neighbour's edge row, in the ghost row;
- or the fixed boundary row.

The C++ expression, the parenthesisation and the compiler flags (`-O2 -ffp-contract=off`)
are the same as in the serial reference. Each node therefore undergoes identical IEEE-754
operations on identical inputs, so its result is identical. By induction over the steps,
the whole field matches bit for bit for every P, and the gathered file is the same file.

The same argument covers the V-case error norms. They are computed on rank 0 from the
gathered field in the serial loop order, so the reduction order does not change.
Minimum and maximum are combined with `MPI_MIN`/`MPI_MAX`, which involve no rounding.

What the argument needs, and what the tests check (see [DELIVERY.md](DELIVERY.md)):

1. the strips tile rows 1..N−1 exactly once (row-size test, gather offsets);
2. every ghost row equals the neighbour's current edge row before each update (debug test);
3. the boundary rows stay fixed in both buffers (`MPI_PROC_NULL` and initial copy);
4. no rank uses a level-(n+1) value during step n (two arrays and a swap, as in Part 1).

## Halo exchange and deadlock

Each step performs two `MPI_Sendrecv` shifts: top rows up / bottom ghosts from below,
then bottom rows down / top ghosts from above. Every rank takes part in both shifts at the
same time, so all neighbour pairs communicate in parallel and the exchange costs
about two message times whatever P is. Sending rows directly from the array works
because a row is contiguous: one message of N+1 doubles, with no packing.

A naive "blocking `MPI_Send` up, then `MPI_Recv`" works only while messages fit the
eager protocol. Above the eager limit `MPI_Send` waits for the matching receive.
Every rank waits in its send for a neighbour that is also waiting in its send, so
the program deadlocks. This explains "works for small N, hangs for large N". The
[README](README.md#why-a-blocking-send-then-recv-exchange-can-deadlock-report-question)
gives the Open MPI limits to check. `MPI_Sendrecv` progresses the send and the receive
together, so it cannot deadlock this way.

## Expected cost: a prediction from Part 0 and Part 1 data

Per step, a middle strip computes about (N−1)²/P updates and exchanges two rows of
8(N+1) bytes. With the Part 0 message model t<sub>msg</sub>(m)=t<sub>s</sub>+m/B and the
paired-exchange convention of background Task 8.2(c):

$$
T_P \approx c\,\frac{(N-1)^2}{P} + 2\left(t_s+\frac{8(N+1)}{B}\right).
$$

Inputs come from archived evidence, not Part 2 runs:

- c ≈ 1.2 ns per node update, from the incidental Part 1 loop timings on heat-1
  (1.0–1.3 ns over the five convergence grids);
- t<sub>s</sub> and B come from the Part 0 summary table.

| N | serial step | link (Part 0) | modelled comm / step | modelled P=4 step | modelled speed-up |
| ---: | ---: | --- | ---: | ---: | ---: |
| 512 | 0.31 ms | same VM, t<sub>s</sub>=0.26 µs, 5830 MiB/s | 0.002 ms | 0.08 ms | 3.9 |
| 512 | 0.31 ms | heat1–heat2, t<sub>s</sub>=17.7 ms, 0.144 MiB/s | 90 ms | 90 ms | 0.003 |
| 2048 | 5.0 ms | same VM | 0.006 ms | 1.26 ms | 4.0 |
| 2048 | 5.0 ms | heat1–heat2 | 253 ms | 254 ms | 0.02 |
| 8192 | 81 ms | same VM | 0.02 ms | 20 ms | 4.0 |
| 8192 | 81 ms | heat1–heat2 | 904 ms | 924 ms | 0.09 |
| 8192 | 81 ms | heat2–heat3, t<sub>s</sub>=77.6 ms, 0.092 MiB/s | 1508 ms | 1528 ms | 0.05 |

What the model predicts:

- **Within one VM**, communication is negligible, and strips should approach ideal speed-up,
  limited in practice by the VM's two vCPUs and memory bandwidth.
- **Across VMs over Tailscale**, the halo exchange dominates for every grid in the assignment.
  The model predicts that spreading strips over machines makes each step tens to hundreds of
  times slower than one process.
- **Communication shrinks only relative to computation.** The ratio
  T<sub>comm</sub>/T<sub>comp</sub> ≈ 2P(t<sub>s</sub>+8N/B)/(cN²) falls as N grows.
  With these latencies it stays above 1 even at N=8192.

These numbers are an extrapolation. The Part 0 bandwidths came from one sweep per pair,
partly while routes changed between relay (DERP) and direct, and Part 1 timings were never
intended as performance data. Part 4 must measure t<sub>comm</sub> and t<sub>comp</sub>
directly (the solver already reports both, as maxima over ranks) and confront this model.

**Practical consequence for C2.** One cross-VM step costs roughly 0.1–0.5 s, so the
default comparison uses few steps (20 for Cases 1/2, T=0.002 for V). Correctness
needs only enough steps for information to cross several strip boundaries.

## Results

*Pending.* After the reviewed cluster study, this section will report:

- the number of identical comparisons and the P and N covered;
- the number of machines used per run;
- the halo-debug transcripts for P=2 and P=3;
- the strips-computed Case 1/2 fields.
