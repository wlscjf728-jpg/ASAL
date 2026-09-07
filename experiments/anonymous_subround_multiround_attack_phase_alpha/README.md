# Phase-Alpha: Dynamic Anonymous Channel Tracking

이 폴더는 기존 MC9 gate-level 실험을 수정하지 않고, attack-side Phase 0
capture를 복사해 behavioral fingerprint tracking 논리만 검증한다.

## 실행

```bash
cd anonymous_subround_multiround_attack_phase_alpha
bash run_phase_alpha.sh | tee logs/phase_alpha.out
```

테스트:

```bash
python3 -m pytest tests/test_phase_alpha_tracking.py -q
```

## 검증 범위

초기 Phase 0 selected slot은 `phase0_discovery.json`의 `final_selected_slot`에서
읽는다. schedule 1의 query `0..15` differential signature를 fingerprint로 만들고,
충돌하면 query `16..62`를 순차적으로 추가하고, 후보가 unique가 된 뒤 query `63,64`를 held-out으로 검증한다.

stable epoch에서는 payload 관측 사이에 hidden permutation을 바꾸되 tracking probe
bundle 내부에서는 고정한다. `stable_refresh_1`은 payload observation마다 위치가
바뀌는 경우지만, 각 reacquisition window에는 하나의 permutation이 유지되는 모델이다.

`negative_independent_probe_permutation`은 probe query마다 permutation을 새로 바꾼다.
이 control은 추적에 실패해야 정상이다.

이 alpha의 PASS는 다음을 뜻한다.

```text
stable epoch 재획득 정확도 100%
+ 초기 fingerprint 충돌 시 추가 probe로 unique
+ independent-per-observation control은 held-out 검증을 통과한 unique 재획득을 만들지 않음
```

이 결과는 key recovery나 `SAT -> UNSAT` 판정이 아니다. 이후 단계에서 재획득한
slot을 기존 `aes-sparse-gate-bridge-v1` observation으로 변환해 기존 solver에
연결할 수 있는지를 별도로 다룬다.
