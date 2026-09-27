"""Run all key-diversity tasks except the separately running smoke task."""
from __future__ import annotations

import argparse
import concurrent.futures
import multiprocessing
from pathlib import Path

from key_diversity_campaign import (
    append_jsonl,
    build_tasks,
    completed_run_ids,
    execute_task,
    load_campaign_config,
    rooted,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=31)
    args = parser.parse_args()
    config = load_campaign_config()
    tasks = build_tasks()
    raw_path = rooted(config["paths"]["raw_results"])
    done = completed_run_ids(raw_path)
    # K01/mc_q0 is the isolated smoke process. It is intentionally excluded here.
    smoke_id = tasks[0]["run_id"]
    pending = [task for task in tasks[1:] if task["run_id"] not in done]
    workers = min(args.workers, 31, len(pending)) if pending else 0
    print(
        f"remainder_total=79 completed={len(done - {smoke_id})} "
        f"pending={len(pending)} workers={workers} smoke_excluded={smoke_id}",
        flush=True,
    )
    if not pending:
        return
    error_path = rooted(config["paths"]["errors"])
    context = multiprocessing.get_context("spawn")
    with concurrent.futures.ProcessPoolExecutor(
        max_workers=workers,
        mp_context=context,
    ) as pool:
        futures = {pool.submit(execute_task, task): task for task in pending}
        for index, future in enumerate(concurrent.futures.as_completed(futures), start=1):
            task = futures[future]
            payload = future.result()
            if payload.get("state") == "terminal":
                append_jsonl(raw_path, payload)
                outcome = payload["terminal_classification"]
            else:
                append_jsonl(error_path, payload)
                outcome = "ERROR"
            print(f"[{index}/{len(pending)}] {task['run_id']} -> {outcome}", flush=True)


if __name__ == "__main__":
    main()
