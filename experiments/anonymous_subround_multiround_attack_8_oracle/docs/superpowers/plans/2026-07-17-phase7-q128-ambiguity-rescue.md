# Phase 7 Q128 Ambiguity Rescue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the broad Phase 8 campaign and run the ambiguity-reuse attack on the six exact Phase 7 early+late 2-bit seed-runs that remain direct `SAT -> SAT` at q128.

**Architecture:** A fixed CSV manifest identifies the six source rows and their exact seeds. A dedicated six-process campaign reuses the existing AES oracle and sound hybrid adaptive attack, asserts that the reconstructed q128 transcript is ambiguous, and continues with solver-generated plaintexts through q255 using dedicated resumable outputs.

**Tech Stack:** Python 3.10, Z3 4.13.4, PyYAML, pytest 9, Bash, `setsid`, `multiprocessing.ProcessPoolExecutor`.

## Global Constraints

- Work only in `anonymous_subround_multiround_attack_8_oracle`; Phase 8_1 is out of scope.
- Preserve all existing full-campaign logs and results.
- Accept only direct Phase 7 q128 `SAT -> SAT`; exclude UNKNOWN, timeout consensus, and imputed rows.
- Use depth 2 and differential leakage with the original Phase 7 seed and nested q128 plaintext prefix.
- Use exactly six tasks and at most six workers.
- Disable Z3 uniqueness and separability timeouts with `timeout=0`.
- Continue from q128 through at most q255.
- Only second-solve UNSAT is key recovery; UNKNOWN and process errors are never attack verdicts.

---

### Task 1: Fixed Rescue Manifest and Configuration

**Files:**
- Create: `anonymous_subround_multiround_attack_8_oracle/configs/phase7_q128_rescue_cases.csv`
- Create: `anonymous_subround_multiround_attack_8_oracle/configs/phase7_q128_rescue.yaml`
- Create: `anonymous_subround_multiround_attack_8_oracle/tests/test_phase7_q128_rescue.py`

**Interfaces:**
- Consumes: Phase 7 `results/raw_solver_runs_2bit.csv` and the Phase 8 candidate map.
- Produces: six rows with fields `attack8_case_id`, `source_phase`, `source_case_id`, `tap_count`, `cand_a..cand_d`, `seed`, and `source_query_count`; YAML attack configuration with q128 initial transcript and 127 adaptive queries.

- [ ] **Step 1: Write manifest/config validation tests**

```python
from __future__ import annotations

import csv
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
PHASE7 = ROOT.parent / "anonymous_subround_multiround_attack_7_oracle"
sys.path.insert(0, str(ROOT / "scripts"))


EXPECTED = {
    ("SB_10__MC_16", 0),
    ("SB_13__MC_14", 0),
    ("SB_17__ARK_92", 2),
    ("SB_37__MC_78", 2),
    ("SB_5__MC_75", 2),
    ("SR_111__MC_6", 1),
}


def rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def test_manifest_is_exact_six_direct_q128_ambiguities():
    manifest = rows(ROOT / "configs/phase7_q128_rescue_cases.csv")
    assert {(r["source_case_id"], int(r["seed"])) for r in manifest} == EXPECTED
    assert all(int(r["tap_count"]) == 2 for r in manifest)
    assert all(int(r["source_query_count"]) == 128 for r in manifest)

    raw = rows(PHASE7 / "results/raw_solver_runs_2bit.csv")
    source = {(r["case_id"], int(r["seed"]), int(r["query_count"])): r for r in raw}
    for case_id, seed in EXPECTED:
        row = source[(case_id, seed, 128)]
        assert row["first_result"] == "sat"
        assert row["second_result"] == "sat"
        assert row["classification"] == "ambiguity"
        assert row["timeout"] == "False"


def test_config_spans_q128_through_q255_with_six_workers():
    config = yaml.safe_load((ROOT / "configs/phase7_q128_rescue.yaml").read_text())
    assert config["campaign"]["workers"] == 6
    assert config["attack"]["initial_query_count"] == 128
    assert config["adaptive_query"]["max_adaptive_queries"] == 127
    assert 128 + 127 == 255
    assert config["solver"]["first_timeout_ms"] == 0
    assert config["solver"]["second_timeout_ms"] == 0
    assert config["adaptive_query"]["separability_timeout_ms"] == 0
```

- [ ] **Step 2: Run tests and verify missing files fail**

Run:

```bash
../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_phase7_q128_rescue.py -v
```

Expected: two failures because the manifest and YAML files do not exist.

- [ ] **Step 3: Create the exact six-row manifest**

