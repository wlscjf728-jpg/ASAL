"""Run lightweight anonymous MC-channel discovery and write an evidence report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import yaml

from discover_mc_channel import analyze_trial
from evaluate_mc_channel import evaluate_result
from export_channel_observation import export_observation
from negative_control import build_decoy_trial
from refine_mc_channel import evaluate_candidate
from scan_channel_generator import build_holdout, build_trial, write_trial


def _write_report(path: Path, rows: list[dict], config: dict) -> None:
    positive = [row for row in rows if row["cohort"] == "positive"]
    negative = [row for row in rows if row["cohort"] == "negative"]
    positives_pass = sum(row["evaluation"]["classification"] == "PASS" for row in positive)
    false_positive = sum(row["evaluation"]["false_positive"] for row in negative)
    top_recall = {f"top_{k}": sum(row["evaluation"]["top_k_recall"][f"top_{k}"] for row in positive) for k in (1, 5, 10)}
    lines = [
        "# MC Leakage-Channel Discovery Report", "",
        "## 실험 목적", "",
        "이 결과는 anonymous scan vector만으로 반복 가능한 pre-ARK MC channel을 선택할 수 있는지 검증한다. 실제 RTL/netlist physical mapping 복원이나 key recovery 성공을 주장하는 결과가 아니다.", "",
        "## 설정", "",
        f"- positive trials: {len(positive)}", f"- negative decoy-only trials: {len(negative)}", f"- scan FF per trial: {config['n_scan_ff']}",
        "- coarse queries: 1 + 16*4 = 65", "- capture schedules: mc_capture, round_register_update, post_update", "- analyzer input: anonymous observations only", "",
        "## 판정 결과", "",
        f"- positive PASS: {positives_pass}/{len(positive)}",
        f"- positive top-1/top-5/top-10 recall: {top_recall['top_1']}/{len(positive)}, {top_recall['top_5']}/{len(positive)}, {top_recall['top_10']}/{len(positive)}",
        f"- negative false-positive count: {false_positive}/{len(negative)}", "",
        "## 해석", "",
        "positive trial에서 PASS가 나오고 negative trial에서 false positive가 없으면, 현재 synthetic scan wrapper와 명시한 scoring 조건이 ground-truth MC source와 decoy를 구분하는 실험 절차로는 타당하다는 뜻이다.", "",
        "반대로 이는 random stitching, trace-level capture, decoy 종류, 무잡음 bit observation이라는 가정 안에서의 타당성이다. 실제 synthesized/retimed AES에서는 scan FF의 D-input cone, capture timing, X/noise, scan compression, multi-cycle behavior를 추가 검증해야 한다.", "",
        "## 세부 결과", "", "```json", json.dumps(rows, indent=2), "```",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="configs/discovery_config.yaml")
    parser.add_argument("--positive", type=int)
    parser.add_argument("--negative", type=int)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    config = yaml.safe_load((root / args.config).read_text())
    positive_count = args.positive if args.positive is not None else int(config["positive_trials"])
    negative_count = args.negative if args.negative is not None else int(config["negative_trials"])
    result_dir = root / config["result_dir"]
    result_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for cohort, count, builder in (("positive", positive_count, build_trial), ("negative", negative_count, build_decoy_trial)):
        for index in range(count):
            seed = int(config["seed_start"]) + index + (10000 if cohort == "negative" else 0)
            anonymous, ground_truth = builder(seed, config)
            discovery = analyze_trial(anonymous, None, top_k=10)
            holdout = build_holdout(seed, config, ground_truth)
            refinement = evaluate_candidate(discovery["selected_slot"], holdout, ground_truth) if discovery["selected_slot"] is not None else None
            evaluation = evaluate_result(discovery, ground_truth, refinement)
            write_trial(result_dir, anonymous, ground_truth)
            if discovery["selected_slot"] is not None:
                export_observation(discovery, anonymous, result_dir / f"{anonymous['trial_id']}.observation.json")
            rows.append({"cohort": cohort, "trial_id": anonymous["trial_id"], "discovery": discovery, "evaluation": evaluation})
    (result_dir / "discovery_results.json").write_text(json.dumps(rows, indent=2) + "\n")
    _write_report(root / config["report"], rows, config)
    print(json.dumps({"positive_trials": positive_count, "negative_trials": negative_count, "positive_pass": sum(row["evaluation"]["classification"] == "PASS" for row in rows if row["cohort"] == "positive"), "negative_false_positive": sum(row["evaluation"]["false_positive"] for row in rows if row["cohort"] == "negative")}, indent=2))


if __name__ == "__main__":
    main()
