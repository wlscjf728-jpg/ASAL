# Sparse Scan-Visible 1-bit FF AES-128 Key-Recovery: Integrated Research and Algorithm Specification

## Standalone Research Overview

### 연구 출발점

이 연구의 출발점은 다음 질문이다.

> AES-128 하드웨어에서 공격자가 전체 128-bit register를 읽지 못하고, scan-visible한 sparse 1-bit FF 몇 개만 시간축으로 관측할 때 master key K0가 유일하게 결정될 수 있는가?

여기서 FF의 정의는 끝까지 동일하다.

~~~text
1-bit leakage = 1개의 1-bit flip-flop 관측
2-bit leakage = 1-bit FF 2개 관측
3-bit leakage = 1-bit FF 3개 관측
4-bit leakage = 1-bit FF 4개 관측
~~~

따라서 이 연구의 128-bit AES state surface는 실제 공격자가 128-bit FF bank 전체를 읽는다는 뜻이 아니다. SB, SR, MC, ARK의 128개 bit index는 후보 semantic 위치를 정의하기 위한 reference map이다. 실제 공격에는 최종적으로 선택된 sparse FF만 필요하다.

### 연구의 핵심 관점

초기 실험은 clean AES semantic surface에서 위치 조합을 직접 지정했다.

~~~text
SB_i, SR_i, MC_i, ARK_i
→ temporal leakage 생성
→ AES key-consistency constraint 구성
→ master-key uniqueness 판정
~~~

이후 연구는 실제 anonymous scan 상황으로 확장됐다.

~~~text
anonymous full scan-out
→ MC-like 1-bit scan slot 발견
→ slot을 semantic/function hypothesis로 해석
→ 동일 slot을 fixed sparse tap으로 전달
→ fixed-query key uniqueness
→ ambiguity 발생 시 adaptive separator query
~~~

따라서 연구 전체는 위치 sweep과 key solver를 별개로 나열하는 것이 아니라, 다음 하나의 공격 파이프라인으로 정의된다.

~~~text
scan-visible FF discovery
→ cryptographic function attribution
→ temporal leakage modeling
→ fixed-query key identifiability
→ ambiguity-driven adaptive recovery
~~~

### 네 가지 실험축

| 축 | 연구 질문 | 입력 | 핵심 구현 | 출력 |
|---|---|---|---|---|
| 1. Subround scan FF 감지·위치 후보화 | anonymous scan-out 중 MC output을 저장할 가능성이 높은 1-bit slot은 무엇인가? | anonymous full scan vector | Python scan wrapper, differential signature, timing/support scoring | s*, MC column 후보, confidence |
| 2. 위치의 semantic/function 해석 | 선택된 slot을 Phase 1 solver가 계산 가능한 Boolean-function hypothesis로 연결할 수 있는가? | s*, support, capture timing | MC hypothesis enumeration, same-slot handoff, optional cone/function analysis | T={s*} 또는 hypothesis 집합 |
| 3. 1차 fixed-query 탈취 | 고정 query에서 관측 제약이 master key 하나만 허용하는가? | sparse tap, temporal transcript | Python AES trace, Z3Py bit-vector model | SAT→UNSAT unique 또는 SAT→SAT ambiguity |
| 4. 2차 ambiguity adaptive 탈취 | ambiguity candidate를 새 chosen plaintext로 분리할 수 있는가? | Ka, Kb, ambiguity transcript | Z3 separator synthesis, Oracle query, dependency-support ranking | 추가 제약, 재검사, 최종 unique/non-recovery |

### 기여와 novelty

이 연구의 novelty는 AES S-box나 Z3 solver 자체를 새로 만드는 데 있지 않다. 기여는 anonymous sparse scan FF를 cryptographic key-identifiability 문제로 변환하는 통합 분석 방법에 있다.

1. **MC-aware anonymous channel discovery**  
   scan stitching map과 RTL instance 이름을 모르는 상태에서 plaintext differential signature, capture timing, AES activity, ShiftRows-aligned MC support를 이용해 후속 공격에 사용할 1-bit channel 후보를 찾는다.

2. **Channel-to-solver handoff**  
   발견된 scan slot을 정확한 physical coordinate로 과장하지 않고, 가능한 MC semantic/function hypothesis 집합으로 유지한다. 동일 trial의 동일 scan slot을 Phase 1 fixed tap으로 직접 넘기는 identity-preserving handoff를 검증한다.

3. **Strict full-key identifiability criterion**  
   첫 번째 SAT model이 true key처럼 보인다는 이유로 성공을 선언하지 않는다. 반드시 C_Q(K) AND K != K_hat가 UNSAT인지 확인한다. 이 기준으로 unique, ambiguity, unresolved를 엄격히 분리한다.

4. **Ambiguity reuse adaptive attack**  
   fixed-query에서 얻은 alternative key를 버리지 않고, 두 후보의 leakage가 달라지는 plaintext를 Z3로 합성해 Oracle에 질의한다. dependency support는 query 우선순위화에 사용하고, 최종 판정은 다시 full-key solver로 한다.

5. **Empirical semantic risk map**  
   위치 자체가 아니라 AES diffusion boundary, temporal round progression, stage, column/diagonal/scatter topology가 sparse leakage 위험에 미치는 영향을 실험적으로 지도화한다.

즉 novelty의 핵심 표현은 다음과 같다.

~~~text
anonymous scan FF
→ AES semantic/function attribution
→ diffusion-aware sparse leakage map
→ strict key identifiability
→ ambiguity-adaptive refinement
~~~

### 공격 모델과 해석 범위

공격자는 다음을 제어할 수 있다고 가정한다.

- chosen plaintext
- AES start
- capture clock 수 또는 capture schedule
- scan shift 및 전체 scan-out 읽기
- Phase 간 설정 전달과 추가 query 선택

Oracle 모델이므로 Phase 중간에 s*, candidate hypothesis, Ka/Kb를 이용해 다음 실험을 구성하는 것은 허용된다. 다만 ground-truth key, 실제 scan permutation, 실제 MC bit index는 discovery analyzer의 입력으로 사용하지 않고, 최종 평가에만 사용한다.

실제 synthesized/retimed AES에서 기존 semantic 결과를 적용하려면 physical FF q가 다음 조건 중 하나를 만족해야 한다.

~~~text
q의 저장 값 = clean SB/SR/MC/ARK semantic bit
또는
q의 저장 값 = 분석 가능한 Boolean function f_q(P,K)
~~~

S-box 내부 node, MixColumns partial XOR, fused node, retimed internal node가 clean output과 다르면 해당 FF는 새로운 f_q 모델과 D-input cone 분석이 필요하다. 따라서 이 연구의 map은 물리적 FF 전체의 vulnerability map이 아니라 empirical semantic/function risk map이다.

### 실험 구현 환경

현재 실험 코드 기준으로 네 축은 모두 Python 3 기반이다. C++ 구현은 이 campaign에 사용되지 않았다.

| 구성요소 | 구현 |
|---|---|
| AES-128 reference | Python aes_ref.py, 표준 AES round/key schedule |
| trace/oracle | Python oracle.py, SB/SR/MC/ARK trace와 differential leakage 생성 |
| discovery | Python anonymous scan wrapper와 signature/support 분석 |
| key solver | Python z3_aes.py, Z3Py bit-vector AES graph |
| S-box | 주로 uf_axiom encoding |
| adaptive query | Python symbolic plaintext 및 separator synthesis |
| dependency support | Python provenance/support propagation |
| 병렬 실행 | Python ProcessPoolExecutor, Bash/setsid |
| 주요 SMT solver | Z3 4.13.4.0 |

cvc5가 environment dependency에 포함된 경우가 있으나, 보고된 핵심 결과는 Z3 기반이므로 본 연구의 주 solver는 Z3로 명시한다.

## Four-Axis Experimental Protocol

### Axis 1. Anonymous MC Leakage-Channel Discovery

#### 목적

전체 anonymous scan-out vector에서 pre-ARK MC output과 일관된 1-bit scan slot을 찾는다. 이 단계는 key recovery가 아니라 관측 channel 선택 단계다.

#### 환경과 구현

- trial당 synthetic scan FF 256개
- MC target FF 1개 이상
- ARK, round-register, SB, SR decoy 및 control FF 포함
- random scan stitching
- 공격자 분석 입력: anonymous scan vector, plaintext, capture schedule
- 비공개 평가 정보: key, source label, permutation, true MC bit

기준 plaintext P0와 각 plaintext byte j에 대해 다음 coarse query를 사용한다.

~~~text
D = {0x01, 0x02, 0x04, 0x08}
|Q_coarse| = 1 + 16×4 = 65
~~~

capture schedule은 다음 세 가지다.

~~~text
mc_capture
round_register_update
post_update
~~~

scan slot s의 differential signature는 다음과 같이 계산한다.

~~~math
sigma_s(P) = X_s(P, capture) XOR X_s(P0, capture)
~~~

