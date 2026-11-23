# Explanation PDFs and evidence scope

The PDFs added in commits 3bec287 and da054e3 explain the existing implementation;
they do not replace the original manifests, raw runs or strict evidence checks.
Their references to 2+2+2 describe the historical Part 0 allocation; the primary
Part 3 retained-field study used heat1=4, heat2=2, heat3=2 guest vCPUs/slots.

## Qualification to the Part 3 explanation

The sentence stating that both executables match serial byte for byte up to P=8
is broader than the retained correctness evidence:

- The new **blocks** study has 108 exact serial comparisons, including 18 at P=8.
- The new **strips** study has 84 exact serial comparisons at P=1,2,3,4, satisfying C2.
- Strips also ran at P=8 in the Part 3 timing matrix, without output fields; those
  timing invocations are not retained-field byte comparisons.

Use those precise statements when presenting the evidence. This qualification
does not invalidate the required Part 3 P=8 checks or call for rerunning them.
The full Part 4 campaign is now collected and strict-verified; see the final report
in ../final-report/final-report.pdf. Technical C3 evidence is ready.
