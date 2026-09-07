# Phase-Alpha Behavioral Tracking 실험 보고서

## 1. 실험 목적

본 실험의 목적은 Phase 0에서 발견한 anonymous scan-out leakage channel이 scan-out 위치의 변화 이후에도 **행동 지문(behavioral fingerprint)** 으로 재획득될 수 있는지 확인하는 것이다.

이 실험은 새로운 key-recovery 실험이 아니다. 다음 연결만 검증한다.

```text
Phase 0 discovery
  -> 초기 anonymous slot s* 선택
  -> 해당 slot의 query별 differential fingerprint 저장
  -> scan permutation 변화
  -> 동일 fingerprint를 갖는 현재 slot 재검색
  -> 후속 solver가 사용할 현재 slot 반환
```

따라서 본 보고서의 PASS는 다음을 의미한다.

> 짧은 tracking probe window 동안 leakage FF의 행동이 보존된다면, 고정된 물리적 scan index를 미리 알지 않아도 동일 leakage channel을 다시 찾을 수 있다.

반대로 본 결과만으로 full-key recovery, 정확한 RTL instance 복원, physical scan map 복원을 주장하지 않는다.

## 2. 기존 실험과의 관계 및 격리

입력은 기존 MC9 gate-level Phase 0 실험에서 생성된 공격자 관점의 산출물을 복사하여 사용했다. 원본 MC9 실험은 현재 진행 중일 수 있으므로 원본 파일과 실행 산출물은 수정하지 않았다.

복사한 입력은 다음과 같다.

```text
inputs/phase0_gate_scan_attack.txt
inputs/phase0_queries.txt
inputs/phase0_discovery.json
inputs/q128_gate_observations_attack.json
inputs/q129_gate_observations_attack.json
```

복사본은 다음 기존 산출물과 byte-identical임을 확인했다.

```text
anonymous_subround_multiround_attack_extra_exp/results/phase_b/phase0_gate_scan_attack.txt
anonymous_subround_multiround_attack_extra_exp/results/phase_b/phase0_queries.txt
anonymous_subround_multiround_attack_extra_exp/results/phase_b/phase0_discovery.json
anonymous_subround_multiround_attack_extra_exp/results/phase_b/q128_gate_observations_attack.json
anonymous_subround_multiround_attack_extra_exp/results/phase_b/q129_gate_observations_attack.json
```

Phase-alpha 코드에는 secret key, true scan stitching map, true MC bit index를 제공하지 않았다. 초기 slot은 Phase 0 discovery 출력의 `final_selected_slot.scan_out_index`를 읽었으며, 이는 공격자가 discovery 단계에서 얻은 입력으로 취급했다.

## 3. 입력 및 관측 모델

기존 Phase 0 capture는 다음 조건을 가진다.

| 항목 | 설정 |
|---|---|
| query 수 | 65개 |
| capture schedule | 3개 |
| anonymous scan width | 256 bit |
| 초기 선택 slot | `s* = 255` |
| fingerprint schedule | schedule 1 |
| 초기 probe query | q0부터 q15 |
| differential 기준 | q0 |
| held-out validation | q63, q64 |
| key recovery | 수행하지 않음 |

초기 Phase 0 discovery에서 선택된 slot은 다음과 같다.

```text
initial_selected_slot = 255
```

공격자는 scan slot 번호 자체를 영구 식별자로 사용하지 않는다. 대신 기준 query q0와 각 probe query의 scan bit 차이를 이용해 slot별 행동 지문을 만든다.

## 4. Behavioral fingerprint

scan slot `s`와 query `q`에 대해 schedule 1의 관측 bit를 `Y(s,q)`라 하면, q0 기준 differential response는 다음과 같이 정의한다.

```text
DeltaY(s,q) = Y(s,q) XOR Y(s,0)
```

초기 fingerprint는 q1부터 q15까지의 differential response를 연결한 벡터이다.

```text
F16(s) = [DeltaY(s,1), DeltaY(s,2), ..., DeltaY(s,15)]
```

Phase 0에서 선택된 slot 255의 초기 fingerprint는 다음과 같다.

```text
0001000000000000
```

초기 16개 probe만으로 후보가 여러 개 남으면 q16부터 q62까지의 query를 순차적으로 추가한다. 후보가 하나가 된 뒤에도 q63, q64는 held-out query로 사용한다. held-out query는 후보를 고르는 데 사용하지 않고, 최종 선택 slot이 동일한 channel의 지문을 실제로 재현하는지 검증하는 데만 사용한다.