후보 점수에는 stable slot, AES activity, pre-round timing, MC column support가 포함된다. ShiftRows-aligned MC column은 다음과 같다.

~~~text
C0 = {0, 5, 10, 15}
C1 = {4, 9, 14, 3}
C2 = {8, 13, 2, 7}
C3 = {12, 1, 6, 11}
~~~

#### 결과

- positive trials: 32
- positive PASS: 32/32
- top-1/top-5/top-10 recall: 모두 32/32
- held-out signature 재현: 32/32
- decoy-only negative trials: 8
- false positive: 0/8

이 결과는 현재 synthetic, 무잡음, random-stitching-fixed wrapper에서 MC-like candidate discovery 절차가 재현된다는 의미다. 실제 netlist의 물리적 mapping까지 증명하는 결과는 아니다.

### Axis 2. Channel Attribution과 Phase 0→Phase 1 Handoff

#### 목적

Phase 0에서 선택한 anonymous slot이 Phase 1의 sparse tap으로 실제 재사용될 수 있는지 확인한다. 단순히 같은 MC column을 찾는 것이 아니라 같은 scan slot identity를 유지하는 것이 핵심이다.

#### hypothesis 구성

discovery가 column Ck를 반환하면, 해당 MC output column의 4 byte × 8 bit를 후보로 만든다.

~~~math
H_s* =
{MC_Ck_BYTE_b_BIT_l
 | b ∈ Ck, l ∈ [0,7]}
~~~

따라서 column 하나당 32개의 MC bit hypothesis를 유지한다. 정확한 bit나 physical location을 임의로 고정하지 않는다.

#### paired handoff 조건

하나의 동일 trial에서 다음을 고정한다.

~~~text
same AES key
same scan FF set
same random scan permutation
same MC target source
~~~

Phase 0에서 선택한 slot을 s0라 하면 Phase 1은 다음을 사용한다.

~~~text
T = {s0}
Phase 1 round 1: Phase 0 raw mc_capture signature 재사용
Phase 1 round 2: 동일 s0의 다음 round observation 추가
~~~

판정 조건은 다음이다.

- Phase 0 selected slot = Phase 1 reused slot
- 공통 plaintext에서 Phase 0와 Phase 1 round-1 signature 일치
- round-2도 동일 slot 사용
- 평가용 ground truth에서 동일 MC source 확인
- true MC hypothesis가 candidate set에 포함
- decoy trial에서는 slot handoff가 발생하지 않음

#### 결과

- positive handoff: 32/32 PASS
- slot identity 유지: 32/32
- 공통 query signature 일치: 각 trial 65/65
- round-2 동일 slot 유지: 32/32
- 동일 MC source 평가: 32/32
- negative handoff: 8/8 PASS
- decoy false handoff: 0/8

이 결과는 Phase 0 discovery output이 Phase 1 fixed tap으로 연결됨을 검증한다. key가 unique하다는 뜻은 아니다.

### Axis 3. Fixed-Query First Key-Recovery Test

#### 목적

선택된 sparse tap의 temporal leakage가 master key K0를 유일하게 결정하는지 검사한다.

#### 환경

- standard AES-128 encryption 및 key schedule
- clean semantic taps: SB, SR, MC, ARK
- tap count: 1, 2, 3, 4
- temporal depth: 2
- leakage mode: differential
- query ladder: q=32, 64, 96, 128, 192, 255
- seeds: topology별 반복 seed
- Z3 S-box encoding: uf_axiom
- parallel case/seed execution

Oracle leakage는 다음과 같다.

~~~math
ell_t(P,P0;K)
= v_t(P;K) XOR v_t(P0;K)
~~~

전체 consistency constraint는 다음과 같다.

~~~math
C_Q(K)
=
AND_{P ∈ Q}
[
L_T^d(P,P0;K)=Y(P)
]
~~~

판정은 두 solve로 고정한다.

~~~text
Solve 1: C_Q(K)
Solve 2: C_Q(K) AND K != K_hat
~~~

| First solve | Second solve | 판정 |
|---|---|---|
| SAT | UNSAT | full-key unique, 1차 탈취 |
| SAT | SAT | ambiguity, alternative key 존재 |
| UNKNOWN/timeout | any | unresolved, 성공 아님 |
| UNSAT | - | model/transcript inconsistency |

#### _7/_7_1 semantic sweep 결과

이 sweep은 실제 물리 scan map이 아니라 clean semantic reference surface의 위치 조합을 평가한 것이다.

- Phase 7: 2-bit 220 cases, 3-bit 100 cases, 4-bit 45 cases
- Phase 7_1: 2-bit 198 cases, 3-bit 90 cases, 4-bit 60 cases
- integrated recorded cases:
  - 2-bit: 418 cases, 1361 runs
  - 3-bit: 190 cases, 570 runs
  - 4-bit: 105 cases, 315 runs
- 최종 integrated rows에서 UNKNOWN/blocked: 0

주요 경향은 다음과 같다.

- 2-bit early-only SB/SR 조합: 대부분 ambiguity
- 2-bit late MC/ARK 포함 조합: high-risk, many full-key unique
- 3-bit early-only: 여전히 ambiguity 경향
- 3-bit weak-late/same-column: 추가 tap으로 unique 전환
- 4-bit 일부 early-only: round-2 temporal diffusion 때문에 unique 가능
- mixed/scatter topology: 단순 same-byte 여부보다 stage와 diffusion support가 중요

이 결과는 위치 기반 empirical semantic risk map을 제공하지만, 모든 physical FF 조합의 전수조사는 아니다.

### Axis 4. Ambiguity-Reuse Adaptive Recovery

#### 목적

1차 fixed-query에서 SAT→SAT가 나온 ambiguity를 버리지 않고, 두 candidate key를 구별하는 plaintext를 추가해 key space를 줄인다.

#### 입력

~~~text
Q_i
C_Qi(K)
Ka: first solve model
Kb: alternative solve model
~~~

#### pair separator 합성

Z3에 symbolic plaintext P를 만들고 다음을 요구한다.

~~~math
L_T^d(P,P0;Ka)
≠
L_T^d(P,P0;Kb)
~~~

동시에 다음 domain 조건을 적용할 수 있다.

- one-byte differential
- bounded active bytes
- unrestricted chosen plaintext
- 기존 query와 중복 금지

separator가 SAT이면 해당 plaintext를 Oracle에 질의하고 다음 제약을 추가한다.

~~~math
C_Q(i+1)(K)
=
C_Qi(K)
AND
[
L_T^d(P_sep,P0;K)=Y(P_sep)
]
~~~

그 후 전체 key space에 대해 First/Second solve를 다시 실행한다. 현재 pair가 분리되지 않는다고 바로 비탈취로 결론내리지 않고, 필요하면 global separator 검사를 수행한다.

#### dependency-support 사용

dependency support는 각 candidate key가 어떤 key byte/bit와 연결되어 있는지 계산하는 구조적 heuristic이다.

~~~text
candidate key difference
→ unresolved key-byte support
→ predicted leakage influence
→ separator 후보 ranking
~~~

support score는 query 선택 순서를 정할 뿐이며, 그 자체로 탈취 판정을 내리지 않는다. 최종 성공은 항상 새 Oracle constraint를 추가한 뒤 SAT→UNSAT으로 확정한다.

#### 종료 조건

- SAT→UNSAT: full-key recovery
- 모든 candidate pair에 대해 global separator UNSAT: 해당 sparse leakage model에서 observational non-recovery
- SAT→SAT: 계속 adaptive
- UNKNOWN: unresolved, 성공/실패 아님

이 구조는 late 1-bit 및 기존 ambiguity hard case에 적용하는 2차 공격 알고리즘이며, 고정 query sweep 자체와는 다른 query-generation 단계다.

## Integrated Reproducibility Record

### 공통 입력과 출력

각 run은 최소한 다음을 기록한다.

~~~text
case/topology
tap list
stage/bit index 또는 function hypothesis
seed
depth/mode
plaintext query set
observed differential transcript
first solver result
second solver result
candidate key / alternative key
separator plaintext
dependency-support score
final classification
~~~

### 결과 파일

- _7 semantic sweep 결과: anonymous_subround_multiround_attack_7_oracle/results/
- _7_1 gap completion 결과: anonymous_subround_multiround_attack_7_1_oracle/results/
- MC discovery 결과: anonymous_subround_multiround_attack_Leakage_Channel_Discovery/results/
- 통합 알고리즘 문서: 현재 파일의 이후 상세 절

### 주장 가능한 것

현재 실험으로 주장할 수 있는 범위는 다음이다.

~~~text
1. 특정 semantic sparse FF topology가 K0 uniqueness에 미치는 empirical 경향
2. anonymous scan vector에서 MC-like channel을 찾는 synthetic procedure
3. 선택 channel을 동일 trial의 Phase 1 tap으로 전달하는 handoff
4. fixed-query SAT→UNSAT key identifiability algorithm
5. ambiguity를 separator query로 재사용하는 adaptive framework
~~~