```csv
attack8_case_id,source_phase,source_case_id,tap_count,cand_a,cand_b,cand_c,cand_d,seed,source_query_count
p7_q128_2b_SB_10__MC_16,7,SB_10__MC_16,2,SB_10,MC_16,,,0,128
p7_q128_2b_SB_13__MC_14,7,SB_13__MC_14,2,SB_13,MC_14,,,0,128
p7_q128_2b_SB_17__ARK_92,7,SB_17__ARK_92,2,SB_17,ARK_92,,,2,128
p7_q128_2b_SB_37__MC_78,7,SB_37__MC_78,2,SB_37,MC_78,,,2,128
p7_q128_2b_SB_5__MC_75,7,SB_5__MC_75,2,SB_5,MC_75,,,2,128
p7_q128_2b_SR_111__MC_6,7,SR_111__MC_6,2,SR_111,MC_6,,,1,128
```

- [ ] **Step 4: Create the q128-to-q255 configuration**

```yaml
campaign:
  workers: 6

attack:
  depth: 2
  mode: differential
  initial_query_count: 128

solver:
  first_timeout_ms: 0
  second_timeout_ms: 0
  diagnostic_timeout_ms: 1
  sbox_encoding: uf_axiom

adaptive_query:
  max_adaptive_queries: 127
  separability_timeout_ms: 0
  query_domain: unrestricted
  max_active_bytes: 16
```

- [ ] **Step 5: Run manifest/config tests**

Run:

```bash
../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_phase7_q128_rescue.py -v
```

Expected: `2 passed`.

- [ ] **Step 6: Commit Task 1**

```bash
git add Scan_Secure/experiments/anonymous_subround_multiround_attack_8_oracle/configs/phase7_q128_rescue_cases.csv Scan_Secure/experiments/anonymous_subround_multiround_attack_8_oracle/configs/phase7_q128_rescue.yaml Scan_Secure/experiments/anonymous_subround_multiround_attack_8_oracle/tests/test_phase7_q128_rescue.py
git commit -m "test: define Phase 7 q128 rescue targets"
```

### Task 2: Baseline Guard and Reusable Run Identity

**Files:**
- Modify: `anonymous_subround_multiround_attack_8_oracle/scripts/run_phase8_campaign.py`
- Modify: `anonymous_subround_multiround_attack_8_oracle/tests/test_phase7_q128_rescue.py`

**Interfaces:**
- Consumes: `sound_adaptive_run(case, seed, config, taps)` existing callers.
- Produces: `sound_adaptive_run(case, seed, config, taps, *, run_tag="phase8_full", require_initial_ambiguity=False)` with backward-compatible defaults.

- [ ] **Step 1: Add failing tests for the initial ambiguity guard and run tag**

Append:

```python
import pytest
import run_phase8_campaign as campaign


def minimal_case():
    return {
        "attack8_case_id": "guard_case",
        "source_phase": "7",
        "source_case_id": "SB_10__MC_16",
        "tap_count": "2",
    }


def test_required_initial_ambiguity_rejects_unique_baseline(monkeypatch):
    monkeypatch.setattr(campaign, "key_for_seed", lambda seed: bytes(16))
    monkeypatch.setattr(campaign, "nested_plaintexts", lambda count, seed: [bytes(16)] * (count + 1))
    monkeypatch.setattr(campaign, "generate_observation", lambda *args: {})
    monkeypatch.setattr(campaign, "solver_result", lambda doc, config: {
        "classification": "full_key_unique", "first_result": "sat", "second_result": "unsat",
        "first_time": 0.0, "second_time": 0.0,
    })
    with pytest.raises(RuntimeError, match="initial transcript is not ambiguous"):
        campaign.sound_adaptive_run(
            minimal_case(), 0,
            {"attack": {"initial_query_count": 128, "depth": 2, "mode": "differential"},
             "adaptive_query": {"max_adaptive_queries": 127}},
            [], run_tag="phase7_q128_rescue", require_initial_ambiguity=True,
        )


def test_custom_run_tag_is_recorded(monkeypatch):
    monkeypatch.setattr(campaign, "key_for_seed", lambda seed: bytes(16))
    monkeypatch.setattr(campaign, "nested_plaintexts", lambda count, seed: [bytes(16)] * (count + 1))
    monkeypatch.setattr(campaign, "generate_observation", lambda *args: {})
    monkeypatch.setattr(campaign, "solver_result", lambda doc, config: {
        "classification": "full_key_unique", "first_result": "sat", "second_result": "unsat",
        "first_time": 0.0, "second_time": 0.0,
    })
    result = campaign.sound_adaptive_run(
        minimal_case(), 0,
        {"attack": {"initial_query_count": 128, "depth": 2, "mode": "differential"},
         "adaptive_query": {"max_adaptive_queries": 127}},
        [], run_tag="phase7_q128_rescue",
    )
    assert result["run_id"] == "guard_case__seed0__phase7_q128_rescue"
```

