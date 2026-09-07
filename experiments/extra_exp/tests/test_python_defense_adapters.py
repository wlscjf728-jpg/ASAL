import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from extra_exp.defense_python_matrix.adapters import (  # noqa: E402
    apply_differential_transform,
    apply_observation_transform,
)
from extra_exp.defense_python_matrix.model import DefenseCondition  # noqa: E402
from extra_exp.defense_python_matrix.policy import (  # noqa: E402
    authorize_access,
    authorize_query,
)


def condition(condition_id, transform, authorization="allow", adaptive_allowed=True):
    return DefenseCondition(
        condition_id=condition_id,
        family="test",
        description="test",
        transform=transform,
        authorization=authorization,
        secret_id=None,
        adaptive_allowed=adaptive_allowed,
        expected_boundary="test",
    )


def test_observation_transforms_have_expected_scope():
    vector = (1 << 255) | (1 << 20)
    assert apply_observation_transform(vector, condition("D0", "identity"), 1, 1) == vector
    state_vector = (1 << 255) | (1 << 240)
    assert apply_observation_transform(state_vector, condition("D1", "state_only"), 1, 1) == (1 << 255)
    assert apply_observation_transform(vector, condition("D1b", "clear_post_mc"), 1, 1) == (1 << 20)
    assert apply_observation_transform(vector, condition("D2", "reset_capture"), 1, 1) == (1 << 20)
    assert apply_observation_transform(vector, condition("D3a", "round_mask_only"), 1, 1) == vector
    assert apply_observation_transform(vector, condition("D3a", "round_mask_only"), 0, 2) != vector
    assert apply_observation_transform(vector, condition("D3b", "round_and_mc_mask"), 1, 1) != vector


def test_static_and_changing_scan_transforms_are_deterministic():
    vector = (1 << 255) | (1 << 20)
    static_a = apply_observation_transform(vector, condition("D5a", "static_permutation"), 3, 1)
    static_b = apply_observation_transform(vector, condition("D5a", "static_permutation"), 99, 3)
    assert static_a == static_b
    assert apply_observation_transform(vector, condition("D5c", "epoch_permutation"), 0, 1) != apply_observation_transform(vector, condition("D5c", "epoch_permutation"), 8, 1)
    assert apply_observation_transform(vector, condition("D5d", "probe_permutation"), 0, 1) != apply_observation_transform(vector, condition("D5d", "probe_permutation"), 1, 1)


def test_differential_inversion_cancels_and_response_hiding_changes_value():
    assert apply_differential_transform(0, condition("D5b", "fixed_inversion"), 0, 1) == 1
    assert apply_differential_transform(1, condition("D5b", "fixed_inversion"), 0, 1) == 0
    hidden_a = apply_observation_transform(0, condition("D8", "response_hide"), 0, 1)
    hidden_b = apply_observation_transform(0, condition("D8", "response_hide"), 1, 1)
    assert hidden_a != hidden_b


def test_access_and_query_policy_are_explicit():
    allowed, reason = authorize_access(condition("D6_invalid", "identity", "deny_access", False), "invalid")
    assert allowed is False
    assert reason == "access_denied"
    allowed, reason = authorize_access(condition("D6_valid", "identity"), "valid")
    assert allowed is True
    assert reason == "access_allowed"

    d7 = condition("D7", "identity", "restrict_adaptive", False)
    assert authorize_query(d7, 1, "fixed", "aa", {"aa"}) == (True, "query_allowed")
    assert authorize_query(d7, 2, "adaptive", "bb", {"aa"}) == (False, "adaptive_query_denied")
    d4 = condition("D4", "identity", "restrict_adaptive", False)
    assert authorize_query(d4, 1, "phase0", "bb", {"aa"}) == (False, "phase0_probe_denied")
