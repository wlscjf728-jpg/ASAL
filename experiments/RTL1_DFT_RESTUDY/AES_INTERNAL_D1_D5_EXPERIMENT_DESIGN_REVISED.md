# AES-Internal D1-D5 DFT Experiment Design, Revised

## 0. Revision status

이 문서는 `AES_INTERNAL_D1_D5_EXPERIMENT_DESIGN.md`의 설계를 대체하는
revision 2이다. 이전 설계의 `host-only common` 구성은 폐기한다. 그 구성은
`key_reg`와 `plaintext_reg`를 variable 후보에서 제외하면서 common scan에서
제거할 수 있어 AES 입력 제어성을 잃었고, 앞단의 내부 fault가 ATPG에서
대량으로 `AU`가 되는 원인을 포함하고 있었다.

이번 revision의 최우선 조건은 다음 두 가지다.

1. `key_reg`와 `plaintext_reg`는 모든 case에서 common scan으로 유지한다.
2. AES의 기능 경로는 `IARK -> SB -> SR -> MC`로 완전히 연결된 동일한
   functional checkpoint에서 분기한다. scan selection은 기능 경로를
   제거하거나 우회하지 않는다.

이 문서는 설계 명세다. 이 revision을 승인하기 전까지 이전에 생성된
`common_scan_aes_internal.list`, `random_aes_seedNN.list` 및 그에 의존하는
DFT/TetraMAX 결과는 새 실험의 결과로 사용하지 않는다. 기존 파일은 삭제하지
않고 stale artifact로 보존하며, revision 2 manifest로 다시 생성한다.

---

## 1. 연구 질문과 가설

### 1.1 연구 질문

동일한 AES-128 one-round functional checkpoint, 동일한 총 scan budget,
동일한 fault universe와 ATPG 조건에서, 어느 AES sequential boundary를
scan-visible하게 만들었는지가 AES 내부 **combinational fault**의 검출률을
바꾸는가?

특히 다음을 검증한다.

> MixColumns output boundary의 scan observability가 SubBytes, ShiftRows,
> AddRoundKey boundary 또는 AES-stage random placement보다 높은 residual
> testability를 제공하는가?

여기서 MC의 높은 결과를 사전에 사실로 가정하지 않는다. MC가 높지 않으면
그 결과를 그대로 `NO_DIFFERENCE` 또는 `RANDOM_BETTER`로 보고한다.

### 1.2 검증 가설

- `H0`: direct FF fault를 제거한 뒤 IARK, SB, SR, MC의 AES 내부 coverage는
  통계적으로 구별되지 않는다.
- `H1`: direct FF fault를 제거한 뒤 MC placement가 stage 대조군과
  AES-stage random 대조군보다 높은 coverage를 보인다.
- `H1b`: MC variable 비중이 증가할수록 AES 내부 residual coverage가
  증가하는 경향이 있다.

`H1` 또는 `H1b`가 기각되면 MixColumns diffusion을 근거로 한 강한 DFT
주장은 하지 않는다. `MC`라는 이름 자체가 높은 testability를 보장하지
않으며, 결과는 실제 fault status와 동일 fault universe로만 판정한다.

---

## 2. 고정 functional checkpoint

모든 configuration은 다음 pre-DFT checkpoint에서만 분기한다.

```text
top                 : mor1kx_aes_soc
AES hierarchy       : u_aes_peripheral
AES architecture    : one-round pipelined AES accelerator
functional FF count : 4,157
AES FF count        : 772
```

AES sequential groups는 다음과 같다.

| Group | Count | Functional role |
|---|---:|---|
| `key_reg` | 128 | AES key input storage |
| `plaintext_reg` | 128 | chosen plaintext storage |
| `IARK_REG` | 128 | AddRoundKey boundary |
| `SB_REG` | 128 | SubBytes boundary |
| `SR_REG` | 128 | ShiftRows boundary |
| `MC_REG` | 128 | MixColumns boundary |
| valid/done control | 4 | AES transaction control |
| **Total** | **772** | |

