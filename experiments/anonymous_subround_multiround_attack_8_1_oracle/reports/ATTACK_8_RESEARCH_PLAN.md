# Attack 8 Research Plan: Dependency-Guided Adaptive Sparse-FF Key Recovery

Date: 2026-07-12

Status: planning document only. No scripts, configurations, result files, solver jobs, or experiment setup have been created for Attack 8.

## 0. Executive Summary

Attack 8 should turn the Phase 7/7_1 passive identifiability sweep into an active, dependency-aware oracle attack.

The proposed attack has three tightly connected components:

1. Build an AES-aware functional dependency model for every candidate 1-bit FF leakage function.
2. Select a fixed sparse tap set whose functions are complementary with respect to `K0`, not merely distant on the `SB/SR/MC/ARK` surface.
3. Repeatedly synthesize plaintext queries that distinguish keys still consistent with the observed leakage, until either `K0` is uniquely determined or the fixed tap set is proven unable to distinguish the residual key class.

The central change is that `SAT -> SAT` is no longer treated immediately as a final attack failure. It is an intermediate state that supplies alternative keys for the next distinguishing-query synthesis step.

The intended high-level contribution is:

> A dependency-guided adaptive oracle attack that recovers AES-128 `K0` from a fixed sparse set of scan-visible 1-bit FFs by combining exact differential support analysis, solver-generated key-distinguishing plaintexts, and proof-based uniqueness or non-separability termination.

The result should be more than a larger query sweep. It should explain and exploit the distinction between:

- query-limited ambiguity: the tap set can distinguish the residual keys, but the existing plaintexts did not;
- support-limited ambiguity: no allowed plaintext can distinguish the residual keys through the fixed tap set;
- full-key uniqueness: the transcript admits exactly one `K0`.

## 1. Hard Semantic Conventions

These conventions must remain explicit in every implementation, result, and paper claim.

- One FF always means one 1-bit flip-flop.
- 2-bit leakage means observing two 1-bit FFs.
- 3-bit leakage means observing three 1-bit FFs.
- 4-bit leakage means observing four 1-bit FFs.
- It never means observing a full 128-bit register bank.
- The clean `SB/SR/MC/ARK x 128` surfaces are semantic reference maps, not assumptions that four physical 128-bit FF banks exist.
- A physical FF can inherit a semantic result only after Boolean equivalence and cycle alignment to a clean semantic bit are established.
- Internal S-box, partial MixColumns, fused, or retimed functions that are not clean-equivalent require their own leakage functions and support profiles.

## 2. Planning Boundary

Attack 8 is currently a design only.

This plan does not authorize or include:

- creating scripts or package structure;
- copying the Attack 7/7_1 solver environment;
- generating configuration CSV/YAML files;
- launching workers or background jobs;
- changing Phase 7 or Phase 7_1 data;
- post-processing existing result files;
- claiming any Attack 8 result before execution.

The implementation agent should treat this document as the handoff specification.

## 3. Baseline Inherited From Earlier Phases

Attack 8 inherits the following valid core model.

- AES-128 master key `K0` is the unknown.
- Exact tap stage, bit index, temporal cycle/round, and observation mode are known to the solver.
- The evaluator can generate exact oracle leakage from a hidden test key.
- The primary observation mode is differential.
- The current semantic depth is two AES rounds unless a depth ablation explicitly changes it.
- The first solve checks whether the transcript constraint `C(K)` is satisfiable.
- The second solve checks `C(K) AND K != K_star`, where `K_star` is the first model.
- First SAT and second UNSAT is the only full-key uniqueness result.
- First SAT and second SAT is finite-transcript ambiguity.
- UNKNOWN is never success and must never be converted by topology consensus.

Earlier results remain useful as empirical anchors:

- 2-bit early-only `SB/SR` cases were generally ambiguous under the tested transcript.
- 2-bit late `MC/ARK` cases were often uniquely identifying.
- mixed early/late cases were topology- and transcript-sensitive.
- 3-bit and 4-bit hard-case escalations showed ambiguity transitions.
- tap count alone did not explain the outcome.

Attack 8 must not inherit the following weaknesses.

### 3.1 Low-budget ambiguity early stop

In Phase 7_1, many ambiguity rows stopped at `q32`. Because the query sets are nested, a SAT alternative at `q32` can disappear at `q64`, `q128`, or later. Only uniqueness can safely stop early under monotonic constraint addition.

### 3.2 Topology consensus for UNKNOWN

Uniqueness is a property of a concrete transcript and model, not only a topology label. A result for one key/query seed cannot replace an UNKNOWN result for another seed.

### 3.3 Surface-coordinate topology

Raw labels such as same row, same column, or scatter do not fully encode cross-stage AES dependency. In particular, `SB -> SR -> MC` movement must be normalized through ShiftRows and the exact GF(2) MixColumns matrix.

### 3.4 Binary ambiguity without severity

One alternative key and an enormous residual key class were both labeled ambiguity. Attack 8 should preserve the exact terminal classification while also measuring residual structure.

### 3.5 Conditional higher-order sampling

The Phase 7/7_1 3-bit and 4-bit sets are hard-case escalations, not population samples. Attack 8 must not use their raw percentages as unconditional tap-count risk rates.

## 4. Primary Research Question

For a fixed sparse tap set `T` of 2, 3, or 4 scan-visible 1-bit FF functions:

> Can an attacker use AES-aware dependency support and solver-generated chosen plaintexts to drive the key-consistency set to a singleton more reliably and with fewer oracle queries than random or fixed query schedules?

