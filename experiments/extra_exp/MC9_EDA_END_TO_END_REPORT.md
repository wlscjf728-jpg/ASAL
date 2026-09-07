# MC9 EDA End-to-End Experiment Report

이 실험은 `late1_MC_9__seed2` semantic case를 대상으로, 동일한 AES-128 RTL을
Synopsys DC로 합성하고 DFT scan insertion을 거친 뒤 VCS gate-level DUT에서
anonymous scan-out, function attribution, adaptive key recovery까지 연결한
controlled EDA validation이다.

최종 판정은 **PASS**다.

기존 evaluator-confirmed semantic lane과 추가 anonymous hypothesis lane을
분리해 기록한다.

```text
[Primary EDA recovery lane]
MC-aware Phase 0 slot 255
  -> same physical slot at round 1/round 2
  -> Q128 SAT -> SAT
  -> adaptive Q129 SAT -> SAT
  -> adaptive Q130 SAT -> UNSAT

[Anonymous function-attribution lane]
same anonymous slot + C0 support
  -> 32 MC hypotheses
  -> 31 UNSAT, h09 only survives
  -> anonymous adaptive extensions Q128/Q129/Q130 remain SAT -> SAT
  -> Q131 SAT -> UNSAT
```

따라서 실제 합성/DFT/VCS DUT에서 발견된 1-bit scan channel이 MC function
hypothesis로 좁혀지고, 그 hypothesis를 사용한 adaptive solver가 최종
`SAT -> UNSAT`까지 도달함을 확인했다. `MC_REG[9]` mapping과 hidden K0는
correctness check에만 사용했다.

Q131은 Q128 fixed transcript 이후 두 차례의 anonymous adaptive extension을
포함한 최종 transcript이며, 최종 key-exclusion 범위는 모든 surviving
hypothesis다.

## 2. 실험 범위와 고정 조건

| 항목 | 값 |
|---|---|
| representative case | `late1_MC_9__seed2` |
| semantic channel | post-MixColumns, pre-ARK `MC_9` |
| temporal depth | round 1 and round 2 |
| leakage | query 0 대비 differential 1-bit leakage |
| P0 | `00000000000000000000000000000000` |
| hidden K0 | `a66f651322597191ab9f8f8af4c2db61` |
| fixed transcript | P0 + 128 plaintexts = 129 observations |
| primary adaptive transcript | Q128 + Q129 + Q130 = 131 observations |
| anonymous final transcript | Q131 = 131 observations |
| scan cells | 256 partial-scan cells |
| selected serialized SO slot | 255 |
| DFT path cell index | 0, evaluator-only |
| solver encoding | Z3 `uf_axiom` |
| timeout policy | unlimited (`timeout_ms=0`); UNKNOWN은 성공으로 취급하지 않음 |

원래 software campaign의 Q128과 hidden key는
`inputs/frozen_case.json`, `inputs/mc9_seed2_q128.json` 및
`provenance/source_hashes.sha256`로 고정했다. 기존 semantic 결과의 Q128
판정은 `SAT -> SAT`이며 alternative는
`a6bc656971597191ab438f849fc2b861`였다.

## 3. 구현 환경

| 구성요소 | 사용 도구 |
|---|---|
| AES RTL / testbench | SystemVerilog |
| RTL reference / scan signature 분석 | Python |
| synthesis / DFT | Synopsys Design Compiler S-2021.06-SP4 |
| gate-level simulation | Synopsys VCS R-2020.12-SP1 |
| waveform | Verdi R-2020.12-SP1 FSDB PLI |
| key consistency / separator synthesis | Z3, `uf_axiom` S-box model |

공식 실행 산출물은 다음 경로에 있다.

```text
extra_exp/rtl/
extra_exp/dft/
extra_exp/netlist/
extra_exp/tb/
extra_exp/results/evaluator/
extra_exp/results/phase_b/
extra_exp/logs/
extra_exp/results/verdi/
```

## 4. DUT와 scan 구성

AES-128은 one-round toy model이 아니라 standard 10-round iterative core로
구현했다. 기능 경계는 다음과 같다.

```text
STATE_REG
  -> SubBytes -> ShiftRows -> MixColumns
  -> MC_REG[127:0]
  -> AddRoundKey -> STATE_REG
```

