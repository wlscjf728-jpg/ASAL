# Late 1-Bit Dependency-Guided Adaptive Campaign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, validate, and detach a 32-position by 3-seed campaign that tests exact AES-128 `K0` recovery from one fixed late 1-bit FF using a `q64` bootstrap and dependency-guided adaptive plaintexts.

**Architecture:** Preserve the inherited AES reference model, oracle, and `SAT -> UNSAT` uniqueness solver. Add a focused 1-bit attack module that enumerates a bounded pool of transcript-consistent keys, generates exact pairwise/global distinguishing plaintexts, ranks them using candidate partitioning and concrete Boolean influence, and loops without a query cutoff until exact recovery or global non-separability is proved. A separate resumable scheduler owns the 96-run/32-worker execution and atomic artifacts.

**Tech Stack:** Python 3, Z3Py, PyYAML, pytest, `concurrent.futures.ProcessPoolExecutor`, Bash, `setsid`.

## Global Constraints

- One run observes exactly one immutable 1-bit tap over rounds 1 and 2.
- Mode is `differential`; depth is `2`; the reference plaintext is query ID `0`.
- Positions are exactly the 16 MC and 16 ARK candidates approved in `reports/LATE_1BIT_ADAPTIVE_CAMPAIGN_DESIGN.md`.
- Run seeds are exactly `0`, `1`, and `2`; total runs are `96`; live workers never exceed `32`.
- Start with deterministic fixed `q64`; report bootstrap recovery separately from adaptive recovery.
- No query-count cutoff and no solver-time cutoff may produce attack failure.
- Only first SAT followed by second UNSAT is key recovery.
- Only global two-key separator UNSAT is observational non-recovery.
- SAT-to-SAT is an intermediate ambiguity; UNKNOWN is nonterminal.
- Candidate-pool and dependency scores select queries but never determine the verdict.
- Keep the old Phase 8 campaigns and their artifacts unchanged.

---

## File Structure

- Create `configs/late_1bit_positions.csv`: exact balanced 32-position manifest.
- Create `configs/late_1bit_adaptive.yaml`: fixed campaign, solver, pool, scoring, and path parameters.
- Create `scripts/late1bit_scoring.py`: concrete leakage signatures, unresolved-bit influence, partition metrics, deterministic ranking.
- Create `scripts/late1bit_attack.py`: exact candidate enumeration, separator portfolio, proof loop, checkpoint state.
- Create `scripts/run_late1bit_campaign.py`: manifest validation, 96-task construction, 32-worker scheduling, atomic final summaries.
- Create `tests/test_late1bit_manifest.py`: position balance, support, equivalence, and task-count tests.
- Create `tests/test_late1bit_scoring.py`: exact leakage and deterministic scoring tests.
- Create `tests/test_late1bit_attack.py`: bootstrap labels, adaptive loop, global proof, UNKNOWN, and resume tests.
- Create `tests/test_late1bit_scheduler.py`: worker bound, completed-run filtering, and artifact tests.
- Create `run_late1bit_campaign.sh`: foreground command with exact interpreter and paths.
- Create `start_late1bit_campaign.sh`: guarded detached `setsid` launcher.
- Create `reports/LATE_1BIT_ADAPTIVE_RUNBOOK.md`: monitoring and interpretation commands.

Do not expand `scripts/adaptive_query_attack.py` or `scripts/run_phase8_campaign.py`; they already combine older finite-budget concerns. Reuse their stable primitives where sound, but keep this campaign isolated.

---

### Task 1: Lock the 32-Tap Manifest and Campaign Configuration

**Files:**
- Create: `anonymous_subround_multiround_attack_8_oracle/configs/late_1bit_positions.csv`
- Create: `anonymous_subround_multiround_attack_8_oracle/configs/late_1bit_adaptive.yaml`
- Create: `anonymous_subround_multiround_attack_8_oracle/tests/test_late1bit_manifest.py`

**Interfaces:**
- Consumes: `experiment_common.load_candidate_map()`, `dependency_support.profile_candidates()`.
- Produces: manifest rows with `case_id,candidate_id,stage,bit_index,byte_index,bit_in_byte`; configuration sections `campaign`, `attack`, `solver`, `candidate_pool`, `query_generation`, and `paths`.

- [ ] **Step 1: Write the failing manifest tests**

