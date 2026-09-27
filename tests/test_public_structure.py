from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FAMILIES = {'multibit_baselines', 'multibit_hard_cases', 'temporal_key_recovery',
            'adaptive_query_strategies', 'channel_discovery', 'key_diversity',
            'channel_tracking', 'gate_reference', 'gate_topologies',
            'partial_scan_testability'}


def test_named_families_have_reader_guides():
    actual = {p.name for p in (ROOT/'experiments').iterdir() if p.is_dir()}
    assert actual == FAMILIES
    for name in FAMILIES:
        assert (ROOT/'experiments'/name/'README.md').is_file()


def test_no_server_home_paths_in_active_code():
    tracked = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
    for rel in tracked:
        p = ROOT/rel
        if not rel.startswith('experiments/') or p.suffix not in {'.py', '.sh', '.tcl'}:
            continue
        if 'results' in p.parts:
            continue
        assert '/srscl/home/' not in p.read_text(), rel


def test_gate_case_rtl_is_resolved_from_checkout():
    for case in (ROOT/'experiments/gate_topologies/cases').glob('case_*'):
        rtl = (case/'../../shared/rtl').resolve()
        assert (rtl/'extra_exp_top.sv').is_file()
        for script in ['run_dc.tcl', 'run_dft.tcl']:
            text = (case/'dft'/script).read_text()
            assert 'ASAL_LIBRARY_DB' in text
            assert '.. .. shared rtl' in text