checkpoint digest는 실행 직전에 다시 계산하고 manifest에 기록한다.

```text
pre-DFT DDC SHA256:
2eac94224ca109e3b2f65a4537b00d1f73aa6113393225c9712729cb123a2a72

pre-DFT Verilog SHA256:
d3989fbeb0353ca7b35dbbd1cb48a74fbdb6b4ad7f4f8cf761205cda9b27870e
```

다음은 case 사이에서 변경하지 않는다.

- RTL, elaboration 결과, mapped functional netlist와 library
- synthesis option, clock constraint, reset polarity와 functional protocol
- scan clock, scan enable, scan style, chain count와 balancing rule
- test procedure, capture schedule, X handling
- fault model별 TetraMAX script, ATPG effort, abort limit, pattern limit
- black-box/memory 처리와 fault classification 기준

---

## 3. Pipeline continuity와 입력 제어성

### 3.1 기능 경로의 의미

본 실험에서 “직렬로 연결”은 선택하지 않은 register를 물리적으로 scan
shift register로 만든다는 뜻이 아니다. 다음 functional D-input 경로가
모든 case에서 동일하게 존재해야 한다는 뜻이다.

```text
plaintext_reg/key_reg
        -> IARK combinational logic -> IARK_REG
        -> SubBytes logic             -> SB_REG
        -> ShiftRows wiring           -> SR_REG
        -> MixColumns logic            -> MC_REG
        -> output/round logic
```

selected variable bank 외의 stage FF는 기능 경로 안에 그대로 남는다. DFT
삽입은 해당 FF의 scan element 속성만 변경하며 functional D-input logic을
재작성하거나 앞단을 bypass하지 않는다.

### 3.2 입력 제어성 조건

모든 case에서 다음 FF는 common scan에 있어야 한다.

- `u_aes_peripheral/key_reg_reg[*]`
- `u_aes_peripheral/plaintext_reg_reg[*]`
- AES transaction을 시작하고 완료시키는 valid/done control FF
- 공통 host scan FF

기준 common list는 기존 `config/stage_common_scan.list`에서 시작한다.
현재 이 list는 AES non-stage 260개와 host 636개로 구성된 896개이며,
그 260개 안에 key/plaintext/control register가 포함된다. revision 2에서는
이 896개를 **그대로 보존**한다. 단, parser가 실제 checkpoint inventory와
일치하는지 실행 시 다시 assert한다.

### 3.3 continuity preflight

ATPG를 시작하기 전에 다음을 모두 확인한다.

### 3.4 Continuity의 operational definition

총 1,024-FF를 유지하면서 네 stage 중 하나만 variable scan bank로 비교하려면
네 stage를 모두 common scan으로 넣을 수는 없다. 그렇게 하면 비교할 variable
location이 남지 않는다. 따라서 본 실험에서 continuity는 다음처럼 정의한다.

- 네 stage의 functional D-input/Q 경로가 모든 case에서 동일하다.
- key/plaintext를 common scan으로 제어한 뒤, 여러 functional clock으로
  IARK, SB, SR, MC register를 순차적으로 채울 수 있다.
- 선택된 stage Q만 scan chain에서 직접 관측점이 되고, 선택되지 않은 stage는
  scan shift 대상은 아니지만 functional pipeline 안에서 제거되거나 bypass되지
  않는다.
- DFT mux와 scan chain 연결은 선택된 boundary와 common FF에만 추가되며,
  AES combinational logic의 functional path를 끊지 않는다.

즉 이 비교는 네 stage register 모두를 scan-visible하게 만든 full-pipeline
scan과 비교하는 실험이 아니다. full-pipeline scan은 total scan count와
variable placement가 달라지므로, 필요하면 1,408-FF의 별도 connectivity
diagnostic으로만 실행하고 주 coverage 표에는 넣지 않는다. 주 결과에서
S-Box fault가 관측되는 것은 input controllability와 functional clock
sequence, 선택 boundary의 downstream observability가 함께 성립했음을
ATPG 결과로 확인해야 하며, 단순히 MC라는 이름만으로 보장된다고 가정하지
않는다.


