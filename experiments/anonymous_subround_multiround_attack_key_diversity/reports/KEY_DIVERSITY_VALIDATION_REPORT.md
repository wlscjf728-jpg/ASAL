# ASAL AES-128 Master-Key Diversity Validation

## Scope

This isolated validation changes only the AES-128 master key. It evaluates four pre-registered post-MC one-bit taps across twenty new deterministic keys, for 80 key/tap runs. The AES model, differential reference plaintext, shared query schedule, temporal depth `d=2`, Z3 encoding, and SAT-to-UNSAT uniqueness rule are inherited from the copied Attack 8 implementation.

## Solver boundary

The evaluator uses the secret key to generate oracle observations and to perform an external sanity check. Before every Z3 call, `true_key_hex` is removed from the document. A run is successful only when the first solve is `SAT` and the second solve with `K != K_hat` is `UNSAT`; evaluator-key equality alone is not a success criterion.

## Tap selection

The repository audit found the 128-entry MC candidate map but no all-128 per-position `N_uniq` artifact. Therefore taps were frozen by a result-independent structural fallback: MC bit-index ranks 0, 42, 85, and 127, corresponding to `MC_0`, `MC_42`, `MC_85`, and `MC_127` in four distinct MC columns. This limitation is recorded rather than presented as an `N_uniq`-based selection.

## Results

- Expected runs: **80**
- Terminal records: **80**
- Complete and duplicate-free: **True**
- Fixed-query unique: **80**
- Adaptive unique: **0**
- Proven non-recovery: **0**
- Unknown: **0**
- Model inconsistent: **0**

| Tap | Runs | Fixed unique | Adaptive unique | Non-recovery | Unknown | Fixed N_uniq median | Fixed N_uniq range |
|---|---:|---:|---:|---:|---:|---:|---:|
| MC_0 | 20 | 20 | 0 | 0 | 0 | 128.0 | 128–192 |
| MC_127 | 20 | 20 | 0 | 0 | 0 | 128.0 | 128–192 |
| MC_42 | 20 | 20 | 0 | 0 | 0 | 128.0 | 128–192 |
| MC_85 | 20 | 20 | 0 | 0 | 0 | 128.0 | 128–192 |

## Interpretation boundary

If all 80 runs are fixed or adaptive unique, the original three-key result is supported as key-diverse over this 20-key sample, but not as a universal theorem. If convergence varies by key, that is reported as key-dependent query efficiency. Any `UNKNOWN` remains unresolved and is not converted to ambiguity or success. `PROVEN_NON_RECOVERY` means the adaptive separator search proved observational non-recovery under the configured unrestricted plaintext model.

## Evidence

- Raw terminal results: `results/raw_runs.jsonl`
- Per-solve checkpoints: `results/checkpoints.jsonl`
- Frozen taps: `configs/representative_post_mc_taps.csv`
- Evaluator-only key manifest: `inputs/evaluator_keys.csv`
- Source and selection audit: `reference/source_manifest.json`
