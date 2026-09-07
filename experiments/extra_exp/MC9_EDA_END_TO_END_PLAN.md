# MC_9 1-Bit Adaptive Key-Recovery EDA Replication Plan

## 1. Purpose

This experiment is a single-case, controlled end-to-end replication of the
existing semantic attack result `late1_MC_9__seed2` on a real
Synopsys-synthesized and scan-inserted AES-128 DUT.

The experiment does not measure how often synthesis naturally exposes MC bits.
It intentionally instantiates one known vulnerable condition: the semantic
post-MixColumns bit `MC_9` is stored in a real sequential cell and included in
an otherwise anonymous scan chain. The attack lane is not given the scan map,
the target FF name, the physical scan position, or the secret key.

The required end-to-end result is:

```text
anonymous gate-level scan-out
  -> Phase 0 discovers one stable post-MC slot s*
  -> the same physical slot is reused at rounds 1 and 2
  -> gate-level Q128 leakage reproduces SAT -> SAT
  -> an adaptive separator is generated from the surviving key pair
  -> that plaintext is applied to the gate-level DUT
  -> the added scan observation produces SAT -> UNSAT
  -> the unique key equals the evaluator-only hidden K0
```

This directory is independent from `eda_validation/`. No result, report, scan
map, testbench, or success claim from that separate experiment is accepted as
evidence here.

## 2. Frozen Representative Case

The representative case is fixed before any RTL or EDA work.

| Field | Frozen value |
|---|---|
| Case | `late1_MC_9__seed2` |
| Semantic tap | `MC_9` |
| Stage | post-MixColumns, pre-ARK |
| Semantic byte/bit | byte 1, bit 1, with bytes in AES column-major order and bits LSB-first |
| Temporal depth | rounds 1 and 2 |
| Leakage mode | differential against query 0 |
| Seed | `2` |
| Hidden K0 | `a66f651322597191ab9f8f8af4c2db61` |
| Reference plaintext P0 | `00000000000000000000000000000000` |
| Fixed-query budget | 128 non-reference plaintexts plus P0 |
| Gate-level encryptions for fixed phase | 129 plaintext executions per capture round |
| Fixed first model Ka | `a66f651322597191ab9f8f8af4c2db61` |
| Fixed alternative Kb | `a6bc656971597191ab438f849fc2b861` |
| Fixed classification | `SAT -> SAT`, finite-query ambiguity |
| Known separator from semantic run | `f4000000004800d86000586000cb0010` |
| Expected separator leakage under Ka | round 1 = 0, round 2 = 1 |
| Expected separator leakage under Kb | round 1 = 0, round 2 = 0 |
| Adaptive classification | `SAT -> UNSAT`, full-key unique |
| Total non-reference queries | 129 |
| Total plaintext executions including P0 | 130 per capture round |

Authoritative source artifacts:

- `anonymous_subround_multiround_attack_8_oracle/results/late_1bit_fixed_q128_runs/late1_MC_9__seed2__late1bit_fixed_q128.json`
- `anonymous_subround_multiround_attack_8_oracle/results/late_1bit_pair_rescue_runs/late1_MC_9__seed2__late1bit_pair_rescue.json`
- `anonymous_subround_multiround_attack_8_oracle/scripts/experiment_common.py`
- `anonymous_subround_multiround_attack_8_oracle/scripts/run_late1bit_pair_rescue.py`

The deterministic source definitions are:

```python
K0 = SHA256("oracle-key-2")[:16]
Q128 = nested_plaintexts(query_count=128, seed=2)
```

`nested_plaintexts(128, 2)` returns 129 plaintexts: P0 followed by 128
non-reference one-byte-difference plaintexts. The adaptive separator is not a
member of this fixed set.

## 3. Claims and Non-Claims

### 3.1 Claims enabled by a PASS

1. A real scan-inserted FF can preserve the Boolean and temporal semantics of
   the software-modelled `MC_9` channel.
2. An anonymous scan slot can be selected by the MC-aware Phase 0 procedure and
   reused across round-1 and round-2 observations.