- [ ] **Step 2: Run focused tests and verify failure**

Run:

```bash
../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_phase7_q128_rescue.py -k 'initial_ambiguity or custom_run_tag' -v
```

Expected: failures because the keyword arguments are not accepted.

- [ ] **Step 3: Extend `sound_adaptive_run` without changing existing defaults**

Change the signature to:

```python
def sound_adaptive_run(
    case: dict,
    seed: int,
    config: dict,
    taps: list[dict],
    *,
    run_tag: str = "phase8_full",
    require_initial_ambiguity: bool = False,
) -> dict:
```

Immediately after constructing `record`, add:

```python
        if step == 0 and require_initial_ambiguity and result["classification"] != "ambiguity":
            raise RuntimeError(
                "initial transcript is not ambiguous: "
                f"{result['first_result']}->{result['second_result']}"
            )
```

Change the returned run ID to:

```python
        "run_id": f"{case['attack8_case_id']}__seed{seed}__{run_tag}",
```

- [ ] **Step 4: Run all rescue tests**

Run:

```bash
../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_phase7_q128_rescue.py -v
```

Expected: `4 passed`.

- [ ] **Step 5: Verify the existing full-campaign dry run remains compatible**

Run:

```bash
../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 scripts/run_phase8_campaign.py --dry-run --config configs/full_phase8_campaign.yaml --workers 64
```

Expected: output contains `workers=64` with no exception.

- [ ] **Step 6: Commit Task 2**

```bash
git add Scan_Secure/experiments/anonymous_subround_multiround_attack_8_oracle/scripts/run_phase8_campaign.py Scan_Secure/experiments/anonymous_subround_multiround_attack_8_oracle/tests/test_phase7_q128_rescue.py
git commit -m "feat: guard Phase 8 rescue baseline ambiguity"
```

### Task 3: Dedicated Six-Task Rescue Campaign

**Files:**
- Create: `anonymous_subround_multiround_attack_8_oracle/scripts/run_phase7_q128_rescue.py`
- Modify: `anonymous_subround_multiround_attack_8_oracle/tests/test_phase7_q128_rescue.py`

**Interfaces:**
- Consumes: manifest rows, candidate map, `taps_for_case`, `sound_adaptive_run`, `result_path`, and `write_atomic`.
- Produces: `load_tasks(config, result_dir) -> list[tuple[dict, int, list[dict], dict]]`, `execute_rescue_task(task) -> dict`, `--dry-run`, and resumable per-run JSON output.

- [ ] **Step 1: Add a failing six-task dry-run test**

Append:

```python
import run_phase7_q128_rescue as rescue


def test_rescue_task_builder_plans_exactly_six(tmp_path):
    config = yaml.safe_load((ROOT / "configs/phase7_q128_rescue.yaml").read_text())
    tasks = rescue.load_tasks(config, tmp_path)
    assert len(tasks) == 6
    assert {seed for _, seed, _, _ in tasks} == {0, 1, 2}
    assert all(int(case["source_query_count"]) == 128 for case, _, _, _ in tasks)
```

- [ ] **Step 2: Run the test and verify the module is missing**

Run:

```bash
../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_phase7_q128_rescue.py::test_rescue_task_builder_plans_exactly_six -v
```

Expected: collection error `No module named 'run_phase7_q128_rescue'`.

- [ ] **Step 3: Implement the dedicated runner**