`MC_REG`는 round 1부터 9까지 재사용되는 post-MixColumns sequential
boundary다. `MC_REG[9]`가 semantic `MC_9`가 되도록 byte-major, LSB-first
packing contract를 RTL과 Python reference에 명시했다. 초기 bit packing
검증에서 physical bit와 semantic bit의 방향이 어긋난 것이 발견되어,
corrected RTL로 KAT, MC trace, 합성, DFT, gate simulation을 전부 다시
수행했다. 수정 전 산출물은 최종 증거로 사용하지 않았다.

DFT scan set은 다음으로 구성했다.

```text
1   target MC_REG[9]
127 AES state/round-register decoys
120 data/control decoys
8   status/control decoys
---
256 scan cells
```

DFT Compiler가 생성한 실제 scan path는
`results/evaluator/scan_path.rpt`에 남겼고, target mapping은
`results/evaluator/target_mapping.json`에 evaluator-only로 저장했다.
현재 evaluator mapping은 다음과 같다.

```text
post-DFT target:          aes_core/MC_REG_reg[9]
DFT path cell index:      0
serialized SO index:     255
```

공격 코드에는 이 mapping을 주지 않았다. DFT report에는 393 nonscan DFF와
256 valid scan cells에 대한 expected S19 disturbance warning이 남아 있다.
이번 결과의 범위는 partial scan functional/gate simulation이며, 이 warning을
없애는 production DFT closure나 full physical implementation을 주장하지
않는다.

## 5. Phase 0: anonymous MC leakage-channel discovery

### 5.1 입력과 정보 경계

총 65개 plaintext를 사용했다.

```text
P0 + 16 source-byte positions x {0x01, 0x02, 0x04, 0x08}
```

각 plaintext에 대해 VCS로 세 capture schedule의 전체 256-bit scan-out을
수집했다.

```text
schedule 1: MC capture 직후
schedule 2: ARK/update boundary
schedule 3: post-update
```

공격 경로의 Phase 0 입력은
`results/phase_b/phase0_gate_scan_attack.txt`다. 원래 VCS 출력에 있던
evaluator target probe 열은 이 파일을 만들 때 제거했다. discovery script는
plaintext label, schedule label, anonymous 256-bit vector만 소비한다.

### 5.2 discovery 결과

`results/phase_b/phase0_discovery.json`의 결과는 다음과 같다.

| 지표 | 결과 |
|---|---:|
| 전체 scan FF | 256 |
| query 수 | 65 |
| AES-dependent candidate | 101 |
| pre-round candidate | 55 |
| MC-aware candidate (column overlap >= 3) | 1 |
| repeat stability | schedule 1/2/3 모두 true |
| 선택 slot | serialized SO index 255 |
| first-active schedule | 1, MC capture |
| plaintext support | `{0, 5, 10, 15}` |
| nearest MC column | `C0` |
| exact four-byte support | true |
| score | 13 |

선택은 ground-truth target 열을 보고 한 것이 아니다. `scan_out[255]`가
MC-aware support, pre-round timing, AES activity, repeat stability를 모두
만족했기 때문에 선택됐다. evaluator가 사후에 연 mapping은 이 slot이 실제
`MC_REG[9]`의 serialized 위치라는 사실을 확인하는 데만 사용했다.

### 5.3 capture timing sanity check

`results/phase_b/phase0_target_sweep_latest.txt`에서 evaluator target과
semantic MC9의 schedule별 일치율은 다음과 같다.

```text
schedule 1: 65/65 round 1
schedule 2: 65/65 round 1
schedule 3: 65/65 round 2
schedule 4: 65/65 round 2
```

따라서 selected slot은 단순히 암호화가 끝난 뒤의 output bit가 아니라,
round별 MC boundary observation을 유지한다.

## 6. Phase 0 -> Phase 1 handoff

Phase 0와 Phase 1은 서로 다른 scan target을 다시 고른 것이 아니다. 하나의
고정된 post-scan netlist와 하나의 scan path에서 선택한 `s*=255`를 round 1과
round 2에 그대로 재사용했다.

Q128 gate transcript는 다음 파일에 있다.

```text
q128_gate_observations_attack.json
q128_gate_observations_evaluator.json
q128_gate_observations_evaluator_reference_check.json
```