The companion diagnostic question is:

> When recovery fails, is the failure caused by an insufficient query transcript or by an observational limitation of the selected tap functions?

## 5. Proposed Contribution Stack

The contribution should not be framed as merely "using more queries" or "using SAT."

The complete contribution stack is:

1. Differential functional attribution of sparse scan-visible 1-bit FFs.
2. Exact or refined `K0` dependency support across AES rounds and key expansion.
3. Equivalence-aware selection of a fixed sparse tap set under a strict tap budget.
4. Residual-key-aware query synthesis rather than random plaintext accumulation.
5. Exact SAT/UNSAT full-key uniqueness certification.
6. Exact non-separability diagnosis when no allowed query can refine the remaining candidate set.
7. Minimal observation certificates explaining which taps, rounds, and queries caused uniqueness.

The generic idea of finding distinguishing inputs between two key hypotheses resembles SAT/DIP attacks used in other domains. Therefore, novelty must be claimed for the AES sparse temporal scan-leakage formulation and the integrated dependency/tap/query/certificate method, not for the generic two-model miter alone.

## 6. Primary Threat Model

The primary Attack 8 threat model should be conservative and fixed throughout the main comparison.

### 6.1 Attacker capabilities

- The attacker has a chosen-plaintext oracle.
- For each queried plaintext, the attacker observes the selected sparse 1-bit FFs at the modeled cycles/rounds.
- The observations are exact and noiseless in the primary experiment.
- The attacker knows the Boolean/semantic mapping of the selected FFs.
- The attacker knows AES-128 and the implementation timing represented by the oracle model.
- The attacker may adapt each next plaintext to all prior leakage observations.

### 6.2 Fixed tap rule

The tap set `T` is selected once before attacking a test key and remains fixed for the run.

- A 2-bit run has exactly two unique 1-bit FF functions in the total observed union.
- A 3-bit run has exactly three.
- A 4-bit run has exactly four.
- Selecting different FFs on later queries would change the threat model unless the total union still respects the tap budget.

This rule prevents an adaptive scan-cell schedule from being mislabeled as fixed 2-bit/3-bit/4-bit leakage.

### 6.3 Primary differential mode

For fixed reference plaintext `P0`, define the leakage of tap `t` at round/cycle `r` as:

```text
D[t,r](P, P0, K) = F[t,r](P, K) XOR F[t,r](P0, K)
```

The main experiment should use a fixed `P0` so query costs and comparisons remain clear. Adaptive differential-pair selection can be a separate stronger ablation.

### 6.4 Physical applicability boundary

The primary Attack 8 experiments remain on clean semantic functions. Physical-netlist claims require a later attribution layer proving that a real FF stores the same function at the aligned cycle.

## 7. Formal Attack Model

Let:

- `K` be the 128-bit AES master key;
- `A` be the set of candidate scan-visible 1-bit FF functions;
- `T subseteq A` be the fixed tap set;
- `b` be the tap budget, with `|T| = b`;
- `R` be the observed round/cycle set;
- `P0` be the differential reference plaintext;
- `P_i` be the `i`th adaptive query plaintext;
- `Y_i` be the observed leakage vector for `P_i`.

The complete leakage signature for one query is:

```text
G_T(P, K) = [ D[t,r](P, P0, K) for t in T, r in R ]
```

After `n` oracle queries, the key constraint is:

```text
C_n(K) = AND over i=1..n of (G_T(P_i, K) = Y_i)
```

The implicit residual key set is:

```text
K_n = { K : C_n(K) }
```

The attack succeeds exactly when `|K_n| = 1`, checked by:

```text
SAT(C_n(K)) -> K_star
UNSAT(C_n(K) AND K != K_star)
```

No model count estimate may replace this final second solve.

## 8. Dependency Support Model

Dependency support must be represented at multiple levels. A single transitive fan-in bitset will saturate quickly after AES diffusion and become uninformative.

### 8.1 Structural support

For each tap function and round/cycle, compute conservative provenance:

```text
S_K(t,r) = K0 bits with a structural path to F[t,r]
S_P(t,r) = plaintext bits with a structural path to F[t,r]
```

The provenance engine must understand:

- initial AddRoundKey;
- S-box byte locality;
- ShiftRows byte permutation;
- exact bit-level GF(2) MixColumns coefficients;
- round-key XOR;
- AES-128 key expansion back to `K0`;
- cross-round state propagation.

### 8.2 Differential support

Support must be recomputed or simplified for the differential function `D[t,r]`, not copied from absolute `F[t,r]`.

Important identities include:

```text
D_MC[i,r] == D_ARK[i,r]
```

for the same round and bit, because the same round-key bit cancels between the two plaintext traces.

Similarly, an `SB` bit and its exactly corresponding `SR` bit are differential-equivalent after applying the ShiftRows mapping.

### 8.3 Exact functional support

Structural support is an over-approximation. A key bit `K[i]` is in the exact functional support of leakage function `D[t,r]` if two keys differing only in that bit can change the leakage for some allowed plaintext.

Use duplicated keys `K` and `K_prime`:

```text
K[j] == K_prime[j] for every j != i
K[i] != K_prime[i]
D[t,r](P, P0, K) != D[t,r](P, P0, K_prime)
```

- SAT gives a witness that `K[i]` is functionally relevant.
- UNSAT proves that `K[i]` is absent from the function under the stated plaintext domain and observation mode.

Structural support should first prune impossible bits; exact SAT support should refine the remaining bits.

