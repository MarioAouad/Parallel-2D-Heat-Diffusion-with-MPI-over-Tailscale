# Part 3: block decomposition, correctness argument and the two report questions

## Outcome and provenance

**Status: complete.** The [reviewed cluster study](results/2026-11-19-cluster/) of
19 November 2026 gives 90/90 block fields byte-identical to serial on two or three VMs
(P = 1, 2, 3, 4, 6; grids up to 3×2). It also gives a three-repetition strips-vs-blocks
timing check. The results are in the last two sections.

Before any MPI run, the block logic was checked by an exact Python emulation of:

- `MPI_Dims_create`;
- the 2D split;
- the four-direction exchange without corners;
- the subarray gather.

The emulation produced 102/102 fields byte-identical to an emulated serial loop (Cases 1,
2, V; N = 4–17; P = 1, 2, 3, 4, 6, 8, 9). It is not evidence about the C++ or MPI.

## Decomposition

`MPI_Dims_create(P, 2)` gives a Py×Px grid with Py ≥ Px and the factors as close as
possible: 1×1, 2×1, 3×1, 2×2, 3×2 and 4×2 for P = 1, 2, 3, 4, 6, 8. Rank (cy, cx) owns
interior rows `split(cy, Py)` and columns `split(cx, Px)`. Here `split` is the Part 2
rule: contiguous ranges, with the first (N−1) mod parts ranges one longer. For Px = 1 the
grid is exactly the Part 2 strips layout. The study's `decomposition.png` shows N=9 on
2×2 and N=10 on 3×2, with one block's ghost layer and its four unexchanged corners.

## Why the output is bit-for-bit identical to serial

The argument is the same as for strips. The update of node (i, j),

$$
u^{n+1}_{i,j}=u^n_{i,j}+r\left(\bigl((u^n_{i-1,j}+u^n_{i+1,j})+u^n_{i,j-1}\bigr)+u^n_{i,j+1}-4u^n_{i,j}\right),
$$

reads only the node and its four axis neighbours at level n. After the exchange, each
neighbour of an owned node is one of three things:

- owned by the same block;
- in a ghost row (up/down neighbour) or ghost column (left/right neighbour), copied from the adjacent block;
- a fixed boundary value.

The stencil expression and compiler flags are those of the serial code. Each node
therefore undergoes identical IEEE-754 operations on identical inputs. No diagonal value
is ever read, so the corner ghosts can hold anything without changing the result.

## Question 1: why are corner ghosts not needed?

The five-point stencil's neighbours of (i, j) are (i±1, j) and (i, j±1). Take the
bottom-left owned node of a block, at local (1, 1). Its neighbours are the local cells (0, 1), (2, 1), (1, 0) and (1, 2):

- (0, 1) is in the bottom ghost **row**;
- (1, 0) is in the left ghost **column**;
- (2, 1) and (1, 2) are owned.

The local corner (0, 0) is the *diagonal* neighbour (i−1, j−1). No five-point update reads
it. So the row exchange only needs the `cols` owned values, the column exchange only the
`rows` owned values, and the four corner ghosts are never sent (the ✕ marks in the
decomposition figure). The debug transcripts print them as `-`.

**A stencil that would need them.** Any stencil with diagonal weights. Examples:

- the compact nine-point Laplacian, (4·axis + diagonals − 20·centre)/(6h²);
- a discretisation of a mixed derivative u<sub>xy</sub>, as in an anisotropic or rotated diffusion tensor;
- a 3×3 smoothing or averaging stencil.

Corners would then have to be filled. A common way is to exchange columns first and then
send rows of `cols+2` values that include the freshly received ghost columns. That carries
each diagonal value in two hops without extra messages. The alternative is four extra
diagonal messages per step, which on this network would cost four more latencies.

## Question 2: strips or blocks? Prediction from Task 8.2 with the measured t<sub>s</sub>, t<sub>w</sub>

Model (background Task 8.2(c), boundary-aware form): per step, each rank performs one
exchange per existing neighbour, costing t<sub>s</sub> + m·t<sub>w</sub> for m doubles.
The step takes as long as the busiest rank:

$$
T_{\text{strips}} = \min(2,P-1)\,\bigl(t_s+(N+1)\,t_w\bigr),\qquad
T_{\text{blocks}} = \min(2,P_y-1)\left(t_s+\tfrac{N-1}{P_x}t_w\right)+\min(2,P_x-1)\left(t_s+\tfrac{N-1}{P_y}t_w\right).
$$

The busiest P = 4 block (2×2) has 2 neighbours and sends N/2 values to each. A middle
strip also has 2 neighbours but sends N values to each. Blocks therefore have the same
latency count and half the data. At P = 6 (3×2) and P = 8 (4×2), a middle block has 3
neighbours against 2 for a strip: one more latency, but less data.

