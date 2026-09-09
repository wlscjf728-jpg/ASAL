# AES Internal SB-to-MC Fault-Share Sweep

## 목적

이 실험은 scan placement 효과와 fault-population 효과를 분리한다. 기존
revision-2 DFT 결과에서 사용한 post-DFT netlist, scan manifest, scan chain,
clock/protocol, ATPG 설정은 재사용하고, fault source의 region별 구성만
변경했다.

이번 실험에서 바꾼 것은 `SB_CONE` fault entry 일부를 제거하고 같은 수의
`MC_CONE` fault entry를 추가하는 것이다. IARK, SR, AES control, AES other
fault entry는 모든 level에서 고정했다.

## 고정 조건

| 항목 | 조건 |
|---|---|
| Functional checkpoint | 기존 AES-internal v2 checkpoint |
| Scan netlist | 기존 `CASE_IARK`, `CASE_SB`, `CASE_SR`, `CASE_MC`, random-stage 10개 |
| Common scan | 896 FF |
| Variable scan | 기존 case별 128 FF |
| Total scan | 1,024 FF |
| Scan chain | 1 |
| Fault model | stuck-at, transition |
| Direct FF fault | AES FF Q/QN fault 전체 제외 |
| Source entries per level | 4,000 |
| Selection | region 내부 deterministic SHA256 ranking |

따라서 이 campaign에는 scan FF 재선택이나 DFT 재합성이 없다. 같은 scan case에
대해 fault list만 바꿔 TetraMAX를 실행했다.

## Fault-share levels

고정 region은 IARK 107, SR 59, AES control 0, AES other 312 entry다.
나머지 3,522 entry를 SB와 MC 사이에서 교환했다.

| Level | IARK | SB | SR | MC | AES other | Total | MC 비율 |
|---|---:|---:|---:|---:|---:|---:|---:|
| `mc0314` | 107 | 3,208 | 59 | 314 | 312 | 4,000 | 7.85% |
| `mc0800` | 107 | 2,722 | 59 | 800 | 312 | 4,000 | 20.00% |
| `mc1600` | 107 | 1,922 | 59 | 1,600 | 312 | 4,000 | 40.00% |
| `mc2400` | 107 | 1,122 | 59 | 2,400 | 312 | 4,000 | 60.00% |
| `mc3200` | 107 | 322 | 59 | 3,200 | 312 | 4,000 | 80.00% |

각 source file에는 정확히 4,000개의 entry가 들어 있다. TetraMAX가 일부
fault site를 model 단계에서 무시하므로 실제 summary의 valid total은
3,989~3,997 범위였으며, coverage는 각 summary의 valid total을 분모로
사용했다.

## CASE_MC 결과

`CASE_MC`의 scan distribution은 모든 level에서 동일하며 variable 128 FF가
전부 `MC_REG`다.

| MC fault share | Stuck detected / total | Stuck coverage | Transition detected / total | Transition coverage |
|---:|---:|---:|---:|---:|
| 7.85% | 152 / 3,989 | 3.81% | 127 / 3,991 | 3.18% |
| 20.00% | 219 / 3,991 | 5.49% | 184 / 3,993 | 4.61% |
| 40.00% | 319 / 3,992 | 7.99% | 281 / 3,992 | 7.04% |
| 60.00% | 430 / 3,996 | 10.76% | 382 / 3,993 | 9.57% |
| 80.00% | 537 / 3,997 | 13.44% | 485 / 3,995 | 12.14% |

MC fault population이 7.85%에서 80%로 증가하는 동안 MC scan을 고정한
`CASE_MC` coverage가 stuck-at과 transition 모두 단조 증가했다.

## Scan control 비교

같은 fault-share source를 적용했을 때 scan placement별 stuck-at coverage는
다음과 같다.

| MC fault share | IARK scan | SB scan | SR scan | MC scan | random-stage mean |
|---:|---:|---:|---:|---:|---:|
| 7.85% | 3.71% | 3.33% | 3.43% | 3.81% | 3.60% |
| 20.00% | 3.73% | 3.31% | 3.46% | 5.49% | 4.11% |
| 40.00% | 3.81% | 3.23% | 3.53% | 7.99% | 4.80% |
| 60.00% | 3.95% | 3.08% | 3.68% | 10.76% | 5.64% |
| 80.00% | 4.10% | 3.08% | 3.83% | 13.44% | 6.53% |

`CASE_MC`는 MC fault 비중 증가에 가장 민감하게 반응했다. IARK/SB/SR
placement는 같은 fault-share 변화에서 변화폭이 작다. Transition에서도
동일한 방향이 관찰됐다.

## 해석

이 결과는 이전의 “MC scan 수를 늘려 coverage가 증가했다”는 결과와 다른
축의 근거를 제공한다. 이번에는 scan 수와 scan 위치를 고정했는데도 MC fault
population이 증가할수록 MC scan case의 coverage가 증가했다.

따라서 다음의 제한된 명제는 실험적으로 지지된다.

> MC cone fault가 fault universe에서 더 큰 비중을 차지할수록, MC boundary를
> scan 관측점으로 사용한 경우의 test coverage contribution이 커진다.

다만 이것은 전체 fault universe의 인위적인 SB-to-MC 재가중 실험이다. 실제
합성 회로에 MC fault site가 더 많이 존재한다는 뜻은 아니다. 또한 이번
campaign의 TetraMAX summary는 전체 fault count를 보고하므로, 각 level의
검출 증가가 MC fault entry에서 직접 발생했는지를 최종적으로 region별
status로 확인하려면 별도의 region-scoped status run이 필요하다.

## 산출물

- `config/aes_internal_v2_mc_faultshare_manifest.json`
- `config/aes_internal_v2_faultshare_mc*_stuck.list`
- `config/aes_internal_v2_faultshare_mc*_transition.list`
- `scripts/aes_internal_v2_mc_faultshare.py`
- `scripts/tmax/run_aes_internal_v2_mc_faultshare_case.tcl`
- `scripts/run_aes_internal_v2_mc_faultshare.sh`
- `results/tmax/aes_internal_v2/faultshare/`

