# Diffusion-Aware Scan-FF Leakage Attribution Methodology

Date: 2026-07-09

This note develops the analysis methodology behind the Phase 7 and Phase 7_1 experiments. The goal is to turn the current results into a concrete research contribution rather than only a collection of SAT runs.

The central idea is:

> A scan-visible FF should not be evaluated only as an unnamed physical cell. It should first be attributed to the cryptographic Boolean value it stores, and then evaluated by whether temporal leakage from that value uniquely determines the AES-128 master key.

In short:

> physical scan FF -> semantic/function attribution -> sparse temporal leakage oracle -> key-identifiability test -> AES diffusion-aware risk explanation

This is the methodology that can connect clean semantic experiments to actual synthesized/retimed AES hardware.

## 1. Why This Is More Than A Result Table

A plain result table says something like:

- `SB_0 + SR_0`: ambiguous
- `MC_0 + ARK_1`: unique
- `SB_114 + SB_4 + SB_80 + SR_14`: unique

That is useful, but it is not yet a methodology.

A methodology says how to evaluate a new design:

1. Given a real scan-visible 1-bit FF, determine what cryptographic value it stores.
2. If it matches a clean AES semantic bit, place it on the AES semantic surface.
3. If it does not match a clean semantic bit, classify its Boolean cone separately.
4. Given a sparse set of such FFs, build a temporal leakage oracle.
5. Decide whether the observed leakage uniquely identifies `K0`.
6. Explain the result using AES diffusion structure.

The novelty is not just that a few 1-bit leakages can recover a key. The stronger claim is that we provide a way to assign **cryptographic identifiability risk** to scan-visible FFs.

## 2. Proposed Name

A usable name for the method:

> Diffusion-Aware Scan-FF Leakage Attribution

Alternative short names:

- Semantic FF Leakage Attribution
- Scan Cell to Key Identifiability Analysis
- AES Semantic Leakage Topology Analysis
- Diffusion-Aware Sparse FF Risk Mapping

The word **attribution** is important. The method does not only report unique/ambiguous. It attributes the result to the FF's cryptographic meaning and its position relative to AES diffusion boundaries.

## 3. Core Thesis

The method is based on the following thesis:

> The key-recovery risk of sparse scan-visible 1-bit FF leakage is governed less by the raw number of observed FFs and more by the AES semantic stage, diffusion boundary, Boolean dependency support, temporal round propagation, and complementarity among the observed bits.

This thesis is supported by the integrated Phase 7 + Phase 7_1 data:

| Leakage | Cases | Main observation |
|---|---:|---|
| 2-bit | 418 | early-only SB/SR pairs remain ambiguous; late MC/ARK pairs are often unique; mixed pairs are topology-sensitive |
| 3-bit | 190 | early-only remains ambiguous; weak late classes often become unique |
| 4-bit | 105 | weak/mixed late classes are high-risk; selected early-only cases can become unique via temporal diffusion |

This means the useful object is not merely a tap count. The useful object is a **semantic leakage topology**.

## 4. Threat Model And Leakage Object

The leakage object is a sparse set of scan-visible 1-bit FFs.

Important definitions:

- One FF means one 1-bit flip-flop.
- 2-bit leakage means two 1-bit FFs are observed.
- 3-bit leakage means three 1-bit FFs are observed.
- 4-bit leakage means four 1-bit FFs are observed.
- This does not mean observing a 128-bit register bank.

The attacker observes the selected sparse FFs over time while chosen or known plaintexts are processed. The solver receives temporal observations of these selected 1-bit values.

The current experiments use clean AES semantic references:

- `SB_i`: bit `i` of SubBytes output
- `SR_i`: bit `i` of ShiftRows output
- `MC_i`: bit `i` of MixColumns output
- `ARK_i`: bit `i` of AddRoundKey output

These references are semantic anchors. They are not a claim that a synthesized implementation necessarily contains all of these as physical FF banks.

## 5. Method Overview

The methodology has five layers.

### Layer 1: FF Function Extraction

For each scan-visible 1-bit FF in a real AES netlist:

1. Locate the FF's D input.
2. Extract the combinational cone driving the FF.
3. Determine which state/key/plaintext signals influence the D input.
4. Normalize the function if retiming or simple logic rewriting occurred.

The output of this layer is a Boolean function:

```text
F_j(P, K, state, round) -> {0,1}
```

For a clean semantic FF, this function may equal something like:

```text
F_j = MC_out[37]
```

For an internal FF, it may instead be:

```text
F_j = partial_xor(SB_out[8], SB_out[24])
```

or an S-box internal node.