다음은 아직 직접 증명한 범위가 아니다.

~~~text
1. 모든 synthesized/retimed AES에서 동일한 결과가 보장됨
2. 실제 physical coordinate가 자동 복원됨
3. S-box 내부/partial-XOR/fused FF에도 clean semantic map이 그대로 적용됨
4. 모든 ambiguity가 adaptive query로 반드시 unique로 바뀜
5. full scan map이나 128-bit register bank가 공격자에게 필요함
~~~

### 논문에서의 핵심 주장

가장 안전하고 강한 논문 framing은 다음이다.

> We present a diffusion-aware methodology for evaluating AES-128 key-identifiability from sparse scan-visible 1-bit flip-flops. The methodology first discovers anonymous MC-like leakage channels, attributes them to semantic or Boolean-function hypotheses, verifies fixed-query master-key uniqueness using a strict SAT-to-UNSAT criterion, and reuses ambiguous candidate keys to synthesize adaptive distinguishing plaintexts. The resulting semantic risk map shows that sparse leakage risk is determined by AES stage, diffusion boundary, temporal round progression, and dependency complementarity rather than by tap count alone.

---

## Detailed Algorithm Specification

## 1. 목적과 공격 대상

본 문서는 AES-128 하드웨어에서 scan-visible한 sparse 1-bit FF leakage만으로 master key `K0`를 복구하는 통합 알고리즘을 정의한다. 여기서 `n` bit leakage는 `n`개의 독립적인 1-bit FF를 관측한다는 뜻이다. 128-bit register 전체를 관측한다는 뜻이 아니다.

공격자는 고정된 tap 집합 `T`를 관측한다.

```text
T = {t1, t2, ..., tm}
ti = (cycle, round, stage, semantic-bit 또는 FF-function)
```

`m`은 scan-visible FF 수이다. 공격 도중 tap의 위치나 개수는 바꾸지 않는다. 바꿀 수 있는 것은 chosen plaintext뿐이다.

이 문서의 목표는 다음 둘 중 하나를 엄격하게 판정하는 것이다.

```text
탈취 성공: 관측 제약이 K0 하나만 허용함
비탈취 확정: 허용된 모든 새 plaintext에서도 남은 후보들을 분리할 수 없음
```

solver `UNKNOWN`, timeout, 재현 불일치는 어느 쪽 판정도 아니다.

## 2. 하드웨어 및 Oracle 가정

### 2.1 AES 모델

- AES-128 표준 encryption과 표준 AES key schedule을 사용한다.
- 초기 master key `K0` 128 bit 전체가 미지수이다.
- round 내부 semantic stage는 `SB`, `SR`, `MC`, `ARK`로 표현한다.
- 관측 깊이는 보통 `d=2`이다. 즉 같은 tap을 round 1과 round 2에서 시간축으로 관측한다.

### 2.2 Subround register와 scan-visible FF

clean semantic reference model에서 예를 들어 `MC_out[i]`는 MixColumns 직후의 semantic bit를 뜻한다. 실제 회로에서 이 결과를 적용하려면 다음이 성립해야 한다.

```text
physical FF q의 저장 값
  = selected cycle의 semantic stage bit x[r, stage, i](P, K0)
```

즉 synthesis, retiming, pipeline 때문에 생긴 실제 FF라도 해당 cycle의 D-input/저장 값이 clean semantic bit와 Boolean 및 cycle 관점에서 동등하면 같은 공격 제약을 적용할 수 있다.

반대로 S-box 내부 node, MixColumns partial XOR, fused logic, retimed internal node처럼 `SB/SR/MC/ARK` output과 다른 Boolean function을 저장한다면 semantic bit index를 그대로 적용하지 않는다. 그 FF의 실제 Boolean function `f_q(P, K0)`를 추출해 아래의 leakage 함수에 직접 넣어야 한다.

### 2.3 Chosen-plaintext differential Oracle

기준 plaintext `P0`와 chosen plaintext `P`에 대해 tap `t`의 관측값은 다음과 같다.

```math
ell_t(P, P0; K) = v_t(P; K) XOR v_t(P0; K)
```

여기서 `v_t`는 해당 FF 또는 semantic bit의 저장 값이다. 전체 leakage signature는 다음이다.

```math
L_T^d(P, P0; K)
 = (ell_t(P, P0; K)) for all t in T and rounds r=1,...,d
```

따라서 tap이 `m`개이고 depth가 `d`이면 plaintext 하나는 `m*d`개의 1-bit temporal observation을 제공한다. 이 식은 FF가 1-bit라는 전제를 보존한다.

Oracle은 실제 hidden key `K0`에 대해 `L_T^d(P, P0; K0)`를 반환한다고 가정한다. noise, observation error, scan ordering error는 이 알고리즘의 기본 모델에 포함하지 않는다.

## 3. End-to-End Stream: Anonymous MC Channel Discovery에서 Key Recovery까지

앞의 절까지는 `T`가 이미 정해져 있다고 가정했다. 즉 공격자가 어떤 FF를 읽는지, 또는 적어도 그 FF가 `MC_out[i]`, `ARK_out[i]`와 어떤 Boolean function/cycle 관계를 갖는지 알고 난 뒤의 key-recovery 알고리즘이었다. 그러나 anonymous full scan-out에서는 공격 코드가 scan slot의 RTL 이름, physical 위치, scan stitching map, 정확한 AES bit index를 알 수 없다. 따라서 실제 공격 흐름은 key solver를 실행하기 전에 먼저 다음 질문에 답해야 한다.

```text
전체 scan-out vector 중에서
현재 plaintext에 반응하고,
MC capture 직후에 처음 나타나며,
round-register update 이전에 관찰되고,
AES의 MC column support와 일치하는
안정적인 1-bit scan slot이 존재하는가?
```

이 질문에 답하는 전단계가 `MC Leakage-Channel Discovery`이다. 그 결과는 정확한 physical mapping을 복원하는 것이 아니라, 후속 key recovery가 사용할 수 있는 후보 channel과 Boolean-function hypothesis의 집합을 만든다.

### 3.1 전체 공격의 논리적 순서

최종 통합 흐름은 다음과 같다.

```text
Anonymous full scan-out vector
        |
        v
[Phase A] MC-aware leakage-channel discovery
        |
        |  scan slot s, first-active schedule,
        |  plaintext-byte support, MC-column hypothesis
        v
[Phase B] Channel/function hypothesis preservation
        |
        |  T = {s*} 또는 {f_q 후보들}
        |  정확한 bit index를 아직 모르면 후보 집합으로 유지
        v
[Phase C] 고정 query Q0에 대한 differential leakage 수집
        |
        v
        C_Q0(K) 구성
        |
        v
[Phase D] 1차 fixed-query full-key uniqueness solve
        |
        +-- SAT -> UNSAT : full-key 탈취 성공
        |
        +-- SAT -> SAT   : alternative key 존재, Phase E로 이동
        |
        v
[Phase E] 2차 pair-adaptive separator + dependency-support ranking
        |
        |  Ka, Kb를 구별하는 Psep 합성
        |  Oracle 질의 후 제약 추가
        |  전체 key space 재검사
        v
[Phase F] 최종 판정
        |
        +-- SAT -> UNSAT : full-key 탈취 성공
        +-- global separator UNSAT : observational non-recovery 확정
        +-- UNKNOWN/timeout : unresolved, 성공/실패 아님
```

여기서 핵심은 `channel discovery`와 `key recovery`의 역할을 섞지 않는 것이다.

- channel discovery는 `어느 anonymous scan slot을 후속 관측 channel로 사용할 것인가`를 정한다.
- key recovery는 선택된 1-bit FF의 반복 관측값이 `K0`를 유일하게 정하는지 검사한다.
- channel discovery의 top-1이 ground truth MC FF였다는 사실만으로 key가 복구된 것은 아니다.
- 반대로 key solver가 특정 semantic tap에 대해 `SAT -> UNSAT`를 보였더라도 실제 회로 FF가 그 semantic function을 저장한다는 mapping 증거가 없으면 physical attack claim으로 바로 확장할 수 없다.

### 3.2 Phase A: Anonymous scan vector에서 MC 후보 찾기

#### 3.2.1 관측 모델

한 query와 capture schedule에서 전체 scan-out vector를 다음처럼 둔다.

```math
X(P, c) = (x_0(P,c), x_1(P,c), ..., x_{N-1}(P,c))
```

`N`은 scan FF 전체 수이지만, 이는 공격자가 128-bit AES register 전체를 관측한다는 의미가 아니다. `N`개의 bit는 anonymous full scan-out stream을 분석하기 위한 입력이고, channel discovery가 최종적으로 선택하는 것은 그중 하나의 1-bit slot `s*`뿐이다. 후속 sparse attack에는 다음처럼 한 bit만 전달된다.