3. Gate-level scan data can reproduce the existing Q128 ambiguity.
4. A solver-generated distinguishing plaintext can be returned to the same
   gate-level DUT and convert that ambiguity into a proven unique AES-128 key.
5. The complete evidence chain can be inspected in Verdi through saved FSDB and
   session artifacts.
6. For the declared C0 MC-function family, anonymous Q128 attribution can reduce
   32 hypotheses to the single surviving hypothesis `h09` before handoff.

### 3.2 Claims explicitly excluded

- No prevalence claim over arbitrary AES implementations or all scan insertions.
- No claim that DFT Compiler naturally selected `MC_9`; its inclusion is an
  experimental condition.
- No exact physical placement or routing claim.
- No universal exact MC row/bit attribution claim is made for arbitrary AES implementations. In this representative C0 family, anonymous hypothesis enumeration retained `h09`; the evaluator confirms only afterward that h09 is `MC_9`.
- No use of solver `UNKNOWN` as success or failure.
- No reuse of synthetic scan vectors as gate-level observations.

## 4. Architecture Options

### Option A: File-Orchestrated Batch VCS, Recommended

Each phase writes an immutable input manifest, runs the same compiled gate-level
VCS executable, and emits scan vectors as JSONL. Python parses the output,
invokes Phase 0 or Z3, and writes the next manifest. VCS is relaunched after the
solver creates an adaptive plaintext.

Advantages:

- no VCS process must remain blocked while Z3 runs;
- every transition has a replayable input/output artifact;
- failures can resume from the last valid phase;
- the attacker and evaluator data lanes can be audited separately;
- FSDB dumping can be disabled for bulk queries and enabled only for evidence
  replays.

Cost: repeated reset and simulation startup overhead. For one case this is
acceptable and is outweighed by reproducibility.

### Option B: Long-Lived VCS with DPI/VPI or Socket Control

VCS waits for Python/Z3 and accepts newly generated plaintexts at runtime.

Advantages: lower process startup overhead and a visually continuous waveform.

Disadvantages: more synchronization code, fragile license/session handling,
harder deterministic replay, and a larger risk that solver state and evaluator
state leak into the testbench. This option is rejected for the first experiment.

### Option C: Static Replay of the Existing Separator Only

The known semantic separator is applied after Q128 without regenerating it.

Advantages: simplest bridge validation.

Disadvantages: proves semantic-to-gate equivalence but not a closed adaptive
loop. It is retained only as a control lane. The primary result must regenerate
a separator from the gate-level Q128 survivor pair.

## 5. Planned Directory Contract

Only this plan exists initially. Implementation will create the following
isolated structure:

```text
extra_exp/
  MC9_EDA_END_TO_END_PLAN.md
  README.md
  provenance/
    source_hashes.sha256
    tool_versions.txt
    frozen_case.json
  inputs/
    phase0_queries.json
    mc9_seed2_q128.json
    known_separator_control.json
    hidden_key.evaluator.json
  rtl/
    aes128_iterative_mc_boundary.v
    aes_sbox.v
    scan_decoy_bank.v
    extra_exp_top.v
  tb/
    extra_exp_gate_tb.sv
    fsdb_control.sv
  dft/
    run_synthesis.tcl
    run_scan_insertion.tcl
    partial_scan_manifest.txt
  netlist/
    extra_exp_prescan.v
    extra_exp_postscan.v
    extra_exp_postscan.sdf
  scripts/
    build_frozen_inputs.py
    run_vcs_batch.py
    extract_scan_vectors.py
    run_phase0.py
    build_solver_observation.py
    run_fixed_solver.py
    generate_separator.py
    run_adaptive_solver.py
    audit_information_flow.py
    verify_semantic_equivalence.py
    build_verdi_bundle.sh
  results/
    phase0/
    phase1/
    phase2/
    evaluator/
    final_summary.json
  logs/
    synthesis.log
    dft.log
    vcs_compile.log
    phase0_vcs.log
    phase1_vcs.log
    phase2_vcs.log
    solver_fixed.log
    solver_adaptive.log
  verdi/
    fsdb/
    sessions/
    screenshots/
    markers/
    README_VISUAL_EVIDENCE.md
```

