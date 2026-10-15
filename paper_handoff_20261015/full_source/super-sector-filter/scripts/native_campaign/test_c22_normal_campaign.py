"""Map routing and prospective expansion guards; no real flights."""
import json
from pathlib import Path
import pytest
import static_latched_preflight as static
from run_c22_normal_campaign import (MAPS, build_plan, campaign_gate, flight_checks, triplet_audit, make_references)
from sensor_acquisition_seed1_smoke import audit_source
from event_recovery_seed1_smoke import audit_recovery
from adaptive_cpu40_seed1 import heading_policy_audit


def test_map_contexts_are_independent_and_bound():
    a, b = static.map_context('seed1'), static.map_context('seed9')
    assert a['geometry'] == static.EXPECTED_GEOMETRY
    assert b['geometry']['points'] == 1042220
    assert b['geometry']['bytes'] == 1042220*32
    assert 'seed9_config' in b['paths'] and 'seed1_config' not in b['paths']
    assert b['paths']['seed9_pcd'].name == 'seed9.pcd'
    b['geometry']['points'] = 1
    assert static.map_context('seed9')['geometry']['points'] == 1042220
    with pytest.raises(ValueError):
        static.map_context('../../seed1')


def test_wrong_map_geometry_and_command_rejected():
    context = static.map_context('seed3')
    geometry = context['geometry']
    counts = dict(publications=1, points=geometry['points'], bytes=geometry['bytes'],
                  stamp_ns=123, timers_created=0, poll_callbacks=0)
    assert static.counters(counts, context=context) == counts
    with pytest.raises(ValueError):
        static.counters(counts) # Cannot use seed1 acceptance on seed3.
    bindings = {'binary_standalone': {'path':'/tmp/fake'}}
    static.check_command(['/tmp/fake','config_name:=seed3.yaml'], 'standalone', bindings, context)
    with pytest.raises(ValueError):
        static.check_command(['/tmp/fake','config_name:=seed1.yaml'], 'standalone', bindings, context)


def test_prospective_counts_and_independent_stages(tmp_path):
    commands = build_plan(tmp_path, 10000)
    flights = [c for c in commands if 'path' in c]
    assert len([c for c in commands if c['phase']=='static']) == 40
    assert len(flights)*3 == 390
    assert len({c['run'] for c in flights}) == len(flights)
    for phase, expected in [('preflight',1),('pilot5',5),('confirm20',20)]:
        for map_name in MAPS:
            selected=[c for c in flights if c['phase']==phase and c['map']==map_name]
            assert len(selected) == expected
            for item in selected:
                assert set(item['modes']) == {'full','sector','adaptive'}
                command=item['command']
                assert command[command.index('--map')+1] == map_name
                assert command[command.index('--side-executor-threads')+1] == '3'
    gate = campaign_gate(tmp_path, commands, 'pilot5')
    assert not gate['valid'] and gate['planned_triplets'] == 25
    # Every slot must exist and explicitly pass; missing/false cannot expand.
    for item in commands:
        if item['phase']=='pilot5':
            folder=Path(item['path']); folder.mkdir(parents=True)
            (folder/'triplet_verification.json').write_text(json.dumps(dict(
                valid=True, map=item['map'], run=item['run'], profiled=False, checks={'fixture':True})))
    assert campaign_gate(tmp_path,commands,'pilot5')['valid']
    target=next(c for c in commands if c['phase']=='pilot5')
    (Path(target['path'])/'triplet_verification.json').write_text(json.dumps({'valid':False}))
    assert not campaign_gate(tmp_path,commands,'pilot5')['valid']


def test_missing_or_failed_evidence_never_passes(tmp_path):
    assert not triplet_audit(tmp_path,'seed3',100,False)['valid']
    assert not all(flight_checks({},False).values())


def test_short_lease_applies_to_every_map_mode_and_phase(tmp_path):
    commands = build_plan(tmp_path, 12000, extended_lease=False)
    flights = [c for c in commands if 'path' in c]
    assert len(flights) == 130
    assert all('--extended-demand-lease' not in c['command'] for c in flights)
    assert all('--guarded-demand-replan' in c['command'] for c in flights)


def test_body_heading_candidate_applies_to_all_prospective_slots(tmp_path):
    commands = build_plan(tmp_path, 14000, extended_lease=False, event_body_heading=True)
    flights = [c for c in commands if 'path' in c]
    assert len(flights) == 130
    assert all('--event-body-heading' in c['command'] for c in flights)
    assert all('--extended-demand-lease' not in c['command'] for c in flights)


def test_historical_timing_keeps_contact_rows_without_safety_claim(tmp_path):
    make_references(tmp_path)
    row = json.loads((tmp_path/'references/seed9/sector_summary.json').read_text())
    assert row['time_only'] is True
    assert row['reference_provenance']['historical_contact_runs'] == 1


def test_heading_policy_is_explicit_and_mode_bound():
    body = '[SECTOR_HEADING_POLICY] body_aligned_event=1 velocity_center=0'
    velocity = '[SECTOR_HEADING_POLICY] body_aligned_event=0 velocity_center=1'
    sector = '[SECTOR_HEADING_POLICY] body_aligned_event=0 velocity_center=0'
    assert heading_policy_audit(body, 'adaptive', True)['valid']
    assert heading_policy_audit(velocity, 'adaptive', False)['valid']
    assert heading_policy_audit(sector, 'sector', True)['valid']
    assert heading_policy_audit(sector, 'sector', False)['valid']
    assert heading_policy_audit('', 'full', True)['valid']
    for text, mode, enabled in [(body, 'full', True), (body, 'sector', True),
                                (velocity, 'adaptive', True), ('', 'adaptive', True),
                                (body + '\n' + body, 'adaptive', True)]:
        assert not heading_policy_audit(text, mode, enabled)['valid']


def test_source_and_event_audits_use_map_name(tmp_path):
    (tmp_path/'seed3_run100_full.attempt1.stack.log').write_text(
        '[SENSOR_ACQUISITION_FRAME] frame=1 cycle=0 full=1 stamp_ns=1 width=900 height=128 '
        'readback_pixels=230400 conversion_rays=115200 generated_points=1 bytes=32 half_angle_deg=180\n')
    assert all(audit_source(tmp_path,100,'full','seed3')['checks'].values())
    with pytest.raises(FileNotFoundError):
        audit_source(tmp_path,100,'full')
    (tmp_path/'seed3_run100_adaptive.attempt1.stack.log').write_text('')
    (tmp_path/'seed3_run100_adaptive.attempt1.filt_stats.json').write_text(json.dumps({'event_recovery_enabled':True}))
    assert all(audit_recovery(tmp_path,100,'seed3')['checks'].values())


def test_canonical_frozen_geometry_matches_independent_pcd():
    import hashlib
    import numpy as np
    from ascii_pcd_xyz import load_ascii_pcd_xyz
    for name in MAPS:
        context = static.map_context(name)
        path = context['paths'][name+'_pcd']
        xyz = load_ascii_pcd_xyz(path)
        wire = np.zeros((len(xyz),8), dtype='<f4')
        wire[:,:3] = xyz
        wire[:,3] = 1
        assert len(xyz) == context['geometry']['points']
        assert hashlib.sha256(wire.tobytes()).hexdigest() == context['geometry']['sha256']