## 5. Dynamic permutation 시나리오

각 epoch에서 외부 평가 wrapper가 scan-out vector의 관측 순서를 permutation한다. permutation은 공격자에게 공개하지 않는다.

핵심 조건은 다음과 같다.

```text
한 epoch의 tracking probe bundle 전체에서는 동일 permutation 유지
payload observation 사이에는 permutation 변경 가능
```

다음 여섯 가지 stable 시나리오를 평가했다.

| 시나리오 | permutation refresh 조건 |
|---|---|
| `identity_static` | permutation 없음 |
| `stable_refresh_65` | 65 query payload 단위로 유지 |
| `stable_refresh_16` | 16 query payload 단위로 유지 |
| `stable_refresh_8` | 8 query payload 단위로 유지 |
| `stable_refresh_4` | 4 query payload 단위로 유지 |
| `stable_refresh_1` | payload observation마다 변경, probe bundle 안에서는 유지 |

`stable_refresh_1`은 각 payload 관측 사이에 scan index가 바뀌는 가장 강한 stable-window 조건이다. 그러나 tracker가 새 permutation 아래에서 probe를 먼저 전송할 수 있다는 oracle 가정을 사용한다.

## 6. Tracking 알고리즘

각 epoch에서 다음 절차를 수행한다.

1. 현재 permutation 아래에서 q0부터 q15까지의 probe를 수집한다.
2. 모든 scan slot에 대해 `F16(s)`를 계산한다.
3. 초기 fingerprint와 일치하는 후보 slot을 만든다.
4. 후보가 둘 이상이면 q16부터 q62를 하나씩 추가한다.
5. 후보가 하나가 되면 selected slot으로 저장한다.
6. q63, q64의 differential response를 선택 slot에 대해 비교한다.
7. 두 held-out query가 모두 일치할 때만 `tracking_success = true`로 판정한다.
8. evaluation-only 현재 slot과 selected slot이 같을 때 `tracking_correct = true`로 판정한다.

초기 fingerprint가 우연히 다른 decoy slot과 충돌할 수 있으므로, 단순히 `final_match_count == 1`인 상태만으로 성공시키지 않는다. held-out validation을 통과해야 최종 성공이다.

## 7. Negative control

별도 negative control에서는 각 probe query마다 독립적인 permutation을 새로 적용한다.

```text
q1 -> pi1
q2 -> pi2
q3 -> pi3
...
```

이 조건에서는 하나의 physical FF가 probe sequence 전체에서 일관된 관측 slot으로 대응되지 않는다. 따라서 행동 지문 기반 reacquisition이 성공하면 안 된다.

실행 중 한 repetition에서 초기 후보가 우연히 하나로 줄어든 경우가 있었지만, q63/q64 held-out validation이 실패하여 최종 성공으로 인정되지 않았다. 이 결과는 held-out 검증이 필요한 이유를 보여준다.

## 8. 결과

### 8.1 Stable permutation 결과

최종 결과 파일 기준 stable 시나리오별 요약은 다음과 같다.

| 시나리오 | epoch 수 | tracking accuracy | collision epoch | 평균 matching probe 수 | held-out 포함 probe 수 |
|---|---:|---:|---:|---:|---:|
| `identity_static` | 1 | 1.0 | 1 | 23 | 25 |
| `stable_refresh_65` | 1 | 1.0 | 1 | 23 | 25 |
| `stable_refresh_16` | 4 | 1.0 | 4 | 23 | 25 |
| `stable_refresh_8` | 7 | 1.0 | 7 | 23 | 25 |
| `stable_refresh_4` | 13 | 1.0 | 13 | 23 | 25 |
| `stable_refresh_1` | 49 | 1.0 | 49 | 23 | 25 |
| **합계** | **75** | **1.0** | **75** | **23** | **25** |

모든 stable epoch에서 다음이 성립했다.

```text
initial_match_count = 2
adaptive refinement 후 final_match_count = 1
held-out q63/q64 validation = pass
tracking_correct = true
```

대표적인 `stable_refresh_1` epoch의 세부 결과는 다음과 같다.

```text
initial matches       = [97, 247]
additional probes    = 7
final matches         = [97]
selected slot         = 97
evaluator current     = 97
validation q63        = observed 1, expected 1
validation q64        = observed 1, expected 1
tracking_success      = true
tracking_correct      = true
```

### 8.2 Independent-per-observation negative control

8회 repetition 모두 validated unique reacquisition에 실패했다.