```python
from __future__ import annotations

import csv
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from dependency_support import profile_candidates
from experiment_common import load_candidate_map


def rows():
    with (ROOT / "configs/late_1bit_positions.csv").open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_manifest_is_balanced_and_nonredundant():
    manifest = rows()
    assert len(manifest) == 32
    assert len({row["case_id"] for row in manifest}) == 32
    assert len({row["candidate_id"] for row in manifest}) == 32
    assert sum(row["stage"] == "MC" for row in manifest) == 16
    assert sum(row["stage"] == "ARK" for row in manifest) == 16
    for stage in ("MC", "ARK"):
        selected = [row for row in manifest if row["stage"] == stage]
        assert {int(row["byte_index"]) for row in selected} == set(range(16))
        assert sorted(int(row["bit_in_byte"]) for row in selected) == sorted(range(8)) * 2
    mc = {int(row["bit_index"]) for row in manifest if row["stage"] == "MC"}
    ark = {int(row["bit_index"]) for row in manifest if row["stage"] == "ARK"}
    assert mc.isdisjoint(ark)


def test_manifest_matches_candidate_map_and_full_round2_support():
    manifest = rows()
    candidate_map = load_candidate_map()
    ids = {row["candidate_id"] for row in manifest}
    assert ids <= candidate_map.keys()
    profiles = profile_candidates(ids, depth=2)
    round2 = [row for row in profiles if row["round"] == 2]
    assert len(round2) == 32
    assert all(row["structural_k0_bit_count"] == 128 for row in round2)


def test_config_fixes_threat_model_and_resources():
    config = yaml.safe_load((ROOT / "configs/late_1bit_adaptive.yaml").read_text())
    assert config["campaign"] == {"workers": 32, "seeds": [0, 1, 2]}
    assert config["attack"]["depth"] == 2
    assert config["attack"]["mode"] == "differential"
    assert config["attack"]["initial_query_count"] == 64
    assert config["attack"]["max_adaptive_queries"] is None
    assert config["solver"]["first_timeout_ms"] == 0
    assert config["solver"]["second_timeout_ms"] == 0
    assert config["solver"]["separability_timeout_ms"] == 0
```

- [ ] **Step 2: Run the tests and verify the files are missing**

Run: `cd anonymous_subround_multiround_attack_8_oracle && ../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_late1bit_manifest.py -q`

Expected: FAIL because the manifest and YAML do not exist.

- [ ] **Step 3: Create the exact manifest**

Use this header and rows:

```csv
case_id,candidate_id,stage,bit_index,byte_index,bit_in_byte
late1_MC_0,MC_0,MC,0,0,0
late1_MC_9,MC_9,MC,9,1,1
late1_MC_18,MC_18,MC,18,2,2
late1_MC_27,MC_27,MC,27,3,3
late1_MC_36,MC_36,MC,36,4,4
late1_MC_45,MC_45,MC,45,5,5
late1_MC_54,MC_54,MC,54,6,6
late1_MC_63,MC_63,MC,63,7,7
late1_MC_64,MC_64,MC,64,8,0
late1_MC_73,MC_73,MC,73,9,1
late1_MC_82,MC_82,MC,82,10,2
late1_MC_91,MC_91,MC,91,11,3
late1_MC_100,MC_100,MC,100,12,4
late1_MC_109,MC_109,MC,109,13,5
late1_MC_118,MC_118,MC,118,14,6
late1_MC_127,MC_127,MC,127,15,7
late1_ARK_4,ARK_4,ARK,4,0,4
late1_ARK_13,ARK_13,ARK,13,1,5
late1_ARK_22,ARK_22,ARK,22,2,6
late1_ARK_31,ARK_31,ARK,31,3,7
late1_ARK_32,ARK_32,ARK,32,4,0
late1_ARK_41,ARK_41,ARK,41,5,1
late1_ARK_50,ARK_50,ARK,50,6,2
late1_ARK_59,ARK_59,ARK,59,7,3
late1_ARK_68,ARK_68,ARK,68,8,4
late1_ARK_77,ARK_77,ARK,77,9,5
late1_ARK_86,ARK_86,ARK,86,10,6
late1_ARK_95,ARK_95,ARK,95,11,7
late1_ARK_96,ARK_96,ARK,96,12,0
late1_ARK_105,ARK_105,ARK,105,13,1
late1_ARK_114,ARK_114,ARK,114,14,2
late1_ARK_123,ARK_123,ARK,123,15,3
```

- [ ] **Step 4: Create the fixed configuration**

```yaml
campaign:
  workers: 32
  seeds: [0, 1, 2]
attack:
  depth: 2
  mode: differential
  initial_query_count: 64
  max_adaptive_queries: null
solver:
  first_timeout_ms: 0
  second_timeout_ms: 0
  diagnostic_timeout_ms: 1
  separability_timeout_ms: 0
  sbox_encoding: uf_axiom
candidate_pool:
  size: 16
query_generation:
  pair_count: 12
  models_per_pair: 4
  query_domain: unrestricted
  max_active_bytes: 16
paths:
  manifest: configs/late_1bit_positions.csv
  checkpoint_dir: results/late_1bit_checkpoints
  result_dir: results/late_1bit_runs
  summary: results/late_1bit_summary.jsonl
  errors: logs/late_1bit_errors.jsonl
```

- [ ] **Step 5: Run the manifest tests**

Run: `cd anonymous_subround_multiround_attack_8_oracle && ../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_late1bit_manifest.py -q`

Expected: `3 passed`.

- [ ] **Step 6: Commit**

```bash
git add anonymous_subround_multiround_attack_8_oracle/configs/late_1bit_positions.csv anonymous_subround_multiround_attack_8_oracle/configs/late_1bit_adaptive.yaml anonymous_subround_multiround_attack_8_oracle/tests/test_late1bit_manifest.py
git commit -m "test: lock late one-bit campaign sample"
```

---

### Task 2: Implement Concrete Leakage and Dependency Scoring

**Files:**
- Create: `anonymous_subround_multiround_attack_8_oracle/scripts/late1bit_scoring.py`
- Create: `anonymous_subround_multiround_attack_8_oracle/tests/test_late1bit_scoring.py`