```python
"""Resolve the six direct Phase 7 q128 early+late ambiguity runs."""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import multiprocessing
import time
import traceback
from pathlib import Path

import yaml

from experiment_common import ROOT, load_candidate_map, read_csv, taps_for_case
from run_phase8_campaign import result_path, sound_adaptive_run, write_atomic

MANIFEST = "configs/phase7_q128_rescue_cases.csv"
RUN_TAG = "phase7_q128_rescue"


def load_tasks(config: dict, result_dir: Path) -> list[tuple[dict, int, list[dict], dict]]:
    candidate_map = load_candidate_map()
    tasks = []
    for case in read_csv(ROOT / MANIFEST):
        seed = int(case["seed"])
        run_id = f"{case['attack8_case_id']}__seed{seed}__{RUN_TAG}"
        if not result_path(result_dir, run_id).exists():
            tasks.append((case, seed, taps_for_case(case, candidate_map), config))
    return tasks


def execute_rescue_task(task: tuple[dict, int, list[dict], dict]) -> dict:
    case, seed, taps, config = task
    run_id = f"{case['attack8_case_id']}__seed{seed}__{RUN_TAG}"
    started = time.perf_counter()
    try:
        payload = sound_adaptive_run(
            case,
            seed,
            config,
            taps,
            run_tag=RUN_TAG,
            require_initial_ambiguity=True,
        )
        payload["source_query_count"] = int(case["source_query_count"])
        payload["baseline_verified"] = True
        payload["wall_time"] = time.perf_counter() - started
        return payload
    except BaseException as error:
        return {
            "run_id": run_id,
            "attack8_case_id": case["attack8_case_id"],
            "source_case_id": case["source_case_id"],
            "seed": seed,
            "terminal_classification": "worker_error",
            "error": repr(error),
            "traceback": traceback.format_exc(),
            "wall_time": time.perf_counter() - started,
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/phase7_q128_rescue.yaml")
    parser.add_argument("--result-dir", default="results/phase7_q128_rescue_runs")
    parser.add_argument("--summary", default="results/phase7_q128_rescue_summary.jsonl")
    parser.add_argument("--errors", default="logs/phase7_q128_rescue_errors.jsonl")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = yaml.safe_load((ROOT / args.config).read_text())
    workers = min(args.workers, int(config["campaign"]["workers"]))
    result_dir = ROOT / args.result_dir
    summary = ROOT / args.summary
    errors = ROOT / args.errors
    tasks = load_tasks(config, result_dir)
    print(f"targets=6 workers={workers} pending={len(tasks)} initial_q=128 final_q=255", flush=True)
    if args.dry_run:
        for case, seed, taps, _ in tasks:
            print(case["source_case_id"], seed, [(tap["stage"], tap["bit_index"]) for tap in taps])
        return

    result_dir.mkdir(parents=True, exist_ok=True)
    summary.parent.mkdir(parents=True, exist_ok=True)
    errors.parent.mkdir(parents=True, exist_ok=True)
    context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
        futures = [pool.submit(execute_rescue_task, task) for task in tasks]
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            payload = future.result()
            if payload["terminal_classification"] == "worker_error":
                with errors.open("a") as handle:
                    handle.write(json.dumps(payload, sort_keys=True) + "\n")
            else:
                write_atomic(result_path(result_dir, payload["run_id"]), payload)
                with summary.open("a") as handle:
                    handle.write(json.dumps(payload, sort_keys=True) + "\n")
            print(
                f"[{index}/{len(tasks)}] {payload['run_id']} -> "
                f"{payload['terminal_classification']} q={payload.get('query_count', '-')}",
                flush=True,
            )


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run all tests and compile the runner**

Run:

```bash
../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m pytest tests/test_phase7_q128_rescue.py -v
../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 -m py_compile scripts/run_phase7_q128_rescue.py
```

Expected: `5 passed`, followed by a zero-exit compile with no output.

- [ ] **Step 5: Verify the exact dry-run schedule**

Run:

```bash
../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 scripts/run_phase7_q128_rescue.py --dry-run --workers 6
```

Expected first line: `targets=6 workers=6 pending=6 initial_q=128 final_q=255`, followed by the six source case/seed rows.

- [ ] **Step 6: Commit Task 3**

```bash
git add Scan_Secure/experiments/anonymous_subround_multiround_attack_8_oracle/scripts/run_phase7_q128_rescue.py Scan_Secure/experiments/anonymous_subround_multiround_attack_8_oracle/tests/test_phase7_q128_rescue.py
git commit -m "feat: add six-worker q128 ambiguity rescue runner"
```

### Task 4: Detached Launcher and Campaign Handoff

**Files:**
- Create: `anonymous_subround_multiround_attack_8_oracle/run_phase7_q128_rescue.sh`
- Create: `anonymous_subround_multiround_attack_8_oracle/start_phase7_q128_rescue.sh`

**Interfaces:**
- Consumes: dedicated rescue runner and shared Phase 7 virtual environment.
- Produces: `logs/phase7_q128_rescue.pid`, `logs/phase7_q128_rescue.out`, dedicated result files, and a detached six-worker process group.

- [ ] **Step 1: Create the foreground wrapper**

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PYTHON="$ROOT/../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3"

cd "$ROOT"
exec "$PYTHON" scripts/run_phase7_q128_rescue.py \
  --config configs/phase7_q128_rescue.yaml \
  --workers 6 \
  --result-dir results/phase7_q128_rescue_runs \
  --summary results/phase7_q128_rescue_summary.jsonl \
  --errors logs/phase7_q128_rescue_errors.jsonl
```