### 8.4 Support tensor

The conceptual support artifact should contain at least:

```text
tap_id
semantic_or_function_id
round_or_cycle
observation_mode
structural_k0_bit_mask
functional_k0_bit_mask
k0_byte_mask
plaintext_bit_mask
source_sb_bytes
source_sr_column
mixcolumns_coefficient_role
first_influence_round
support_size_by_round
equivalence_class
physical_cycle_alignment
proof_status
```

`proof_status` should distinguish structural over-approximation from SAT-proven functional support.

### 8.5 Equivalence and redundancy classes

Before selecting tap sets, collapse or label exact-equivalent functions.

Candidate equivalence checks include:

- `MC_i` versus `ARK_i` in differential mode;
- exact `SB_i` versus mapped `SR_j`;
- retimed copies of the same semantic value;
- duplicated/fanout FFs storing the same Boolean function;
- any pair proven equivalent by a Boolean miter.

An equivalence miter is:

```text
exists P,K: D_a(P,P0,K) != D_b(P,P0,K)
```

- UNSAT proves exact equivalence.
- SAT produces a separating witness and shows they are not equivalent.

### 8.6 Conditional functional contribution

Two taps can have identical support sets yet impose independent equations. Conversely, different support sets can still be redundant under a transcript.

For existing tap set `T` and candidate tap `u`, test whether `u` can distinguish a pair that `T` cannot distinguish on the same query:

```text
exists P,K1,K2:
    K1 != K2
    G_T(P,K1) == G_T(P,K2)
    D_u(P,K1) != D_u(P,K2)
```

SAT means `u` has a functional contribution beyond `T` for at least one key pair. UNSAT means it adds no same-query pairwise discrimination in the tested domain.

This exact test should be used after support-based shortlisting.

## 9. Static Sparse Tap-Set Selection

The main attack must choose `T` without knowing the test key.

### 9.1 Selection pipeline

1. Generate candidate FF functions.
2. Normalize all candidates to the common `K0` dependency coordinate system.
3. Remove exact duplicates or retain only one representative per equivalence class.
4. Group candidates by support shape, stage, round growth, and MixColumns role.
5. Generate tap sets under exact budgets `b in {2,3,4}`.
6. Rank sets using support complementarity.
7. Apply exact conditional-contribution tests to finalists.
8. Freeze the tap set before evaluating hidden test keys.

### 9.2 Recommended lexicographic objectives

Avoid an unexplained weighted sum as the primary selector. Use a documented lexicographic order:

1. Maximize the minimum `K0` byte/column coverage.
2. Maximize total exact functional support coverage.
3. Maximize cross-round support growth diversity.
4. Maximize the number of distinct support/equivalence classes.
5. Maximize exact conditional functional contribution.
6. Minimize redundancy and support overlap that does not add independent discrimination.

Support overlap is not automatically bad. The selector must retain taps that constrain the same key variables through different nonlinear functions.

### 9.3 Support-aware hypergraph view

Represent the selection problem as a hypergraph:

- variable vertices: `K0` bits, bytes, or columns;
- tap hyperedges: exact functional support of each tap/round;
- edge labels: stage, round, coefficient role, equivalence class, function identity;
- tap-set objective: cover residual key structure with diverse labeled hyperedges.

This gives an AES-structural explanation for each selected set and avoids relying only on raw geometric distance.

### 9.4 No evaluation leakage

Tap sets must not be selected using the hidden keys later used to report success.

Acceptable selection inputs are:

- key-independent structural/functional support;
- a separately declared training-key set;
- a candidate-key pool generated independently of the held-out evaluation set.

Final claims require held-out keys.

## 10. Dynamic Residual Support During Attack

Once queries have been observed, the relevant support is the part intersecting the residual ambiguity.

### 10.1 Backbone and residual variables

For each `K0` bit or byte, determine whether it is fixed under `C_n`.

For bit `i`, check:

```text
C_n(K) AND K[i] != K_star[i]
```

- UNSAT: bit `i` is a backbone bit.
- SAT: bit `i` remains variable.
- UNKNOWN: unresolved, never treated as either.

The residual support of tap `t` is:

```text
R_n(t) = S_K(t) intersect {non-backbone K0 bits under C_n}
```

### 10.2 Candidate-disagreement weighting

Bitwise backbone checks can be expensive and can miss nonlinear correlations. Extract a diverse model pool and estimate where candidate keys disagree.

For each bit/byte, record:

- number of distinct sampled values;
- empirical entropy;
- pairwise disagreement frequency;
- affected AES columns;
- correlations with other residual bytes.

Use these values only to prioritize query synthesis. They must not replace exact final SAT checks.

### 10.3 Dynamic support role

Dynamic support should guide:

- which alternative key models to select;
- which plaintext bytes are allowed to vary first;
- which tap/round output differences are emphasized in optimization;
- whether the residual ambiguity appears query-limited or support-limited.

## 11. Adaptive Distinguishing-Query Engine

### 11.1 Core separability formula

Given transcript `C_n`, duplicate the key variables and introduce symbolic plaintext `P`:

```text
SEP(C_n,T) :=
    C_n(K1)
    AND C_n(K2)
    AND K1 != K2
    AND G_T(P,K1) != G_T(P,K2)
```

Interpretation:

- SAT: at least two currently compatible keys can be separated by an allowed plaintext through the fixed taps.
- UNSAT: every currently compatible key produces the same future leakage for every allowed plaintext through the fixed taps.
- UNKNOWN: the separability status is unresolved.

