from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


FORBIDDEN = (
    "true_key_hex",
    "MC_9",
    "MC9",
    "scan_mapping",
    "response_hiding_secret",
)


def _find_unknown(value: Any, path: str = "") -> list[str]:
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            child_path = f"{path}.{key}" if path else key
            if key in {"status", "first_result", "second_result", "classification"} and str(child).lower() == "unknown":
                found.append(child_path)
            if key == "unknown" and child is True:
                found.append(child_path)
            found.extend(_find_unknown(child, child_path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_find_unknown(child, f"{path}[{index}]"))
    return found


def audit(results_dir: Path) -> dict[str, Any]:
    violations = []
    unknown_paths = []
    scanned = []
    for path in sorted(results_dir.glob("*/*")):
        if path.name == "evaluator_truth.json" or not path.is_file():
            continue
        if path.suffix not in {".json", ".txt"}:
            continue
        text = path.read_text(errors="replace")
        scanned.append(str(path.relative_to(results_dir)))
        for token in FORBIDDEN:
            if token in text:
                violations.append({"file": str(path.relative_to(results_dir)), "token": token})
        if path.suffix == ".json":
            try:
                unknown_paths.extend(
                    f"{path.relative_to(results_dir)}:{item}"
                    for item in _find_unknown(json.loads(text))
                )
            except json.JSONDecodeError:
                violations.append({"file": str(path.relative_to(results_dir)), "token": "invalid_json"})
    return {
        "schema": "python-defense-information-flow-audit-v1",
        "status": "PASS" if not violations and not unknown_paths else "FAIL",
        "files_scanned": scanned,
        "forbidden_token_violations": violations,
        "unknown_status_paths": unknown_paths,
        "evaluator_truth_excluded": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "files_scanned": len(result["files_scanned"])}, indent=2))


if __name__ == "__main__":
    main()