- [ ] **Step 2: Create the setsid launcher**

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PID_FILE="$ROOT/logs/phase7_q128_rescue.pid"
LOG_FILE="$ROOT/logs/phase7_q128_rescue.out"

mkdir -p "$ROOT/logs" "$ROOT/results/phase7_q128_rescue_runs"
if [[ -f "$PID_FILE" ]] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
  echo "already running: $(cat "$PID_FILE")"
  exit 0
fi

cd "$ROOT"
setsid bash ./run_phase7_q128_rescue.sh > "$LOG_FILE" 2>&1 < /dev/null &
echo "$!" > "$PID_FILE"
echo "started Phase 7 q128 rescue pid $(cat "$PID_FILE")"
```

- [ ] **Step 3: Validate shell syntax and permissions**

Run:

```bash
chmod +x run_phase7_q128_rescue.sh start_phase7_q128_rescue.sh
bash -n run_phase7_q128_rescue.sh
bash -n start_phase7_q128_rescue.sh
```

Expected: zero exit and no output.

- [ ] **Step 4: Commit Task 4**

```bash
git add Scan_Secure/experiments/anonymous_subround_multiround_attack_8_oracle/run_phase7_q128_rescue.sh Scan_Secure/experiments/anonymous_subround_multiround_attack_8_oracle/start_phase7_q128_rescue.sh
git commit -m "chore: add q128 rescue background launcher"
```

- [ ] **Step 5: Stop the old 64-worker process group without deleting outputs**

Run from the Phase 8 directory:

```bash
PID="$(cat logs/phase8_full.pid)"
PGID="$(ps -o pgid= -p "$PID" | tr -d ' ')"
test "$PID" = "$PGID"
kill -TERM -- "-$PGID"
```

Expected: `test` succeeds before the signal. After the signal, `ps -p "$PID"` and `ps --ppid "$PID"` return no campaign processes. If processes remain after 30 seconds, inspect them before any stronger signal.

- [ ] **Step 6: Start the dedicated rescue campaign**

Run:

```bash
./start_phase7_q128_rescue.sh
```

Expected: `started Phase 7 q128 rescue pid <PID>`.

- [ ] **Step 7: Verify detached execution and six workers**

Run:

```bash
PID="$(cat logs/phase7_q128_rescue.pid)"
ps -p "$PID" -o pid= -o stat= -o etime= -o cmd=
ps --ppid "$PID" -o pid= -o stat= -o cmd=
sed -n '1,20p' logs/phase7_q128_rescue.out
test ! -s logs/phase7_q128_rescue_errors.jsonl
```

Expected: one detached parent, six solver workers plus at most one multiprocessing resource tracker, log header `targets=6 workers=6 pending=6 initial_q=128 final_q=255`, and no errors.

- [ ] **Step 8: Record final operational status**

Report the new PID, six target case/seed pairs, worker count, output paths, and that the former PID no longer exists. Do not claim recovery until a run ends with second-solve UNSAT.

## Self-Review Correction: Pre-Launch Baseline Preflight

Before Task 4 stops the old campaign, extend `run_phase7_q128_rescue.py` with this exact preflight function and CLI branch:

```python
from adaptive_query_attack import solver_result
from experiment_common import key_for_seed, nested_plaintexts
from oracle import generate_observation


def validate_baseline_task(task):
    case, seed, taps, config = task
    doc = generate_observation(
        key_for_seed(seed), taps, nested_plaintexts(128, seed), 2, "differential"
    )
    result = solver_result(doc, config)
    if result["first_result"] != "sat" or result["second_result"] != "sat":
        raise RuntimeError(
            f"baseline mismatch for {case['source_case_id']} seed {seed}: "
            f"{result['first_result']}->{result['second_result']}"
        )
    return case["source_case_id"], seed
```

Add `--validate-baseline`. In that branch, submit all six tasks to a six-worker `ProcessPoolExecutor`, consume every future, print each case/seed as `sat->sat`, and return without writing attack verdict files.

Run before stopping PID `logs/phase8_full.pid`:

```bash
../anonymous_subround_multiround_attack_7_oracle/.venv/bin/python3 scripts/run_phase7_q128_rescue.py --validate-baseline --workers 6
```

Expected: six direct `sat->sat` lines and zero exit. Any mismatch aborts the handoff and leaves the old campaign running.
