import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "analysis"))

from aes_internal_cones import classify_aes_region  # noqa: E402
from aes_internal_faults import (  # noqa: E402
    build_direct_exclusion_lines,
    filter_fault_line,
)
from aes_internal_v2_faults import is_aes_internal_site, is_interface_site  # noqa: E402
from aes_internal_prepare import (  # noqa: E402
    partition_candidate_cells,
    select_host_common,
    select_seeded_pool,
)
from analysis_utils import classify_atpg_state  # noqa: E402


def test_candidate_partition_keeps_stage_banks_disjoint_from_common():
    inventory = {"a_stage[0]", "a_key[0]", "h0", "h1"}
    common = {"h0", "a_key[0]"}
    stages = {"MC": {"a_stage[0]"}}
    result = partition_candidate_cells(inventory, common, stages)
    assert result["MC"] == {"a_stage[0]"}
    assert result["AES_NON_STAGE"] == set()
    assert result["COMMON"] == common


def test_aes_fault_filter_excludes_interface_and_host():
    assert filter_fault_line("sa0 NC \\u_aes_peripheral/U1/Z", {"u_aes_peripheral/"}, set()) is not None
    assert filter_fault_line("sa0 NC aes_result_o[0]", {"u_aes_peripheral/"}, set()) is None
    assert filter_fault_line("sa0 NC iwb_adr_o[0]", {"u_aes_peripheral/"}, set()) is None


def test_direct_exclusion_emits_nc_both_polarities():
    assert build_direct_exclusion_lines({"n0"}, "stuck") == ["sa0 NC n0", "sa1 NC n0"]
    assert build_direct_exclusion_lines({"n0"}, "transition") == ["str NC n0", "stf NC n0"]


def test_region_classifier_does_not_follow_clock_or_reset():
    metadata = {"mc_cone_sites": {"aes/U1/Z"}, "clock_sites": {"clk"}, "reset_sites": {"rst"}}
    assert classify_aes_region("aes/U1/Z", metadata) == "MC_CONE"
    assert classify_aes_region("clk", metadata) == "UNRESOLVED"


def test_atpg_state_normalization():
    assert classify_atpg_state("DS") == "DT"
    assert classify_atpg_state("AU") == "AU"
    assert classify_atpg_state("--") == "EQUIVALENT"


def test_transition_fault_filter_accepts_transition_polarities():
    assert filter_fault_line("str NC \\u_aes_peripheral/U1/Z", {"u_aes_peripheral/"}, set()) is not None
    assert filter_fault_line("stf NC \\u_aes_peripheral/U1/Z", {"u_aes_peripheral/"}, set()) is not None


def test_host_common_preserves_old_host_cells_and_fills_deterministically():
    result = select_host_common({"h0", "h1", "h2", "a0"}, {"h1"}, {"a0"}, 2)
    assert result == ["h1", "h0"]


def test_seeded_pool_is_reproducible_and_exact_size():
    pool = {"c0", "c1", "c2", "c3"}
    assert select_seeded_pool(pool, 2, 7) == select_seeded_pool(pool, 2, 7)
    assert len(select_seeded_pool(pool, 2, 7)) == 2


def test_fault_scope_distinguishes_internal_and_interface_sites():
    assert is_aes_internal_site("\\u_aes_peripheral/u_aes_round1/U1/Z")
    assert not is_interface_site("\\u_aes_peripheral/u_aes_round1/U1/Z")
    assert not is_aes_internal_site("aes_result_o[0]")
    assert is_interface_site("aes_result_o[0]")
    assert not is_aes_internal_site("iwb_adr_o[0]")