**Interfaces:**
- Consumes: `aes_ref.encrypt_with_trace()` and one tap dictionary.
- Produces: `leakage_signature()`, `unresolved_key_bits()`, `influence_profile()`, `score_plaintext()`, and `rank_plaintexts()`.

- [ ] **Step 1: Write failing unit tests**

```python
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from late1bit_scoring import (
    leakage_signature,
    rank_plaintexts,
    score_plaintext,
    unresolved_key_bits,
)

TAP = {"tap_id": "t0", "stage": "MC", "bit_index": 0}


def test_signature_has_one_bit_per_round_and_zero_at_reference():
    key = bytes(range(16))
    reference = bytes(16)
    assert leakage_signature(key, TAP, reference, reference, 2) == (0, 0)
    assert len(leakage_signature(key, TAP, bytes.fromhex("01" + "00" * 15), reference, 2)) == 2


def test_unresolved_bits_follow_little_endian_bit_indexing():
    keys = [bytes(16), bytes([1]) + bytes(15), bytes([0, 128]) + bytes(14)]
    assert unresolved_key_bits(keys) == {0, 15}


def test_partition_gain_dominates_influence_and_ties_are_deterministic():
    keys = [bytes([value]) + bytes(15) for value in range(4)]
    reference = bytes(16)
    points = [bytes.fromhex("01" + "00" * 15), bytes.fromhex("02" + "00" * 15)]
    ranked = rank_plaintexts(points, keys, TAP, reference, depth=2, prior_active_bits=set())
    assert ranked == sorted(ranked, key=lambda item: item["rank_key"], reverse=True)
    assert {item["plaintext_hex"] for item in ranked} == {point.hex() for point in points}
    for item in ranked:
        assert set(item) >= {"partition_gain", "entropy", "active_bits", "novel_bits", "rank_key"}
```

- [ ] **Step 2: Run the tests and verify the module is missing**

Run: `cd anonymous_subround_multiround_attack_8_oracle && ../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_late1bit_scoring.py -q`

Expected: FAIL with `ModuleNotFoundError: late1bit_scoring`.

- [ ] **Step 3: Implement exact concrete helpers**

Implement these functions directly; `encrypt_with_trace()` uses the same state and bit indexing as the oracle:

```python
from collections import Counter
from math import log2
from aes_ref import encrypt_with_trace

def _absolute_bit(key, tap, plaintext, round_index):
    trace = encrypt_with_trace(plaintext, key)["rounds"]
    value = trace[round_index][str(tap["stage"])][int(tap["bit_index"]) // 8]
    return (value >> (int(tap["bit_index"]) % 8)) & 1

def leakage_signature(key, tap, plaintext, reference, depth):
    return tuple(
        _absolute_bit(key, tap, plaintext, r) ^ _absolute_bit(key, tap, reference, r)
        for r in range(1, depth + 1)
    )

def unresolved_key_bits(keys):
    return {bit for bit in range(128) if len({(key[bit // 8] >> (bit % 8)) & 1 for key in keys}) > 1}

def influence_profile(plaintext, keys, tap, reference, depth, unresolved_bits):
    profile = {}
    for bit in sorted(unresolved_bits):
        count = 0
        for key in keys:
            mutated = bytearray(key)
            mutated[bit // 8] ^= 1 << (bit % 8)
            count += leakage_signature(key, tap, plaintext, reference, depth) != leakage_signature(bytes(mutated), tap, plaintext, reference, depth)
        profile[bit] = count
    return profile

def score_plaintext(plaintext, keys, tap, reference, depth, prior_active_bits):
    signatures = [leakage_signature(key, tap, plaintext, reference, depth) for key in keys]
    buckets = Counter(signatures)
    entropy = -sum((count / len(keys)) * log2(count / len(keys)) for count in buckets.values())
    influence = influence_profile(plaintext, keys, tap, reference, depth, unresolved_key_bits(keys))
    active_bits = {bit for bit, count in influence.items() if count}
    values = list(influence.values())
    rank_key = (len(keys) - max(buckets.values()), entropy, len(active_bits - prior_active_bits), len(active_bits), -(max(values, default=0) - min(values, default=0)), -int.from_bytes(plaintext, "big"))
    return {"plaintext_hex": plaintext.hex(), "partition_gain": rank_key[0], "entropy": entropy, "active_bits": sorted(active_bits), "novel_bits": sorted(active_bits - prior_active_bits), "influence_counts": {str(bit): count for bit, count in influence.items()}, "rank_key": rank_key}

def rank_plaintexts(points, keys, tap, reference, depth, prior_active_bits):
    return sorted([score_plaintext(p, keys, tap, reference, depth, prior_active_bits) for p in points], key=lambda item: item["rank_key"], reverse=True)
```

Use `trace[round_index][stage][bit_index // 8] >> (bit_index % 8)` exactly as `oracle.py` does. Flip key bit `j` with `mutated[j // 8] ^= 1 << (j % 8)`. Form signature buckets across the pool, set `partition_gain = len(keys) - max(bucket_sizes)`, calculate Shannon entropy, and use this deterministic maximization key:

```python
rank_key = (
    partition_gain,
    entropy,
    len(active_bits - prior_active_bits),
    len(active_bits),
    -(max(influence.values(), default=0) - min(influence.values(), default=0)),
    -int.from_bytes(plaintext, "big"),
)
```

Return JSON-safe score fields; keep `rank_key` as a tuple only during in-process ranking.

- [ ] **Step 4: Run scoring tests**

Run: `cd anonymous_subround_multiround_attack_8_oracle && ../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_late1bit_scoring.py -q`

Expected: `3 passed`.

- [ ] **Step 5: Commit**

```bash
git add anonymous_subround_multiround_attack_8_oracle/scripts/late1bit_scoring.py anonymous_subround_multiround_attack_8_oracle/tests/test_late1bit_scoring.py
git commit -m "feat: score adaptive queries by residual influence"
```

---

### Task 3: Implement Candidate-Pool Enumeration and Separator Portfolio

**Files:**
- Create: `anonymous_subround_multiround_attack_8_oracle/scripts/late1bit_attack.py`
- Create: `anonymous_subround_multiround_attack_8_oracle/tests/test_late1bit_attack.py`

**Interfaces:**
- Consumes: `solve_known_mapping.build_problem()`, `adaptive_query_attack.synthesize_distinguishing_query()`, `AESGraphBuilder`, and Task 2 scoring functions.
- Produces: `CandidatePool`, `enumerate_candidate_keys()`, `generate_separator_candidates()`, `choose_adaptive_query()`.

- [ ] **Step 1: Write failing pool and query-selection tests**

```python
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import late1bit_attack as attack


def test_choose_query_uses_best_scored_separator(monkeypatch):
    p1, p2 = bytes.fromhex("01" + "00" * 15), bytes.fromhex("02" + "00" * 15)
    monkeypatch.setattr(attack, "generate_separator_candidates", lambda *args, **kwargs: [p1, p2])
    monkeypatch.setattr(
        attack,
        "rank_plaintexts",
        lambda points, *args, **kwargs: [
            {"plaintext_hex": p2.hex(), "rank_key": (2,)},
            {"plaintext_hex": p1.hex(), "rank_key": (1,)},
        ],
    )
    selected = attack.choose_adaptive_query({}, [bytes(16), bytes([1]) + bytes(15)], {}, {}, set())
    assert selected["plaintext_hex"] == p2.hex()


def test_pairwise_exhaustion_requires_global_miter(monkeypatch):
    monkeypatch.setattr(attack, "generate_separator_candidates", lambda *args, **kwargs: [])
    monkeypatch.setattr(attack, "global_separator", lambda *args, **kwargs: {"status": "unsat"})
    result = attack.choose_adaptive_query({}, [bytes(16), bytes([1]) + bytes(15)], {}, {}, set())
    assert result == {"status": "proven_nonseparable", "global_status": "unsat"}


def test_unknown_is_nonterminal(monkeypatch):
    monkeypatch.setattr(attack, "generate_separator_candidates", lambda *args, **kwargs: [])
    monkeypatch.setattr(attack, "global_separator", lambda *args, **kwargs: {"status": "unknown"})
    result = attack.choose_adaptive_query({}, [bytes(16), bytes([1]) + bytes(15)], {}, {}, set())
    assert result["status"] == "unresolved"
```

- [ ] **Step 2: Run tests and verify failure**

Run: `cd anonymous_subround_multiround_attack_8_oracle && ../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_late1bit_attack.py -q`

Expected: FAIL because `late1bit_attack` does not exist.

- [ ] **Step 3: Implement bounded exact candidate enumeration**

Define:

```python
@dataclass(frozen=True)
class CandidatePool:
    keys: tuple[bytes, ...]
    exhausted: bool
    status: str
    elapsed: float
    reason_unknown: str = ""

def enumerate_candidate_keys(
    doc: dict,
    *,
    limit: int,
    sbox_encoding: str,
    timeout_ms: int | None,
) -> CandidatePool:
    key, builder, by_round = build_problem(doc, sbox_encoding)
    solver = z3.Solver()
    solver.set(timeout=0 if timeout_ms is None else timeout_ms)
    solver.add(*builder.sbox_constraints)
    for round_index in sorted(by_round):
        solver.add(*by_round[round_index])
    models = []
    started = time.perf_counter()
    while len(models) < limit:
        status = solver.check()
        if status == z3.unsat:
            return CandidatePool(tuple(models), True, "unsat", time.perf_counter() - started)
        if status == z3.unknown:
            return CandidatePool(tuple(models), False, "unknown", time.perf_counter() - started, solver.reason_unknown())
        model = solver.model()
        candidate = bytes(model.eval(value, model_completion=True).as_long() for value in key)
        models.append(candidate)
        solver.add(z3.Or(*[value != z3.BitVecVal(candidate[index], 8) for index, value in enumerate(key)]))
    return CandidatePool(tuple(models), False, "limit", time.perf_counter() - started)
```

Build one transcript solver with `build_problem()`. After each SAT model, append the concrete key and add `Or(key[i] != model_byte[i])`. Stop at `limit`; mark `exhausted=True` only when the next exact check is UNSAT. Preserve UNKNOWN and its reason. Never infer uniqueness from `len(keys) == 1` unless `exhausted=True`.