1. `key_reg`와 `plaintext_reg`가 common list에 각각 128개 존재한다.
2. IARK/SB/SR/MC 각 bank의 128개 cell이 functional checkpoint에 존재한다.
3. 각 stage register D net에 combinational driver가 있다.
4. `IARK -> SB -> SR -> MC` graph traversal이 stage boundary에서만
   멈추고, scan-only mux나 missing driver 때문에 끊기지 않는다.
5. DFT insertion 전후 functional output equivalence 또는 지정된
   scan-disabled equivalence가 유지된다.
6. TetraMAX DRC에서 scan protocol 오류가 있으면 해당 case를 결과에서
   제외하고 `INVALID`로 기록한다.

이 검사를 통과하지 못하면 S-Box fault가 AU가 되는 현상을 MC의 장점으로
해석하지 않는다.

---

## 4. Scan budget과 비교군

### 4.1 고정 budget

주 비교의 scan budget은 다음과 같다.

```text
common scan FF    = 896
variable scan FF  = 128
total scan FF     = 1,024
scan chain        = 1
chain length      = 1,024
```

모든 case에서 common 896개는 동일한 instance set이어야 한다. variable
bank만 바뀐다.

### 4.2 주 stage comparison

| Case | Common set | Variable 128 FF | 목적 |
|---|---|---|---|
| `CASE_IARK` | fixed common 896 | `IARK_REG[127:0]` | ARK boundary control |
| `CASE_SB` | fixed common 896 | `SB_REG[127:0]` | S-Box boundary control |
| `CASE_SR` | fixed common 896 | `SR_REG[127:0]` | ShiftRows boundary control |
| `CASE_MC` | fixed common 896 | `MC_REG[127:0]` | MixColumns boundary control |

네 case의 variable set은 각각 정확히 128개이며, 모든 case에서 input
register common 조건을 동일하게 만족한다.

### 4.3 AES-stage random control

기존의 host random 또는 key/plaintext를 random pool으로 뽑는 구성은 주
비교군으로 사용하지 않는다. 그것들은 AES stage placement의 대조군이
아니며 입력 제어성 조건을 흔들 수 있다.

새 random 대조군은 네 stage bank의 union에서만 뽑는다.

```text
AES_STAGE_POOL = IARK_REG union SB_REG union SR_REG union MC_REG
pool size      = 512
sample size    = 128
seeds          = 01 ... 10
```

각 seed는 `random_stage_seedNN.list`로 저장한다. seed마다 선택된 bank
비율도 함께 기록한다. random set에 MC bit가 포함될 수 있으므로, 각 seed의
`MC fraction`을 보고하지 않고 단순히 random 평균만 비교하는 것은 금지한다.

random 통계는 다음을 모두 보고한다.

- mean, median, standard deviation
- minimum, maximum
- MC-selected fraction per seed
- `MC - random mean`
- `MC - random maximum`

### 4.4 MC 비중 sweep

`H1b`를 검증하기 위해 동일한 128-FF budget 안에서 MC 비중을 바꾼다.

| Case family | MC variable count | Non-MC variable count |
|---|---:|---:|
| `CASE_MIX_MC_000` | 0 | 128 |
| `CASE_MIX_MC_032` | 32 | 96 |
| `CASE_MIX_MC_064` | 64 | 64 |
| `CASE_MIX_MC_096` | 96 | 32 |
| `CASE_MIX_MC_128` | 128 | 0 |

각 행은 고정된 nested subset을 사용한다.

- MC subset: 하나의 deterministic permutation에서 앞의 0/32/64/96/128개
- non-MC subset: IARK/SB/SR의 고정 balanced permutation에서 필요한 개수
- 모든 mix case의 total variable count: 128

