# Phase-Alpha Behavioral Tracking Design

## 목적

기존 MC9 gate-level Phase 0에서 선택된 anonymous scan channel이 scan-out 위치의
순열이 바뀐 뒤에도 짧은 behavioral fingerprint로 다시 식별되는지 검증한다.
이 실험은 key recovery, physical mapping 복원, 새 EDA 합성을 수행하지 않는다.
기존 MC9 실험의 attack-side scan capture와 query만 복사해 host-side permutation
wrapper에서 재사용한다.

## 입력 경계

복사된 입력은 다음과 같다.

- `inputs/phase0_gate_scan_attack.txt`: 65개 plaintext, 3개 capture schedule,
  anonymous 256-bit scan vector
- `inputs/phase0_queries.txt`: query ID와 plaintext
- `inputs/phase0_discovery.json`: Phase 0가 선택한 slot과 공개 discovery 결과
- `inputs/q128_gate_observations_attack.json`, `inputs/q129_gate_observations_attack.json`:
  이후 solver 연결을 위한 attack-side reference artifact

hidden key, evaluator scan map, RTL instance name은 입력으로 사용하지 않는다.

## Fingerprint

Phase 0에서 선택된 slot을 `s*`라 하고 schedule 1의 reference query `q=0`을 기준으로
한다. 초기 probe 집합은 `q=0..15`이며, slot `s`의 fingerprint는 다음과 같다.

```text
F(s) = [ Y(q, schedule=1, s) XOR Y(0, schedule=1, s) ] for q in 0..15
```

현재 MC9 데이터에서는 16-query fingerprint에 충돌이 있을 수 있으므로, 후보가
하나가 될 때까지 `q=16..62`를 한 개씩 추가한다. 최종 후보는 `q=63,64` held-out
probe에서 다시 검증한다. 이는 tracking용 adaptive probe이고,
key-separation query가 아니다.

## Dynamic permutation 모델

원본 256-bit vector의 old slot `i`를 새 scan slot `pi[i]`로 보내는 permutation을
사용한다. permutation은 평가 wrapper 내부에서만 생성하며 tracker에는 제공하지 않는다.

각 dynamic epoch에서는 tracker probe bundle 동안 하나의 permutation을 유지한다.
payload observation 사이에서 epoch을 바꿀 수 있으며, 다음 refresh 간격을 평가한다.

- static identity: permutation 없음
- 65 payload observations마다 refresh
- 16 payload observations마다 refresh
- 8 payload observations마다 refresh
- 4 payload observations마다 refresh
- 매 payload observation마다 refresh

마지막 경우에도 reacquisition probe bundle 내부에서는 permutation이 고정된다.

## Negative control

tracker probe bundle 안에서 query마다 독립 permutation을 적용한다. 이 경우 같은
channel의 fingerprint가 하나의 현재 slot에 모이지 않으므로 tracker가 unique slot을
찾으면 안 된다.

## 판정

stable-epoch 시나리오의 PASS 조건은 모든 epoch에서 다음을 만족하는 것이다.

1. tracker가 16개 초기 probe 또는 추가 probe 후 후보를 찾는다.
2. 최종 후보가 하나다.
3. 선택 후보가 evaluator-only scoring용 현재 slot과 일치한다.
4. held-out probe가 모두 expected fingerprint와 일치한다.

negative control은 `expected_failure`이며 unique reacquisition이 발생하면 FAIL이다.
이 실험의 성공은 `tracking_success`일 뿐 `SAT -> UNSAT` key recovery 성공을 의미하지
않는다.

## 출력

`results/phase_alpha_tracking.json`에 다음을 기록한다.

- source artifact와 selected initial slot
- 초기 fingerprint와 probe 수
- refresh interval별 epoch 수, tracking accuracy, collision 수, 평균 probe 수
- 각 epoch의 hidden current slot은 평가용으로만 기록
- independent-per-observation negative control 결과

후속 solver 연결 시에는 각 epoch에서 재획득한 slot으로 관측한 bit만 기존
`aes-sparse-gate-bridge-v1` observation의 의미적 `(query, round, differential)`
튜플로 변환한다. 이번 alpha에서는 그 solver 호출을 하지 않는다.