Generated netlists, FSDB files, compiled VCS databases, and tool logs must be
excluded from source-control commits if their size is unsuitable, but their
paths and SHA-256 hashes must be recorded in the final evidence manifest.

## 6. DUT Design

### 6.1 Functional AES

The DUT will be a standalone, standard AES-128 iterative core, not a one-round
toy datapath. It must pass known-answer tests for complete 10-round AES-128
encryption before DFT.

The core will contain one physical post-MixColumns sequential boundary reused
by rounds 1 through 9:

```text
STATE_REG
  -> SubBytes
  -> ShiftRows
  -> MixColumns
  -> MC_REG[127:0]       physical post-MC boundary
  -> AddRoundKey
  -> STATE_REG
```

The final AES round bypasses MixColumns according to FIPS-197. Round keys are
generated by the standard AES-128 key schedule. Key registers are explicitly
excluded from scan.

### 6.2 Semantic Packing Contract

Internal semantic packing will be explicit:

```text
MC_REG[8*i +: 8] = AES state byte i
MC_REG[8*i + b]  = semantic bit 8*i+b
```

Therefore `MC_9` is physically represented before synthesis as `MC_REG[9]`.
No implicit Verilog MSB/LSB convention may be used to infer this mapping. A
pre-synthesis assertion and a post-synthesis evaluator mapping report must
confirm it.

### 6.3 Scan Composition

The planned partial scan chain contains 256 cells:

- one target: `MC_REG[9]`;
- 127 AES state/round-register decoys that become active after ARK/update;
- 120 independent data/control decoys;
- 8 control/status decoys.

Other `MC_REG` bits remain functional FFs but are excluded from the scan set in
this representative experiment. This ensures that Phase 0 is tested against a
large anonymous stream without making exact target selection underdetermined by
many equally valid MC channels.

DFT Compiler creates the actual scan cells and one serial chain. The final
stitching order comes only from the generated scan-path report. The attack lane
receives only chain length and serialized SO values; the evaluator retains the
scan-path report and original-register mapping.

The secret-key storage, key schedule registers, and hidden-key testbench file
must never be included in scan or copied into attacker-visible outputs.

## 7. Testbench and VCS Control

### 7.1 Batch Interface

One gate-level SystemVerilog testbench reads plusargs:

```text
+MANIFEST=<query-manifest.jsonl>
+CAPTURE=phase0_mc|phase0_update|phase0_post|round1_mc|round2_mc
+OUTPUT=<scan-vector.jsonl>
+WAVE=0|1
+FSDB=<path>
```

For each manifest record, the testbench:

1. resets the DUT to a known state;
2. loads the evaluator-hidden K0 and attacker-selected plaintext;
3. starts AES and advances to the requested capture point;
4. asserts scan enable only after the target functional capture;
5. serially shifts the complete 256-cell chain;
6. writes the full anonymous SO vector with query and schedule labels;
7. resets before the next functional execution.

Round-1 and round-2 observations use separate reset/re-execution paths because
scan shifting destroys functional state. The scan slot index must remain fixed
between all runs because the same postscan netlist is reused.

### 7.2 Tool Configuration

Audited executables currently visible in the environment are:

```text
VCS    R-2020.12-SP1
Verdi  R-2020.12-SP1
DC     S-2021.06-SP4
```

VCS compilation must enable 64-bit execution, SystemVerilog, gate-level timing
support, KDB, debug access, and Verdi FSDB PLI. The exact compile and run command
lines must be captured in `logs/vcs_compile.log` and phase logs.

The campaign path runs with waveform dumping disabled. Evidence replays use the
same postscan netlist and compiled simulator with FSDB enabled for selected
queries only.

## 8. Experimental Phases

### Phase A: RTL, Synthesis, and Scan Integrity

1. Verify full AES ciphertext against standard known-answer vectors.
2. Verify round-1 and round-2 `MC_REG` values against the inherited Python AES
   reference for at least P0, Q30, and Psep.