`q128_gate_observations_attack.json`에는 evaluator key가 없고, observation
builder가 읽는 값은 anonymous scan vector의 slot 255뿐이다. evaluator
reference check 결과는 다음과 같다.

```json
{
  "query_count": 129,
  "slot": 255,
  "round1_schedule": 1,
  "round2_schedule": 3,
  "bitwise_match": true,
  "mismatch_count": 0
}
```

즉 129개 Q128 plaintext에 대해 gate-level scan observation의 round-1/2
차분 transcript가 Python AES semantic `MC_9` reference와 모두 일치했다.
이것이 본 실험에서 요구한 Phase 0 channel과 Phase 1 solver tap 사이의
실험적 연결 증거다.

## 7. Fixed-query solver

Q128 gate observation을 기존 `solve_known_mapping.py`에 전달했다.
solver는 첫 model을 찾은 뒤 `C_Q(K) AND K != K_hat`를 다시 풀었고,
최종 결과는 `results/phase_b/q128_gate_fixed_solver.json`에 있다.

```text
Solve 1: SAT
K_hat = a66f651322597191ab9f8f8af4c2db61
        = evaluator hidden K0

Solve 2: SAT
K_alt = a6bc656971597191ab438f849fc2b861

classification: ambiguity
timeout: false
UNKNOWN: false
```

첫 solve 시간은 약 0.021초, 두 번째 solve 시간은 약 884.276초였다.
첫 model이 hidden key와 같다는 사실만으로 성공 처리하지 않았고, 두 번째
solve가 SAT이므로 fixed-query 단계는 정확히 ambiguity로 분류했다.

## 8. Adaptive loop: 실제 gate-level query 재사용

### 8.1 Q129: 첫 pair separator

Q128의 두 후보 `K0`와 historical alternative를 기준으로 생성한 첫
separator는:

```text
67d00000002c00000000000000000019
```

이 plaintext를 실제 VCS DUT에 다시 질의했고, scan vector에서 slot 255만
추출했다. gate-to-semantic reference check는
`adaptive_separator_gate_observation_reference_check.json`에서
`bitwise_match=true`, `mismatch_count=0`이다.

하지만 Q129 전체를 다시 풀었을 때:

```text
Solve 1: SAT, K0
Solve 2: SAT, a6d665e41d597191ab5e8f7972c24761
classification: ambiguity
```

가 되었다. 이것은 pair separator가 당시 지정된 두 key를 구분한다는
조건과 전체 remaining key space에 대해 unique하게 만든다는 조건이
다르다는 것을 gate-level에서 직접 보여준다. 따라서 Q129에서 중단하지
않고 새 alternative를 adaptive loop의 다음 입력으로 사용했다.

Q129 산출물:

```text
results/phase_b/adaptive_separator_synthesis.json
results/phase_b/adaptive_separator_gate_scan_eval5.txt
results/phase_b/adaptive_separator_gate_observation.json
results/phase_b/q129_gate_observations_attack.json
results/phase_b/q129_gate_adaptive_solver.json
```

### 8.2 Q130: 새 alternative 기반 두 번째 separator

Q129의 실제 second solve model
`a6d665e41d597191ab5e8f7972c24761`를 사용해 separator를 다시 합성했다.

```text
candidate 1: a66f651322597191ab9f8f8af4c2db61
candidate 2: a6d665e41d597191ab5e8f7972c24761
separator: 40c000000012000000007b0000000048
```

이 query도 동일한 VCS post-scan netlist, 동일한 scan path, 동일한 selected
slot 255로 측정했다. reference check:

```json
{
  "query_count": 2,
  "slot": 255,
  "round1_schedule": 1,
  "round2_schedule": 3,
  "bitwise_match": true,
  "mismatch_count": 0
}
```

Q130 전체 observation은 P0 포함 131개이며, 최종 solver 결과는
`results/phase_b/q130_gate_adaptive_solver.json`이다.

```text
Solve 1: SAT
K_hat = a66f651322597191ab9f8f8af4c2db61

Solve 2: UNSAT
alternative model: none
classification: full_key_unique
all 16 key bytes: fixed
timeout: false
UNKNOWN: false
```