This formula jointly finds `K1`, `K2`, and a distinguishing plaintext `P_star`.

### 11.2 Pairwise adaptive loop

Conceptual pseudocode:

```text
input: fixed tap set T, reference P0, query budget q_max
C = true
transcript = []

while number_of_oracle_queries < q_max:
    first = solve(C)
    if first is UNSAT:
        return inconsistent_model
    if first is UNKNOWN:
        return unresolved

    K_star = model(first)
    second = solve(C AND K != K_star)

    if second is UNSAT:
        return unique(K_star, transcript)
    if second is UNKNOWN:
        return unresolved

    sep = solve(SEP(C,T))
    if sep is UNSAT:
        return support_limited_ambiguity(transcript)
    if sep is UNKNOWN:
        return unresolved

    P_star = plaintext_model(sep)
    Y_star = oracle(P_star, T)
    C = C AND (G_T(P_star,K) == Y_star)
    transcript.append(P_star, Y_star)

return query_budget_exhausted(C, transcript)
```

### 11.3 Progress guarantee

For the selected `K1`, `K2`, the synthesized `P_star` gives different predicted signatures. A single observed signature cannot match both, so at least one selected model is eliminated.

This guarantees logical progress, although it does not guarantee a large reduction in the full residual key set.

### 11.4 Incremental solving requirement

The implementation should use incremental formulas where practical.

- Reuse AES key-schedule constraints.
- Add one plaintext graph and one leakage equality block per query.
- Use push/pop or assumption literals for first, second, diagnostic, and core solves.
- Avoid rebuilding the entire accumulated attack state for every iteration unless validation requires it.

Incrementality affects performance only. It must not change the semantics of any result.

## 12. Multi-Model Query Partitioning

Pairwise separation can eliminate only one selected model in the worst case. The stronger engine should optimize a query against a diverse residual model pool.

### 12.1 Candidate pool

Generate `m` diverse keys satisfying `C_n` using one or more of:

- blocking clauses;
- maximum Hamming-distance objectives;
- per-byte diversity objectives;
- random XOR constraints;
- column-conditioned model extraction;
- alternative-model chains.

Record that this pool is a heuristic sample, not the complete key set.

### 12.2 Pair-separation objective

For each candidate pair `(K_a,K_b)`, define:

```text
z[a,b](P) = OR over observed tap/round bits of
            (G_T(P,K_a) XOR G_T(P,K_b))
```

Choose:

```text
P_star = argmax_P sum_{a<b} weight[a,b] * z[a,b](P)
```

Possible weights:

- uniform pair weights;
- higher weight for pairs differing in poorly covered residual columns;
- cluster-size weights;
- inverse-frequency weights so rare candidate structures are not ignored.

### 12.3 Balanced signature partition

The stronger objective is to minimize the largest predicted leakage-signature bucket. This approximates a minimax query:

```text
minimize over P: max_y |{K_j : G_T(P,K_j) = y}|
```

Because exact minimax encoding can be expensive, pair-separation or Gini-style objectives can be the primary implementation, with balanced-bucket optimization as an advanced profile.

### 12.4 Correctness fallback

If MaxSAT/Optimize times out:

1. fall back to the exact pairwise separability engine;
2. retain UNKNOWN for the failed optimization attempt;
3. never infer that no distinguishing query exists from optimization timeout.

The heuristic changes query efficiency, not the final correctness criterion.

## 13. Query-Domain Development

Query count alone is not the only attack variable. The plaintext domain should be explicitly controlled and ablated.

### 13.1 Domain A: inherited one-byte perturbations

- Fixed zero reference.
- One nonzero byte per query.
- Best comparability with earlier phases.
- May fail to excite cross-byte residual dependencies efficiently.

### 13.2 Domain B: unrestricted plaintext with fixed reference

- Fixed reference `P0`.
- All 128 plaintext bits symbolic.
- Strongest direct adaptive-query model under one new encryption per step after reference acquisition.

### 13.3 Domain C: bounded Hamming-weight plaintext

- Constrain the number of active bytes or bits.
- Provides a controlled bridge between one-byte and unrestricted queries.
- Can reveal how much query complexity comes from multi-byte excitation.

### 13.4 Domain D: adaptive differential pair

Synthesize both plaintexts:

```text
D_t(P_a,P_b,K) = F_t(P_a,K) XOR F_t(P_b,K)
```

Optimize `(P_a,P_b)` for residual-key separation.

This is a stronger oracle model and must report encryption cost accurately. One pair normally costs two encryptions unless one member reuses a prior reference.

### 13.5 Recommended development order

1. Pairwise adaptive query with fixed zero reference and inherited one-byte domain.
2. Pairwise adaptive query with unrestricted plaintext.
3. Multi-model optimization with unrestricted plaintext.
4. Adaptive differential-pair synthesis as an explicit stronger ablation.

## 14. Query-Limited and Support-Limited Ambiguity

Attack 8 should replace a single ambiguity label with a proof-aware taxonomy.

### 14.1 Full-key unique

```text
SAT(C_n) AND UNSAT(C_n AND K != K_star)
```

Meaning: exactly one master key satisfies the transcript.

### 14.2 Query-resolvable ambiguity

```text
SAT(C_n AND K != K_star) AND SAT(SEP(C_n,T))
```

Meaning: alternatives exist, and at least one allowed future plaintext can separate currently compatible keys.

### 14.3 Support-limited ambiguity

