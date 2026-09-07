# D1-D5 DFT Reassessment

## Purpose

This campaign tests whether the earlier MC-versus-random coverage gap survives
after removing the direct stuck-at faults on the variable scan FF Q sites. The
same one-round `mor1kx_aes_soc` mapped checkpoint, common scan set, 128-FF
variable budget, one scan chain, and TetraMAX setup are reused. No result from
the earlier collapsed 422-fault campaign is silently substituted for the new
functional fault universe.

## Experimental axes

| Axis | Cases | Evidence |
|---|---|---|
| D1 | B=128, direct variable FF faults excluded | Non-direct incremental gain |
| D2 | IARK, SB, SR, MC, random under D1 fault universe | Controlled stage comparison |
| D3 | direct FF, MC cone, AES other, host, unresolved | Fault-level attribution and status diffs |
| D4 | stuck-at and transition-delay smoke/full runs where protocol permits | Fault-model sensitivity |
| D5 | automated structural/SCOAP candidate ranking and security overlay | Selection heuristic and Pareto evidence |

The direct-fault exclusion is the union of the SA0/SA1 Q-net faults for all
four AES stage banks and the eligible random pool. The union is applied to every
case so the fault population is identical and no case-specific deletion biases
the comparison. Common scan FF direct faults remain in the shared universe and
are reported separately.

## Validity gates

Every case records the functional checkpoint digest, manifest digest, exact scan
count, chain count/length, loaded fault count, exclusion count, invalid-site
warnings, ATPG class totals, patterns, and runtime. A case is `INVALID` rather
than comparable if a gate fails. D1/D2 claims use TetraMAX's post-collapse
representatives only as a measurement unit; D3 additionally preserves the
uncollapsed site report for region attribution.

## Interpretation policy

The strongest DfT claim is allowed only when MC remains better on faults outside
the variable FF Q sites. If the gain disappears, the result is reported as a
direct-observability effect and the earlier broad testability language is not
reused. Transition syntax or protocol limitations are recorded as `UNRESOLVED`,
not converted into a zero or a success.

The D5 security axis is imported from the existing independently generated
round-1 leakage results. It is an overlay, not a new cryptographic run and not
evidence that TetraMAX coverage itself implies key recovery. The report labels
this provenance explicitly.