```text
T = {s*}
```

각 plaintext byte `j`의 반응을 확인하기 위해 기준 plaintext `P0`와 다음 차분을 사용한다.

```text
D = {0x01, 0x02, 0x04, 0x08}
P(j, delta) = P0 with byte j XOR delta
Qcoarse = {P0} union {P(j, delta) | j=0,...,15; delta in D}
|Qcoarse| = 1 + 16 * 4 = 65
```

각 `P`에 대해 최소한 다음 세 capture schedule의 scan vector를 저장한다.

```text
mc_capture
round_register_update
post_update
```

그리고 scan slot `s`에 대해 기준 plaintext와의 differential signature를 계산한다.

```math
sigma[s,j,delta,c] = X_s(P(j,delta), c) XOR X_s(P0,c)
```

이 signature는 scan bit 자체의 고정값보다 유용하다. control/reset 값처럼 plaintext와 무관한 FF는 차분 후 대부분 0이 되며, AES datapath에 반응하는 FF는 plaintext byte를 바꿀 때 반복되는 반응 패턴을 만든다.

#### 3.2.2 anonymous lane과 evaluation lane의 분리

실험은 두 개의 정보 흐름으로 나뉜다.

```text
Anonymous analysis lane
  입력: scan slot index, scan vector, plaintext, capture schedule
  금지: key, scan permutation, RTL/FF name, physical location, MC bit index
  출력: candidate slot, timing, support, score, hypothesis

Ground-truth evaluation lane
  입력: 실험 생성기 내부의 hidden source label/target slot
  사용: 최종 recall과 false-positive 평가에만 사용
  출력: 실제 MC FF 여부, ARK/round-register 오선택 여부
```

ground truth가 analyzer에 들어가면 channel discovery가 아니라 분류 결과를 답안으로 주는 것이 된다. 따라서 anonymous JSON에는 `key_hex`, `scan_sources`, `scan_permutation`을 넣지 않고, 별도 평가 파일에서만 실제 target slot을 비교한다.

#### 3.2.3 후보 조건과 score

각 scan slot에 대해 다음 네 가지 관점으로 점수를 계산한다.

1. **Stable slot**: 여러 query와 동일 schedule에서 같은 scan index가 반복되어야 한다. slot 자체가 query마다 움직이면 고정 tap으로 사용할 수 없다.
2. **AES activity**: AES start가 없는 idle/control 조건과 비교하여 AES 동작 및 plaintext 변화에 반응해야 한다.
3. **Pre-round timing**: 현재 plaintext의 반응이 `mc_capture`에서 나타나고, `round_register_update` 또는 `post_update`에서 처음 생긴 반응이 아니어야 한다. 즉 round-register/ARK 이후 decoy만으로는 통과하지 않아야 한다.
4. **MC-aware byte support**: 반응한 plaintext byte 집합이 ShiftRows 이후 하나의 MixColumns column과 최대한 겹쳐야 한다.

ShiftRows-aligned column은 다음과 같이 정의한다.

```text
C0 = {0, 5, 10, 15}
C1 = {4, 9, 14, 3}
C2 = {8, 13, 2, 7}
C3 = {12, 1, 6, 11}
```

관측 support `S_s`와 column `Ck`의 유사도는 예를 들어 다음 Jaccard score로 계산할 수 있다.

```math
MCColumnScore(s) = max_k |S_s intersection C_k| / |S_s union C_k|
```

실험 구현은 support가 하나의 column에 충분히 겹치는 후보를 보존하기 위해 다음 gate를 사용했다.

```text
|S_s| >= 2
MCColumnScore(s) >= 0.5
first_active_schedule(s) = mc_capture
```

이는 `정확히 네 byte가 모두 관측되어야 한다`는 hard gate가 아니다. 4개 coarse delta와 S-box/MC 비선형성 때문에 일부 source byte가 해당 query 집합에서 반응하지 않을 수 있으므로, 최소 support와 column overlap을 먼저 확인하고 held-out/refinement query로 보강한다. 점수의 예시적 결합은 다음과 같다.

```math
Score(s) =
  stable_slot_score(s)
  + AES_activity_score(s)
  + pre_round_timing_score(s)
  + MC_column_support_score(s)
```

정확한 MC row/bit index를 억지로 하나로 고정하지 않고 top-`k` 후보와 다음 hypothesis를 함께 반환한다.

```text
{scan_slot, first_active_schedule, support, closest_MC_column,
 score, differential_signature, candidate_function_class}
```

`candidate_function_class`는 `pre-ARK MC bit`, `MC-derived Boolean function`, `ARK/round-register decoy`, `unknown AES-dependent` 같은 기능적 후보군이다. 이후 실제 D-input cone 분석에서 하나로 좁혀지지 않으면 후보 집합을 유지한 채 각 hypothesis별 key constraint를 분기할 수 있다.

#### 3.2.4 refinement와 superposition 확인

top-`k` 후보에 대해서만 추가 query를 사용한다. 이 단계는 전체 scan slot과 128-bit key를 하나의 거대한 Z3 문제로 만드는 단계가 아니다. 우선 Python bit-vector/signature 분석으로 후보를 줄인다.

```text
1. source byte별 delta를 8개 또는 16개로 확장
2. coarse query에 포함되지 않은 held-out random plaintext 적용
3. 같은 MC column의 두 source byte를 동시에 변화
4. 단일 변화 signature와 joint 변화 signature의 관계 기록
5. 후보 slot의 first-active schedule과 support 재검사
```

두 source byte를 동시에 변화시키는 실험은 다음 diagnostic을 제공한다.

```math
joint_response(P_a XOR P_b)
  ?= response(P_a) XOR response(P_b)
```

다만 AES S-box 앞단의 비선형성, differential signature의 정의, capture state에 따라 이 등식이 항상 성립한다고 가정하면 안 된다. 따라서 superposition match는 MC 후보를 보조하는 관찰값이지 단독 PASS 조건이 아니다. 최종 channel 선택에는 반복성, pre-ARK timing, MC support, held-out 재현성을 함께 사용한다.

#### 3.2.5 channel discovery의 산출물

후속 key-recovery 단계로 전달하는 최소 observation 파일은 다음과 같다.

```json
{
  "scan_slot": 101,
  "first_active_capture_schedule": "mc_capture",
  "observed_plaintext_byte_support": [2, 8, 13],
  "closest_mc_column": 2,
  "confidence_score": 0.71442308,
  "differential_signature": "...",
  "function_hypotheses": ["pre_ARK_MC_bit", "MC_derived_bit"]
}
```

여기서 `scan_slot: 101`은 예시일 뿐이며, 실제 scan stitching이 바뀌면 숫자도 달라진다. observation 파일은 exact RTL instance나 physical coordinate를 복원하지 않는다. 실제 FF가 clean `MC_out[i]`와 cycle/function equivalent하다는 별도 분석이 완료되면 이 slot을 `T={t}`로 변환한다. 그렇지 않으면 후보 function hypothesis별로 `f_t(P,K)`를 정의하여 동일한 key consistency 식에 넣는다.

### 3.3 Phase A 실험 결과와 의미

현재 구현한 `anonymous_subround_multiround_attack_Leakage_Channel_Discovery`의 campaign은 다음과 같다.

| 항목 | 결과 |
|---|---:|
| positive trial | 32 |
| negative decoy-only trial | 8 |
| trial당 anonymous scan FF | 256 |
| coarse query | 65 (`P0 + 16*4`) |
| capture schedule | 3 (`mc_capture`, `round_register_update`, `post_update`) |
| positive PASS | 32/32 |
| top-1 recall | 32/32 |
| top-5 recall | 32/32 |
| top-10 recall | 32/32 |
| held-out signature 재현 | 32/32 |
| decoy-only false positive | 0/8 |
| focused implementation tests | 6/6 |

세부 trial JSON, anonymous observation, negative control 및 판정 로그는 [MC Leakage-Channel Discovery Report](../anonymous_subround_multiround_attack_Leakage_Channel_Discovery/reports/MC_LEAKAGE_CHANNEL_DISCOVERY_REPORT.md)에 기록되어 있다.

이 결과가 말하는 것은 다음으로 한정된다.

```text
현재 synthetic anonymous scan wrapper와
무잡음 bit observation, 고정 random stitching,
명시적인 capture schedule 모델 안에서는
MC target이 있는 경우 MC-like pre-ARK candidate를 top-k에 포함시키고,
MC target이 없는 decoy-only 경우는 선택하지 않는 절차가 재현되었다.
```

이는 기존 semantic surface sweep과 다른 종류의 결과다. 기존 sweep은 `MC_out[i]` 같은 위치를 이미 알고 그 위치 조합의 key identifiability를 검사했다. 새 실험은 위치를 모르는 anonymous scan vector에서 `MC capture 직후 + pre-round + MC column-like support`라는 관측 특징으로 후속 sparse tap의 후보를 찾는다. 따라서 두 결과의 관계는 다음과 같다.