### Layer 2: Semantic Or Function Attribution

Each FF is assigned one of the following labels.

| Label | Meaning | Can current semantic map be directly applied? |
|---|---|---|
| `clean_SB_i` | equivalent to clean SubBytes output bit | yes |
| `clean_SR_i` | equivalent to clean ShiftRows output bit | yes |
| `clean_MC_i` | equivalent to clean MixColumns output bit | yes |
| `clean_ARK_i` | equivalent to clean AddRoundKey output bit | yes |
| `retimed_clean_semantic` | same Boolean value as a clean semantic bit, stored at a shifted cycle | yes, with timing alignment |
| `internal_sbox_node` | internal S-box Boolean node | no, needs new function model |
| `partial_mixcolumns_node` | partial XOR or partial linear mixture | no, needs new function model |
| `fused_internal_node` | optimized or fused cone not equal to clean surface | no, needs new function model |
| `control_or_nonstate` | not direct AES state leakage | separate analysis |

This is the bridge from real hardware to the semantic experiments.

If a real FF is proven equivalent to `MC_out[37]`, then the existing semantic map can be used for that FF. If it is not equivalent, the map should not be overclaimed.

### Layer 3: Sparse Temporal Leakage Oracle

For a selected FF set:

```text
T = {F_a, F_b, ...}
```

and a plaintext set:

```text
P = {P_0, P_1, ..., P_q}
```

the oracle records temporal leakage bits:

```text
L = {F_j(P_i, K0, t) for F_j in T, P_i in P, t in observed cycles}
```

The solver builds constraints:

```text
C(K) := AES constraints consistent with all observed leakage bits
```

The current experiments use:

- `depth = 2`
- differential observation mode
- temporal observations across AES subround surfaces
- query ladder from `q=32` up to `q=255` for confirmation

### Layer 4: Key Identifiability Test

This is the algorithmic heart of the method.

The goal is not merely to find a key candidate. The goal is to decide whether the leakage uniquely determines the master key.

The test is:

```text
1. Solve C(K)
   - If UNSAT: oracle/modeling error or inconsistent observation.
   - If SAT: obtain one key K*.

2. Solve C(K) AND K != K*
   - If UNSAT: K* is the unique satisfying key. Label full_key_unique.
   - If SAT: an alternative key exists. Label ambiguity.
   - If UNKNOWN/TIMEOUT: label undecided, not success.
```

This distinction matters.

A key candidate is not enough. A security claim requires proving there is no alternative key under the same leakage constraints.

### Layer 5: Diffusion-Aware Risk Attribution

After classification, the method explains why the case is unique or ambiguous.

The explanation uses AES structure:

- SubBytes is byte-local and nonlinear.
- ShiftRows permutes bytes but does not mix information.
- MixColumns linearly mixes four bytes inside a column.
- AddRoundKey exposes the post-MixColumns state after round-key XOR.
- Across rounds, MC diffusion from one round influences SB/SR values in the next round.

This creates a structural distinction:

```text
SB/SR before sufficient diffusion -> local constraints
MC/ARK after diffusion -> column/global constraints
Temporal multi-round observation -> diffusion accumulates over time
```

The method therefore does not only say:

```text
unique
```

It says:

```text
unique because these taps cross the diffusion boundary and jointly constrain enough key-byte dependencies
```

or:

```text
ambiguous because these taps remain byte-local or redundant under the observed temporal depth
```

## 6. Why AES Structure Predicts The Observed Classes

### 6.1 Early-Only SB/SR Leakage

SB and SR outputs are early-layer semantic surfaces.

- `SB_i` depends on one state byte after AddRoundKey.
- `SR_i` is a byte permutation of SB output.
- No MixColumns has occurred yet at that subround boundary.

Therefore, an early-only leakage set tends to constrain isolated byte functions. It often leaves many master-key bytes free.

This is exactly what the integrated data shows:

| Leakage | early-only cases | all ambiguous | any unique |
|---|---:|---:|---:|
| 2-bit | 86 | 86 | 0 |
| 3-bit | 86 | 86 | 0 |
| 4-bit | 56 | 49 | 7 |

The 4-bit exception is important. It shows the boundary is not simply "early is safe." The correct statement is:

> Early-only leakage is low-risk at 2 and 3 taps under the tested depth, but selected 4-tap early-only configurations can become unique because temporal observations include cross-round diffusion effects.

### 6.2 Late MC/ARK Leakage

MC and ARK are late semantic surfaces.

`MC_i` is after the column-mixing layer. Even a single MC output bit is a Boolean constraint over a linear combination of four S-box outputs. Over many plaintexts and temporal observations, this can constrain a much larger portion of `K0`.