이 sweep은 단일 MC bit index 선택의 우연성을 줄이고, MC fraction과
coverage의 단조성 여부를 관찰하기 위한 것이다. 단조성이 없더라도 이를
실패로 숨기지 않는다.

### 4.5 Baseline과 automatic case

다음 case는 보조 또는 D5 용도다.

- `CASE_COMMON_ONLY`: common 896만 scan. total scan이 다르므로 주
  1,024-FF 비교에는 포함하지 않고 input-control baseline으로만 사용한다.
- `CASE_AUTO_STAGE`: 전체 512 stage FF를 후보로 하여 topology/SCOAP
  ranking이 선택한 128개. ranking은 ATPG 결과, leakage 결과, secret key를
  입력으로 사용하지 않는다.

`CASE_AUTO_STAGE`는 MC가 자동으로 선택되는지를 보는 실험이지, commercial
partial-scan tool의 선택을 재현한다고 주장하는 실험은 아니다.

---

## 5. Fault universe

### 5.1 Scope

모든 case는 하나의 AES-internal functional fault universe를 읽는다.

```text
U_AES_RAW = all valid combinational fault entries under u_aes_peripheral
            - AES FF Q/QN direct faults
            - aes_result_o/aes_done_o interface output faults
            - scan-only/test-only nets
            - non-AES host/interface faults
```

여기서 “all”은 MC만 수동으로 골라낸다는 뜻이 아니다. S-Box gate, XOR,
ShiftRows wiring, AddRoundKey logic, MixColumns XOR/multiply logic 및 그
사이의 내부 net을 가능한 한 동일한 raw source에서 모두 포함한다.

historical `historical_canonical_faults_422.list`는 이 universe의 source로
사용하지 않는다. 422-entry 목록은 AES internal combinational fault를
대표하지 않으며, 과거의 22.04% 대 82.70% 결과를 재현하는 보조 자료일
뿐이다.

### 5.2 Direct FF fault exclusion

이번에는 variable 후보의 union만이 아니라 AES sequential inventory 전체
772개 FF의 Q/QN site를 direct exclusion set으로 만든다.

```text
S_DIRECT_AES = Q/QN sites of all 772 AES FFs
```

모든 case에 동일하게 적용한다.

- stuck-at: `sa0`와 `sa1`
- transition: `str`와 `stf`

따라서 MC output FF 자신의 direct SA0/SA1가 검출되는 효과는 주 비교에서
사라진다. key/plaintext FF direct fault도 같은 규칙으로 제외되지만,
그 FF의 Q에서 downstream combinational logic으로 들어가는 fault cone은
fault domain에 남는다.

### 5.3 Raw와 collapsed source

두 source를 구분한다.

1. `U_AES_RAW`: checkpoint에서 생성한 valid uncollapsed fault entries.
2. `U_AES_COLLAPSED`: 같은 checkpoint와 같은 AES scope에 대해 별도의
   TetraMAX collapse 단계로 얻은 representative entries.

collapsed source가 AES 내부 대표를 0개 생성하면 임의로 422 목록을 끼워
넣지 않고 `UNRESOLVED`로 기록한다. raw 결과는 그와 독립적으로 진행할 수
있다.

모든 case에서 다음 equality를 검사한다.

```text
fault_source_hash_CASE_IARK = ... = fault_source_hash_CASE_MC
loaded_fault_count_CASE_IARK = ... = loaded_fault_count_CASE_MC
```

다르면 coverage 비교를 중단한다.

---

## 6. D1: direct fault 제거 후 residual testability

### 목적

기존 22.04% 대 82.70%의 핵심 혼동인 “선택된 MC FF 자신의 fault를 직접
세었기 때문인가?”를 제거한다. D1은 MC가 자기 Q fault가 아닌 AES 내부
combinational fault의 관측에도 이득을 주는지 묻는다.

### 실행