Inputs come from the Part 0 summary. t<sub>w</sub> is per double, i.e. 8 bytes divided by the fitted bandwidth:

| Link | t<sub>s</sub> | t<sub>w</sub> per double |
| --- | ---: | ---: |
| same VM (heat1-local) | 0.258 µs | 0.0013 µs |
| heat1–heat2, best cross-VM | 17.7 ms | 53.0 µs |
| heat2–heat3, worst cross-VM | 77.6 ms | 82.6 µs |

Predicted communication per step, strips / blocks (ms), and the predicted winner:

| P (grid) | N | same VM | heat1–heat2 | heat2–heat3 |
| --- | ---: | --- | --- | --- |
| 4 (2×2) | 512 | 0.0019 / 0.0012 → **blocks** | 89.8 / 62.5 → **blocks** | 240 / 197 → **blocks** |
| 4 (2×2) | 2048 | 0.0059 / 0.0032 → **blocks** | 253 / 144 → **blocks** | 494 / 324 → **blocks** |
| 4 (2×2) | 8192 | 0.022 / 0.011 → **blocks** | 904 / 469 → **blocks** | 1508 / 832 → **blocks** |
| 6 (3×2) | 512 | 0.0019 / 0.0017 → blocks | 89.8 / 89.3 → tie | 240 / 289 → **strips** |
| 6 (3×2) | 2048 | 0.0059 / 0.0043 → blocks | 253 / 198 → **blocks** | 494 / 458 → blocks |
| 6 (3×2) | 8192 | 0.022 / 0.015 → **blocks** | 904 / 632 → **blocks** | 1508 / 1135 → **blocks** |
| 8 (4×2) | 512 | 0.0019 / 0.0016 → blocks | 89.8 / 87.0 → tie | 240 / 286 → **strips** |
| 8 (4×2) | 2048 | 0.0059 / 0.0041 → blocks | 253 / 189 → **blocks** | 494 / 444 → blocks |
| 8 (4×2) | 8192 | 0.022 / 0.014 → **blocks** | 904 / 596 → **blocks** | 1508 / 1078 → **blocks** |

What the model predicts:

- **P = 4: blocks always win.** They have the same number of messages as strips and half
  the data, so the bandwidth term halves.
- **P = 6 and 8: it depends on t<sub>s</sub>/(N t<sub>w</sub>).** From Task 8.2, an interior
  4×2 block beats a middle strip only when t<sub>s</sub> < 0.75 N t<sub>w</sub>. Large N
  favours blocks. At N = 512 on the high-latency heat2–heat3 link, the extra message makes
  strips win.
- **The ranking is a secondary effect.** The difference is at most a factor of about 2,
  while either layout over Tailscale is 100–10 000× slower than the computation it
  replaces (see Part 2). Both are dominated by latency.

These predictions rest on one Part 0 sweep per pair. The fitted bandwidths are very low
(0.09–0.14 MiB/s) and were measured partly while routes changed. Real messages of 4–64 KiB
may move faster. If they do, t<sub>w</sub> shrinks, latency weighs relatively more, and
the 3-neighbour layouts lose some of their advantage. The measured check will show which
regime applies.

**P = 8 cannot be measured.** The cluster has six slots (3 VMs × 2 vCPUs), and the
assignment forbids running more processes than vCPUs. P = 8 is answered by the model
only; P = 6 (3×2) is measured instead, since it has the same 3-neighbour structure.

## Then check: measured strips vs blocks

Setup: Case 1, 10 steps, no output file, P = 4 and 6, N = 512, 2048 and 8192. There were
three repetitions. Within each repetition, strips and blocks ran back to back, so each
pair saw similar network conditions. Every run used all three VMs. Placement was
`--map-by node`, so in both layouts every neighbour pair is on different VMs. The data is
in `timing_summary.csv`, `timing.csv` and `timing.png`.

Halo exchange per step, as the median of 3 in ms, with min–max in brackets. The last
column counts how many of the 3 paired repetitions each layout won:

| P (grid) | N | strips | blocks | paired wins | predicted (heat1–heat2 / heat2–heat3) |
| --- | ---: | ---: | ---: | --- | --- |
| 4 (2×2) | 512 | 344 (165–771) | 1159 (186–1537) | strips 3/3 | blocks / blocks |
| 4 (2×2) | 2048 | 2305 (600–3162) | 2630 (1051–3614) | strips 3/3 | blocks / blocks |
| 4 (2×2) | 8192 | 5739 (3074–9243) | **2485** (2152–5731) | blocks 3/3 | blocks / blocks |
| 6 (3×2) | 512 | 1283 (791–2678) | 1492 (964–1648) | strips 2/3 | tie / strips |
| 6 (3×2) | 2048 | 2793 (2029–3911) | 2959 (2255–3859) | strips 2/3 | blocks / blocks |
| 6 (3×2) | 8192 | 8580 (6707–10868) | **5611** (4932–9769) | blocks 3/3 | blocks / blocks |