```text
semantic surface sweep:
  알려진 semantic bit 조합 -> key recovery 가능성 map

anonymous channel discovery:
  알려지지 않은 scan slot -> MC-like sparse tap 후보 map

통합:
  anonymous scan slot 후보 -> function/cycle mapping 확인
  -> 기존 semantic/Boolean leakage 모델로 변환
  -> 1차/2차 full-key solver 판정
```

현재 결과는 `MC FF가 실제 synthesized/retimed netlist에 존재한다`는 물리적 사실을 증명하지 않는다. 또한 random stitching을 trial 안에서 고정했기 때문에 같은 trial의 query 사이에서 slot identity가 유지되는 것은 channel discovery의 입력 조건에 포함된 안정성이다. 실제 회로에 대한 주장으로 확장하려면 다음이 추가되어야 한다.

- RTL/netlist의 실제 FF D-input cone과 저장 cycle 확인
- MC capture와 round-register update를 clock-level로 분리
- retiming/fusion 후 `f_q(P,K)`의 semantic/function equivalence 확인
- scan compression, X value, observation noise, multi-cycle update 검증
- query 사이에서 scan slot이 실제로 안정적인지 확인
- 선택된 slot을 후속 key-recovery observation으로 연결하고, 최종 `SAT -> UNSAT` 검증

즉 이번 Phase A의 판정은 `MC leakage channel 후보 발견 PASS/FAIL`이지 `K0 탈취 PASS`가 아니다. key 탈취 판정은 반드시 아래 Phase C 이후에 별도로 내려야 한다.

### 3.4 Phase A에서 Phase B로: 동일 anonymous slot의 identity-preserving handoff

Phase 0에서 발견한 channel을 Phase 1의 fixed tap으로 사용하려면, 단순히
`closest_mc_column`이 같다는 것만으로는 충분하지 않다. 두 phase가 서로 다른
scan stitching 또는 서로 다른 MC FF를 사용하면 semantic column이 같아도
anonymous scan slot의 physical identity가 달라질 수 있다. 따라서 두 phase를
독립적인 trial로 실행하지 않고, 하나의 고정된 underlying trial 안에서 다음
조건을 유지한다.

```text
고정된 synthetic AES trial
  = 동일 key
  + 동일 scan FF 집합
  + 동일 random scan permutation
  + 동일 MC target source

Phase 0:
  anonymous full scan-out -> s0 선택

Phase 1:
  T = {s0}를 그대로 재사용
  -> round 1 / round 2 observation 생성
```

이 handoff에서 공격자에게 전달되는 값은 `s0`, capture schedule, 관측
signature, MC column 후보, Boolean-function hypothesis 집합이다. key, 실제
source label, scan permutation, 정확한 MC bit index는 공격자 경로에 전달하지
않고 평가 경로에서만 사용한다. Oracle 공격 모델에서는 Phase 0 결과를 Phase 1
설정에 반영하는 이런 중간 개입을 허용한다.

#### 3.4.1 Phase 0 값의 직접 재사용

Phase 0 observation의 raw scan vector에서 선택 slot `s0`의 값을 읽어
`Y_0(P)`를 만든다.

```math
Y_0(P) = X_{s0}(P, mc_capture) XOR X_{s0}(P0, mc_capture)
```

Phase 1의 round-1 입력은 새로 semantic bit를 재계산한 값이 아니라, 이
`Y_0(P)`를 그대로 사용한다.

```math
Y_{Phase1,r=1}(P) := Y_0(P)
```

따라서 공통 plaintext에 대해 다음을 직접 검사한다.

```math
Y_{Phase1,r=1}(P) = Y_0(P)
```

Phase 1 round-2는 같은 `s0`가 다음 AES round의 MC capture에서 내는 값으로
추가한다. round가 다르므로 round-2의 bit 값이 round-1과 같을 필요는 없다.
필수 조건은 값의 동일성이 아니라 다음 두 가지다.

```text
round-1과 round-2가 동일 scan slot s0를 사용
round index만 달라지고 source/scan identity는 변경되지 않음
```

#### 3.4.2 연결 PASS/FAIL 조건

이 단계는 key가 unique한지를 판정하지 않는다. 다음 조건만 판정한다.

| 조건 | 의미 |
|---|---|
| `s_phase0 == s_phase1` | Phase 0에서 선택한 anonymous slot이 Phase 1에 그대로 전달됨 |
| 공통 query의 `Y_phase0 == Y_phase1,r1` | Phase 0 raw observation이 Phase 1 round-1 입력으로 재사용됨 |
| round-2도 동일 `s0` 사용 | temporal extension이 다른 FF를 새로 선택하지 않음 |
| 평가용 source가 동일 MC FF | slot identity가 실제 MC source에 연결됨 |
| true MC hypothesis가 후보 집합에 포함 | Phase 1 Boolean-function hypothesis가 sound하게 보존됨 |
| negative trial은 `s0`를 만들지 않음 | decoy가 Phase 1 tap으로 잘못 승격되지 않음 |

하나라도 실패하면 Phase 0 discovery 자체와 별개로 `Phase 0 -> Phase 1
handoff FAIL`이다. 반대로 모든 조건이 PASS하면 `동일 anonymous MC channel을
Phase 1 fixed tap으로 전달할 수 있음`을 증명한다. 이것은 key recovery PASS가
아니다.

#### 3.4.3 경량 paired bridge 실험

위 조건을 검사하기 위해 다음 실험을 실행했다.

```text
script:
  anonymous_subround_multiround_attack_Leakage_Channel_Discovery/
  scripts/paired_phase0_phase1_bridge.py

input:
  기존 Phase 0 discovery trial의 anonymous vector와 observation

conditions:
  same trial, same key, same scan stitching, same MC source
  Phase 0 mc_capture signature를 Phase 1 round 1에 직접 재사용
  동일 s0에서 round 2 signature 추가
  ground truth는 source identity 평가에만 사용
  Z3 full-key solve와 adaptive key recovery는 수행하지 않음
```

결과는 다음과 같다.

| 항목 | 결과 |
|---|---:|
| positive trial | 32 |
| positive handoff PASS | 32/32 |
| Phase 0 selected slot = Phase 1 reused slot | 32/32 |
| 공통 query signature 일치 | 32/32, 각 65/65 |
| round-2 동일 slot 유지 | 32/32 |
| 평가용 동일 MC source/round-1 확인 | 32/32 |
| 평가용 true MC hypothesis 보존 | 32/32 |
| negative decoy-only trial | 8 |
| negative handoff PASS | 8/8 |
| decoy에서 잘못된 handoff | 0/8 |

세부 산출물은
[phase0_phase1_slot_handoff.json](../anonymous_subround_multiround_attack_Leakage_Channel_Discovery/results/phase0_phase1_slot_handoff.json)이다.

이 결과의 의미는 명확히 제한된다.

```text
Phase 0에서 선택된 anonymous slot s0가
동일 trial의 Phase 1 round-1 입력으로 직접 재사용되고,
같은 slot의 round-2 temporal observation으로 확장될 수 있음이 확인됨
```

반면 다음은 이 실험의 결과가 아니다.

```text
key가 unique하게 복구됨
정확한 physical coordinate가 복원됨
모든 synthesized/retimed AES에서 slot identity가 보장됨
```

실제 netlist에서는 동일한 실험을 scan stitching이 고정된 gate-level
시뮬레이션 또는 실측 scan capture에 대해 반복해야 한다. 특히 retiming으로
round별 register가 달라지는 구조라면 `s0`가 동일 physical FF인지, 아니면
동일 semantic tap class를 나타내는지 별도로 명시해야 한다.

### 3.5 Phase B: 발견된 channel을 key solver 입력으로 변환

channel discovery가 반환한 `s*`를 바로 semantic index로 치환하지 않는다. 변환에는 세 수준이 있다.

#### 수준 1: clean semantic equivalence가 확인된 경우

실제 FF `q_s`가 선택 cycle에서 `MC_out[i]`와 동일한 값을 저장한다는 것이 D-input cone 또는 RTL correspondence로 확인되면 다음처럼 고정한다.

```text
s* -> (round r, stage MC, semantic bit i)
T = {t_MC(r,i)}
```

이때 기존 semantic surface 실험의 `L_T^d(P,P0;K)`와 동일한 모델을 사용할 수 있다.

#### 수준 2: MC-derived function만 확인된 경우

FF 값이 clean `MC_out[i]`가 아니라 예를 들어 partial XOR, byte-level Boolean function, retimed equivalent node인 경우에는 다음과 같이 함수 가설을 유지한다.

```math
v_{t_s}(P,K) = f_s(P,K)
```

후속 solver constraint는 `MC_out[i]`를 넣는 대신 `f_s`를 넣는다. `f_s`가 여러 개면 각 hypothesis `h`에 대해 별도 branch를 만들고, hypothesis와 key를 동시에 검증한다.

