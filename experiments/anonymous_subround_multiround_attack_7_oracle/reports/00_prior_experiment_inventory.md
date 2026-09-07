# Inventory of Prior Experiments (Attack 5 & 6)

This report details the findings and parameters from `anonymous_subround_multiround_attack_5_oracle` and `anonymous_subround_multiround_attack_6_oracle`.

## 1. Parameters & Terminology

### 1.1 Leakage Stage Naming
The AES subround outputs are named as follows:
* **`SB`**: SubBytes output.
* **`SR`**: ShiftRows output.
* **`MC`**: MixColumns output (absent in Round 10).
* **`ARK`**: AddRoundKey output (Round output).

### 1.2 Bit Index Convention
The 128-bit state uses a column-major ordering of bytes `0..15`, where:
* `byte_index = row + 4 * column`
* `bit_index = byte_index * 8 + bit_in_byte` (where `bit_in_byte` 0 is the LSB).

Example mappings:
* `bit_index = 0` $\rightarrow$ `(byte_index=0, row=0, col=0, bit_in_byte=0)`
* `bit_index = 1` $\rightarrow$ `(byte_index=0, row=0, col=0, bit_in_byte=1)`
* `bit_index = 8` $\rightarrow$ `(byte_index=1, row=1, col=0, bit_in_byte=0)`
* `bit_index = 32` $\rightarrow$ `(byte_index=4, row=0, col=1, bit_in_byte=0)`
* `bit_index = 41` $\rightarrow$ `(byte_index=5, row=1, col=1, bit_in_byte=1)` (since $5 \times 8 + 1 = 41$)

### 1.3 Temporal Depth Definition
* **`depth = 1`**: Observe physical taps only during Round 1.
* **`depth = 2`**: Observe physical taps across Round 1 and Round 2.
* **`depth = 3` / `depth = 4`**: Observe taps across 3/4 rounds. Historically, Z3 timeouts rise exponentially at depth $\ge 3$ due to repeated S-box uninterpreted functions.

### 1.4 Query Count Definition
The chosen differential query sets are defined using one byte of non-zero chosen difference compared to an all-zero base plaintext.
* **`q32`, `q64`, `q96`, `q128`, `q192`, `q255`**: Number of query plaintexts.
* These form a nested structure since they are generated deterministically starting from a fixed seed. E.g., `q32` is a subset of `q64`, which is a subset of `q128`.

### 1.5 Differential Mode Definition
* Observation for query plaintext $P_i$ is $V(P_i)$.
* Observation for base plaintext $P_0$ is $V(P_0)$.
* Differential value: $D(P_i) = V(P_i) \oplus V(P_0)$.
* Under AddRoundKey (ARK) stage leakage, since $V(P_i) = \text{state} \oplus \text{RoundKey}$ and $V(P_0) = \text{base_state} \oplus \text{RoundKey}$, the differential value $D(P_i) = \text{state} \oplus \text{base_state}$ completely cancels out the RoundKey.

### 1.6 Solver Success Criteria
* **`first_result`**: Satisfiability of constraints $C(K)$. Must return `sat`.
* **`second_result`**: Satisfiability of constraints $C(K) \land K \neq K^*$.
  * If `unsat`: Full-key recovery successful (`full_key_unique`).
  * If `sat`: Alternative key exists (`ambiguity`).
  * If `unknown`: Solver timeout (`undecided`).

### 1.7 Seed Processing
* Seeds `0..19` are used to generate keys (via SHA-256 of `"oracle-key-{seed}"`) and plaintexts (deterministic Random with seed-dependent PRNG).

---

## 2. Key Results from Phase 5 & 6

### 2.1 Confirmed Unique Cases (2bit)
* `mc_same_byte_2` `[0,1]` under `depth=2`, `q128`, `differential` $\rightarrow$ 20/20 unique.
* `mc_same_byte_farbit_2` `[0,7]` $\rightarrow$ 20/20 unique.
* `mc_distinct_diag_2` $\rightarrow$ 20/20 unique.
* `ark_same_byte_2` $\rightarrow$ 20/20 unique.
* `ark_distinct_row0_2` $\rightarrow$ 20/20 unique.
* `ark_distinct_diag_2` $\rightarrow$ 20/20 unique.
* `mc0_ark1_same_byte_like` $\rightarrow$ 20/20 unique.
* `mc0_ark32_distinct_row` $\rightarrow$ 20/20 unique.
* `mc0_ark41_distinct_diag` $\rightarrow$ 20/20 unique.

### 2.2 Ambiguity Cases (2bit)
* `sb_same_byte_2` $\rightarrow$ 0/20 unique, 20/20 ambiguity.
* `sr_same_byte_2` $\rightarrow$ 0/20 unique, 20/20 ambiguity.
* `sb_distinct_row0_2`, `sb_distinct_diag_2`, `sr_distinct_row0_2`, `sr_distinct_diag_2` $\rightarrow$ 0/20 unique (ambiguity).
* `mc0_ark0_same_bit` $\rightarrow$ 10/20 unique, 9/20 ambiguity, 1/20 unknown (information redundancy makes it weak).
* `mc_same_col_diagbit_2` $\rightarrow$ 15/20 unique, 5/20 ambiguity.
* `ark_same_col_diagbit_2` $\rightarrow$ 15/20 unique, 5/20 ambiguity.

### 2.3 UNKNOWN / Timeout Cases (2bit)
* depth $\ge 3$ sweeps for most placements produced high UNKNOWN rates due to Z3 solver timeout.
* At depth 2: `mc_distinct_row0_2` (19/20 unique, 1 UNKNOWN), `mc_random_pair_seeded` (19/20 unique, 1 UNKNOWN).

---

## 3. Core Files to Reuse/Modify in Phase 7

We will import the following files from Attack 6:
* `aes_ref.py`: AES-128 concrete reference.
* `z3_aes.py`: Z3 symbolic execution graph of AES.
* `oracle.py`: Concrete observation generator.
* `solve_known_mapping.py`: Solver wrapper and diagnostics.
* `local_candidates.py`: SMT round-1 byte pruner.

We will modify or wrap them inside our scripts folder for clean execution and coordinate mapping.