첫 solve 시간은 약 0.010초, second solve는 약 755.720초였다. 따라서
최종 full-key recovery는 첫 model이 hidden key와 같아서가 아니라, 두 번째
key-exclusion solve가 `UNSAT`이어서 인정한다.

## 9. Verdi evidence

VCS는 Verdi FSDB PLI를 연결해 Phase 0, Phase 1, Phase 2, scan identity의
네 가지 evidence replay를 수행했다.

```text
results/verdi/phase0_mc_slot_discovery.fsdb
results/verdi/phase1_q30_depth2.fsdb
results/verdi/phase2_separator.fsdb
results/verdi/scan_shift_identity.fsdb
```

앞의 세 FSDB는 기능 동작과 capture schedule을 확인하기 위한 compact
one-shift window이고, 마지막 FSDB는 walking-one으로 256개 shift를 모두
기록한 scan identity evidence다. 각 FSDB에는 선택된 scan output, capture
control, round/case marker가 보존되어 있다. 기계 판정은 FSDB가 아니라 bulk
scan vector와 evaluator-independent reference check를 사용하며, FSDB는
그 판정을 시각적으로 재현하는 보조 증거다.

각 marker stream은 다음 종료 marker를 포함한다.

```text
VERDI_TRACE_DONE
```

모든 FSDB에 대해 `fsdb2vcd -summary` 재오픈 검사가 exit 0으로 끝났고,
headless Xvfb 환경에서 Verdi GUI를 각 FSDB에 연결해 HLC session artifact도
생성했다. GUI 자체는 제한 시간 후 종료했으므로 pass/fail 판정은 GUI 종료
여부에 의존하지 않는다. 재현 명령과 signal-group 정보는 다음에 있다.

```bash
verdi -ssf extra_exp/results/verdi/phase0_mc_slot_discovery.fsdb
verdi -ssf extra_exp/results/verdi/phase1_q30_depth2.fsdb
verdi -ssf extra_exp/results/verdi/phase2_separator.fsdb
verdi -ssf extra_exp/results/verdi/scan_shift_identity.fsdb
```

상세 목록은 `results/verdi/README_VISUAL_EVIDENCE.md`와
`results/verdi/sessions/`에 기록했다. PNG 네 개는 marker 기반의 portable
evidence panel이며, FSDB와 raw gate vector를 대체하지 않는다.

## 10. 회귀검증과 정보 경계

현재 focused regression 결과:

```text
16 passed in 0.39s
```

검증 항목은 frozen input, AES reference/KAT, scan manifest, DFT report,
anonymous Phase 0 selection, gate-to-semantic Q128/Q129/Q130 bridge,
historical separator control, held-out Phase 0, attacker/evaluator artifact
분리다.

공격-side transcript에서는 다음 문자열이 검출되지 않는다.

```text
hidden K0
post-DFT target instance
MC_REG_reg[9]
evaluator target probe
```

공격 코드가 사용하는 순서는 다음과 같다.

```text
anonymous scan vectors
  -> selected serialized slot 255
  -> differential round-1/round-2 observation
  -> Z3 candidate solve
  -> actual alternative key
  -> separator synthesis
  -> real VCS query
  -> append observation
  -> repeat until second solve UNSAT
```

evaluator key는 correctness check를 위해 solver wrapper에 별도로 주입되지만,
leakage constraint나 separator synthesis의 입력으로 사용되지 않는다.

## 11. 해석과 제한

이번 PASS가 직접 입증하는 것은 다음이다.

1. 실제 합성/scan-inserted sequential cell이 clean `MC_9` semantic function을
   보존할 수 있다.
2. anonymous full scan-out에서 MC-aware signature 분석으로 stable pre-ARK
   slot을 선택할 수 있다.
3. Phase 0의 selected slot과 Phase 1의 round-1/2 solver observation이
   동일 physical scan identity를 유지한다.
4. fixed ambiguity를 actual gate-level adaptive query로 재사용하고,
   pair separator가 남긴 새 alternative를 다시 처리해 `SAT -> UNSAT`까지
   도달할 수 있다.

이번 실험만으로 주장하지 않는 것은 다음이다.

- arbitrary AES implementation에서 MC FF가 자연스럽게 scan에 들어갈 확률;
- 모든 synthesis/retiming/pipeline 구조에 대한 prevalence;
- physical placement/routing 또는 scan compression/noise 대응;
- exact MC row/bit를 항상 anonymous하게 unique 복원한다는 주장;
- production DFT DRC closure.