```math
C_Q(K,h) = AND_{P in Q}
  [L_{f_h}^d(P,P0;K) = Y(P)]
```

물리 mapping이 불확실한 상태에서 여러 semantic bit를 임의로 OR하거나 평균내면 안 된다. 그 경우 solver가 찾은 key는 실제 FF의 관측을 설명하는 key인지 알 수 없기 때문이다.

#### 수준 3: 단지 AES-dependent slot인 경우

AES activity만 있고 MC timing/support가 부족하면 `AES-dependent candidate`일 뿐이다. 이 slot을 MC leakage channel로 고정하여 key recovery를 시작하지 않는다. 추가 schedule, support, held-out query, D-input cone 분석으로 candidate class를 먼저 올려야 한다.

### 3.6 Phase C 이후 기존 key-recovery 절차

Phase B가 끝나면 실제 key solver가 읽는 것은 전체 scan vector가 아니라 선택된 sparse observation뿐이다.

```text
매 query P
  -> chosen plaintext와 capture schedule 적용
  -> scan-out vector에서 s* 한 bit 추출
  -> 기준 P0와 XOR
  -> round 1/2 temporal leakage tuple 생성
  -> Y(P) 기록
  -> C_Q(K) 갱신
```

그 다음은 아래 절들의 fixed-query `Solve 1/2`, pair-adaptive separator, dependency-support ranking, global separability 검사를 그대로 수행한다. channel discovery는 key solver를 대체하지 않으며, key solver가 사용할 수 있는 `T`와 leakage function을 찾아주는 전처리/식별 단계다.

## 4. Key Consistency Constraint

초기 chosen-plaintext 집합을 `Q0 = {P0, P1, ..., Pn}`라고 하자. Oracle로 얻은 transcript를 `Y(P)`라 하면, 후보 key `K`의 일관성 제약은 다음이다.

```math
C_Q(K) = AND over P in Q [L_T^d(P, P0; K) = Y(P)]
```

`C_Q(K)`는 AES round function, key schedule, 선택된 FF/tap 함수, 관측 mode, depth를 모두 포함하는 bit-vector/Boolean 제약이다. implementation에서는 Z3가 AES graph의 symbolic key bytes와 S-box 제약을 풀어 이를 만족하는 key를 찾는다.

중요한 점은 `C_Q`가 개별 byte key recovery가 아니라 **128-bit master key 전체의 제약**이라는 것이다. `K != K*`는 16개 key byte 중 하나라도 다른 전체-key 부등식이다.

## 5. 1차 탈취: Fixed-Query Full-Key Uniqueness Test

초기 transcript `Q0`에 대해 다음 두 solve를 순서대로 수행한다.

```text
Solve 1: C_Q0(K)
Solve 2: C_Q0(K) AND K != K_hat
```

`K_hat`은 Solve 1의 model이다. 판정은 아래와 같다.

| Solve 1 | Solve 2 | 판정 | 의미 |
|---|---|---|---|
| SAT | UNSAT | `fixed_query_unique` | `K_hat = K0`만 가능. 1차 탈취 성공 |
| SAT | SAT | `finite_query_ambiguity` | 현재 Q0에서 alternative key가 존재 |
| UNKNOWN 또는 timeout | 임의 | `solver_unresolved` | 성공도 ambiguity도 아님 |
| UNSAT | - | transcript/model error | true key가 제약을 만족하지 않거나 모델 불일치 |

`SAT -> SAT`는 공격 실패 확정이 아니다. 이는 현재 plaintext 집합이 부족할 수 있다는 신호이며, 2차 adaptive 탈취의 입력이다.

## 6. 2차 탈취: Pair-Adaptive Query Separation

### 6.1 기본 반복

현재 query 집합을 `Qi`라고 하자. `C_Qi(K)`가 `SAT -> SAT`이면 다음 두 concrete model을 얻는다.

```text
Ka: Solve 1의 후보 key
Kb: Solve 2의 alternative key
```

두 key를 구별하는 plaintext `Psep`는 다음 조건을 만족해야 한다.

```math
L_T^d(Psep, P0; Ka) != L_T^d(Psep, P0; Kb)
```

추가 조건은 다음과 같다.

- `Psep`는 `Qi`에 이미 있는 plaintext가 아니다.
- chosen-plaintext domain 제약을 만족한다.
  - 예: unrestricted nonzero difference, bounded active byte 수, one-byte differential.
- separator synthesis와 key uniqueness solve는 timeout 없이 수행하거나, UNKNOWN을 terminal success/failure로 바꾸지 않는다.

`Psep`가 SAT이면 공격자는 Oracle에 `Psep`를 질의하고, 실제 leakage `Y(Psep)`를 받는다. 그 뒤 제약을 갱신한다.

```math
Q(i+1) = Qi union {Psep}
C_Q(i+1)(K) = C_Qi(K) AND [L_T^d(Psep, P0; K) = Y(Psep)]
```

그 다음 반드시 **전체 key space**에 대해 다시 Solve 1과 Solve 2를 수행한다. 새 alternative key가 있으면 이전 `Kb`를 고집하지 않고, 새 `Ka/Kb`로 다시 separator를 합성한다.

```text
repeat:
    solve C_Qi(K)
    solve C_Qi(K) AND K != Ka

    if SAT -> UNSAT:
        full key recovered
    if not SAT -> SAT:
        unresolved/error handling

    synthesize Psep for current Ka, Kb
    query Oracle at Psep
    append observed constraint
```

이 절차가 late 1-bit MC/ARK ambiguity를 복구할 때 사용한 핵심 알고리즘이다. fixed Q0에서 남았던 두 key가 어떤 plaintext에서는 다른 leakage를 낸다면, adaptive query가 그 차이를 실제 Oracle constraint로 바꿔 후보 공간을 줄인다.

### 6.2 Pair separator를 먼저 쓰는 이유

처음에는 current `Ka/Kb`라는 concrete key 두 개만 고정한다. 그 결과 separator miter는 symbolic key 두 세트를 동시에 푸는 global miter보다 작고 빠르다.

```math
exists P: L_T^d(P, P0; Ka) != L_T^d(P, P0; Kb)
```

pair separator가 SAT이면 이 plaintext를 즉시 사용한다. pair separator가 SAT인 상황에서 매 단계 global separator를 미리 합성하지 않는다. global search는 계산량이 크고, current pair를 제거하는 데 필요하지 않기 때문이다.

## 7. Global Separability: 비탈취의 엄격한 종료 조건

current pair가 어떤 plaintext에서도 분리되지 않아 pair separator가 UNSAT일 수 있다. 하지만 다른 candidate pair는 분리 가능할 수 있으므로, 이 시점에서 바로 비탈취라고 하면 안 된다.

global separability miter는 다음을 푼다.

```math
exists K1, K2, P:
    C_Qi(K1) AND C_Qi(K2)
    AND K1 != K2
    AND L_T^d(P, P0; K1) != L_T^d(P, P0; K2)
```

여기서 `P`는 기존 query가 아니고 허용된 plaintext domain에 속한다.

| Pair separator | Global separator | 판정 | 다음 행동 |
|---|---|---|---|
| SAT | - | current pair 분리 가능 | 해당 P를 Oracle에 질의하고 반복 |
| UNSAT | SAT | 다른 후보 pair는 분리 가능 | global P를 Oracle에 질의하고 반복 |
| UNSAT | UNSAT | `proven_observational_non_recovery` | 비탈취 확정 |
| UNKNOWN | 임의 | unresolved | 성공/비탈취 주장 금지 |

global separator의 UNSAT은 다음 범위 안에서 강한 의미를 갖는다.

```text
고정 tap T
고정 depth d
고정 leakage mode
현재까지 얻은 Oracle transcript
허용한 chosen-plaintext domain
정확한 AES/FF Boolean model
```

이 범위에서는 현재 남아 있는 서로 다른 두 key를 구별할 새 plaintext가 존재하지 않는다. 따라서 query를 무한히 임의로 늘려도 관측 제약은 singleton이 되지 않는다. 이 결론은 “AES 전체에서 key가 불가능하다”는 뜻이 아니라, 현재 sparse FF 관측 모델에서의 observational non-recovery를 뜻한다.

## 8. Dependency-Support Guided Separator Selection

pair separator가 하나 이상 SAT일 때, 모든 separator가 같은 효율을 갖지는 않는다. 현재 후보 `Ka/Kb`가 다른 key bit 집합을 다음처럼 둔다.

```math
D(Ka, Kb) = {j in [0,127] : Ka[j] != Kb[j]}
```

후보 plaintext `P`와 key bit `j`에 대해 functional support activity를 concrete AES evaluator로 계산한다.

```math
A(P, j, K) = 1
  if L_T^d(P, P0; K) != L_T^d(P, P0; K with bit j flipped)
  else 0
```

