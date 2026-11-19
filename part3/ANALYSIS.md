# Part 3: block decomposition, correctness argument and the two report questions

## Outcome and provenance

**Status: implementation complete; cluster evidence pending.** No Part 3 measurement has
been recorded yet. The [results index](results/README.md) will link the reviewed study.
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

*Pending the cluster study.* `run_experiments.py --cluster` will produce `timing_summary.csv`
and `timing.png`. That stage runs Case 1, 10 steps, with no output file, for P = 4 and 6
and N = 512, 2048, 8192, with three interleaved repetitions of strips and blocks. This
section will compare the medians and spread with the table above and explain any
disagreement.

## Correctness results

*Pending the cluster study.* This section will report:

- byte-identical comparisons for P = 1, 2, 3, 4, 6, with the 2×2 and 3×2 grids;
- uneven blocks;
- the machines used;
- the 2×2 and 3×2 debug transcripts;
- the blocks-computed Case 1/2 fields.
