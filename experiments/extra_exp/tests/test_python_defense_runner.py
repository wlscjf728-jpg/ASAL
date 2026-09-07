import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from extra_exp.defense_python_matrix.evaluator import aggregate_verdict  # noqa: E402
from extra_exp.defense_python_matrix.model import StageResult  # noqa: E402


def test_verdict_precedence_keeps_policy_block_distinct_from_ambiguity():
    assert aggregate_verdict([
        StageResult("access", "pass"),
        StageResult("fixed", "ambiguity"),
        StageResult("adaptive", "query_denied", "adaptive_query_denied"),
    ]) == "BLOCKED_BY_POLICY"


def test_verdict_requires_second_solve_unsat_for_success():
    assert aggregate_verdict([
        StageResult("access", "pass"),
        StageResult("attribution", "pass"),
        StageResult("fixed", "ambiguity"),
        StageResult("adaptive", "pass"),
        StageResult("final", "full_key_unique"),
    ]) == "ATTACK_SUCCESS"
    assert aggregate_verdict([
        StageResult("access", "pass"),
        StageResult("attribution", "pass"),
        StageResult("final", "ambiguity"),
    ]) == "AMBIGUOUS_AFTER_ALLOWED_QUERIES"


def test_verdict_never_turns_unknown_into_success_or_block():
    assert aggregate_verdict([StageResult("final", "unresolved")]) == "UNRESOLVED"
    assert aggregate_verdict([StageResult("attribution", "no_channel")]) == "NO_ATTRIBUTABLE_CHANNEL"
