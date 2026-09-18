"""Synthetic report-only integration: no flight, ROS, or recorded-data edits."""
import csv
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import run_gapfree_n5 as controller
sys.path.insert(0, str(controller.LEGACY))
from test_c24_normal_validation import valid_triplet, write_raw


def synthetic_campaign(root, fault=None, contamination=False):
    originals = []
    for repeat in (1, 2):
        folder = root/'test5'/controller.MAPS[0]/f'synthetic_r{repeat}'
        plan, raw = valid_triplet(folder, controller.MAPS[0], 31000+repeat, False,
                                 controller.CANDIDATE, controller.MODES, True)
        plan.update(gapfree_scratch_directory=f'/tmp/synthetic_unique_{repeat}',
                    logical_cpus=20, synthetic_no_flight=True)
        controller.base.save(folder/'plan.json', plan)
        for row in raw:
            row.update(end_to_end_cpu_scope='experiment cgroup incl simulator',
                       algorithm_cpu_scope='unavailable composed process', mission_time_s='39',
                       static_pcd_clearance_m='.4')
        if repeat == 2 and (fault or contamination):
            raw[0].update(end_to_end_cpu_cores_mean='9.0', success='False',
                          safety_collisions='2', static_pcd_collisions='2',
                          static_pcd_clearance_m='-.1')
            if fault:
                raw[0].update(fault)
            summary = controller.base.read(folder/'full_summary.json')
            summary.update(end_to_end_cpu_cores_mean=9.0, success=False, safety_collisions=2)
            controller.base.save(folder/'full_summary.json', summary)
            if contamination:
                controller.base.save(folder/'diagnostic_contamination.json', dict(contaminated=True))
        write_raw(folder, raw)
        originals += list(folder.glob('*.json')) + [folder/'raw.csv']
    return {str(path): controller.base.sha(path) for path in originals}


def metric_rows(root):
    with (root/'report_test5/all_metrics.csv').open(newline='') as stream:
        return list(csv.DictReader(stream))


def test_repeated_scratch_aggregates_and_retry_cost_is_missing_but_outcome_remains(tmp_path):
    originals = synthetic_campaign(tmp_path, {'retry_count':'1', 'attempt_count':'2'})
    original_fingerprint = controller.base.reports.protocol_fingerprint
    original_loader = controller.base.reports.load_runs
    records = controller.reports(tmp_path)
    assert records[-1]['state'] == 'WRITTEN'
    assert controller.base.reports.protocol_fingerprint is original_fingerprint
    assert controller.base.reports.load_runs is original_loader
    for name in ('all_metrics.csv', 'summary_ko.md', 'run_metrics.csv', 'comparison.json'):
        assert (tmp_path/'report_test5'/name).is_file()
    cpu = next(row for row in metric_rows(tmp_path)
               if row['metric'] == 'end_to_end_cpu_cores_mean' and row['mode'] == 'full')
    assert (cpu['n'], cpu['n_missing'], cpu['mean']) == ('1', '1', '0.5')
    with (tmp_path/'summary_by_map.csv').open(newline='') as stream:
        progress = next(row for row in csv.DictReader(stream)
                        if row['map'] == controller.MAPS[0] and row['mode'] == 'full')
    assert (progress['attempts'], progress['performance_valid_runs'], progress['cpu_cores_mean']) == ('2', '1', '0.5')
    document = controller.base.read(tmp_path/'report_test5/comparison.json')
    full = document['cohorts'][0]['modes']['full']
    assert (full['attempts'], full['successes'], full['contact_runs']) == (2, 1, 1)
    assert full['metrics']['static_pcd_clearance_m']['n'] == 2
    invalid = next(run for run in document['runs'] if run['mode'] == 'full' and run['run'] == '31002')
    assert invalid['metrics']['retry_count'] == 1
    assert invalid['metrics']['safety_collisions'] == 2
    assert invalid['metrics']['success'] == 0
    assert invalid['metrics']['static_pcd_clearance_m'] == -.1
    assert invalid['metrics']['end_to_end_cpu_cores_mean'] is None
    assert invalid['metrics']['mission_time_s'] is None
    assert invalid['cost_comparison_admission']['valid'] is False
    assert invalid['scopes']['end_to_end_cpu_scope'] == 'experiment cgroup incl simulator'
    assert any('comparative costs N/A' in warning for warning in document['warnings'])
    assert all(controller.base.sha(path) == digest for path, digest in originals.items())


@pytest.mark.parametrize('fault', [
    {'run_valid':'False'}, {'resource_valid':'False'}, {'speed_limit_valid':'False'},
    {'infrastructure_failure':'True'}, {'attempt_count':'2'}, {'retry_count':'1'},
    {'cgroup_cpu_duration_s':'0'}, {'cgroup_cpu_duration_s':'nan'},
    {'cgroup_cpu_duration_s':''},
])
def test_every_raw_cost_gate_masks_invalid_cost(fault, tmp_path):
    originals = synthetic_campaign(tmp_path, fault)
    assert controller.reports(tmp_path)[-1]['state'] == 'WRITTEN'
    cpu = next(row for row in metric_rows(tmp_path)
               if row['metric'] == 'end_to_end_cpu_cores_mean' and row['mode'] == 'full')
    assert (cpu['n'], cpu['n_missing'], cpu['mean']) == ('1', '1', '0.5')
    assert all(controller.base.sha(path) == digest for path, digest in originals.items())


def test_diagnostic_contamination_preserves_contact_metadata(tmp_path):
    synthetic_campaign(tmp_path, contamination=True)
    assert controller.reports(tmp_path)[-1]['state'] == 'WRITTEN'
    rows = metric_rows(tmp_path)
    for mode in controller.MODES:
        cpu = next(row for row in rows if row['metric'] == 'end_to_end_cpu_cores_mean' and row['mode'] == mode)
        assert (cpu['n'], cpu['n_missing']) == ('1', '1')
    contacts = next(row for row in rows if row['metric'] == 'static_pcd_clearance_m' and row['mode'] == 'full')
    assert contacts['n'] == '2'


def test_report_functions_restored_after_failure(tmp_path, monkeypatch):
    synthetic_campaign(tmp_path)
    fingerprint = controller.base.reports.protocol_fingerprint
    loader = controller.base.reports.load_runs
    def fail(_args):
        raise ValueError('Synthetic report failure')
    monkeypatch.setattr(controller.base.reports, 'main', fail)
    assert controller.reports(tmp_path)[-1]['state'] == 'REPORT_ERROR'
    assert controller.base.reports.protocol_fingerprint is fingerprint
    assert controller.base.reports.load_runs is loader