```text
SAT(C_n AND K != K_star) AND UNSAT(SEP(C_n,T))
```

Meaning: multiple keys remain, but all produce identical leakage for every allowed future plaintext through the fixed taps. More queries of the same allowed type cannot help.

### 14.4 Query-budget exhausted

The query ceiling was reached while both alternative keys and a possible distinguishing query remain.

This is not structural ambiguity and not low risk. It means only that the configured attack budget was insufficient.

### 14.5 Solver unresolved

Any required first, second, separability, support, or certificate solve returns UNKNOWN after the declared escalation policy.

UNKNOWN must remain unresolved.

### 14.6 Inconsistent model

`C_n` is UNSAT or the evaluator's true key fails the transcript check. This indicates an oracle, timing, mapping, AES model, or data-integrity error.

## 15. Optional Tap-Lift Diagnosis

The primary attack retains fixed taps. A separate diagnostic may ask whether changing the tap set would resolve a support-limited case.

For accessible candidate set `A` and strict budget `b`, introduce tap-selection variables `x_t`:

```text
sum_t x_t <= b
OR over t with x_t of (D_t(P,K1) != D_t(P,K2))
```

This can distinguish:

- fixed-set support limitation: current `T` cannot separate;
- tap-budget-resolvable limitation: another set of the same size can separate;
- accessible-surface limitation: no allowed clean semantic set of size `b` can separate the tested residual structure.

This diagnosis must not be folded into the fixed-tap recovery rate.

## 16. Proof and Explanation Artifacts

Every terminal result should carry evidence.

### 16.1 Unique-key certificate

Required fields:

- first SAT model;
- true-key consistency check in evaluator mode;
- second-solve UNSAT;
- solver encoding and version;
- exact query transcript hash;
- exact tap-function identifiers;
- timing/round mapping;
- timeout policy;
- optional independently replayed second solve.

### 16.2 Alternative-key witness

For finite-transcript ambiguity or budget exhaustion, store:

- `K_star`;
- at least one concrete alternative key;
- confirmation that both predict the complete current transcript;
- their residual bit/byte/column difference profile.

### 16.3 Non-separability certificate

For support-limited ambiguity, store the UNSAT result for `SEP(C_n,T)` and enough metadata to replay it.

Because solver-generated UNSAT is central to the claim, selected cases should be cross-checked with a second encoding or independently rebuilt formula where computationally feasible.

### 16.4 Minimal observation core

Attach assumption literals to query/tap/round observation blocks. After uniqueness, extract and minimize an UNSAT core for:

```text
C_n(K) AND K != K_star
```

Report:

- total queries issued;
- queries in the minimized core;
- taps represented in the core;
- rounds/cycles represented;
- leakage bits that were redundant;
- effective oracle-encryption cost.

The minimized core turns a black-box unique result into an explanatory recovery certificate.

## 17. Attack 8 Experimental Questions

The eventual experiment should answer the following separately.

### Q1. Query correction

How many Phase 7_1 `q32` ambiguity cases become unique when all cases are evaluated at a common fixed maximum query budget?

### Q2. Adaptive-query gain

For the same fixed tap set, hidden key, plaintext domain, and maximum query cost, how much does adaptive query synthesis improve:

- full-key unique rate;
- median queries to uniqueness;
- worst-case queries;
- solver time;
- unresolved rate?

### Q3. Dependency-aware selection gain

At the same tap and query budgets, does support-aware tap selection outperform surface-coordinate stratification or random tap selection on held-out keys?

### Q4. Interaction gain

Is the combination of dependency-aware taps and adaptive queries stronger than either component alone?

### Q5. Ambiguity diagnosis

What fraction of failed runs are:

- query-resolvable at budget exhaustion;
- proven support-limited;
- solver-unresolved;
- inconsistent?

### Q6. Sparse threshold

How do 2-bit, 3-bit, and 4-bit fixed tap budgets change:

- success probability over held-out keys;
- minimum query count;
- support-limited collision rate;
- minimal-core tap count?

### Q7. AES structural explanation

Which support features best explain query efficiency and final identifiability?

- number of late taps;
- exact `K0` byte/column coverage;
- cross-round support expansion;
- equivalence class diversity;
- functional contribution score;
- MixColumns coefficient/bit role;
- residual support alignment.

## 18. Required Ablation Matrix

The minimum fair ablation is a 2 x 2 design.

| Tap selection | Query selection | Purpose |
|---|---|---|
| surface/random | fixed random | inherited baseline |
| support-aware | fixed random | isolate tap-selection gain |
| surface/random | adaptive | isolate query-synthesis gain |
| support-aware | adaptive | measure combined method |

Additional adaptive-query ablations:

| Query engine | Meaning |
|---|---|
| pairwise miter | exact progress baseline |
| diverse-pool pair separation | multi-model heuristic |
| balanced partition | stronger minimax-style heuristic |
| adaptive differential pair | stronger oracle variant |

All paired comparisons must use the same tap budget, hidden keys, oracle model, and encryption-cost accounting.

## 19. Sampling and Generalization Design

Attack 8 should not claim exhaustive coverage.

### 19.1 Tap-set sampling

Use declared strata based on exact support rather than only surface geometry:

- equivalent/redundant controls;
- narrow early support;
- same-column late support;
- cross-column late support;
- mixed early/late complementary support;
- matched-support but functionally different pairs;
- matched-stage but support-divergent pairs;
- high support union with high redundancy;
- moderate support union with high functional contribution.

### 19.2 Train/validation/test separation