3. Synthesize with DC and insert the 256-cell partial scan chain.
4. Confirm the target original register maps to one scan cell.
5. Confirm no key or key-schedule register is in scan.
6. Verify serial shift order by loading a known walking-one pattern and comparing
   SO against the evaluator scan-path report.
7. Verify functional ciphertext equivalence with scan disabled.

Failure in this phase stops the attack. No solver result is meaningful until
the scan and functional integrity checks pass.

### Phase 0: Anonymous MC Leakage-Channel Discovery

Use the existing coarse discovery set:

```text
P0
+ 16 plaintext-byte positions
  x {0x01, 0x02, 0x04, 0x08}
= 65 plaintexts
```

For each plaintext collect three full scan vectors:

- MC capture;
- ARK/round-register update boundary;
- post-update.

The attacker-side discovery input contains only plaintext labels, schedule
labels, and anonymous SO vectors. It excludes K0, FF names, scan stitching,
ground-truth class, and MC bit index.

The discovery implementation will be adapted from:

- `anonymous_subround_multiround_attack_Leakage_Channel_Discovery/scripts/discover_mc_channel_gate_v1.py`;
- `anonymous_subround_multiround_attack_Leakage_Channel_Discovery/scripts/refine_mc_channel_joint_v1.py`;
- `anonymous_subround_multiround_attack_Leakage_Channel_Discovery/scripts/export_channel_observation.py`.

Phase 0 passes when the selected slot is stable, first active at MC capture,
shows ShiftRows-aligned column support, survives held-out checks, and maps to the
target `MC_REG[9]` only when the evaluator opens the scan truth.

### Phase 0.5: Anonymous MC-Function Attribution and Handoff

The supplemental run removes the former evaluator-label dependency from the
channel-to-function interface. The attacker receives only the selected slot,
the inferred C0 support, and the gate-level Q128 transcript:

```text
anonymous slot s*=255 + C0 support
  -> generate h00..h31 for the 32 MC output bits in C0
  -> evaluate every hypothesis against the Q128 transcript
  -> 31 hypotheses UNSAT, h09 survives
  -> pass h09 as the inferred Boolean-function hypothesis to Phase 1
```

The attack-side artifacts contain no `MC_9`, `MC9`, hidden K0, scan mapping, or
evaluator label. The evaluator opens `MC_REG[9]` and the scan path only after the
attribution result for post-hoc correctness. This is a family-local attribution,
not a universal claim that every anonymous MC bit can be identified exactly.

### Phase 1: Gate-Level Q128 Ambiguity Reproduction

Apply P0 and all 128 frozen non-reference plaintexts to the same postscan DUT.
For every plaintext, separately capture and shift the round-1 and round-2 MC
states. Extract only slot `s*` and convert it to the existing
`aes-sparse-oracle-v1` differential schema with surviving anonymous function hypothesis `h09`.

Before invoking Z3, compare all gate-level leakage bits against the semantic
reference:

```text
129 plaintexts x 2 rounds = 258 differential bits
required equality: 258 / 258
```

Any mismatch is a bridge failure and must not be hidden by continuing to solve.

The fixed solver uses depth 2, differential mode, `uf_axiom`, and no timeout.
Required result:

```text
first solve  = SAT
second solve = SAT
classification = ambiguity
true K0 remains consistent in evaluator-only validation
```

The exact returned candidate ordering is not a PASS condition. Candidate models
may differ across Z3 versions while the ambiguity classification remains valid.

### Phase 2A: Known-Separator Replay Control

Apply the previously recorded separator
`f4000000004800d86000586000cb0010` to the gate-level DUT, capture the same slot
at rounds 1 and 2, and append the observation to Q128.

This control must produce the true-DUT differential response `(0, 1)` and reject
the previously recorded alternative key, which predicts `(0, 0)`.

Required result: `SAT -> UNSAT`, with the unique key equal to hidden K0.

### Phase 2B: Closed-Loop Adaptive Recovery, Primary Result