1. 모든 AES FF Q/QN direct fault를 source에서 공통 삭제한다.
2. `CASE_IARK`, `CASE_SB`, `CASE_SR`, `CASE_MC`, random stage seeds를
   같은 `U_AES_RAW`에 대해 ATPG한다.
3. detected, possibly detected, AU, UD/ND, aborted, pattern, runtime을
   기록한다.
4. `U_AES_COLLAPSED`는 별도 표에서 같은 direct exclusion policy로 반복한다.

### 판정

- `D1_RESIDUAL_SUPPORT`: MC가 random mean과 stage 대조군보다 높고, 그
  증가가 direct FF site가 아닌 내부 region fault에서 발생한다.
- `D1_NO_RESIDUAL_GAIN`: direct exclusion 후 MC와 대조군이 수렴한다.
- `D1_INVALID`: fault source, input common, scan count 또는 DRC가 다르다.

---

## 7. D2: stage comparison과 MC diffusion-weight sweep

### 7.1 Stage 비교

주 표는 다음 순서로 만든다.

```text
IARK, SB, SR, MC, RANDOM_STAGE_seed01...seed10, AUTO_STAGE
```

각 case에 대해 whole AES-internal coverage와 region별 coverage를 함께
표시한다. `CASE_AUTO_STAGE`는 random 평균에 포함하지 않는다.

### 7.2 MC 비중 분석

`CASE_MIX_MC_000`부터 `CASE_MIX_MC_128`까지의 detected count와 coverage를
MC fraction에 대해 plot한다. 필요한 수치는 다음과 같다.

```text
Delta_FC(p) = FC(MC fraction p) - FC(MC fraction 0)
```

단순히 MC가 한 점에서 높다는 것보다, 여러 mix에서 증가 경향이 재현되는지와
그 증가가 어느 region에서 오는지를 본다.

### 7.3 주의할 해석

MC logic은 AES 수학상 diffusion을 수행하지만, stuck-at coverage는
cryptographic diffusion 그 자체의 측정값이 아니다. 관측 fanout, register
boundary, reconvergence, ATPG controllability/observability가 함께 영향을
준다. 따라서 “MC가 높다”는 결과가 나와도 `MC_CONE` status transition과
S-Box/ARK region의 변화가 동반되는지 D3에서 확인해야 한다.

---

## 8. D3: fault-cone와 region breakdown

### 8.1 Region 정의

direct/interface fault를 먼저 제거한 뒤, netlist graph와 stage D-cone을
사용해 각 fault site를 다음 중 하나로 분류한다.

| Region | Definition |
|---|---|
| `IARK_CONE` | IARK boundary D-input backward cone의 combinational site |
| `SB_CONE` | SB boundary D-input backward cone의 combinational site |
| `SR_CONE` | SR boundary D-input backward cone의 combinational site |
| `MC_CONE` | MC boundary D-input backward cone의 combinational site |
| `AES_CONTROL` | AES valid/done/start control logic |
| `AES_OTHER` | AES hierarchy 내에서 위 cone에 속하지 않는 logic |
| `SHARED_OR_OVERLAP` | 두 개 이상의 cone에 공동으로 속하는 site |
| `UNRESOLVED` | graph상 자동 분류가 불가능한 site |

clock, reset, scan enable은 data cone으로 따라가지 않는다. FF Q/QN,
`aes_result_o`, `aes_done_o`, host/interface와 scan-only site는 region
table에 들어가기 전에 제거한다.

### 8.2 산출 표

각 placement에 대해 다음을 모두 만든다.

```text
region_total
region_detected
region_coverage
region_AU / UD / ND / aborted
```

특히 case diff를 다음 형식으로 저장한다.

```text
CASE_RANDOM_STAGE: AU/ND -> CASE_MC: DT
CASE_RANDOM_STAGE: DT      -> CASE_MC: AU/ND
```