- [ ] **Step 4: Implement diverse pair and plaintext generation**

Define `select_diverse_pairs(keys, pair_count)` by sorting all key pairs by descending key Hamming distance and greedily covering new XOR-difference bit sets, with bytewise lexical order as tie-breaker. Implement `generate_separator_candidates()` with a concrete-key Z3 miter matching `synthesize_for_candidate_pair()`, but enumerate `models_per_pair` distinct plaintext models by adding a 128-bit plaintext blocking clause after each SAT model.

Every returned plaintext must:

- satisfy `query_domain=unrestricted` and differ from the reference;
- differ from all transcript plaintexts;
- distinguish the concrete pair under the exact two-round one-tap signature;
- be deduplicated across pairs.

- [ ] **Step 5: Implement global fallback and scoring selection**

Reuse `synthesize_distinguishing_query()` as `global_separator()`. `choose_adaptive_query()` must rank pairwise candidates with Task 2. If none exist, call the global miter exactly once:

```python
if global_result["status"] == "unsat":
    return {"status": "proven_nonseparable", "global_status": "unsat"}
if global_result["status"] != "sat":
    return {"status": "unresolved", "global_status": global_result["status"],
            "reason_unknown": global_result.get("reason_unknown", "")}
```

If global SAT, score and return its plaintext. Persist whether selection came from `pair_portfolio` or `global_fallback`.

- [ ] **Step 6: Run attack primitive tests**

Run: `cd anonymous_subround_multiround_attack_8_oracle && ../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_late1bit_attack.py -q`

Expected: all Task 3 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add anonymous_subround_multiround_attack_8_oracle/scripts/late1bit_attack.py anonymous_subround_multiround_attack_8_oracle/tests/test_late1bit_attack.py
git commit -m "feat: add one-bit separator query portfolio"
```

---

### Task 4: Implement the Unlimited Proof Loop and Atomic Resume

**Files:**
- Modify: `anonymous_subround_multiround_attack_8_oracle/scripts/late1bit_attack.py`
- Modify: `anonymous_subround_multiround_attack_8_oracle/tests/test_late1bit_attack.py`

**Interfaces:**
- Consumes: Task 3 query selection, `oracle.generate_observation()`, `adaptive_query_attack.solver_result()`, `experiment_common.nested_plaintexts()`.
- Produces: `run_late1bit_attack(case, seed, config, tap, checkpoint_path) -> dict`.

- [ ] **Step 1: Add failing terminal-classification tests**

```python
TAP = {"tap_id": "t0", "candidate_id": "MC_0", "stage": "MC", "bit_index": 0}

def minimal_config():
    return {"attack": {"depth": 2, "mode": "differential", "initial_query_count": 64}, "solver": {"first_timeout_ms": 0, "second_timeout_ms": 0, "diagnostic_timeout_ms": 1, "separability_timeout_ms": 0, "sbox_encoding": "uf_axiom"}, "candidate_pool": {"size": 4}, "query_generation": {"pair_count": 2, "models_per_pair": 2, "query_domain": "unrestricted", "max_active_bytes": 16}}

def ambiguity_result(*args, **kwargs):
    return {"classification": "ambiguity", "first_result": "sat", "second_result": "sat", "first_model_hex": bytes(16).hex(), "alternative_model": (bytes([1]) + bytes(15)).hex()}

def test_q64_unique_is_not_labeled_adaptive(monkeypatch, tmp_path):
    monkeypatch.setattr(attack, "solve_transcript", lambda *args: {"classification": "full_key_unique", "first_result": "sat", "second_result": "unsat"})
    result = attack.run_late1bit_attack({"case_id": "late1_MC_0", "candidate_id": "MC_0"}, 0, minimal_config(), TAP, tmp_path / "c.json")
    assert result["terminal_classification"] == "fixed_q64_recovered"
    assert result["adaptive_query_count"] == 0


def test_ambiguity_then_unique_is_adaptive_recovery(monkeypatch, tmp_path):
    solves = iter([
        {"classification": "ambiguity", "first_result": "sat", "second_result": "sat"},
        {"classification": "full_key_unique", "first_result": "sat", "second_result": "unsat"},
    ])
    monkeypatch.setattr(attack, "solve_transcript", lambda *args: next(solves))
    monkeypatch.setattr(attack, "enumerate_candidate_keys", lambda *args, **kwargs: attack.CandidatePool((bytes(16), bytes([1]) + bytes(15)), False, "limit", 0.0))
    monkeypatch.setattr(attack, "choose_adaptive_query", lambda *args: {"status": "sat", "plaintext_hex": (bytes([1]) + bytes(15)).hex(), "active_bits": [0]})
    result = attack.run_late1bit_attack({"case_id": "late1_MC_0", "candidate_id": "MC_0"}, 0, minimal_config(), TAP, tmp_path / "c.json")
    assert result["terminal_classification"] == "adaptive_key_recovered"
    assert result["adaptive_query_count"] == 1
    assert result["total_query_count"] == 65