따라서 이 결과는 **MC9 한 representative condition에 대한 EDA
composability와 adaptive key-recovery의 end-to-end 증명**으로 보고해야 하며,
일반적인 모든 AES 회로에 대한 정량적 보장으로 확대하면 안 된다.


## 12. Plan-completion addenda

### 12.1 Phase 2A known-separator control

The historical semantic separator
`f4000000004800d86000586000cb0010` was independently replayed on the same
postscan VCS DUT. The measured slot-255 differential was `(round 1, round 2) =
(0, 1)`. The previously recorded alternative predicts `(0, 0)` and is rejected
by the complete Q128-plus-separator solve:

```text
Solve 1 = SAT
Solve 2 = UNSAT
classification = full_key_unique
UNKNOWN/timeout = 0
```

The control artifacts are:

```text
results/phase_b/q129_phase2a_known_separator_evaluator.json
results/phase_b/q129_phase2a_known_separator_attack.json
results/phase_b/q129_phase2a_known_separator_solver.json
logs/q129_phase2a_known_separator_solver.log
```

This control is separate from the primary closed-loop path. The primary path
uses a solver-generated separator, observes Q129 ambiguity, and then continues
with a new separator to Q130.

### 12.2 Held-out Phase 0 check

A new plaintext not present in the 65-query coarse discovery set,
`00112233445566778899aabbccddeeff`, was sent to the same postscan DUT. The
selected anonymous slot 255 matched the public semantic MC9 reference at all
three timing views used for the check:

```text
round 1 / schedule 1: observed = expected = 1
round 1 / schedule 2: observed = expected = 1
round 2 / schedule 3: observed = expected = 1
```

The raw scan vector, sanitized attacker vector, and check are:

```text
results/phase_b/phase0_heldout_gate_scan_eval5.txt
results/phase_b/phase0_heldout_gate_scan_attack.txt
results/phase_b/phase0_heldout_check.json
```

### 12.3 Information-flow audit

`extra_exp/scripts/audit_information_flow.py` checks the actual attacker-side
files and evaluator-only files. It rejects the hidden key, target hierarchy,
post-DFT target cell, target mapping report, and evaluator fields in attacker
inputs. The result is:

```text
results/evaluator/information_flow_audit.json
status = PASS
violations = []
```

The numeric selected slot and post-Phase-0.5 semantic `MC_9` label are allowed by
the declared oracle handoff model; the underlying physical mapping is not
passed to the attack-side files.

### 12.4 Verdi evidence bundle

Four FSDB artifacts were generated with the same compiled postscan VCS image:

```text
results/verdi/phase0_mc_slot_discovery.fsdb
results/verdi/phase1_q30_depth2.fsdb
results/verdi/phase2_separator.fsdb
results/verdi/scan_shift_identity.fsdb
```

The first three are compact functional evidence replays with a one-shift visual
window. The full 256-shift walking-one replay is retained separately in
`scan_shift_identity.fsdb`; complete scan identity and slot ordering remain
proven by `scan_calibration.txt`, `scan_path.rpt`, and the bulk scan vectors.
Each functional marker records P0 and one selected query across schedules 1, 2,
and 3, while the scan identity marker records all 256 shifts and ends with
`VERDI_TRACE_DONE`.

The portable visual evidence consists of:

```text
results/verdi/figures/phase0_timing.png
results/verdi/figures/round_slot_identity.png
results/verdi/figures/adaptive_separator.png
results/verdi/figures/scan_shift_identity.png
```

Each PNG is rendered from the corresponding marker stream with gnuplot. The
FSDBs remain the authoritative waveform artifacts; PNGs are not used as the
sole evidence. `fsdb2vcd -summary` successfully reopened all four FSDB files.
Signal-group/session manifests and viewing commands are in
`results/verdi/sessions/` and `results/verdi/README_VISUAL_EVIDENCE.md`.

### 12.5 Reproducibility manifest

The reproducibility-critical netlists, inputs, solver outputs, scan reports,
FSDBs, markers, figures, logs, and session manifests are hashed in:

```text
results/evidence_manifest.json
```

