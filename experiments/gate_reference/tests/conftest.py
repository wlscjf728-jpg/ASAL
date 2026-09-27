"""Separate self-contained tests from optional physical-run record checks."""
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
DEFENSE_FILES = {
    'test_defense_capture_contract.py', 'test_defense_dft_profiles.py',
    'test_defense_manifest.py', 'test_defense_rtl_contract.py',
    'test_rtl_golden_manifest.py', 'test_rtl_golden_matrix.py',
    'test_rtl_golden_report.py', 'test_rtl_query_manifest.py',
    'test_rtl_transcript_comparison.py',
}


def pytest_addoption(parser):
    parser.addoption('--require-gate-records', action='store_true',
                     help='Fail rather than skip when optional gate record bundles are absent')


def pytest_collection_modifyitems(config, items):
    for item in items:
        if Path(item.path).parent != Path(__file__).parent:
            continue
        name = Path(item.path).name
        required = []
        if name in DEFENSE_FILES:
            required = [ROOT/'defense_boundary']
        elif name == 'test_dft_reports.py':
            required = [ROOT/'results/evaluator']
        elif name == 'test_gate_bridge.py':
            required = [ROOT/'results/phase_b', ROOT/'results/evaluator']
        elif name == 'test_python_defense_matrix_results.py':
            required = [ROOT/'defense_python_matrix/results']
        missing = [str(p.relative_to(ROOT)) for p in required if not p.is_dir()]
        if missing and not config.getoption('--require-gate-records'):
            item.add_marker(pytest.mark.skip(reason='Optional physical-run bundle not distributed: '+', '.join(missing)))