이 diff가 `MC_CONE` 또는 downstream observation에 집중되는지 확인한다.
S-Box region이 여전히 0% AU라면 input/control 또는 pipeline connectivity
preflight 결과와 함께 원인을 보고하며 MC diffusion의 증거로 포장하지 않는다.

---

## 9. D4: stuck-at와 transition fault

### Stuck-at

`U_AES_RAW`에서 SA0/SA1를 로드한다. 모든 case는 동일 source hash와 동일
direct exclusion file을 사용한다.

### Transition

동일한 AES internal site set에 대해 rising/falling transition fault를 만든다.
transition setup에서 launch/capture, scan enable constraint, clock protocol,
abort limit을 고정한다.

transition source의 site set이 stuck source와 다르면 그 차이를 먼저
보고하고, “stuck-at 대비 transition improvement”를 동일 denominator
비교처럼 쓰지 않는다.

### D4 판정

- 두 fault model 모두에서 MC 우위: `D4_COMPARATIVE_SUPPORT`
- stuck-at만 우위: `D4_STUCK_ONLY`
- transition만 우위: `D4_TRANSITION_ONLY`
- 모두 수렴: `D4_NO_DIFFERENCE`
- source/protocol/DRC 불일치: `D4_INVALID`

---

## 10. D5: automatic stage selection과 security-testability 연결

### Ranking 입력

`AUTO_STAGE` ranking은 다음 공개 구조 정보만 사용한다.

- FF의 D-input backward cone size
- Q fanout과 downstream endpoint 수
- logic depth/reconvergence proxy
- deterministic SCOAP-like controllability/observability proxy
- stage label은 분석용으로만 보존하며 ranking score의 직접 bonus로 넣지
  않는다.

ATPG detected status, leakage success, key, ground-truth placement label을
ranking 입력으로 사용하지 않는다.

### D5 산출

- top-128 selected stage cell 목록
- IARK/SB/SR/MC별 선택 개수
- ranking score 분포
- `AUTO_STAGE` coverage와 stage/random 비교
- 기존 leakage map을 연결할 경우, security metric은 외부 입력으로
  표시하고 ranking 이후에 join한다.

`AUTO_STAGE`가 MC를 선택하지 않아도 문제가 아니다. 그것은 현재 heuristic이
MC의 DFT utility를 자동 rediscover하지 못했다는 결과이며, commercial
partial-scan tool의 동작을 증명하지 않는다.

---

## 11. 공정성 및 validity gate

다음 표를 각 실행 전후에 생성한다.

| Check | Required value |
|---|---:|
| Functional checkpoint hash | identical |
| AES input common (`key_reg`) | 128 in every case |
| AES input common (`plaintext_reg`) | 128 in every case |
| AES control common | identical |
| Common scan FF count | 896 |
| Variable scan FF count | 128 |
| Total scan FF count | 1,024 |
| Scan chain count | 1 |
| Fault source hash | identical |
| Loaded fault count | identical |
| Direct Q/QN exclusion policy | all 772 AES FFs, identical |
| Scan clock/enable/protocol | identical |
| ATPG options hash | identical |
| Pipeline connectivity preflight | PASS |

다음 중 하나라도 발생하면 해당 비교는 `INVALID`다.

- key/plaintext가 common에 없는 case
- stage D-cone 또는 functional pipeline이 끊긴 case
- common/variable/total scan count 불일치
- fault source나 direct exclusion이 case별로 다름
- TetraMAX DRC가 case마다 다르거나 unresolved
- class sum이 loaded total과 다름
- UNKNOWN/timeout을 detected 또는 undetected로 임의 변환

---

## 12. 실행 workflow

