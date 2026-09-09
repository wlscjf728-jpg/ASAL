"""Collect source-identical review evidence or verify the bundled file manifest."""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import shutil
import re

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'evidence/source'
MANIFEST = ROOT / 'evidence/manifest.json'
DISC = 'anonymous_subround_multiround_attack_Leakage_Channel_Discovery'
TRACK = 'anonymous_subround_multiround_attack_phase_alpha'
DFT = 'RTL1_DFT_RESTUDY'
PATTERNS = {
    'Section VI-B key diversity': ['anonymous_subround_multiround_attack_key_diversity/results/raw_runs.jsonl', 'anonymous_subround_multiround_attack_key_diversity/results/summary.json'],
    'Table II discovery': [f'{DISC}/reports/MC_LEAKAGE_CHANNEL_DISCOVERY_REPORT.md', f'{DISC}/results/phase0_phase1_slot_handoff.json', f'{DISC}/results/discovery_trials/*.anonymous.json', f'{DISC}/results/discovery_trials/*.observation.json'],
    'Table III tracking': [f'{TRACK}/results/phase_alpha_tracking.json', f'{TRACK}/inputs/phase0*.txt', f'{TRACK}/inputs/phase0_discovery.json'],
    'Table IV gate recovery': ['extra_exp1/cases/case_*/results/phase_b/phase0_discovery.json', 'extra_exp1/cases/case_*/results/phase_b/phase0_gate_scan_attack.txt', 'extra_exp1/cases/case_*/results/phase_b/phase0_queries.txt', 'extra_exp1/cases/case_*/results/phase_b/q*_mc_hypotheses_attack*.json', 'extra_exp1/cases/case_*/results/phase_b/q*_mc_hypothesis_solver_attack.json', 'extra_exp1/cases/case_*/results/phase_b/q128_gate_scan.txt', 'extra_exp1/cases/case_*/results/phase_b/q128_queries.txt', 'extra_exp1/cases/case_*/results/phase_b/sep_*_scan.txt', 'extra_exp1/cases/case_*/results/phase_b/sep_*_query.txt'],
    'Fig.5 DFT': [f'{DFT}/results/analysis/aes_internal_v2_*summary.csv', f'{DFT}/results/analysis/aes_internal_v2_*region_breakdown.csv', f'{DFT}/results/analysis/aes_internal_v2_dft_fairness.csv', f'{DFT}/results/analysis/aes_internal_v2_validity.json', f'{DFT}/results/tmax/aes_internal_v2/**/summary.rpt', f'{DFT}/config/aes_internal_v2*manifest.json', f'{DFT}/reports/AES_INTERNAL_D1_D5_REPORT.md', f'{DFT}/reports/AES_INTERNAL_FAULTSHARE_25CELL_REPORT.md', f'{DFT}/reports/AES_INTERNAL_FAULTSHARE_SB_TO_MC_REPORT.md'],
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def collect(source):
    if source == ROOT / 'experiments':
        raise ValueError('Use the original experiment directory')
    entries = []
    for group, patterns in PATTERNS.items():
        paths = sorted({p for pattern in patterns for p in source.glob(pattern) if p.is_file()})
        if group == 'Fig.5 DFT':
            paths = [p for p in paths if 'balanced' not in str(p) and 'multicapture' not in str(p)]
        if not paths:
            raise ValueError(f'No source evidence: {group}')
        for path in paths:
            rel = path.relative_to(source)
            target = ARCHIVE / rel
            if target.exists() and digest(target) != digest(path):
                raise ValueError(f'Existing evidence differs: {target}')
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            entries.append({'group': group, 'source_relative': str(rel), 'path': str(target.relative_to(ROOT)), 'bytes': target.stat().st_size, 'sha256': digest(path)})
    MANIFEST.write_text(json.dumps({'schema': 'asal-evidence-v1', 'files': entries}, indent=2) + '\n')


def verify():
    rows = json.loads(MANIFEST.read_text())['files']
    for row in rows:
        path = ROOT / row['path']
        if not path.is_file() or path.stat().st_size != row['bytes'] or digest(path) != row['sha256']:
            raise ValueError(f'Evidence mismatch: {path}')
    print('Verified source-file hashes:', dict(Counter(r['group'] for r in rows)))
    diversity = ARCHIVE / 'anonymous_subround_multiround_attack_key_diversity/results'
    runs = [json.loads(line) for line in (diversity / 'raw_runs.jsonl').read_text().splitlines() if line.strip()]
    summary = json.loads((diversity / 'summary.json').read_text())
    if len(runs) != 80 or len({r['run_id'] for r in runs}) != 80 or not all(r['state'] == 'terminal' and r['attack_success'] and r['correct_key_match'] for r in runs):
        raise ValueError('Key-diversity result mismatch')
    if dict(Counter(r['terminal_classification'] for r in runs)) != summary['counts']:
        raise ValueError('Key-diversity summary mismatch')
    print('Section VI-B: 80 unique successful key-diversity records match the summary')
    handoff = json.loads((ARCHIVE / DISC / 'results/phase0_phase1_slot_handoff.json').read_text())
    positive, negative = handoff['positive'], handoff['negative']
    if len(positive) != 32 or len(negative) != 8:
        raise ValueError('Discovery cohort count mismatch')
    for r in positive:
        if not (r['classification'] == 'PASS' and r['common_query_signature_match_count'] == 65 and r['phase0_selected_slot'] == r['phase1_reused_slot'] and r['round2_same_slot']):
            raise ValueError('Discovery handoff mismatch')
    if any(r['handoff_attempted'] for r in negative):
        raise ValueError('Decoy handoff detected')
    print('Table II: 32 positive handoffs, 65/65 signatures each; 0/8 decoy handoffs')
    tracking = json.loads((ARCHIVE / TRACK / 'results/phase_alpha_tracking.json').read_text())
    stable = [r for r in tracking['scenarios'].values() if r['mode'] in ('identity', 'epoch_stable')]
    epochs = [e for r in stable for e in r['epochs']]
    if len(epochs) != 75 or not all(e['tracking_correct'] and e['validation_passed'] and e['probe_count'] == 23 for e in epochs):
        raise ValueError('Tracking epoch mismatch')
    print('Table III: 75/75 correct epochs; 23 matching probes plus held-out validation')
    for mode in ('stuck', 'transition'):
        path = ARCHIVE / DFT / f'results/analysis/aes_internal_v2_{mode}_summary.csv'
        with path.open() as handle:
            data = list(csv.DictReader(handle))
        for row in data:
            report = (ARCHIVE / DFT / f"results/tmax/aes_internal_v2/{mode}/{row['case']}/summary.rpt").read_text()
            for key, pattern in [('detected', r'\bDT\s+(\d+)'), ('total_faults', r'total faults\s+(\d+)')]:
                match = re.search(pattern, report)
                if not match or int(match[1]) != int(row[key]):
                    raise ValueError(f'ATPG summary mismatch: {mode}/{row["case"]}/{key}')
        print(f'Fig.5 {mode}: {len(data)} CSV rows agree with original ATPG total/detected counts')
    cases = sorted((ARCHIVE / 'extra_exp1/cases').glob('case_*'))
    if len(cases) != 8:
        raise ValueError('Expected eight gate cases')
    for case in cases:
        phase = case / 'results/phase_b'
        discovery = json.loads((phase / 'phase0_discovery.json').read_text())
        funnel = [discovery[k] for k in ('total_scan_ff', 'aes_dependent_candidate_count', 'pre_round_candidate_count', 'mc_aware_candidate_count_overlap_ge_3')]
        if funnel != [256, 207, 144, 1]:
            raise ValueError(f'Discovery funnel mismatch: {case.name}')
        files = list(phase.glob('q*_mc_hypothesis_solver_attack.json'))
        final = max(files, key=lambda p: int(p.name.split('_')[0][1:]))
        r = json.loads(final.read_text())
        s = r['joint_key_uniqueness']
        if (s['first_result'], s['second_result']) != ('sat', 'unsat') or r['surviving_hypothesis_count'] != 1:
            raise ValueError(f'Invalid terminal result: {case.name}')
        transcript = phase / Path(r['input_transcript']).name
        if not transcript.is_file():
            raise ValueError(f'Missing solver input: {transcript}')
        print(case.name, final.name.split('_')[0], '256->207->144->1; single hypothesis; SAT->UNSAT; input present')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root', type=Path, help='Import reviewed files from original experiments; omit for verification')
    args = parser.parse_args()
    if args.source_root:
        collect(args.source_root.resolve())
    verify()