`Ka`와 `Kb` 양쪽에서 이 test를 수행해, `P`가 현재 alternative difference의 어떤 key bit들을 실제 leakage에 반영하는지 얻는다.

```text
active_bits(P) = {j in D(Ka,Kb) | A(P,j,Ka)=1 or A(P,j,Kb)=1}
```

여러 pair separator 후보 `P1, ..., Ps`가 있을 때 다음 순서로 ranking한다.

1. 이전 adaptive query에서 아직 활성화하지 않은 differing key bit 수가 큰 후보
2. 전체 active differing key bit 수가 큰 후보
3. `Ka`와 `Kb` 한쪽에만 과도하게 치우치지 않은 후보
4. 동일 점수일 때 deterministic plaintext ordering

이 과정은 **support-guided query selection heuristic**이다. support score가 높다는 사실만으로 key recovery를 선언하지 않는다. 실제 Oracle leakage를 추가하고, 매 단계 Solve 1/2를 다시 수행해야 한다.

### 8.1 Soundness와 효율의 분리

| 구성 요소 | 역할 | 최종 판정에 필요한가 |
|---|---|---|
| Pair separator | current `Ka/Kb`를 빠르게 제거할 query 생성 | 예, adaptive 진행에 사용 |
| Dependency support ranking | 여러 pair separator 중 정보성이 높은 후보 선택 | 아니오, 효율 최적화 |
| Solve 2 `C_Q AND K != K_hat` | full-key uniqueness 증명 | 예 |
| Global separability UNSAT | 더 이상의 query로도 분리 불가함 증명 | 예, 비탈취 확정 시 |

support analysis는 tap의 semantic 위치만 보는 거리 heuristic이 아니다. 현재 alternative key difference와 선택된 FF의 실제 temporal leakage signature를 함께 사용한다. physical internal FF를 다룰 때도 semantic stage label이 아니라 그 FF의 실제 `f_q(P,K)`에 대해 같은 flip-and-observe support 계산을 적용할 수 있다.

## 9. 전체 알고리즘 의사코드

이 의사코드는 Phase A channel discovery와 Phase B mapping 검증이 끝나서, 후속 key solver에 입력할 고정 sparse tap `T`가 준비된 뒤 실행된다. 전체 통합 실행에서는 §3의 Phase A를 먼저 수행하고, 후보가 없거나 function/cycle mapping을 확인할 수 없으면 이 의사코드의 solver 단계로 넘어가지 않는다.

```text
Phase A anonymous scan analysis
  -> stable pre-ARK MC-like slot s* 선택
  -> clean semantic bit 또는 exact FF function으로 mapping
  -> T = {s*}와 Q0/Y 생성
  -> 아래 fixed-query 및 adaptive key-recovery loop 실행
```

```text
Input:
    fixed sparse tap/FF set T
    base plaintext P0
    initial chosen-plaintext set Q0
    depth d, leakage mode, allowed plaintext domain Dp
    exact Oracle O_T,d(P) = L_T^d(P, P0; K0)

Q <- Q0
Y <- Oracle observations for all P in Q

loop forever:
    construct C_Q(K) from AES model, T, d, and Y

    Ka <- solve C_Q(K)
    if Ka is UNKNOWN: return SOLVER_UNRESOLVED
    if Ka is UNSAT: return MODEL_OR_TRANSCRIPT_ERROR

    Kb <- solve C_Q(K) AND (K != Ka)
    if Kb is UNSAT: return FULL_KEY_RECOVERED(Ka)
    if Kb is UNKNOWN: return SOLVER_UNRESOLVED

    candidates <- synthesize one or more P in Dp such that
                  L_T^d(P,P0;Ka) != L_T^d(P,P0;Kb)

    if candidates contains SAT plaintext:
        Psep <- select by dependency-support ranking
    else if candidate-pair result is UNSAT:
        Psep <- solve global separability miter over K1,K2,P
        if global result is UNSAT:
            return PROVEN_OBSERVATIONAL_NON_RECOVERY
        if global result is UNKNOWN:
            return SOLVER_UNRESOLVED
    else:
        return SOLVER_UNRESOLVED

    ysep <- O_T,d(Psep)
    Q <- Q union {Psep}
    Y <- Y union {ysep}
    checkpoint Q, Y, Ka, Kb, Psep, solver verdicts
```

## 10. 구현 및 기록 원칙

- AES model, S-box encoding, key schedule, tap ordering, depth, leakage mode, plaintext domain을 모든 solve에서 고정한다.
- 기존 fixed-query ambiguity를 2차 입력으로 사용할 때도 Q0/tap/seed를 재생성하고 `SAT -> SAT`를 다시 확인한다. 재현 실패를 adaptive 성공으로 세지 않는다.
- 각 accepted separator 직후 checkpoint를 원자적으로 기록한다. 재시작 시 같은 Q와 동일한 Oracle transcript를 복원한다.
- 각 step에 `Ka`, `Kb`, pair/global separator SAT/UNSAT/UNKNOWN, selected plaintext, support score, query count, final Solve 1/2 결과를 남긴다.
- full-key recovery는 항상 마지막 `SAT -> UNSAT`로만 보고한다. 특정 byte가 고정되었거나 first solve model이 true key와 같아 보인다는 사실만으로는 성공이 아니다.

## 11. 적용 범위

이 알고리즘은 fixed sparse scan-visible FF set에 대한 **oracle-model key recovery procedure**이다. clean semantic subround register model에서는 `SB_out[i]`, `SR_out[i]`, `MC_out[i]`, `ARK_out[i]`에 적용할 수 있다. 실제 synthesized/retimed AES에 적용할 때는 각 physical FF가 어느 semantic bit 또는 어느 Boolean function을 저장하는지 먼저 map해야 한다.

따라서 논리적 순서는 다음이다.

```text
physical FF identification
    -> cycle/Boolean-function mapping
    -> fixed sparse tap set T definition
    -> fixed-query uniqueness test
    -> pair-adaptive recovery
    -> global non-recovery proof or full-key uniqueness proof
```

이 순서를 지키면 semantic reference map 결과와 physical FF leakage 분석을 혼동하지 않고, 같은 엄격한 solver 판정 기준으로 탈취 가능성과 한계를 함께 기록할 수 있다.


## 12. MC9 EDA End-to-End Representative Validation

앞의 알고리즘이 실제 scan-inserted 구현에서도 연결되는지 검증하기 위해,
semantic campaign에서 fixed ambiguity 후 adaptive recovery가 확인된
`late1_MC_9__seed2` 한 케이스를 Synopsys 합성/DFT netlist로 재현했다.
상세 결과는 [MC9 EDA End-to-End Report](../extra_exp/MC9_EDA_END_TO_END_REPORT.md)에,
기계 판정 결과는 [final_summary.json](../extra_exp/results/final_summary.json)에 있다.

### 12.1 실험 경계

이것은 arbitrary AES에서 MC FF가 자연스럽게 scan-visible이 되는 빈도를
측정하는 실험이 아니다. `MC_REG[9]`를 실제 sequential boundary로 구현하고
256-cell partial scan set에 포함시켜, 공격자가 익명 scan-out만 받는 조건에서
기존 solver stream이 gate-level DUT까지 조합되는지를 검증한 controlled
representative case다. 공격 경로에는 secret K0, scan stitching map,
RTL/DFT instance name, physical position, MC bit index, evaluator target probe를
제공하지 않았다.

### 12.2 Phase 0 channel discovery

공격-side 입력은 P0와 16 byte position x `{01,02,04,08}`의 65개 query,
각 query의 anonymous 256-bit scan vector, 세 capture schedule이었다.
keyless Python signature analysis 결과는 다음과 같다.

| metric | result |
|---|---:|
| total scan FF | 256 |
| AES-dependent candidates | 101 |
| pre-round candidates | 55 |
| MC-aware overlap >= 3 | 1 |
| selected serialized slot | 255 |
| first-active schedule | MC capture, schedule 1 |
| source-byte support | `{0,5,10,15}` = `C0` |
| exact four-byte support | true |
| repeat stability | schedule 1/2/3 모두 true |

`results/phase_b/phase0_discovery.json`은 evaluator target 열을 소비하지
않았음을 명시한다. evaluator-only `target_mapping.json`을 사후에 열면
DFT path cell 0이 serialized scan-out index 255인 `MC_REG[9]`임을 확인할
수 있지만, 이 mapping은 discovery 입력이 아니다.

### 12.3 Phase 0 -> Phase 1 연결

Phase 1은 새 위치를 재선정하지 않고 Phase 0의 `s*=255`를 동일 post-scan
netlist에서 round 1과 round 2에 그대로 사용했다. Q128의 129개 observation에
대해 anonymous slot transcript와 semantic reference for the surviving `h09` hypothesis를 비교한 결과는:

```text
bitwise_match = true
mismatch_count = 0
query_count = 129
```