- Training keys may tune selector thresholds or optimization profiles.
- Validation keys may choose solver parameters.
- Held-out test keys produce reported recovery rates.
- No hidden test transcript may influence tap selection.

### 19.3 Key and query replication

Three seeds are suitable for smoke tests, not strong generalization claims. The final design should declare enough independent hidden keys for confidence intervals and use paired runs across competing methods.

### 19.4 Population claims

Because tap sets are stratified or targeted, raw aggregate percentages are not estimates of uniform risk over all combinations unless explicit sampling weights justify that interpretation.

Report both:

- per-stratum outcomes;
- overall campaign counts without presenting targeted sampling as population prevalence.

## 20. Metrics

### 20.1 Primary metrics

- full-key unique rate under fixed tap/query budgets;
- adaptive queries to first proven uniqueness;
- oracle encryptions to uniqueness;
- support-limited ambiguity rate;
- query-budget-exhausted rate;
- UNKNOWN/unresolved rate;
- wall-clock solver cost.

### 20.2 Secondary metrics

- minimized-core query count;
- minimized-core tap count;
- number of residual backbone bits/bytes over time;
- alternative-key Hamming distance over time;
- candidate-pool partition score;
- support coverage and residual-support coverage;
- number of candidate models eliminated per adaptive step in the sampled pool;
- query plaintext Hamming weight and active-byte count;
- per-round leakage contribution.

### 20.3 Curves rather than only endpoints

Report:

- cumulative unique rate versus oracle encryptions;
- residual free-byte/backbone profile versus query step;
- support-limited detections versus tap budget;
- solver time per adaptive iteration;
- random-versus-adaptive paired query savings.

## 21. Statistical Analysis Plan

Use paired evaluation because the same tap set/key instances can be attacked by multiple query strategies.

Recommended summaries:

- bootstrap confidence intervals for median query reduction;
- Wilson intervals for per-stratum unique rates;
- paired binary comparison for success at fixed budget;
- paired nonparametric comparison for queries-to-unique among commonly solved runs;
- survival-style curves where unsolved runs are censored at the query budget;
- effect sizes, not only p-values.

Mixed outcomes across keys should be reported as key dependence, not resolved by case-level majority vote.

## 22. Correctness Contract

The implementation agent must satisfy all of the following.

### 22.1 Monotonic transcript rule

When a new correct observation is added:

```text
Models(C_{n+1}) subseteq Models(C_n)
```

Therefore:

- unique may stop early;
- ambiguity may not stop early unless support-limited non-separability is proven;
- a previously proven unique transcript cannot become ambiguous after adding consistent observations.

### 22.2 No consensus imputation

- Never replace UNKNOWN using another key seed.
- Never infer one topology's result from another exact position.
- Never infer an untested 3/4-bit case from a 2-bit subset except the valid monotonic statement that a genuinely unique subset remains unique when consistent additional tap constraints are added at the same transcript.

### 22.3 True-key isolation

The evaluator may know `K0` to generate and validate oracle observations. The attack logic must not use `K0` for:

- tap selection on held-out runs;
- plaintext synthesis;
- candidate-model scoring;
- termination;
- ambiguity diagnosis.

### 22.4 Tap-budget accounting

- Count unique physical/semantic 1-bit FF functions in the total observation union.
- Count exact duplicate functions explicitly if the physical threat model observes separate but identical FFs, but do not claim extra information from them.
- Keep fixed-tap and reconfigurable-tap results separate.

### 22.5 Query-cost accounting

- Distinguish adaptive query count from total oracle encryptions.
- Count acquisition of the differential reference.
- Count both plaintexts for adaptive pairs unless one is reused.
- Do not compare q-values with different cost conventions.

### 22.6 UNKNOWN handling

- UNKNOWN is neither ambiguity nor uniqueness.
- Escalation may increase timeout, change a proven-equivalent encoding, or run without a timeout.
- Any encoding change must be replay-validated.
- If still UNKNOWN, retain unresolved status.

## 23. Validation Gates Before Large Runs

The implementation must pass these gates in order.

### Gate A: AES trace agreement

- Compare concrete reference and symbolic AES at every modeled `SB/SR/MC/ARK` bit.
- Test multiple random plaintext/key pairs and every modeled round.
- Verify key-schedule outputs independently.

### Gate B: differential identities

- Prove or exhaustively validate `D_MC[i] == D_ARK[i]` for matching round/bit.
- Validate every `SB/SR` permutation-equivalence mapping.
- Confirm that nonmatching controls produce SAT separating witnesses.

### Gate C: support correctness

- Every exact-support SAT result has a replayable witness.
- Every selected exact-support UNSAT result is reproduced with an independent formula construction or encoding sample.
- Compare structural and functional masks and explain removed dependencies.

### Gate D: attack invariants

- True key remains SAT after every oracle update.
- The selected `K1` and `K2` satisfy the complete transcript.
- Synthesized `P_star` actually gives different predicted leakage for `K1` and `K2` in concrete replay.
- After adding the real observation, both selected models cannot remain simultaneously valid.

### Gate E: terminal classification

- Unique cases reproduce first SAT and second UNSAT.
- Finite ambiguity stores an alternative key.
- Support-limited cases reproduce second SAT and separability UNSAT.
- UNKNOWN remains unresolved.

### Gate F: inherited anchors

- Reproduce known early-only ambiguity anchors at a common declared budget.
- Reproduce known late unique anchors.
- Do not use these anchors as the entire validation set.