## 13. Supplemental anonymous EDA end-to-end validation

### 13.1 검증 목적

기존 EDA 결과는 anonymous Phase 0에서 선택한 slot을 evaluator-confirmed
`MC_9` function으로 해석한 뒤 primary Q128/Q129/Q130 recovery를 재현했다.
추가 실험은 이 semantic label handoff를 제거하고, 공격자가 얻은 slot과
MC-aware support만으로 가능한 Boolean-function hypothesis를 생성한 뒤,
동일한 gate-level DUT transcript와 solver를 끝까지 연결하는 것을 목적으로
했다.

### 13.2 현실적인 DUT 구성

DUT는 one-round toy model이 아니라 다음 구조의 10-round iterative AES-128
core다.

```text
STATE_REG
  -> SubBytes -> ShiftRows -> MixColumns
  -> MC_REG[127:0]       // real sequential boundary
  -> AddRoundKey
  -> STATE_REG
```

`MC_REG`는 round 1--9에서 재사용되는 post-MixColumns/pre-ARK register다.
이번 representative condition에서는 `MC_REG[9]`가 실제 sequential cell로
존재하도록 RTL에 명시했고, 256-cell partial scan set에 포함시켰다. 나머지는
AES state/round-register와 control/data decoy FF로 채웠다. DFT Compiler가
scan chain을 구성하고, VCS는 합성 후 scan-inserted netlist를 그대로
시뮬레이션했다.

공격자가 받은 것은 chosen plaintext, capture schedule, anonymous full
scan-out vector뿐이다. 다음은 attack path에 제공하지 않았다.

```text
secret K0
scan stitching map
RTL/DFT instance name
physical position
exact MC row/bit label
```

target FF를 scan set에 포함한 것은 자연 노출률을 측정하기 위한 것이 아니라,
`scan-visible MC sequential boundary`라는 공격 조건을 gate-level DUT에
명시적으로 instantiation한 것이다. 따라서 이 실험은 모든 AES에서 MC FF가
자연스럽게 노출된다는 prevalence 주장이 아니다.

### 13.3 Phase 0: anonymous slot discovery

65개 coarse query를 사용했다.

```text
P0 + 16 plaintext-byte positions x {0x01, 0x02, 0x04, 0x08}
```

각 query에서 세 capture schedule의 256-bit anonymous scan-out을 수집했다.

```text
schedule 1 = MC capture 직후
schedule 2 = ARK/update boundary
schedule 3 = update 이후
```

Python signature analyzer는 AES activity, first-active timing, repeat
stability, ShiftRows-aligned source support를 이용했다. 결과는 다음과 같다.

```text
scan FF count       = 256
AES-dependent       = 101
pre-round candidates = 55
MC-aware candidate  = 1
selected SO slot    = 255
source support      = {0,5,10,15} = C0
first-active        = schedule 1, MC capture
repeat stability    = true
```

선택은 evaluator target probe를 사용하지 않고 수행했다. evaluator mapping은
사후에 slot 255가 실제 `MC_REG[9]`의 serialized 위치임을 확인하는 데만
사용했다.

### 13.4 Phase 0.5: anonymous function attribution

C0 support가 주어진 뒤 C0 column의 32개 MC output-bit hypothesis
`h00`--`h31`를 생성했다. 각 hypothesis에 대해 gate-level Q128 transcript
전체와 AES/Z3 model의 consistency를 검사했다.

```text
initial hypotheses = 32
UNSAT branches     = 31
survivor           = h09
h09                = C0 row 1, byte bit 1
UNKNOWN/timeout    = 0/0
```

이 단계의 attack-side transcript에는 `MC_9`, `MC9`, hidden key, mapping,
physical FF name이 없었다. `h09`와 실제 `MC_REG[9]`의 동일성은 evaluator
post-hoc check다. 따라서 이 결과는 선언된 C0 MC-function family에서의
anonymous attribution이며, 임의의 AES에 대한 universal exact-bit mapping
보장은 아니다.

### 13.5 Phase 1/2: fixed query와 adaptive recovery

Phase 0에서 발견한 동일 serialized slot을 round 1과 round 2 observation에
그대로 재사용했다. P0 대비 differential leakage를 만들고, first solve와
second solve에서 각각 다음을 수행했다.

