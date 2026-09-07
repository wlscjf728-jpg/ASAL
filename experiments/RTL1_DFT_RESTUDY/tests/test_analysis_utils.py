import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "analysis"))

from analysis_utils import (  # noqa: E402
    build_direct_fault_lines,
    classify_region,
    parse_fault_line,
    parse_summary_text,
    pareto_frontier,
)


def test_parse_tmax_fault_line_keeps_polarity_status_and_site():
    result = parse_fault_line(" sa0   DS   aes_result_o[7]   (_PO)   ( 1: 2/0/0 )")
    assert result == {"polarity": "sa0", "status": "DS", "site": "aes_result_o[7]"}


def test_parse_transition_fault_line_keeps_fault_kind():
    result = parse_fault_line(" str   DS   u_aes/U1/Z   (and2)")
    assert result == {"polarity": "str", "status": "DS", "site": "u_aes/U1/Z"}


def test_direct_fault_exclusion_contains_both_stuck_at_polarities_once():
    lines = build_direct_fault_lines(["u_aes/MC_REG_reg[0]"], {"u_aes/MC_REG_reg[0]": "aes_result_o[0]"})
    assert lines == ["sa0 aes_result_o[0]", "sa1 aes_result_o[0]"]


def test_region_classifier_is_disjoint_and_assigns_host_and_aes_cones():
    metadata = {
        "direct_sites": {"aes_result_o[0]"},
        "mc_cone_sites": {"u_aes/u_mc/U1/Z"},
        "aes_sites": {"u_aes/u_sb/U2/Z"},
    }
    assert classify_region("aes_result_o[0]", metadata) == "selected_ff_direct"
    assert classify_region("u_aes/u_mc/U1/Z", metadata) == "mc_cone"
    assert classify_region("u_aes/u_sb/U2/Z", metadata) == "aes_other"
    assert classify_region("u_mor1kx/U3/Z", metadata) == "host"


def test_summary_parser_reads_full_atpg_classes():
    text = """
    Detected DT 10
    Possibly detected PT 2
    Undetectable UD 1
    ATPG untestable AU 3
    Not detected ND 4
    total faults 20
    test coverage 60.00%
    #internal patterns 9
    Total CPU time 1.25
    """
    assert parse_summary_text(text) == {
        "detected": 10,
        "possibly_detected": 2,
        "undetectable": 1,
        "atpg_untestable": 3,
        "not_detected": 4,
        "total_faults": 20,
        "coverage_pct": 60.0,
        "patterns": 9,
        "cpu_seconds": 1.25,
    }


def test_pareto_frontier_maximizes_testability_and_minimizes_leakage():
    points = [
        {"name": "A", "testability": 0.70, "leakage": 0.20},
        {"name": "B", "testability": 0.80, "leakage": 0.20},
        {"name": "C", "testability": 0.80, "leakage": 0.40},
        {"name": "D", "testability": 0.60, "leakage": 0.10},
    ]
    assert [point["name"] for point in pareto_frontier(points)] == ["B", "D"]