1. 동일 pre-DFT checkpoint digest와 register inventory를 확인한다.
2. 기존 896 common을 복원하고 key/plaintext/control 포함 여부를 assert한다.
3. IARK/SB/SR/MC 512 stage inventory와 AES graph connectivity를 검증한다.
4. stage primary, random-stage, MC-mix, auto-stage manifests를 생성한다.
5. AES FF 772개의 Q/QN direct exclusion source를 한 번 생성한다.
6. 전체 AES internal raw fault source와 별도 collapsed source를 생성한다.
7. 각 scan manifest에 대해 동일 checkpoint에서 DFT insertion을 수행한다.
8. DFT DRC와 scan count/chain count를 검증한다.
9. 동일 raw stuck-at source로 ATPG를 수행한다.
10. 동일 transition source와 protocol로 D4를 수행한다.
11. TetraMAX summary와 detailed fault status를 case별로 보존한다.
12. D1 residual, D2 stage/mix, D3 region, D4 fault-model, D5 ranking을
    분석한다.
13. 마지막으로 validity gate를 통과한 행만 coverage 비교에 포함한다.

---

## 13. 산출물 이름

### Scan manifests

```text
config/common_scan_v2.list
config/iark_scan_v2.list
config/sb_scan_v2.list
config/sr_scan_v2.list
config/mc_scan_v2.list
config/random_stage_seed01.list ... seed10.list
config/mix_mc_000.list ... mix_mc_128.list
config/auto_stage_scan_v2.list
```

### Fault sources

```text
config/aes_internal_v2_raw_stuck.list
config/aes_internal_v2_raw_transition.list
config/aes_internal_v2_collapsed_stuck.list
config/aes_internal_v2_direct_exclusion_stuck.list
config/aes_internal_v2_direct_exclusion_transition.list
```

### Analysis

```text
results/analysis/aes_internal_v2_case_summary.csv
results/analysis/aes_internal_v2_region_breakdown.csv
results/analysis/aes_internal_v2_status_diff.csv
results/analysis/aes_internal_v2_mc_fraction.csv
results/analysis/aes_internal_v2_validity.json
reports/AES_INTERNAL_D1_D5_REPORT_REVISED.md
```

기존 `22.04% vs 82.70%` 표와 revision 2 residual 표는 같은 표에 섞지
않는다. 전자는 historical direct-output illustrative result이고, 후자는
AES internal direct-excluded controlled experiment이다.

---

## 14. 결과 해석 표

| Result | Correct interpretation |
|---|---|
| MC > all random and stage cases, raw/transition 모두 | MC boundary의 residual DFT utility를 지지하는 강한 결과 |
| MC > random mean이지만 일부 stage/random보다 낮음 | 제한된 조건에서의 MC utility; “항상 최고” 금지 |
| MC-mix에서 fraction 증가와 coverage가 함께 증가 | diffusion-weighted placement 가설을 지지하는 경향성 |
| MC direct-excluded gain이 0 | 과거 gain은 direct FF observability였을 가능성이 큼 |
| SB/internal faults가 여전히 전부 AU | 입력 제어성/clock/protocol/cone 문제 우선 조사 |
| random-stage가 MC보다 높음 | MC 우위 가설 기각; 결과를 그대로 보고 |
| auto-stage가 MC를 선택하지 않음 | heuristic 한계 또는 MC가 global ranking 최적이 아님 |

어떤 결과에서도 “MC diffusion이 자동으로 높은 coverage를 보장한다”고
수학적으로 일반화하지 않는다. 주장 가능한 범위는 측정된 checkpoint,
fault universe, budget, ATPG protocol과 seed 범위로 한정한다.

---

## 15. 핵심 변경 요약

```text
이전: host-only common 896
수정: 기존 common 896 유지, key/plaintext/control 포함

이전 주 random: AES non-stage 또는 host pool
수정 주 random: 512 AES stage FF pool

이전 direct exclusion: variable candidate union 중심
수정 direct exclusion: 전체 AES 772 FF Q/QN 공통 배제

이전 핵심 주장: MC placement가 residual utility를 가질 것
수정 핵심 가설: MC 우위 여부를 stage/random/mix/region으로 검증

이전 pipeline 조건: 입력 register 제거 가능
수정 pipeline 조건: 입력 제어성과 functional IARK-SB-SR-MC continuity 필수
```

