# Part 4 measurement and model conventions

For each rank q, let A_q be its exact number of owned interior cells. Let
c_h(N) be measured serial seconds per interior cell per step on its guest h.
We log-interpolate between the five baseline grid sizes, clamping at endpoints
for a smoke/custom grid outside the measured range. The required full grids lie
within that range. This is an empirical isolated-process rate, not a guarantee
that simultaneous ranks have the same cache/memory throughput.

The Task 8.2 model used in the code is:

```text
compute_q = A_q * c_host(q)(N)
exchange_q = sum over actual neighbors j of [ts_link(q,j) + m_qj * tw_link(q,j)]
predicted_seconds_per_step = max_q(compute_q + exchange_q)
```

Strips send N+1 doubles per neighbor; blocks send their owned column count in
each row exchange and owned row count in each column exchange. There are no
diagonal exchanges. Boundary ranks have fewer neighbors and uneven splits use
their exact counts. The model uses the **observed rank-to-guest placement**,
including same-guest edges under map-by-slot and the 4+2+2 allocation. It does
not assume that every halo crosses a VM boundary.

## Communication calibration

The Part 0 `mpi_pingpong` executable is reused, with unchanged source. The full
campaign measures each guest locally with two ranks and all three inter-guest
pairs, three sweeps each. Heat and calibration both use Open MPI's `ob1`,
`btl=tcp,self` and the same interface settings. This deliberately avoids feeding
the old same-VM shared-memory measurements into a forced-TCP model.

Each size's median half-RTT is formed across sweeps. Startup ts is the median of
the four size medians at 8,16,32,64 bytes. The anchored least-squares transfer
slope b in seconds/byte uses the largest three sizes:

```text
b = sum(bytes * (median_oneway - ts)) / sum(bytes^2)
tw_seconds_per_double = 8 * b
```

The default sweep is 8..131072 bytes, covering the largest required halo
(8193 doubles = 65544 bytes). This is a fresh size-relevant supplement to Part
0, not a replacement for its original full 8 B..16 MiB evidence. A wider sweep
can be requested with `--calibration-max-bytes`, up to 16 MiB. Startup is an
estimate from finite-size messages, and half-RTT assumes similar directions.
RMSE and all original samples are retained. A nonpositive slope is flagged as
nonphysical; it is never silently replaced with a plausible bandwidth. Model
generation then fails, preserving data for inspection/recalibration.

## Ratios and limitations

Strong speed-up is serial **heat1** T1(N) divided by the parallel median TP(N).
Efficiency is speed-up/P. MPI P=1 includes MPI loop overhead and need not equal
serial time exactly. The other two serial baselines expose heterogeneous guest
speeds and supply their own model rates. Weak efficiency compares each layout/
placement to its own P=1 weak run. Weak work is held approximately constant in
interior nodes; rounding and min/max ownership are explicitly reported.

Communication share for each run is `t_comm/t_total`. Both are maxima over ranks
from the existing solvers, possibly attained on different ranks. Their component
maxima are not additive, so do not force t_comp+t_comm=t_total or add their medians.

The busiest-rank model omits phase critical paths of blocking Sendrecv,
simultaneous-link contention, packing costs, cache effects and shared guest
bandwidth. Before/after Tailscale status snapshots do not establish the route
throughout each measured run. These are explanations to investigate, not causes
that can be inferred uniquely from one disagreement. Layout order alternates
between repetitions, reducing one ordering bias without eliminating network drift.

The dotted curve replaces ts with 1 microsecond everywhere while keeping measured
bandwidth and compute rates unchanged. This isolates startup latency; a real
supercomputer would change more than that. `REPORT.md` answers the assignment's
crossover/model/interconnect/advice questions with measured data and these limits.

Primary launcher/transport references:

- [Open MPI 4.1 launcher](https://www.open-mpi.org/doc/v4.1/man1/mpirun.1.php)
- [Open MPI TCP/self and same-guest transport](https://www.open-mpi.org/faq/?category=tcp)