Restart from the gate-level Q128 transcript. Use the current first and
alternative models returned by that run to synthesize an unrestricted pairwise
separator. Do not force it to equal the historical separator.

```text
gate-level Q128
  -> SAT, SAT
  -> current Ka, Kb
  -> synthesize Psep'
  -> write adaptive manifest
  -> VCS re-query of same postscan DUT
  -> append SO[s*] round-1/round-2 leakage
  -> solve entire key space again
```

Required terminal result:

```text
first solve  = SAT
second solve = UNSAT
classification = full_key_unique
recovered K0 = a66f651322597191ab9f8f8af4c2db61
UNKNOWN count = 0
```

If pairwise separator synthesis is UNSAT, the existing global-separator fallback
may run. If either solver returns UNKNOWN, the experiment is unresolved and
must preserve its checkpoint for diagnosis.

## 9. Attacker/Evaluator Information Separation

The orchestration is split into two data lanes.

### Attacker-visible

- chosen plaintexts;
- capture schedule labels;
- anonymous complete SO vectors during Phase 0;
- selected slot index after Phase 0;
- extracted differential bits at the selected slot;
- public AES-128 model;
- the surviving anonymous function hypothesis `h09` after Phase 0.5 attribution;
- solver models and synthesized separator plaintexts.

### Evaluator-only

- hidden K0 file;
- scan-path report and original-register mapping;
- hierarchical target FF name;
- truth that the selected slot maps to `MC_REG[9]`;
- semantic reference transcript;
- recovered-key correctness comparison.

The inherited solver currently embeds `evaluator.true_key_hex` in its input
document for diagnostics. The EDA implementation must not pass that document
unchanged to the attacker lane. The solver interface must accept a sanitized
observation document; true-key satisfiability and correctness checks run later
in a separate evaluator process and must not contribute constraints.

An audit script will list every file opened by each lane and fail if an
attacker-side file contains K0, target hierarchy, or scan-map fields.

## 10. Verdi Evidence Plan

### 10.1 Bulk Versus Evidence Runs

Dumping every signal for all Phase 0 and Q128 transactions would create a large,
slow FSDB without improving the claim. Therefore:

- bulk discovery and Q128 runs: FSDB disabled;
- selected evidence replays: FSDB enabled with full hierarchy and scan signals;
- every evidence replay uses the identical postscan netlist, hidden key, scan
  map, and capture schedule as the bulk run.

### 10.2 Required FSDB Files

1. `phase0_mc_slot_discovery.fsdb`
   - P0 and one coarse discovery plaintext that toggles the selected slot;
   - MC capture, update, and post-update schedules;
   - demonstrates first-active timing and serial SO position.
2. `phase1_q30_depth2.fsdb`
   - P0 and fixed query 30, plaintext
     `00000000005200000000000000000000`;
   - expected `MC_9` differential `(1, 1)`;
   - demonstrates the same physical scan slot at rounds 1 and 2.
3. `phase2_separator.fsdb`
   - P0 and the accepted adaptive separator;
   - for the historical Psep, true response `(0, 1)`;
   - demonstrates scan capture, shift, and the observation that eliminates Kb.
4. `scan_shift_identity.fsdb`
   - walking-one scan integrity check;
   - demonstrates the evaluator mapping between one physical scan cell and SO
     slot `s*`.

### 10.3 Verdi Sessions and Figures

For each FSDB, save a Verdi session with fixed signal groups and time markers:

```text
Functional control: clk, reset_n, start, round, phase
Data: plaintext, STATE_REG, MC_REG[9]
Scan: scan_en, scan_in, scan_out, shift_count
Evaluator overlay: target scan-cell Q and selected slot marker
```

The visual bundle must include:

- FSDB files;
- VCS KDB/debug database reference;
- Verdi session files;
- a text signal manifest;
- marker CSV files naming capture and shift intervals;
- at least three PNG screenshots: Phase 0 timing, round-1/round-2 slot identity,
  and adaptive separator elimination;