Only after all gates pass should large parallel experiments begin.

## 24. Conceptual Data Records

The implementing agent may choose file formats, but the following information must be retained.

### 24.1 Tap profile record

```text
tap/function identity
semantic mapping or internal-function label
round/cycle alignment
observation mode
structural support
functional support
equivalence class
support proof metadata
```

### 24.2 Tap-set record

```text
tap-set ID
tap budget
member tap IDs
selection method
support union/intersection
column/byte coverage
functional-contribution evidence
training/test provenance
```

### 24.3 Query-step record

```text
run ID and step
plaintext/reference plaintext
oracle leakage signature
query domain
query-synthesis method
selected K1/K2 or candidate-pool hash
predicted separation score
solver status/time
residual diagnostic summary
```

### 24.4 Terminal attack record

```text
classification
first and second solve statuses
separability status
recovered key if unique
alternative key if ambiguous
query count and encryption count
tap count
UNKNOWN fields and reasons
certificate/core references
```

## 25. Suggested Implementation Decomposition

This is a conceptual module boundary for the future implementation agent, not a request to create these files now.

```text
AES semantic/function normalizer
Differential leakage-function builder
Structural support propagator
Exact functional-support checker
Equivalence/redundancy checker
Sparse tap-set selector
Incremental transcript solver
Pairwise separability solver
Diverse candidate-model sampler
Multi-model query optimizer
Oracle adapter
Uniqueness/non-separability certifier
UNSAT-core minimizer
Campaign runner and result validator
```

The oracle adapter should remain separate from attack logic so the hidden evaluator key cannot leak into query selection.

## 26. Execution Phases For The Future Agent

### Phase 8A: Baseline integrity repair

Goal: establish a comparable fixed-budget baseline before claiming adaptive gains.

- Import exact Phase 7/7_1 tap cases without editing original results.
- Re-evaluate prior low-budget ambiguity cases at a common maximum query budget.
- Remove consensus-imputed rows from proof-grade analysis unless independently solved.
- Record query counts and encryption counts consistently.
- Produce a corrected baseline table, not a replacement of historical raw data.

Exit condition: every baseline row is unique, finite-budget ambiguous, or unresolved under the same declared policy.

### Phase 8B: Dependency support engine

Goal: produce validated structural and exact differential support profiles.

- Implement AES bit-level provenance.
- Normalize ShiftRows and MixColumns relations.
- Map round-key support back to `K0`.
- Collapse differential equivalence classes.
- Refine selected support bits with SAT miters.

Exit condition: all validation gates A-C pass.

### Phase 8C: Support-aware fixed tap selection

Goal: select 2/3/4-bit sets without test-key leakage.

- Generate matched support-aware and surface/random sets.
- Preserve stage-pair controls for comparability.
- Record exact reasons for each selected tap.
- Freeze selections before held-out evaluation.

Exit condition: every selected set has a complete support and provenance record.

### Phase 8D: Exact pairwise adaptive query attack

Goal: implement the correctness-first active loop.

- Duplicate key variables.
- Synthesize `K1`, `K2`, and `P_star` jointly.
- Replay every distinguishing witness concretely.
- Update transcript incrementally.
- Implement all terminal classes.

Exit condition: validation gates D-E pass on small anchors and synthetic controls.

### Phase 8E: Multi-model partition optimizer

Goal: improve query efficiency without weakening correctness.

- Extract diverse residual models.
- Optimize pair separation.
- Add balanced-partition profile if tractable.
- Retain pairwise fallback.

Exit condition: optimizer queries never violate pairwise witness validation and final outcomes match exact second solves.

### Phase 8F: Controlled campaign

Goal: measure support and query contributions independently.

- Run the required 2 x 2 ablation.
- Use paired hidden keys.
- Cover 2/3/4-bit fixed tap budgets.
- Measure query curves, support-limited outcomes, and cores.

Exit condition: all runs have proof-aware terminal status and no silent UNKNOWN.

### Phase 8G: Stronger oracle ablations

Goal: map the value of expanded query freedom.

- unrestricted plaintext;
- bounded active-byte plaintext;
- adaptive differential pairs;
- optional tap-lift diagnosis.

These results must remain labeled as stronger threat-model variants.

## 27. Priority Order

If implementation resources are limited, use this order:

1. Correct Phase 7_1 ambiguity budget handling.
2. Exact pairwise adaptive query loop with fixed existing taps.
3. Structural/differential support normalization and equivalence removal.
4. Support-aware fixed tap selection.
5. Query/support-limited terminal diagnosis.
6. Multi-model query optimization.
7. Minimal UNSAT cores.
8. Adaptive differential pairs and optional tap-lift variants.

This order produces a correct active attack before adding optimization complexity.

## 28. Main Risks And Mitigations

### Risk 1: Generic SAT-attack prior art overlap

Mitigation: frame novelty around sparse temporal AES scan leakage, exact differential FF support, strict tap-budget selection, support-aware query optimization, and proof-aware ambiguity diagnosis. Do not claim invention of generic distinguishing-input SAT loops.

### Risk 2: Support saturation

After enough rounds, many taps may structurally depend on all `K0` bits.

Mitigation: retain round-of-first-influence, exact functional support, coefficient roles, equivalence classes, conditional contribution, and residual candidate separation rather than support size alone.

### Risk 3: Solver scaling

The separability miter contains two keys plus a symbolic plaintext and duplicated AES logic.

Mitigation:

- incremental solving;
- structural support pruning;
- staged plaintext domains;
- pairwise engine before multi-model optimization;
- alternative S-box encodings with equivalence validation;
- exact fallback policies and retained UNKNOWN.

### Risk 4: Heuristic candidate-pool bias

Mitigation: use pools only for query optimization. Preserve exact first/second solve and exact pairwise fallback for correctness.

### Risk 5: Threat-model inflation

Mitigation: keep fixed taps, adaptive taps, fixed reference, adaptive pair, semantic functions, and physical FFs as separately labeled models.

### Risk 6: Query-cost ambiguity

Mitigation: report both logical distinguishing steps and actual oracle encryptions, including reference traces.

### Risk 7: Overfitting tap selection

Mitigation: key-independent support selection plus held-out keys and predefined strata.

### Risk 8: Mistaking finite-budget ambiguity for safety

Mitigation: use `query_budget_exhausted`, `query_resolvable`, and `support_limited` labels instead of `confirmed_low_risk` unless a precise low-risk definition is justified.

### Risk 9: Physical mapping gap

Mitigation: limit Attack 8 semantic claims to function-equivalent FFs. Treat synthesized internal-node attribution as a subsequent extension.

## 29. Expected Result Interpretations

### Outcome A: Adaptive queries convert many q32 ambiguities to unique

Interpretation: a substantial part of the earlier map measured query insufficiency rather than tap insufficiency.

### Outcome B: Fixed-budget query extension helps, but adaptive queries need far fewer encryptions

Interpretation: the sparse tap functions were already identifying; solver-guided excitation improves attack efficiency.

### Outcome C: Support-aware taps outperform surface-coordinate taps

Interpretation: actual AES dependency and functional complementarity explain vulnerability better than geometric placement labels.

### Outcome D: Some cases remain support-limited

Interpretation: those tap sets induce observational key-equivalence classes under the allowed query domain. More queries alone cannot repair them.

### Outcome E: Support-aware selection adds little after adaptive queries

Interpretation: query synthesis may dominate static support heuristics, or the support representation may be too coarse. This is still a meaningful ablation result.

### Outcome F: Structural support does not predict exact recovery, but conditional contribution does

Interpretation: support coverage is a useful filter, while nonlinear constraint independence is the actual discriminator.

## 30. Paper-Level Framing

### 30.1 Strong central statement

> We formulate sparse temporal scan leakage as an adaptive key-identifiability problem. AES-aware differential dependency analysis selects a fixed set of 1-bit FF functions, while a solver repeatedly synthesizes chosen plaintexts that partition the residual key space. Recovery is accepted only with an alternative-key UNSAT proof; failures are separated into query-budget exhaustion and proven non-separability under the selected taps.

### 30.2 Defensible novelty statement

> The contribution is the integration of function-attributed sparse scan FFs, AES diffusion-aware dependency support, strict tap-budget selection, adaptive residual-key discrimination, and proof-aware terminal classification.

### 30.3 Claims to avoid

- "All synthesized AES FFs are covered."
- "Any two late FFs recover the key."
- "SAT/SAT proves permanent security."
- "UNKNOWN follows the topology majority."
- "Support union alone predicts uniqueness."
- "The 3/4-bit hard-case sample is exhaustive."
- "The generic distinguishing-input SAT loop is entirely new."

## 31. Candidate Method Names

The method name should emphasize the integrated contribution.

- Dependency-Guided Adaptive Sparse-FF Attack
- Support-Aware Adaptive Key Discrimination
- Diffusion-Aware Sparse Scan Oracle Attack
- Dependency-Guided Temporal Leakage Key Recovery

A concise working name is:

> DGAS: Dependency-Guided Adaptive Scan attack

The name should remain provisional until the implementation and result emphasis are known.

## 32. Completion Criteria For Attack 8

Attack 8 is complete only when all of the following are true.

- Baseline ambiguity uses a common declared query budget or an exact non-separability proof.
- No UNKNOWN has been converted to a security outcome.
- Differential support and equivalence are validated.
- Fixed tap budgets are enforced.
- Support-aware selections are frozen before held-out runs.
- Pairwise adaptive queries pass concrete replay validation.
- Final uniqueness uses first SAT and second UNSAT.
- Support-limited ambiguity uses second SAT and separability UNSAT.
- Query-budget exhaustion remains distinct from structural ambiguity.
- At least the 2 x 2 support/query ablation is complete.
- Query costs and oracle encryption costs are both reported.
- Minimal observation cores are available for representative unique cases.
- Physical applicability claims are restricted to function-equivalent FFs.
- All paper claims can be traced to exact result and certificate records.

## 33. Final Conceptual Picture

Attack 7/7_1 asked:

```text
Given a selected semantic tap set and a prepared transcript,
is K0 unique?
```

Attack 8 should ask:

```text
Given a strict sparse-FF budget,
which functionally complementary taps should be fixed,
which plaintext should be queried next,
and can the solver prove either unique K0 recovery
or the inability of those taps to further distinguish the residual keys?
```

The intended flow is:

```text
candidate 1-bit FF functions
    -> differential functional attribution
    -> exact/support-aware equivalence classes
    -> fixed sparse tap-set selection
    -> initial transcript
    -> residual candidate-key analysis
    -> solver-generated distinguishing plaintext
    -> oracle leakage update
    -> repeat
    -> unique-key UNSAT certificate
       or support-limited non-separability certificate
       or explicit query-budget/solver unresolved status
```

This is the boundary between an empirical semantic sweep and a full dependency-guided adaptive key-recovery methodology.