Computation took at most 0.35 s per step in any run. Communication was at least **98.1 %**
of every run's time.

**Where the prediction holds: N = 8192.** Blocks won all six paired repetitions. Their
median exchange was 2.3× faster at P = 4 and 1.5× faster at P = 6. This is the
bandwidth-dominated regime: blocks send N/P<sub>x</sub> or N/P<sub>y</sub> values per
message, not N.

**Where it fails: N = 512 and 2048.** Strips won 10 of 12 paired repetitions, including
all six at P = 4, where the model said blocks win for every N. So the measured
crossover sits between N = 2048 and N = 8192. The spread is wide: within one layout,
repetitions differ by up to 4.7×. Three repetitions over home Wi-Fi cannot fix the
crossover point. However, the direction at small N is consistent across the pairs, so
it is not just noise.

**Why the model is wrong at small N.** The Task 8.2 model counts *messages per rank*.
That is 2 for a middle strip and 2 for a 2×2 block, hence "same latency, half the data".
The code instead exchanges in blocking `MPI_Sendrecv` *phases*, which run in sequence:

- strips: rows up, then rows down;
- blocks: rows up, rows down, columns right, columns left.

In a 2×2 grid, each rank's row neighbour is reached in two phases: one send-only, then
one receive-only after the neighbour's own phase finishes. The column phases only start
after the row phases finish. So the critical path holds about four latencies per step
for blocks, against two for strips. The extra 2t<sub>s</sub> is 35–155 ms on these links.
At N = 512 the payload term is tiny (2–4 KiB per message), so the extra latencies
decide the result. At N = 8192 the halved payload outweighs them.

**Why both layouts are slower than predicted.** At N = 8192, strips at P = 4 measured
5.7 s per step against the model's worst-link 1.5 s. Part 0 measured one message at a
time on an idle link. Here, every rank sends at once, and two ranks share each VM's home
connection. The *total* bytes per step therefore matter as well. Blocks move fewer:
(P<sub>y</sub>−1)+(P<sub>x</sub>−1) cut lines against P−1, which is 2 against 3 at
P = 4 and 3 against 5 at P = 6. This also fits blocks winning at large N.

The two explanations above are consistent with the data but were not tested separately.
Two experiments would test the phase explanation:

- an Isend/Irecv version that posts all four exchanges at once (the optional overlap);
- the Part 4 study, with more repetitions.

**Answer for the report.** On this cluster:

- strips are better for small grids (N ≤ 2048 at P = 4 and 6);
- blocks are better for large grids (N = 8192), by 1.5–2.3×.

The busiest-rank model predicts the large-N winner. It misses the small-N winner because
it ignores how the exchange phases are ordered. For P = 8 (4×2, model only), the same
reasoning gives the same pattern. 4×2 blocks still have four sequential phases and three
or four neighbours, so strips should win at small N and blocks at large N. Measuring the
crossover would need eight real vCPUs.

## Correctness results

From the [cluster study](results/2026-11-19-cluster/) (launched from heat-3, Open MPI 4.1.6):

- **6 correctness groups OK** on heat-3 (`console/check-blocks.txt`).
- **90/90 comparisons byte-identical to serial**, with matching steps, r, dt, T, minimum,
  maximum and Case V error norms. They cover Cases 1, 2 and V, N = 8, 9, 10, 17, 64, 101,
  and P = 1, 2, 3, 4, 6, i.e. grids 1×1, 2×1, 3×1, 2×2 and 3×2.
- **Uneven blocks:** 48 rows have N−1 not divisible by P<sub>y</sub> or P<sub>x</sub>,
  e.g. N = 8 on 3×2 gives rows 3/2/2 and columns 4/3.
- **Machines:** every P = 2 run used 2 VMs and every P = 3, 4 or 6 run used all 3.
  That makes 72 multi-machine runs, so every row and column ghost crossed the network.
- **Halo transcripts** (`debug_halo.txt`, Case 1, N = 8, one step, 2×2 and 3×2):
  - every ghost row and ghost column equals the neighbour's owned values;
  - plate-edge ghosts hold the fixed boundary value 1;
  - corners print as `-`.
- **Fields** (`cases.png`, 3×2, N = 64, 500 steps): Case 1 and Case 2 computed by blocks
  are byte-identical to serial, symmetric, within [0, 1], with no seam at block edges.
- **Provenance:** the source hashes in `metadata.json` equal the committed
  `heat_serial.cpp`, `heat_mpi.cpp` and `heat_blocks.cpp`.

Checkpoint C3's correctness part is therefore met. The Part 4 performance runs remain.