```text
negative_control_repetitions = 8
validated_unique_reacquisition = 0/8
all_trials_non_unique_or_rejected = true
```

일부 repetition에서 초기 fingerprint가 우연히 후보를 만들었지만, held-out validation까지 통과한 잘못된 선택은 없었다. 따라서 이 실험에서는 독립 permutation noise를 실제 channel tracking 성공으로 오인하지 않았다.

### 8.3 실행 로그의 최종 요약

`logs/phase_alpha.out`의 최종 요약은 다음과 같다.

```text
{
  "stable_scenario_count": 6,
  "stable_all_correct": true,
  "stable_min_accuracy": 1.0,
  "stable_max_accuracy": 1.0,
  "negative_control_expected": "FAIL_EXPECTED",
  "negative_control_all_trials_non_unique": true,
  "alpha_verdict": "PASS"
}
```

## 9. 판정

최종 판정은 `PASS`이다.

```text
alpha_verdict = PASS
```

이 판정은 다음 명제에 대한 것이다.

> Phase 0에서 발견한 MC leakage channel의 observable slot identity가 짧은 probe window 동안 유지된다면, scan permutation이 payload 관측 사이에서 변해도 behavioral fingerprint를 이용해 현재 slot을 재획득할 수 있다.

반면 다음은 본 실험의 결론이 아니다.

```text
scan order가 매 query마다 독립적으로 무작위화되어도 tracking 가능하다
정확한 MC row/bit 또는 physical FF 위치를 복원했다
anonymous channel만으로 master key를 복구했다
Phase 0 discovery 없이 arbitrary scan bit를 추적할 수 있다
```

따라서 이 결과는 고정 scan index 가정의 완화에 대한 보조 근거이며, 기존 Phase 0 discovery와 Phase 1/2 key-recovery 사이에 사용할 수 있는 host-side reacquisition 단계의 타당성을 보여준다.

## 10. 후속 공격과의 인터페이스

본 실험의 tracker 출력은 다음과 같이 정의된다.

```text
(epoch, selected_current_slot, observed_payload_bit)
```

후속 solver에는 physical scan index의 연속성이 아니라 다음 logical observation만 전달한다.

```text
(plaintext, capture schedule, leakage bit)
```

그러므로 기존 key-recovery 단계는 다음 구조로 연결할 수 있다.

```text
Phase 0 discovery
  -> initial slot s*
Phase-alpha tracking
  -> current slot s_e
  -> current leakage observation Y(P)
Phase 1 fixed-query solve
  -> C0(K)
Phase 2 adaptive separator
  -> additional constraint
  -> SAT/UNSAT uniqueness test
```

Phase-alpha 자체는 key solver를 호출하지 않으며, Z3도 사용하지 않는다. scan-bit signature 계산과 후보 filtering만 Python으로 수행한다. 이 분리는 tracking 논리의 성립 여부와 key-recovery 성능을 혼동하지 않기 위한 것이다.

## 11. 재현 방법

실험 디렉터리에서 다음 명령으로 실행한다.

```bash
bash run_phase_alpha.sh
```

테스트와 정적 검증은 다음과 같다.

```bash
../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_phase_alpha_tracking.py -q
bash -n run_phase_alpha.sh
python3 -m py_compile scripts/phase_alpha_tracking.py
```

주요 산출물은 다음과 같다.

```text
results/phase_alpha_tracking.json
logs/phase_alpha.out
```

JSON에는 scenario별 epoch 결과, 후보 수, 추가 probe 수, held-out validation 결과, selected slot, ground-truth evaluation-only correctness가 기록되어 있다. `logs/phase_alpha.out`에는 최종 PASS/FAIL 요약만 기록한다.

## 12. 증거 파일

```text
anonymous_subround_multiround_attack_phase_alpha/README.md
anonymous_subround_multiround_attack_phase_alpha/docs/superpowers/specs/2026-08-12-phase-alpha-tracking-design.md
anonymous_subround_multiround_attack_phase_alpha/docs/superpowers/plans/2026-08-12-phase-alpha-tracking.md
anonymous_subround_multiround_attack_phase_alpha/results/phase_alpha_tracking.json
anonymous_subround_multiround_attack_phase_alpha/logs/phase_alpha.out
```

이 보고서는 결과 JSON과 실행 로그를 해석한 별도 요약본이다. 수치의 authoritative source는 `results/phase_alpha_tracking.json`이며, 최종 실행 상태의 간결한 증거는 `logs/phase_alpha.out`이다.