```text
Solve 1: C_Q(K) satisfiable? -> candidate K_hat
Solve 2: C_Q(K) AND K != K_hat satisfiable? -> alternative check
```

anonymous hypothesis path의 실제 결과는 다음과 같다.

| transcript | observations | Solve 1 | Solve 2 | 판정 |
|---|---:|---|---|---|
| Q128 fixed | 129 | SAT | SAT | ambiguity |
| Q129 adaptive extension | 130 | SAT | SAT | ambiguity |
| Q130 adaptive extension | 130 | SAT | SAT | ambiguity |
| Q131 final extension | 131 | SAT | UNSAT | full-key unique |

각 adaptive 단계에서 현재 candidate pair를 분리하는 plaintext를 Z3로
합성하고, 그 plaintext를 실제 VCS scan-inserted DUT에 다시 질의했다. 새
scan observation을 transcript에 추가한 뒤 전체 surviving hypothesis를
대상으로 key exclusion을 반복했다. Q131의 최종 결과는 다음과 같다.

```text
surviving hypothesis = h09
first model          = a66f651322597191ab9f8f8af4c2db61
alternative model    = none
key exclusion scope  = all_surviving_hypotheses
classification       = full_key_unique
UNKNOWN              = false
timeout              = false
```

첫 model이 evaluator hidden K0와 같다는 사실만으로 성공 처리한 것이 아니다.
최종 second solve가 `UNSAT`이고 alternative key가 존재하지 않는 것을 기준으로
full-key recovery를 인정했다.

### 13.6 EDA validation이 실제로 입증하는 범위

이번 실험의 end-to-end evidence chain은 다음이다.

```text
RTL semantic MC boundary
  -> DC synthesis
  -> DFT scan insertion with decoy FFs
  -> anonymous full scan-out
  -> MC-aware slot discovery
  -> C0 function hypothesis enumeration
  -> same physical slot at round 1/round 2
  -> gate-level differential transcript
  -> Z3 fixed/adaptive candidate solving
  -> actual DUT re-query for separators
  -> final SAT -> UNSAT
```

따라서 다음을 주장할 수 있다.

> **선택된 scan-visible MC sequential boundary가 실제 합성/DFT/VCS DUT에서
> anonymous 1-bit channel로 관측되고, 그 channel의 function hypothesis를
> ground-truth semantic label 없이 좁힌 뒤, adaptive chosen-plaintext와
> solver를 결합해 AES-128 master key를 full-key unique로 판정할 수 있다.**

단, 이 결과는 다음을 주장하지 않는다.

- 임의의 AES implementation에서 MC FF가 scan에 들어갈 확률
- 모든 retiming/pipeline/physical implementation에 대한 일반화
- physical placement/routing 및 scan compression/noise 대응
- C0 밖의 모든 MC bit에 대한 attribution 성공률
- production DFT closure

### 13.7 재현 산출물

```text
extra_exp/rtl/aes128_iterative_mc_boundary.sv
extra_exp/dft/
extra_exp/netlist/extra_exp_postscan.v
extra_exp/tb/
extra_exp/results/phase_b/phase0_discovery.json
extra_exp/results/phase_b/q128_mc_hypothesis_solver_attack.json
extra_exp/results/phase_b/q129_mc_hypothesis_solver_attack.json
extra_exp/results/phase_b/q130_mc_hypothesis_solver_attack.json
extra_exp/results/phase_b/q131_mc_hypothesis_solver_attack.json
extra_exp/results/phase_b/q128_mc_hypotheses_attack.json
extra_exp/results/phase_b/q129_mc_hypotheses_attack.json
extra_exp/results/phase_b/q130_mc_hypotheses_attack_closed_loop.json
extra_exp/results/phase_b/q131_mc_hypotheses_attack_closed_loop.json
extra_exp/results/verdi/
extra_exp/results/evaluator/information_flow_audit.json
extra_exp/results/evidence_manifest.json
```

Verdi FSDB는 DUT 내부 timing과 scan activity를 시각화하고, machine-readable
scan transcript는 실제 solver 입력을 보존하며, solver JSON은 Solve 1/2의
권위 있는 판정을 보존한다. 세 artifact 층을 함께 사용해야 EDA validation
전체를 재현할 수 있다.
