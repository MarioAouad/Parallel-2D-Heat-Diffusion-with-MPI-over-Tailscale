# Part 1 results index

| Record | Role | Contents |
| --- | --- | --- |
| [19 November Ubuntu study](2026-11-19-ubuntu/) | **Primary Part 1 delivery** | Five-grid convergence, isolated instability, stable Cases 1/2, plots, raw commands, source metadata, manifest and review |
| [19 November Windows study](2026-11-19-windows/) | Supporting earlier local verification | Separate platform study; retained for provenance and serial comparisons |
| [First Ubuntu run](2026-11-19-ubuntu-smoke/) | Historical build/smoke evidence | One N=16 solver summary and transcript provenance; superseded in scope by the full Ubuntu study |

Use the [analysis](../ANALYSIS.md) for interpretation and the
[delivery checklist](../DELIVERY.md) for requirement links. The Ubuntu study is
complete; earlier records are retained evidence rather than pending tasks.

`make verify-part1-results` checks the primary published archive offline.
`make verify-part1` creates a new timestamped folder under ignored `runs/`.
Review new runs before publishing them; keep the dated originals and manifests
unchanged. Reproducible binary fields remain ignored/private.

The recorded loop timings are incidental serial measurements, not a controlled
cluster scaling study.