따라서 이 단계는 단순히 같은 MC column을 추정한 것이 아니라, Phase 0에서
발견한 anonymous slot의 실제 값이 Phase 1의 round-1/round-2 solver 입력으로
직접 재사용됨을 gate-level simulation으로 확인한 것이다.

### 12.4 fixed 및 반복 adaptive 판정

```text
Q128:
  Solve 1 = SAT
  Solve 2 = SAT
  -> ambiguity

Q129:
  첫 pair separator를 실제 DUT에 질의
  Solve 1 = SAT
  Solve 2 = SAT
  -> 새 alternative가 남음

Q130:
  Q129의 실제 alternative로 새 separator 합성
  실제 DUT에 재질의
  Solve 1 = SAT
  Solve 2 = UNSAT
  -> full-key unique
```

Q128의 first model은 hidden `K0`와 일치했지만, 이것만으로 성공 처리하지
않았다. Q129의 second solve가 SAT였기 때문에 adaptive loop를 계속했고,
Q130에서만 `SAT -> UNSAT`를 full-key recovery로 인정했다.
최종 solver는 16개 key byte가 모두 fixed이고 `UNKNOWN`/timeout이 없었다.

이 결과는 pair separator 하나가 전역 uniqueness를 자동 보장한다는 뜻이
아니다. separator는 현재 후보 pair를 줄이는 query이고, 매 query 뒤에 새
alternative를 다시 찾아 다음 separator를 합성해야 한다. 이 반복성이
실제 gate-level transcript에서 Q129 ambiguity와 Q130 uniqueness로 확인됐다.

### 12.5 EDA 결과의 적용 범위

이 representative validation은 다음 연결을 입증한다.

```text
anonymous scan-out
 -> MC-aware slot discovery
 -> same physical slot temporal handoff
 -> semantic/Boolean leakage observation
 -> fixed SAT/SAT ambiguity
 -> actual gate-level adaptive re-query
 -> repeated alternative elimination
 -> final SAT/UNSAT key proof
```

반면 arbitrary synthesis/retiming 구조의 prevalence, physical placement,
scan compression/noise, production DFT closure까지 주장하지 않는다. 실제
physical FF를 논문에 일반화할 때는 여전히 해당 FF의 D-input cone, 저장 cycle,
Boolean-function equivalence를 별도로 확인해야 한다.


### 12.6 Plan-completion evidence

MC9 EDA representative validation의 부속 control도 별도로 완료했다.

```text
Phase 2A historical separator:
  Psep = f4000000004800d86000586000cb0010
  measured differential = (0,1)
  complete solve = SAT -> UNSAT

Held-out Phase 0 plaintext:
  P = 00112233445566778899aabbccddeeff
  slot 255 semantic checks = 3/3 match

Information-flow audit:
  status = PASS
  violations = 0
```

관련 산출물은
`extra_exp/results/phase_b/q129_phase2a_known_separator_solver.json`,
`extra_exp/results/phase_b/phase0_heldout_check.json`,
`extra_exp/results/evaluator/information_flow_audit.json`이다.

Verdi evidence는 Phase 0 timing, Phase 1 round-1/round-2 slot identity,
Phase 2 separator, 256-shift scan identity의 네 FSDB와 marker/session/PNG
bundle로 보존했다. 세부 경로와 SHA-256은
`extra_exp/results/evidence_manifest.json` 및
`extra_exp/MC9_EDA_END_TO_END_REPORT.md`에 기록되어 있다.

### 12.7 Anonymous Phase 0.5 function attribution and complete EDA handoff

기존 MC9 EDA 결과에는 Phase 0에서 선택한 slot을 후속 solver의 `MC_9`
semantic function으로 해석하는 evaluator bridge가 있었다. 추가 실험은 이
interface를 보완하기 위해 `MC_9` label을 attack path에 넣지 않고, Phase 0의
anonymous output으로부터 함수 가설을 직접 좁힌 뒤 adaptive recovery를
끝까지 재실행했다.

#### 12.7.1 현실적인 DUT 구성

대표 DUT는 one-round toy model이 아닌 10-round iterative AES-128 core다.
실제 sequential boundary를 다음과 같이 두었다.

```text
STATE_REG
  -> SubBytes -> ShiftRows -> MixColumns
  -> MC_REG[127:0]
  -> AddRoundKey -> STATE_REG
```

`MC_REG`는 round 1--9에서 재사용되는 post-MixColumns/pre-ARK register다.
`MC_REG[9]`를 256-cell partial scan set에 포함시키고, 나머지 scan cell은
state/round-register/control/data decoy로 구성했다. Synopsys DC/DFT가 만든
postscan netlist를 VCS로 실행했으며, 공격자는 chosen plaintext와 anonymous
full scan-out만 받았다.

공격 path에는 다음을 넣지 않았다.

```text
hidden K0
scan stitching map
RTL/DFT instance name
physical scan position
MC_9/MC9 semantic label
```

target MC FF를 scan set에 포함한 것은 자연 노출률을 측정하려는 것이 아니라,
scan-visible MC sequential boundary라는 공격 조건을 gate-level DUT에
명시적으로 instantiation한 것이다.

#### 12.7.2 Phase 0와 Phase 0.5

Phase 0은 `P0 + 16 byte positions x {01,02,04,08}`의 65개 query에서
schedule 1/2/3의 anonymous 256-bit scan vector를 수집했다. Python signature
analysis는 MC timing, AES activity, repeat stability, ShiftRows-aligned
support를 사용해 다음을 선택했다.

```text
selected serialized slot = 255
first-active schedule    = MC capture
source support           = C0 = {0,5,10,15}
MC-aware candidate count = 1
```

C0 안의 32개 MC output-bit hypothesis `h00`--`h31`를 만들고 Q128 gate-level
transcript와 consistency를 검사한 결과는 다음과 같다.

```text
initial hypotheses = 32
UNSAT branches     = 31
survivor           = h09
UNKNOWN/timeout    = 0/0
```

이 과정의 attack-side transcript에는 MC9 label, hidden key, mapping, target
hierarchy가 없다. evaluator는 사후에만 `h09 == MC_REG[9]`와 slot mapping을
확인한다.

#### 12.7.3 Q128부터 Q131까지의 key recovery

Phase 0에서 선택한 동일 physical slot을 round 1/round 2에 재사용하고,
각 query를 P0 대비 differential observation으로 변환했다. 각 단계에서
solver는 다음을 수행했다.

```text
Solve 1: C_Q(K) -> candidate K_hat
Solve 2: C_Q(K) AND K != K_hat -> alternative-key check
```

anonymous hypothesis path의 결과는 다음과 같다.

| transcript | observation count | Solve 1 | Solve 2 | 판정 |
|---|---:|---|---|---|
| Q128 fixed | 129 | SAT | SAT | ambiguity |
| Q129 adaptive | 130 | SAT | SAT | ambiguity |
| Q130 adaptive | 130 | SAT | SAT | ambiguity |
| Q131 final adaptive | 131 | SAT | UNSAT | full-key unique |

Q129/Q130/Q131의 separator는 각 직전 solver model pair를 Z3로 분리하도록
합성하고, 실제 VCS DUT에 다시 질의했다. 새 scan observation을 누적한 뒤
모든 surviving hypothesis에 대해 alternative key exclusion을 수행했다.
Q131의 최종 결과는:

```text
surviving hypothesis = h09
first model          = a66f651322597191ab9f8f8af4c2db61
alternative model    = none
classification       = full_key_unique
UNKNOWN/timeout      = 0/0
```

첫 model이 hidden K0와 일치한다는 것만으로 성공 처리하지 않았다. 최종
second solve가 `UNSAT`이고 모든 surviving hypothesis에서 다른 key가 없다는
조건으로만 full-key recovery를 인정했다.

#### 12.7.4 EDA validation의 의미와 한계

이번 결과는 다음의 실제 DUT 연결을 입증한다.

```text
RTL MC sequential boundary
  -> synthesis
  -> DFT scan insertion with decoy FFs
  -> anonymous full scan-out
  -> MC-aware slot discovery
  -> anonymous MC-function attribution
  -> same slot at round 1/round 2
  -> gate-level differential transcript
  -> adaptive Z3 separator synthesis
  -> actual DUT re-query
  -> final SAT -> UNSAT
```

따라서 이 representative condition에서는 **scan-visible 1-bit MC
sequential boundary만으로 anonymous channel discovery부터 master-key
full-key uniqueness까지 연결되는 것**을 EDA 수준에서 검증했다고 주장할 수
있다.

다만 이것은 임의의 AES에서 MC FF가 자연스럽게 scan에 들어갈 확률, 모든
retiming/pipeline 구조, physical placement/routing, scan compression/noise,
production DFT closure를 보장하는 실험은 아니다. 다른 physical FF에 적용할
때는 해당 FF의 D-input cone, 저장 cycle, Boolean-function equivalence를
별도로 확인해야 한다.

주요 산출물:

```text
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
