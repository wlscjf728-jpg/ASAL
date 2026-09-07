"""Attacker-side solver wrapper with no evaluator-key diagnostic."""
from __future__ import annotations

import json

import z3

from solve_known_mapping import (
    _status,
    _timed_check,
    build_problem,
    diagnostics_after_second,
)


def solve_document_without_truth(
    doc: dict,
    first_timeout_ms: int = 0,
    second_timeout_ms: int = 0,
    diagnostic_timeout_ms: int = 0,
    sbox_encoding: str = "uf_axiom",
) -> dict:
    """Solve only the observation constraints; never add a true-key constraint."""
    key, builder, by_round = build_problem(doc, sbox_encoding)
    solver = z3.Solver()
    solver.add(*builder.sbox_constraints)
    for round_constraints in by_round.values():
        solver.add(*round_constraints)

    first, first_time, first_timeout, first_reason = _timed_check(solver, first_timeout_ms)
    unknown_bytes = {str(index): "unknown" for index in range(16)}
    unknown_columns = {str(index): "unknown" for index in range(4)}
    row = {
        "first_result": _status(first),
        "second_result": "not_run",
        "first_time": first_time,
        "second_time": 0.0,
        "first_model": "",
        "first_model_hex": "",
        "alternative_model": "",
        "first_model_correct": False,
        "true_key_satisfiable": "not_checked",
        "true_key_timeout": False,
        "second_timeout": False,
        "timeout": first_timeout,
        "z3_reason_unknown": first_reason,
        "byte_diagnostic_summary": json.dumps(unknown_bytes, sort_keys=True),
        "column_diagnostic_summary": json.dumps(unknown_columns, sort_keys=True),
        "fixed_bytes": "[]",
        "free_bytes": "[]",
        "unknown_bytes": json.dumps(list(range(16))),
        "first_timeout": first_timeout,
        "classification": "undecided",
        "confirmed_unique_candidate": False,
        "sbox_encoding": sbox_encoding,
        "attacker_side": True,
    }
    if first != z3.sat:
        row["classification"] = "inconsistent" if first == z3.unsat else "undecided"
        return row

    model = solver.model()
    candidate = bytes(
        model.eval(key[index], model_completion=True).as_long() for index in range(16)
    )
    row["first_model"] = candidate.hex()
    row["first_model_hex"] = candidate.hex()

    solver.push()
    solver.add(z3.Or(*[key[index] != candidate[index] for index in range(16)]))
    second, second_time, second_timeout, second_reason = _timed_check(
        solver, second_timeout_ms
    )
    alternative = None
    if second == z3.sat:
        second_model = solver.model()
        alternative = bytes(
            second_model.eval(key[index], model_completion=True).as_long()
            for index in range(16)
        )
        row["alternative_model"] = alternative.hex()
    solver.pop()

    row.update({
        "second_result": _status(second),
        "second_time": second_time,
        "second_timeout": second_timeout,
        "timeout": first_timeout or second_timeout,
        "z3_reason_unknown": second_reason if second == z3.unknown else first_reason,
        "classification": (
            "full_key_unique" if second == z3.unsat
            else "ambiguity" if second == z3.sat
            else "undecided"
        ),
        "confirmed_unique_candidate": second == z3.unsat,
    })
    byte_summary, column_summary = diagnostics_after_second(
        solver,
        key,
        candidate,
        _status(second),
        alternative,
        diagnostic_timeout_ms,
    )
    row["byte_diagnostic_summary"] = json.dumps(byte_summary, sort_keys=True)
    row["column_diagnostic_summary"] = json.dumps(column_summary, sort_keys=True)
    row["fixed_bytes"] = json.dumps(
        [int(index) for index, value in byte_summary.items() if value == "fixed"]
    )
    row["free_bytes"] = json.dumps(
        [int(index) for index, value in byte_summary.items() if value == "free"]
    )
    row["unknown_bytes"] = json.dumps(
        [int(index) for index, value in byte_summary.items() if value == "unknown"]
    )
    return row
