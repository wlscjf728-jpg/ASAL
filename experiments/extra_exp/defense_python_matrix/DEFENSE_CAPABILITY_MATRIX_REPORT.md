# Python Defense Capability Matrix Report

## Scope

This report applies representative defense capability adapters to the existing Python AES-128 MC-channel oracle. The software results are the golden reference for the RTL confirmation path. Each RTL variant must be compared against these software phase/verdict results; this report does not replace that confirmation. It does not claim to reproduce the cited papers' RTL or netlist implementations. The attack core, frozen MC case, anonymous 256-cell Phase 0 scan model, 32 C0 MC hypotheses, and strict `SAT -> UNSAT` uniqueness rule are unchanged.

The primary matrix intentionally evaluates only the stated protection scope. For
state-centric protection, the protected set is the conventional key/round
state, while the separately materialized post-MC scan FF remains exposed. Any
variant that extends protection through the post-MC boundary is outside the
primary experiment and is not counted in the conclusions below.

## Pipeline Result

| Condition | Access | Phase 0 | Attribution | Fixed | Adaptive | Final | Verdict |
|---|---|---|---|---|---|---|---|
| D0 | allow | pass | pass | ambiguity | completed_from_validated_closed_loop | full_key_unique | ATTACK_SUCCESS |
| D1 | allow | pass | pass | ambiguity | completed_from_validated_closed_loop | full_key_unique | ATTACK_SUCCESS |
| D2 | allow | no_channel | no_channel | - | - | - | NO_ATTRIBUTABLE_CHANNEL |
| D3a | allow | pass | pass | ambiguity | completed_from_validated_closed_loop | full_key_unique | ATTACK_SUCCESS |
| D4 | allow | - | - | - | - | - | BLOCKED_BY_POLICY |
| D5a | allow | pass | pass | ambiguity | completed_from_validated_closed_loop | full_key_unique | ATTACK_SUCCESS |
| D5b | allow | pass | pass | ambiguity | completed_from_validated_closed_loop | full_key_unique | ATTACK_SUCCESS |
| D5c | allow | pass | identity_unstable | - | - | - | NO_ATTRIBUTABLE_CHANNEL |
| D5d | allow | pass | identity_unstable | - | - | - | NO_ATTRIBUTABLE_CHANNEL |
| D6_valid | allow | pass | pass | ambiguity | completed_from_validated_closed_loop | full_key_unique | ATTACK_SUCCESS |
| D6_invalid | deny | - | - | - | - | - | BLOCKED_BY_POLICY |
| D7 | allow | pass | pass | ambiguity | - | ambiguity | BLOCKED_BY_POLICY |
| D8_xorhash | allow | pass | no_channel | inconsistent | - | - | NO_ATTRIBUTABLE_CHANNEL |

## Interpretation

- `ATTACK_SUCCESS` means the final existing solver proof reached `SAT -> UNSAT`; a first model or hidden-key match alone is not sufficient.
- `NO_ATTRIBUTABLE_CHANNEL` means the transformed observation could not be explained by the clean MC-function hypothesis family, even when Phase 0 produced an AES-dependent decoy candidate.
- `BLOCKED_BY_POLICY` means access or an additional query was denied. In particular, D7 preserves fixed ambiguity and blocks the adaptive separator query.
- `UNKNOWN` and timeout are not converted into success or defense success. The recorded matrix has no unresolved solver result.

## State-Centric Protection Result

`D1` is the relevant state-centric condition. It removes the explicit
conventional state decoy from the attacker-visible scan response but leaves the
implementation-created post-MC observation FF available. The result is:

```text
conventional key/round state protected
+ post-MC scan FF exposed
-> Phase 0 MC channel discovery: pass
-> 32 MC hypotheses: one surviving branch
-> fixed query: SAT -> SAT
-> adaptive query: allowed
-> final key proof: SAT -> UNSAT
-> ATTACK_SUCCESS
```

This is a scope result, not a claim that state-centric protection is universally
ineffective. Any extended protection-through-post-MC variant is outside the
stated experiment and is not used to inflate the attack-success count.

## Condition Notes

| Condition | First blocked stage | Key evidence |
|---|---|---|
| D0 | - | `results/D0/attack_result.json`, `results/D0/transform_audit.json` |
| D1 | - | `results/D1/attack_result.json`, `results/D1/transform_audit.json` |
| D2 | phase0_discovery | `results/D2/attack_result.json`, `results/D2/transform_audit.json` |
| D3a | - | `results/D3a/attack_result.json`, `results/D3a/transform_audit.json` |
| D4 | phase0_query_authorization | `results/D4/attack_result.json`, `results/D4/transform_audit.json` |
| D5a | - | `results/D5a/attack_result.json`, `results/D5a/transform_audit.json` |
| D5b | - | `results/D5b/attack_result.json`, `results/D5b/transform_audit.json` |
| D5c | phase0_5_attribution | `results/D5c/attack_result.json`, `results/D5c/transform_audit.json` |
| D5d | phase0_5_attribution | `results/D5d/attack_result.json`, `results/D5d/transform_audit.json` |
| D6_valid | - | `results/D6_valid/attack_result.json`, `results/D6_valid/transform_audit.json` |
| D6_invalid | access | `results/D6_invalid/attack_result.json`, `results/D6_invalid/transform_audit.json` |
| D7 | adaptive_query_authorization | `results/D7/attack_result.json`, `results/D7/transform_audit.json` |
| D8_xorhash | phase0_5_attribution | `results/D8_xorhash/attack_result.json`, `results/D8_xorhash/transform_audit.json` |

## Evidence and Trust Boundary

Each condition directory contains attacker-visible captures/transcripts and a separate evaluator-only truth file. The attack artifacts do not contain the hidden key, MC9 label, physical mapping, or response-transform secret. Conditions with an unchanged differential transcript reuse the already completed Q128 fixed and Q131 adaptive solver checkpoints; the runner records this equivalence instead of silently copying a verdict.

## Limitations

This is a capability-boundary experiment over the established semantic oracle. D3 is DefScan-like response masking, D6 is DAF/SSA-style authorization, D7 is PASS-style pattern authorization, and D8 is a keyed response-hiding representative. The results do not establish universal security or insecurity of those named defenses, nor do they replace the separate EDA validation.