`ARK_i` is similarly late, because it is after MixColumns and key addition.

Integrated 2-bit behavior:

| 2-bit late count | Cases | unique-any rate |
|---:|---:|---:|
| 0 late taps | 86 | 0.0% |
| 1 late tap | 184 | 43.5% |
| 2 late taps | 148 | 90.5% |

The risk jumps when both observed FFs are late-class.

### 6.3 Mixed Early+Late Leakage

Mixed early+late leakage is the most subtle class.

It cannot be summarized as simply dangerous or safe.

Integrated 2-bit mixed class:

| Class | all ambiguous | all unique | some unique |
|---|---:|---:|---:|
| early_late_mixed | 104 | 74 | 6 |

This means mixed leakage is **topology-sensitive**. The late tap may provide a diffusion bridge, but the early tap must be complementary rather than redundant.

This is where the methodology needs a map. A single scalar such as tap count cannot explain this class.

### 6.4 Higher-Order Escalation

The 3-bit and 4-bit experiments are not exhaustive. They are hard-case escalation studies.

They answer:

> If a 2-bit subset is not enough, does adding one or two more sparse FFs cross the identifiability threshold?

Observed pattern:

| Leakage | late_count 0 | late_count 1 | late_count 2 | late_count 3/4 |
|---|---:|---:|---:|---:|
| 3-bit unique-any rate | 0.0% | 4.2% | 63.9% | 95.5% |
| 4-bit unique-any rate | 12.5% | 0.0% | 92.3% | 100.0% |

The 4-bit `late_count=1` result is from a hard-case biased sample, so it should not be generalized as a theorem. The robust signal is that two or more late-class taps become very strong.

## 7. Concrete Examples From The Experiments

### Example A: 2-bit early-only ambiguity

Case:

```text
SB_0__SR_0
```

Observed result:

```text
20/20 runs: ambiguity
```

Interpretation:

- Both taps are early semantic surfaces.
- `SB_0` and `SR_0` are byte-local / permutation-related observations.
- They constrain only a small local portion of the AES state/key relation.
- The second solve finds an alternative key, so the master key is not uniquely determined.

Methodological point:

> This is not a solver failure. It is a proven ambiguity under the leakage model because `C(K) AND K != K*` is SAT.

### Example B: 2-bit late unique recovery

Case:

```text
MC_0__ARK_1
```

Observed result:

```text
3/3 runs: full_key_unique
query_count: 96 for all observed seeds
```

Interpretation:

- Both taps are late-class semantic FFs.
- `MC_0` is after MixColumns diffusion.
- `ARK_1` is after MixColumns plus key addition.
- The two temporal leakage streams provide complementary post-diffusion constraints.
- The second solve is UNSAT, so no alternative master key satisfies the same leakage.

Methodological point:

> Two 1-bit FFs can be enough if their semantic positions lie beyond the AES diffusion boundary.

### Example C: 2-bit mixed ambiguity from gap coverage

Case:

```text
SB_1__MC_24
```

Observed result:

```text
3/3 runs: ambiguity
query_count: 32 for all observed seeds
```

Interpretation:

- This case has one early tap and one late tap.
- Stage membership alone might suggest risk, but the solver proves ambiguity.
- The early and late constraints do not complement each other enough under this topology.

Methodological point:

> Mixed early+late leakage must be evaluated topologically. It is not automatically high-risk.

This is why Phase 7_1 matters. It filled structural gaps that Phase 7 did not cover and exposed boundary cases.

### Example D: 3-bit weak-late escalation

Case:

```text
3bit_weak_late__ARK_15__ARK_27__MC_12
```

Observed result:

```text
3/3 runs: full_key_unique
query_count: 64 or 96
```

Interpretation:

- The case was selected as a hard case without a known unique 2-bit subset.
- The third late-class tap adds enough independent constraint to break the ambiguity.
- This shows a threshold transition: weak/redundant late 2-bit structures can become unique at 3 bits.

Methodological point:

> The method can identify not only high-risk pairs, but also escalation thresholds for hard topologies.

### Example E: 4-bit early-only breakthrough

Case:

```text
4bit_early__SB_114__SB_4__SB_80__SR_14
```

Observed result:

```text
3/3 runs: full_key_unique
query_count: 128 or 192
```

Candidate locations:

| Candidate | Stage | Byte | Column | Row | Bit-in-byte |
|---|---|---:|---:|---:|---:|
| SB_114 | SB | 14 | 3 | 2 | 2 |
| SB_4 | SB | 0 | 0 | 0 | 4 |
| SB_80 | SB | 10 | 2 | 2 | 0 |
| SR_14 | SR | 1 | 0 | 1 | 6 |

Interpretation:

- All taps are early semantic surfaces.
- If viewed only within one round before diffusion, this should look local.
- But temporal observations over depth 2 include later-round effects.
- Values at early surfaces in the next round have already absorbed previous-round MixColumns diffusion.
- With four carefully placed early taps, enough cross-round constraints accumulate to isolate `K0`.

Methodological point:

> Early-only is not a permanent safety label. It is safe at low tap count in the tested data, but temporal diffusion can make selected 4-tap early-only leakage uniquely identifying.

### Example F: 4-bit early-only ambiguity remains common

Case:

```text
4bit_gap_early__SB_0__SB_22__SB_30__SR_0
```

Observed result:

```text
3/3 runs: ambiguity
```

Interpretation:

- This is also early-only 4-bit leakage.
- Unlike Example E, the selected positions do not produce enough complementary cross-round constraints.
- Therefore, 4-bit early-only success is topology-dependent.

Methodological point:

> The map must preserve both unique and ambiguous early-only 4-bit cases. Collapsing them into one label would lose the main scientific signal.

### Example G: 4-bit mixed gap unique recovery

Case:

```text
4bit_gap_mixed__MC_105__MC_47__MC_85__SB_93
```

Observed result:

```text
3/3 runs: full_key_unique
query_count: 64
```

Interpretation:

- Three taps are MC late-class taps.
- One tap is SB early-class.
- The late taps already provide strong diffusion-aware constraints.
- The early tap can act as an additional alignment or disambiguation constraint.

Methodological point:

> Once enough late-class support exists, even sparse 4-bit leakage becomes strongly key-identifying.

## 8. What Exactly Is Novel Here?

There are two possible novelty claims. One is weaker; one is stronger.

### Weaker claim

> We perform SAT-based AES key recovery from sparse scan leakage.

This is not the best framing. SAT/SMT-based AES analysis and key recovery are not new in a broad sense.

### Stronger claim

> We introduce a diffusion-aware methodology for attributing scan-visible 1-bit FFs to cryptographic leakage variables and testing whether sparse temporal leakage from those FFs uniquely identifies the AES-128 master key.

This is more defensible because it combines:

1. 1-bit scan FF granularity.
2. Semantic/function attribution of FF values.
3. Temporal sparse leakage modeling.
4. SAT-based uniqueness, not just candidate recovery.
5. AES diffusion-aware explanation.
6. Empirical semantic risk map generation.

The novelty is therefore not just the solver. It is the full attribution-to-identifiability pipeline.

## 9. The Method As An Algorithm

### Input

- AES implementation or clean AES semantic model.
- Set of scan-visible 1-bit FFs.
- Plaintext observations or chosen plaintext capability.
- Temporal leakage traces for selected FFs.

### Output

For each FF set:

- semantic/function attribution
- `full_key_unique`, `ambiguity`, or `undecided`
- risk label
- AES diffusion-aware explanation
- applicability note: clean semantic, retimed equivalent, or function-specific analysis needed

### Pseudocode

```text
for each scan-visible FF f:
    cone_f = extract_D_input_cone(f)
    class_f = attribute_to_AES_semantic_or_internal_function(cone_f)

for each sparse FF set S of size k:
    if all FFs in S are clean semantic or retimed-clean:
        taps = map_to_semantic_surface(S)
    else:
        taps = build_function_specific_oracle(S)

    C(K) = build_temporal_leakage_constraints(taps, observations)

    result1 = solve(C(K))
    if result1 != SAT:
        label = modeling_error_or_undecided
        continue

    K_star = model(result1)
    result2 = solve(C(K) AND K != K_star)

    if result2 == UNSAT:
        label = full_key_unique
    elif result2 == SAT:
        label = ambiguity
    else:
        label = undecided

    explanation = attribute_label_to_AES_diffusion_structure(S, label)
    record_map_entry(S, label, explanation)
```

## 10. Risk Labels For A Map

Recommended case-level labels:

| Label | Meaning |
|---|---|
| `confirmed_high_risk` | all seeds/runs are `full_key_unique` |
| `confirmed_low_risk` | all seeds/runs are `ambiguity` |
| `boundary_or_seed_sensitive` | mixed unique/ambiguous outcomes |
| `not_resolved` | any final UNKNOWN remains |
| `function_specific_needed` | FF does not match clean semantic surface |

Recommended structural labels:

| Structural label | Meaning |
|---|---|
| `early_only_low_order` | SB/SR-only at 2 or 3 taps; empirically ambiguous |
| `early_only_temporal_breakthrough` | SB/SR-only at 4 taps with unique recovery |
| `late_dominant` | MC/ARK-heavy leakage; usually high-risk |
| `weak_late_escalating` | same-column/redundant late leakage that becomes unique with more taps |
| `mixed_complementary` | early+late taps that jointly identify the key |
| `mixed_redundant_or_local` | early+late taps that remain ambiguous |

These labels are better than simply saying safe/unsafe because they preserve the AES reason behind the result.

## 11. How This Becomes A Paper Methodology Section

A paper section could be structured as follows.

### 11.1 Problem

Existing scan-security views often treat scan FF leakage as a physical observability problem. But for cryptographic hardware, the security impact of observing a FF depends on what cryptographic Boolean value it stores.

### 11.2 Method

We define a scan-FF leakage attribution method:

1. Attribute each FF to a clean AES semantic bit or an internal Boolean function.
2. Construct sparse temporal leakage constraints.
3. Use a two-solve SAT uniqueness test.
4. Assign a diffusion-aware risk label.

### 11.3 Empirical Map

We instantiate the method on AES clean semantic surfaces and evaluate 2/3/4-bit leakage sets.

### 11.4 Key Result

The resulting map shows that:

- 2-bit early-only leakage is consistently ambiguous.
- 2-bit late leakage is frequently unique.
- Mixed leakage is topology-sensitive.
- 3/4-bit escalation collapses many weak late ambiguities.
- 4-bit early-only leakage can become unique in selected temporal-diffusion configurations.

### 11.5 Hardware Implication

A synthesized AES design should be assessed not by counting exposed scan FFs alone, but by attributing those FFs to cryptographic semantic/function classes and evaluating key identifiability.

## 12. What To Avoid Overclaiming

Do not claim:

> Any 2-bit leakage recovers AES-128.

The data disproves this.

Do not claim:

> Any early-only leakage is safe.

The 4-bit Phase 7 early-only unique cases disprove this.

Do not claim:

> Any mixed early+late leakage is high-risk.

Phase 7_1 found many 2-bit mixed gap cases that remained ambiguous.

Do not claim:

> The semantic map automatically applies to all synthesized FFs.

It applies directly only when the physical FF is equivalent to a clean semantic bit. Internal nodes require new function-specific analysis.

The defensible claim is:

> Sparse scan-visible FF leakage has a cryptographic risk that can be attributed, tested, and explained through AES semantic diffusion topology.

## 13. Why The Method Has Practical Value

For a real AES hardware evaluator, the method gives a concrete workflow.

Without this method, the evaluator might ask:

```text
How many scan FFs are exposed?
```

With this method, the evaluator asks:

```text
Which Boolean AES values do the exposed FFs store?
Do these values cross AES diffusion boundaries?
Does their temporal leakage uniquely determine K0?
If unique, which semantic/topological relation explains the collapse?
```

This changes the security analysis from physical visibility to cryptographic identifiability.

That is the important conceptual shift.

## 14. Suggested Figure

A useful paper figure would be:

```text
Physical netlist
   |
   v
Scan-visible 1-bit FFs
   |
   v
D-input cone extraction
   |
   v
Semantic/function attribution
   |------------------------------|
   |                              |
clean SB/SR/MC/ARK bit        internal Boolean node
   |                              |
   v                              v
semantic risk map             function-specific SAT oracle
   |                              |
   |--------------|---------------|
                  v
        temporal leakage constraints C(K)
                  |
                  v
        SAT uniqueness test
                  |
                  v
    unique / ambiguous / unresolved
                  |
                  v
       AES diffusion-aware explanation
```

The point of the figure is to show that the map is not the end product by itself. It is one layer inside a larger scan-FF attribution methodology.

## 15. Final Condensed Contribution Statement

A concise contribution statement could be:

> We propose a diffusion-aware scan-FF leakage attribution methodology for AES hardware. The method maps scan-visible 1-bit FFs to cryptographic semantic or Boolean-function classes, constructs sparse temporal leakage constraints, and uses a two-solve SAT procedure to determine whether the leakage uniquely identifies the AES-128 master key. Applying this methodology to clean AES subround surfaces yields an empirical semantic risk map showing that key identifiability is governed by diffusion topology rather than tap count alone.

A more direct version:

> Our methodology turns scan-visible flip-flops from unnamed physical cells into cryptographic leakage variables with measurable key-identifiability risk.

This is the cleanest conceptual framing.