- `README_VISUAL_EVIDENCE.md` describing exactly what each figure proves and
  distinguishing attacker-visible signals from evaluator-only overlays.

The final report must never use a waveform screenshot as the only evidence.
Every pictured bit must also be present in machine-readable scan-vector and
solver-result artifacts.

## 11. Pass, Fail, and Unresolved Criteria

### PASS

All conditions must hold:

1. RTL and postscan functional AES known-answer tests pass.
2. The chain contains exactly the declared partial-scan set, includes the target,
   and excludes all key registers.
3. Scan shifting matches the generated scan-path report.
4. Phase 0 selects a stable slot that evaluator truth maps to `MC_REG[9]`.
5. The slot identity is unchanged at round-1 and round-2 capture.
6. Gate-level and semantic Q128 leakage match for all 258 bits.
7. Gate-level Q128 yields `SAT -> SAT` with no UNKNOWN.
8. The adaptive plaintext is applied to the actual postscan DUT.
9. The final complete-key check yields `SAT -> UNSAT` with no UNKNOWN.
10. The unique key equals hidden K0.
11. The information-flow audit passes.
12. All required Verdi/FSDB evidence artifacts exist and reopen successfully.

### FAIL

- Phase 0 selects only a non-MC/update slot.
- The selected slot changes between rounds or queries.
- Any Q128 gate-level leakage bit disagrees with the semantic reference.
- The fixed gate-level transcript does not reproduce ambiguity after equivalence
  has otherwise passed.
- A proven global non-separability result is returned.
- The final unique key differs from hidden K0.
- Ground-truth key or scan mapping leaks into attacker-side inputs.

### UNRESOLVED

- VCS, Verdi, DC, library, or license failure prevents a required run.
- Scan capture contains unresolved X/Z values.
- Capture timing cannot distinguish MC and update boundaries.
- Z3 or separator synthesis returns UNKNOWN.
- FSDB cannot be reopened or correlated with machine-readable results.

## 12. Implementation and Verification Order

1. Freeze provenance, K0, Q128, historical Psep, and source hashes.
2. Implement and verify full AES RTL with explicit MC semantic packing.
3. Implement attacker/evaluator-separated testbench I/O.
4. Synthesize and insert the declared partial scan chain.
5. Prove scan integrity and key-register exclusion.
6. Compile one reusable VCS/KDB simulation image.
7. Run Phase 0 and lock selected slot `s*`.
8. Run Phase 0.5 anonymous C0 hypothesis attribution and handoff audit.
9. Run Q128 gate-level collection and 258-bit semantic equivalence check.
10. Run fixed solver and require `SAT -> SAT`.
11. Run known-separator gate-level control.
12. Restart Q128 and execute closed-loop separator generation and DUT re-query.
13. Require final `SAT -> UNSAT` and exact K0 match.
14. Replay selected transactions with FSDB enabled.
15. Save Verdi sessions, screenshots, marker files, and visual-evidence guide.
16. Generate one final JSON summary that links every claim to raw artifacts.

No later phase may continue after an earlier invariant fails. In particular,
the solver must not be used to conceal a scan-capture or semantic-equivalence
error.

## 13. Supplemental execution addendum

The supplemental Phase 0.5 run is now extended through the final anonymous
adaptive solve. It uses the same gate-level transcript and declared C0
hypothesis family; no new physical mapping is supplied to the attack lane.

```text
Phase 0 anonymous slot discovery
  -> C0 support attribution
  -> 32 MC-function hypotheses
  -> Q128 eliminates 31, h09 survives
  -> adaptive gate-level extensions Q128/Q129/Q130 remain SAT -> SAT
  -> Q131 final transcript yields SAT -> UNSAT
```

The measured Q131 result is:

```text
surviving hypothesis = h09
first solve          = SAT
second solve         = UNSAT
classification       = full_key_unique
UNKNOWN/timeout      = 0/0
key exclusion        = all surviving hypotheses
```