def test_global_unsat_is_only_nonrecovery_verdict(monkeypatch, tmp_path):
    monkeypatch.setattr(attack, "solve_transcript", ambiguity_result)
    monkeypatch.setattr(attack, "enumerate_candidate_keys", lambda *args, **kwargs: attack.CandidatePool((bytes(16), bytes([1]) + bytes(15)), False, "limit", 0.0))
    monkeypatch.setattr(attack, "choose_adaptive_query", lambda *args: {"status": "proven_nonseparable", "global_status": "unsat"})
    result = attack.run_late1bit_attack({"case_id": "late1_MC_0", "candidate_id": "MC_0"}, 0, minimal_config(), TAP, tmp_path / "c.json")
    assert result["terminal_classification"] == "proven_observational_non_recovery"
```

- [ ] **Step 2: Add failing resume and UNKNOWN tests**

Add these concrete tests:

```python
import json
import pytest

def test_resume_keeps_existing_adaptive_plaintexts(monkeypatch, tmp_path):
    checkpoint = tmp_path / "c.json"
    p1 = (bytes([1]) + bytes(15)).hex()
    p2 = (bytes([2]) + bytes(15)).hex()
    checkpoint.write_text(json.dumps({"schema": "late-1bit-checkpoint-v1", "run_id": "late1_MC_0__seed0__late1bit_adaptive", "case_id": "late1_MC_0", "candidate_id": "MC_0", "seed": 0, "tap": TAP, "bootstrap_query_count": 64, "adaptive_plaintexts_hex": [p1, p2], "prior_active_bits": [0], "steps": [], "state": "running"}))
    observed_counts = []
    monkeypatch.setattr(attack, "generate_observation", lambda key, taps, points, depth, mode: observed_counts.append(len(points)) or {})
    monkeypatch.setattr(attack, "solve_transcript", lambda *args, **kwargs: {"classification": "full_key_unique", "first_result": "sat", "second_result": "unsat"})
    result = attack.run_late1bit_attack({"case_id": "late1_MC_0", "candidate_id": "MC_0"}, 0, minimal_config(), TAP, checkpoint)
    assert result["adaptive_query_count"] == 2
    assert observed_counts == [67]

def test_unknown_is_checkpointed_and_not_returned(monkeypatch, tmp_path):
    checkpoint = tmp_path / "c.json"
    monkeypatch.setattr(attack, "solve_transcript", lambda *args, **kwargs: {"classification": "undecided", "first_result": "sat", "second_result": "unknown"})
    with pytest.raises(attack.NonTerminalSolverState):
        attack.run_late1bit_attack({"case_id": "late1_MC_0", "candidate_id": "MC_0"}, 0, minimal_config(), TAP, checkpoint)
    assert json.loads(checkpoint.read_text())["state"] == "solver_unresolved"
```

- [ ] **Step 3: Implement solver wrapper, nonterminal state, and checkpoint schema**

Use these exact control interfaces before the checkpoint code:

```python
class NonTerminalSolverState(RuntimeError):
    pass

def solve_transcript(doc, config):
    return solver_result(doc, config)

def require_exact_classification(result):
    if result["first_result"] == "sat" and result["second_result"] in {"sat", "unsat"}:
        return
    raise NonTerminalSolverState(
        "uniqueness unresolved: {}->{}".format(result["first_result"], result["second_result"])
    )
```

Then implement checkpoint schema and atomic writes.

Use this minimum JSON schema:

```python
{
    "schema": "late-1bit-checkpoint-v1",
    "run_id": run_id,
    "case_id": case["case_id"],
    "candidate_id": case["candidate_id"],
    "seed": seed,
    "tap": tap,
    "bootstrap_query_count": 64,
    "adaptive_plaintexts_hex": [],
    "prior_active_bits": [],
    "steps": [],
    "state": "running",
}
```

Write to `checkpoint.tmp.<pid>` and use `Path.replace()`. Validate run ID, seed, and immutable tap before accepting an existing checkpoint.

- [ ] **Step 4: Implement an unbounded proof loop**

Use `while True`, not a large numeric substitute. Rebuild plaintexts as `nested_plaintexts(64, seed) + checkpoint adaptive plaintexts`, regenerate the exact oracle document, and run the first/second proof at each step.

Terminal mapping:

```python
if unique and adaptive_count == 0:
    terminal = "fixed_q64_recovered"
elif unique:
    terminal = "adaptive_key_recovered"
elif selection["status"] == "proven_nonseparable":
    terminal = "proven_observational_non_recovery"
else:
    append exactly one new oracle plaintext and continue
```

On UNKNOWN, write the diagnostic checkpoint and raise `NonTerminalSolverState`. Do not return `attack_success=False`; no verdict exists.

- [ ] **Step 5: Run proof-loop tests**

Run: `cd anonymous_subround_multiround_attack_8_oracle && ../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_late1bit_attack.py -q`

Expected: all Task 3 and Task 4 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add anonymous_subround_multiround_attack_8_oracle/scripts/late1bit_attack.py anonymous_subround_multiround_attack_8_oracle/tests/test_late1bit_attack.py
git commit -m "feat: add resumable unlimited one-bit proof loop"
```

---

### Task 5: Build the 96-Run, 32-Worker Scheduler

**Files:**
- Create: `anonymous_subround_multiround_attack_8_oracle/scripts/run_late1bit_campaign.py`
- Create: `anonymous_subround_multiround_attack_8_oracle/tests/test_late1bit_scheduler.py`