This closes the anonymous `scan slot -> MC function hypothesis -> gate-level
transcript -> adaptive full-key uniqueness` path for the declared C0 family on
the representative scan-inserted DUT. The evaluator uses MC9 mapping and hidden
K0 only for post-hoc correctness checks. It does not claim prevalence across
arbitrary synthesis, retiming, or DFT configurations.

The primary known-semantic EDA control remains separately recorded as Q128/Q129/Q130
with final `SAT -> UNSAT`; the supplemental Q131 result is the stronger anonymous
hypothesis-path result.

## Appendix A. Frozen P0 + Q128 Plaintext Manifest

The following list is the exact output of `nested_plaintexts(128, 2)`. Query 0
is P0; queries 1 through 128 are the fixed non-reference set.

```csv
query_id,plaintext_hex
0,00000000000000000000000000000000
1,0000000000000000000000008f000000
2,000000000000000000d3000000000000
3,00000000000000d10000000000000000
4,00005100000000000000000000000000
5,00000000000000000000000000003b00
6,00000000240000000000000000000000
7,96000000000000000000000000000000
8,00b60000000000000000000000000000
9,00000000000000df0000000000000000
10,00000000000000008c00000000000000
11,00000000008a00000000000000000000
12,00000000000000cc0000000000000000
13,00000000000000000000000000c40000
14,000000b0000000000000000000000000
15,00000900000000000000000000000000
16,0000000000000000002b000000000000
17,0000001f000000000000000000000000
18,00000000000000080000000000000000
19,00000000000000001600000000000000
20,0000000000dc00000000000000000000
21,00000000000000000000000000005400
22,00000000000000000000000000000026
23,0000000000000000000000a400000000
24,00000000002d00000000000000000000
25,00000000000000000000000000f30000
26,000000e4000000000000000000000000
27,00000000e00000000000000000000000
28,000000000000000000000000ab000000
29,53000000000000000000000000000000
30,00000000005200000000000000000000
31,00000000000000000000000031000000
32,0000b500000000000000000000000000
33,00000000000000003300000000000000
34,0000005a000000000000000000000000
35,00001e00000000000000000000000000
36,00000035000000000000000000000000
37,00470000000000000000000000000000
38,000000000000000000e8000000000000
39,00000000000040000000000000000000
40,000000000000000000000000003f0000
41,00000093000000000000000000000000
42,0000000000000000000000000000001b
43,8b000000000000000000000000000000
44,00000000000000007400000000000000
45,00000000000000007700000000000000
46,00000000000000a20000000000000000
47,00000000000000000000000000000086
48,00e00000000000000000000000000000
49,00000000000000005d00000000000000
50,00000000000014000000000000000000
51,000000000000000000000000000000b4
52,00002700000000000000000000000000
53,00000000740000000000000000000000
54,000000000000dc000000000000000000
55,00000000c70000000000000000000000
56,00000000000000000000000000000029
57,0000000000000000000000005d000000
58,0000bb00000000000000000000000000
59,000000000000000000009e0000000000
60,0000a400000000000000000000000000
61,00000000000000006a00000000000000
62,0000000000000000000000000000f000
63,000000000000000000002e0000000000
64,00000071000000000000000000000000
65,00000000000000000000004400000000
66,00000000000084000000000000000000
67,00000000000000000000000000008100
68,00000000000000000000400000000000
69,00000000000000000075000000000000
70,00000000000000150000000000000000
71,0000000000a600000000000000000000
72,000000000000009d0000000000000000
73,00000000000000000093000000000000
74,0000000000000000000000fb00000000
75,0000000000000000db00000000000000
76,000000000000bd000000000000000000
77,00000000000000ff0000000000000000
78,00000000700000000000000000000000
79,0000000000000000d500000000000000
80,00000000000000000000000000000021
81,00000000de0000000000000000000000
82,00000000000000040000000000000000
83,00000000000000000000000000dd0000
84,00000000006300000000000000000000
85,00000000000000000000300000000000
86,00000000000000000053000000000000
87,00000000000000d70000000000000000
88,63000000000000000000000000000000
89,000000000000000000000000b5000000
90,0000000000000000000000000000c300
91,000000000000000000000000b7000000
92,000000004f0000000000000000000000
93,0000000000fd00000000000000000000
94,0000ef00000000000000000000000000
95,00000000540000000000000000000000
96,00003900000000000000000000000000
97,0000000000000000000000a900000000
98,000000004e0000000000000000000000
99,00001c00000000000000000000000000
100,00000000b60000000000000000000000
101,0000000000000000000000005e000000
102,00000000000000100000000000000000
103,00000000000000000000f70000000000
104,000000cd000000000000000000000000
105,000000000000006b0000000000000000
106,007d0000000000000000000000000000
107,000000000000000000c9000000000000
108,00000000002400000000000000000000
109,0000000000d600000000000000000000
110,00006700000000000000000000000000
111,0000af00000000000000000000000000
112,00000000000000000000002000000000
113,000000000000000000000000b4000000
114,00000000660000000000000000000000
115,00000000000000000000000000001f00
116,00000000000000000000000000080000
117,00000000000000000000000000003500
118,000000000000000000000000000000df
119,0000000000000000000000bc00000000
120,00000000000000003e00000000000000
121,00000000000000007300000000000000
122,00004b00000000000000000000000000
123,000000000000000000009c0000000000
124,f4000000000000000000000000000000
125,00b70000000000000000000000000000
126,00000000000000003600000000000000
127,0000009a000000000000000000000000
128,00005f00000000000000000000000000
```

## Appendix B. Frozen Historical Adaptive Record

```json
{
  "case_id": "late1_MC_9",
  "seed": 2,
  "tap": {
    "stage": "MC",
    "bit_index": 9
  },
  "fixed_result": {
    "first_result": "sat",
    "second_result": "sat",
    "first_model": "a66f651322597191ab9f8f8af4c2db61",
    "alternative_model": "a6bc656971597191ab438f849fc2b861"
  },
  "historical_separator": {
    "plaintext_hex": "f4000000004800d86000586000cb0010",
    "ka_round1_round2": [0, 1],
    "kb_round1_round2": [0, 0]
  },
  "adaptive_result": {
    "first_result": "sat",
    "second_result": "unsat",
    "classification": "full_key_unique",
    "confirmed_unique_candidate": true
  }
}
```


## 13. Execution status and final evidence

The plan has been executed for the frozen representative case
`late1_MC_9__seed2`. The final result is `PASS` under the declared oracle
model and solver decision rule.

```text
Phase 0 anonymous discovery: PASS
  scan cells = 256
  selected serialized slot = 255
  first-active schedule = 1
  support = {0,5,10,15} = C0
  repeat stability = true for schedules 1,2,3

Phase 0 -> Phase 1 bridge: PASS
  Q128 query count = 129
  round-1/round-2 reference mismatch = 0

Fixed query: SAT -> SAT
  classification = finite-query ambiguity

Adaptive Q129: SAT -> SAT
  new alternative retained; loop continued

Adaptive Q130: SAT -> UNSAT
  classification = full-key unique
  UNKNOWN/timeout = 0

Historical separator control: SAT -> UNSAT
Held-out Phase 0 check: 3/3 selected-slot matches
Information-flow audit: PASS, violations = 0
Focused regression: 16 passed
```

The implementation uses the following actual path names for the planned
synthesis/DFT stages:

```text
planned run_synthesis.tcl       -> dft/run_dc.tcl
planned run_scan_insertion.tcl  -> dft/run_dft.tcl
planned results/phase0/*         -> results/phase_b/*
planned verdi/fsdb/*             -> results/verdi/*.fsdb
```

This naming difference does not change the experiment contract. The generated
netlists, scan-path report, evaluator-only mapping, attacker-side transcripts,
solver verdicts, Verdi FSDB/marker/session bundle, logs, and source/tool
provenance are hashed in:

```text
results/evidence_manifest.json
```

The exact interpretation boundary remains the one in Sections 1 and 3: this is
an end-to-end composability demonstration for one deliberately instantiated
scan-visible MC boundary, not a prevalence result for arbitrary synthesized
AES implementations.