**Interfaces:**
- Consumes: Task 1 manifest/config and Task 4 `run_late1bit_attack()`.
- Produces: `load_tasks()`, `execute_task()`, CLI `main()`, atomic per-run JSON, rebuilt JSONL summary.

- [ ] **Step 1: Write failing scheduler tests**

```python
def test_load_tasks_builds_96_runs(tmp_path):
    tasks = campaign.load_tasks(load_config(), tmp_path)
    assert len(tasks) == 96
    assert len({task.run_id for task in tasks}) == 96
    assert {task.seed for task in tasks} == {0, 1, 2}
    assert all(len(task.taps) == 1 for task in tasks)


def test_completed_results_are_not_rescheduled(tmp_path):
    tasks = campaign.load_tasks(load_config(), tmp_path)
    first = tasks[0]
    (tmp_path / f"{first.run_id}.json").write_text("{}\n")
    assert len(campaign.load_tasks(load_config(), tmp_path)) == 95


def test_worker_argument_is_capped_at_32():
    assert campaign.effective_workers(96, configured=32, requested=64) == 32
    assert campaign.effective_workers(6, configured=32, requested=32) == 6
```

- [ ] **Step 2: Run tests and verify module is missing**

Run: `cd anonymous_subround_multiround_attack_8_oracle && ../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_late1bit_scheduler.py -q`

Expected: FAIL with missing scheduler module.

- [ ] **Step 3: Implement immutable task loading**

Define a frozen `RunTask` dataclass carrying `run_id`, manifest row, seed, one-tap tuple, config, checkpoint path, and result path. Construct run IDs as:

```text
{case_id}__seed{seed}__late1bit_adaptive
```

Reject any row whose stage/index disagrees with the candidate map. Reject tap count other than one. Skip only a valid terminal result JSON; a checkpoint or error row remains resumable.

- [ ] **Step 4: Implement bounded process scheduling and summary rebuild**

Use spawn context and:

```python
workers = min(len(tasks), requested or config["campaign"]["workers"], 32)
with ProcessPoolExecutor(max_workers=workers, mp_context=get_context("spawn")) as pool:
    futures = {pool.submit(execute_task, task): task.run_id for task in tasks}
    for future in concurrent.futures.as_completed(futures):
        payload = future.result()
        if payload["state"] == "terminal":
            write_atomic(Path(payload["result_path"]), payload)
            rebuild_summary(result_dir, summary_path)
        else:
            append_jsonl(error_path, payload)
```

`execute_task()` must convert `NonTerminalSolverState` to an error/diagnostic artifact, not a scientific result. Write successful terminal payloads atomically. Rebuild `late_1bit_summary.jsonl` from sorted per-run JSON files after every completed future so resume cannot duplicate rows.

- [ ] **Step 5: Add CLI dry-run output**

The dry run must print exactly: manifest cases, seeds, total/pending runs, requested/effective workers, depth, mode, bootstrap query count, and `max_adaptive_queries=unlimited`. It must create no result or checkpoint files.

- [ ] **Step 6: Run scheduler tests**

Run: `cd anonymous_subround_multiround_attack_8_oracle && ../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_late1bit_scheduler.py -q`

Expected: `3 passed` or more.

- [ ] **Step 7: Commit**

```bash
git add anonymous_subround_multiround_attack_8_oracle/scripts/run_late1bit_campaign.py anonymous_subround_multiround_attack_8_oracle/tests/test_late1bit_scheduler.py
git commit -m "feat: schedule 96 late one-bit attack runs"
```

---

### Task 6: Add Detached Launch and Monitoring Runbook

**Files:**
- Create: `anonymous_subround_multiround_attack_8_oracle/run_late1bit_campaign.sh`
- Create: `anonymous_subround_multiround_attack_8_oracle/start_late1bit_campaign.sh`
- Create: `anonymous_subround_multiround_attack_8_oracle/reports/LATE_1BIT_ADAPTIVE_RUNBOOK.md`
- Modify: `anonymous_subround_multiround_attack_8_oracle/tests/test_late1bit_scheduler.py`

**Interfaces:**
- Consumes: Task 5 CLI.
- Produces: detached PID `logs/late_1bit_campaign.pid`, log `logs/late_1bit_campaign.out`, result/checkpoint directories.

- [ ] **Step 1: Add failing launcher-content tests**

```python
def test_launcher_uses_sets_id_and_32_workers():
    start = (ROOT / "start_late1bit_campaign.sh").read_text()
    run = (ROOT / "run_late1bit_campaign.sh").read_text()
    assert "setsid bash ./run_late1bit_campaign.sh" in start
    assert "logs/late_1bit_campaign.pid" in start
    assert "--workers 32" in run
    assert "scripts/run_late1bit_campaign.py" in run
```

- [ ] **Step 2: Run the launcher test and verify files are missing**

Run: `cd anonymous_subround_multiround_attack_8_oracle && ../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_late1bit_scheduler.py::test_launcher_uses_sets_id_and_32_workers -q`

Expected: FAIL with missing launcher.

- [ ] **Step 3: Create foreground and detached launchers**

`run_late1bit_campaign.sh` must use the inherited Phase 7 virtual environment and execute:

```bash
exec "$PYTHON" scripts/run_late1bit_campaign.py \
  --config configs/late_1bit_adaptive.yaml \
  --workers 32
```

`start_late1bit_campaign.sh` must refuse a second live PID, create log/result/checkpoint directories, then run:

```bash
setsid bash ./run_late1bit_campaign.sh > "$LOG_FILE" 2>&1 < /dev/null &
echo "$!" > "$PID_FILE"
```

- [ ] **Step 4: Write the monitoring runbook**

Include exact non-mutating commands for PID liveness, process count, tailing progress, terminal-result counts, checkpoint ages, UNKNOWN/error inspection, and safe resume by rerunning the guarded start script. State that killing workers or deleting checkpoints is not part of ordinary monitoring.

- [ ] **Step 5: Run scheduler and shell syntax tests**

Run: `bash -n anonymous_subround_multiround_attack_8_oracle/run_late1bit_campaign.sh anonymous_subround_multiround_attack_8_oracle/start_late1bit_campaign.sh`

Expected: exit `0`.

Run: `cd anonymous_subround_multiround_attack_8_oracle && ../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_late1bit_scheduler.py -q`

Expected: all tests PASS.

- [ ] **Step 6: Commit**

```bash
git add anonymous_subround_multiround_attack_8_oracle/run_late1bit_campaign.sh anonymous_subround_multiround_attack_8_oracle/start_late1bit_campaign.sh anonymous_subround_multiround_attack_8_oracle/reports/LATE_1BIT_ADAPTIVE_RUNBOOK.md anonymous_subround_multiround_attack_8_oracle/tests/test_late1bit_scheduler.py
git commit -m "chore: add detached late one-bit campaign launcher"
```

---

### Task 7: Verify the Full Campaign and Start It Detached

**Files:**
- Verify: all files created in Tasks 1-6.
- Runtime output: `anonymous_subround_multiround_attack_8_oracle/logs/late_1bit_campaign.out`
- Runtime output: `anonymous_subround_multiround_attack_8_oracle/logs/late_1bit_campaign.pid`
- Runtime output: `anonymous_subround_multiround_attack_8_oracle/results/late_1bit_checkpoints/`
- Runtime output: `anonymous_subround_multiround_attack_8_oracle/results/late_1bit_runs/`

**Interfaces:**
- Consumes: the complete tested campaign.
- Produces: one detached 32-worker campaign and auditable runtime identifiers.

- [ ] **Step 1: Run all Phase 8 tests**

Run: `cd anonymous_subround_multiround_attack_8_oracle && ../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests -q`

Expected: all tests PASS with no skipped late-1bit acceptance test.

- [ ] **Step 2: Run static and shell validation**

Run: `cd anonymous_subround_multiround_attack_8_oracle && ../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 scripts/validate_setup.py`

Expected: exit `0` and inherited setup checks PASS.

Run: `bash -n anonymous_subround_multiround_attack_8_oracle/run_late1bit_campaign.sh anonymous_subround_multiround_attack_8_oracle/start_late1bit_campaign.sh`

Expected: exit `0`.

- [ ] **Step 3: Verify the exact dry-run schedule**

Run: `cd anonymous_subround_multiround_attack_8_oracle && ../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 scripts/run_late1bit_campaign.py --config configs/late_1bit_adaptive.yaml --workers 32 --dry-run`

Expected fields: `cases=32 seeds=3 total=96 pending=96 workers=32 depth=2 mode=differential initial_q=64 max_adaptive_queries=unlimited`. Pending may be lower only when valid terminal results already exist.

- [ ] **Step 4: Start the campaign with `setsid`**

Run: `bash anonymous_subround_multiround_attack_8_oracle/start_late1bit_campaign.sh`

Expected: one line containing `started late 1-bit campaign pid <PID>`.

- [ ] **Step 5: Verify detachment and bounded workers**

Run: `PID=$(cat anonymous_subround_multiround_attack_8_oracle/logs/late_1bit_campaign.pid); kill -0 "$PID"; ps -eo pid,ppid,cmd | rg 'run_late1bit_campaign|late1bit_attack' | sed -n '1,40p'`

Expected: launcher PID is live; no more than 32 run workers plus the scheduler/resource-tracker processes are present.

- [ ] **Step 6: Report launch evidence without claiming results**

Report the PID, effective worker count, 96 total runs, output paths, and any completed terminal rows visible at that moment. Do not claim 1-bit recovery until a per-run `SAT -> UNSAT` artifact exists.

---

## Plan Self-Review Checklist

- Spec coverage: position balance, three seeds, q64 separation, dynamic influence, exact proof outcomes, no query cutoff, checkpoint/resume, 32-worker cap, detached execution, and physical-applicability boundary are each assigned to a task.
- Soundness: sampled candidate pools and scores never replace the second solve or global separator proof.
- Nontermination: UNKNOWN and interrupted workers produce resumable diagnostics, not failure labels.
- Type consistency: tap dictionaries use `tap_id`, `candidate_id`, `stage`, `bit_index`; plaintexts and keys are 16-byte `bytes`; persisted forms are lowercase hex.
- Existing-work safety: no old result, launcher, config, or Phase 7/7_1 file is modified.
