"""Seven-map identity admission and inherited-policy checks; no ROS or flights."""
import ast
import copy
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import scenario7_campaign_support as support
import scenario7_cpu_compare as child


def save(path, document):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, allow_nan=False))


@pytest.fixture
def suite(tmp_path, monkeypatch):
    package = tmp_path / 'runtime'
    mirror = tmp_path / 'mirror'
    install = tmp_path / 'install'
    manifest = tmp_path / 'manifest.json'
    monkeypatch.setattr(support, 'PACKAGE', package)
    monkeypatch.setattr(support, 'MIRROR', mirror)
    monkeypatch.setattr(support, 'INSTALL_CONFIG', install)
    monkeypatch.setattr(support, 'MANIFEST', manifest)
    baseline = 'pcd_name: "seed_maps/gapfree_d1_m01.pcd"\nsensing_rate: 10\n'
    (package / 'config').mkdir(parents=True)
    (package / 'config/gapfree_d1_m01.yaml').write_text(baseline)
    original = dict(valid=True, manifest=str(tmp_path / 'original.json'),
                    manifest_sha256='a' * 64, assets_sha256={}, maps={})
    for name in support.ORIGINAL_MAPS:
        path = package / 'pcd/seed_maps' / (name + '_cylinders.csv')
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('x,y,r\n0,0,.5\n')
        original['assets_sha256'][str(path)] = support.sha256(path)
        original['maps'][name] = dict(map=name, label=support.MAP_LABELS[name],
                                     geometry=dict(points=1, sha256='b' * 64))
    monkeypatch.setattr(support.gapfree, 'validate_suite', lambda: copy.deepcopy(original))
    pcd = ('VERSION 0.7\nFIELDS x y z intensity\nSIZE 4 4 4 4\nTYPE F F F F\n'
           'COUNT 1 1 1 1\nWIDTH 1\nHEIGHT 1\nPOINTS 1\nDATA ascii\n1 2 3 0\n')
    rows = []
    for name, family in zip(support.ADDED_MAPS, ('urban', 'forest')):
        paths = support._required_added_assets(name)
        for path in paths:
            path.parent.mkdir(parents=True, exist_ok=True)
        config = baseline.replace('gapfree_d1_m01', name)
        solid = dict(schema='scenario-solid-geometry-v1', map=name, body_radius_m=.2,
                     boxes=[], cylinders=[])
        if family == 'urban':
            solid['boxes'] = [dict(id='b1', cx=10., cy=10., z_min=0., z_max=6., size_x=6., size_y=8.)]
        else:
            solid['cylinders'] = [dict(id='t1', x=10., y=10., r=.5, z_min=0., z_max=4.)]
        for i in (0, 3, 6):
            paths[i].write_text(config)
        for i in (1, 4):
            paths[i].write_text(pcd)
        for i in (2, 5):
            save(paths[i], solid)
        rows.append(dict(map=name, label=support.MAP_LABELS[name], family=family,
                         point_count=1, statistics={}, route_audit=dict(valid=True),
                         assets_sha256={str(path): support.sha256(path) for path in paths}))
    document = dict(schema='scenario7-added-maps-v1', maps=rows)
    save(manifest, document)
    return SimpleNamespace(document=document, manifest=manifest, original=original)


def test_seven_contexts_keep_original_validation_and_new_geometry(suite):
    value = support.validate_suite()
    assert tuple(value['maps']) == support.MAPS7
    assert value['maps']['urban_blocks_u01']['box_count'] == 1
    assert value['maps']['forest_cluster_f01']['cylinder_count'] == 1
    assert value['maps'][support.ORIGINAL_MAPS[-1]]['label'] == 'G5-R2'
    assert value['original_manifest_sha256'] == suite.original['manifest_sha256']
    assert value['manifest_sha256'] == support.sha256(suite.manifest)
    assert not value['transport_certified'] and not value['flights_started']


def test_old_suite_rejection_is_not_bypassed(suite, monkeypatch):
    def rejected():
        raise ValueError('original suite mismatch')
    monkeypatch.setattr(support.gapfree, 'validate_suite', rejected)
    with pytest.raises(ValueError, match='original suite mismatch'):
        support.validate_suite()


def test_added_identity_and_required_mirrors_fail_closed(suite):
    suite.document['maps'].reverse()
    save(suite.manifest, suite.document)
    with pytest.raises(ValueError, match='exact ordered'):
        support.validate_suite()
    suite.document['maps'].reverse()
    row = suite.document['maps'][0]
    del row['assets_sha256'][str(support._required_added_assets(row['map'])[5])]
    save(suite.manifest, suite.document)
    with pytest.raises(ValueError, match='Incomplete'):
        support.validate_suite()


def test_asset_and_point_count_mismatches_fail_closed(suite):
    row = suite.document['maps'][0]
    path = support._required_added_assets(row['map'])[1]
    row['assets_sha256'][str(path)] = '0' * 64
    save(suite.manifest, suite.document)
    with pytest.raises(ValueError, match='asset changed'):
        support.validate_suite()
    row['assets_sha256'][str(path)] = support.sha256(path)
    row['point_count'] = 2
    save(suite.manifest, suite.document)
    with pytest.raises(ValueError, match='point count mismatch'):
        support.validate_suite()


def test_self_consistently_rehashed_sensor_change_still_rejected(suite):
    row = suite.document['maps'][0]
    paths = support._required_added_assets(row['map'])
    for i in (0, 3, 6):
        paths[i].write_text(paths[i].read_text().replace('sensing_rate: 10', 'sensing_rate: 20'))
        row['assets_sha256'][str(paths[i])] = support.sha256(paths[i])
    save(suite.manifest, suite.document)
    with pytest.raises(ValueError, match='simulator/sensor profile changed'):
        support.validate_suite()


@pytest.mark.parametrize('change', ['negative_size', 'nonfinite', 'wrong_map', 'duplicate_id', 'empty'])
def test_invalid_solid_geometry_rejected(suite, change):
    row = suite.document['maps'][0]
    path = support._required_added_assets(row['map'])[2]
    document = json.loads(path.read_text())
    if change == 'negative_size':
        document['boxes'][0]['size_x'] = -1
    elif change == 'nonfinite':
        document['boxes'][0]['cx'] = float('nan')
    elif change == 'wrong_map':
        document['map'] = 'other'
    elif change == 'duplicate_id':
        document['boxes'].append(dict(document['boxes'][0]))
    else:
        document['boxes'] = []
    path.write_text(json.dumps(document))
    with pytest.raises(ValueError):
        support.validate_solid_geometry(path, row['map'])


def test_registration_conflict_is_atomic(suite, monkeypatch):
    import static_latched_preflight as static
    registry = {support.ADDED_MAPS[-1]: (99, 'conflicting')}
    monkeypatch.setattr(static, 'MAP_GEOMETRIES', registry)
    with pytest.raises(ValueError, match='Conflicting in-process'):
        support.register_maps()
    assert registry == {support.ADDED_MAPS[-1]: (99, 'conflicting')}


def test_registered_admission_is_json_safe_without_changing_static_context_paths(suite, monkeypatch):
    import static_latched_preflight as static
    monkeypatch.setattr(static, 'MAP_GEOMETRIES', {})
    admitted = support.register_maps()
    assert json.loads(json.dumps(admitted)) == admitted
    for name, context in admitted['maps'].items():
        assert all(isinstance(path, str) for path in context['paths'].values())
        assert all(isinstance(path, Path) for path in static.map_context(name)['paths'].values())


def test_adapter_keeps_all_argument_and_conditional_gates_and_isolated_globals():
    source = support.GAPFREE_ADAPTER.read_text()
    original = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'main')
    adapted = ast.parse(child.adapted_main_source()).body[0]
    def gates(node):
        conditions = [ast.dump(n.test) for n in ast.walk(node) if isinstance(n, ast.If)]
        arguments = [ast.dump(n) for n in ast.walk(node) if isinstance(n, ast.Call)
                     and isinstance(n.func, ast.Attribute) and n.func.attr in ('add_argument', 'error')]
        return conditions, arguments
    assert gates(original) == gates(adapted)
    inherited_maps, inherited_monitor = child.inherited.MAPS, child.inherited.MONITOR
    main = child.build_main()
    assert main.__globals__['MAPS'] == support.MAPS7
    assert main.__globals__['MONITOR'] == child.MONITOR
    assert main.__globals__['register_maps'] is support.register_maps
    assert child.inherited.MAPS == inherited_maps
    assert child.inherited.MONITOR == inherited_monitor
    assert main.__globals__ is not child.inherited.main.__globals__


def test_adapter_refuses_changed_inherited_source(tmp_path, monkeypatch):
    changed = tmp_path / 'gapfree_cpu_compare.py'
    changed.write_text(support.GAPFREE_ADAPTER.read_text() + '\n# changed\n')
    monkeypatch.setattr(support, 'GAPFREE_ADAPTER', changed)
    with pytest.raises(ValueError, match='baseline changed'):
        child.build_main()


@pytest.mark.parametrize('missing_or_changed', child.MAP_MATCH_FIELDS)
def test_profile_reference_binds_each_map_and_observer_identity(monkeypatch, missing_or_changed):
    monkeypatch.setattr(child.inherited.legacy, 'small_pool_profile_reference_audit',
                        lambda *_: dict(valid=True, checks={}, acceptance_checks={}))
    values = {key: 'same' for key in child.MAP_MATCH_FIELDS}
    assert child.small_pool_profile_reference_audit(values, dict(values), {})['valid']
    altered = dict(values)
    altered[missing_or_changed] = 'different'
    assert not child.small_pool_profile_reference_audit(values, altered, {})['valid']
    del altered[missing_or_changed]
    assert not child.small_pool_profile_reference_audit(values, altered, {})['valid']


def profiled_solid_reference():
    plan = {key: 'same' for key in child.MAP_MATCH_FIELDS}
    plan.update(map='urban_blocks_u01', modes=['full', 'sector', 'adaptive'])
    solid = dict(schema='scenario-solid-audit-v1', schema_version=1, audit_valid=True,
                 completion=True, map=plan['map'], geometry_sha256='same', observer_code_sha256='same',
                 robot_radius_m=.2, observation='received_odometry_samples_only', swept_collision_check=False,
                 contact_episodes=0, samples=3, invalid_samples=0,
                 timestamp_nonmonotonic_count=0, receipt_nonmonotonic_count=0)
    return plan, {mode: dict(solid_obstacle_audit=dict(solid)) for mode in plan['modes']}


@pytest.mark.parametrize('mode', ['full', 'sector', 'adaptive'])
def test_profile_reference_uses_solid_contacts_when_point_cloud_misses_them(monkeypatch, mode):
    monkeypatch.setattr(child.inherited.legacy, 'small_pool_profile_reference_audit',
                        lambda *_: dict(valid=True, checks={'legacy_passed': True}, acceptance_checks={'legacy_passed': True}))
    plan, summaries = profiled_solid_reference()
    assert child.small_pool_profile_reference_audit(plan, dict(plan), summaries)['valid']
    summaries[mode]['solid_obstacle_audit']['contact_episodes'] = 1
    audit = child.small_pool_profile_reference_audit(plan, dict(plan), summaries)
    assert audit['valid'] == (mode == 'sector')
    assert audit['checks']['legacy_passed'] is True
    assert audit['checks'][mode + '_solid_observation_valid'] is True
    if mode != 'sector':
        assert audit['acceptance_checks'][mode + '_solid_zero_contact'] is False


@pytest.mark.parametrize('field,value', [
    ('audit_valid', False), ('completion', False), ('contact_episodes', None),
    ('contact_episodes', True), ('samples', 0), ('map', 'other_map'),
    ('geometry_sha256', 'changed'), ('observer_code_sha256', 'changed'),
    ('invalid_samples', 1), ('timestamp_nonmonotonic_count', 1), ('receipt_nonmonotonic_count', 1),
    ('observation', 'point_cloud_only'), ('robot_radius_m', .1),
])
def test_profile_reference_missing_invalid_or_mismatched_solid_evidence_fails(monkeypatch, field, value):
    monkeypatch.setattr(child.inherited.legacy, 'small_pool_profile_reference_audit',
                        lambda *_: dict(valid=True, checks={}, acceptance_checks={}))
    plan, summaries = profiled_solid_reference()
    summaries['sector']['solid_obstacle_audit'][field] = value
    assert not child.small_pool_profile_reference_audit(plan, dict(plan), summaries)['valid']
    summaries['sector'].pop('solid_obstacle_audit')
    assert not child.small_pool_profile_reference_audit(plan, dict(plan), summaries)['valid']


def test_valid_solid_reference_never_overrides_failed_legacy_gate(monkeypatch):
    monkeypatch.setattr(child.inherited.legacy, 'small_pool_profile_reference_audit',
                        lambda *_: dict(valid=False, checks={'legacy_passed': False}, acceptance_checks={'legacy_passed': False}))
    plan, summaries = profiled_solid_reference()
    assert not child.small_pool_profile_reference_audit(plan, dict(plan), summaries)['valid']


def test_solid_and_odometry_copy_preservation_and_overwrite_refusal(tmp_path):
    scratch = tmp_path / 'scratch'
    scratch.mkdir()
    root = tmp_path / 'result with spaces'
    campaign = SimpleNamespace(TMPDIR=str(scratch))
    stem = 'urban_blocks_u01_run7_full.attempt1'
    audit = scratch / (stem + '.solid_audit.json')
    trace = scratch / (stem + '.odometry.csv')
    trace.write_text('partial observations\n')
    with pytest.raises(FileNotFoundError):
        child.copy_supplemental_artifacts(root, 'urban_blocks_u01', 7, 'full', campaign)
    assert not list((root / 'artifacts').iterdir())
    save(audit, dict(audit_valid=True, map='urban_blocks_u01'))
    native = scratch / (stem + '.json')
    save(native, dict(success=True))
    result = child.copy_supplemental_artifacts(root, 'urban_blocks_u01', 7, 'full', campaign)
    assert result['audit_valid'] and Path(result['artifact_path']).is_file()
    assert (root / 'artifacts' / native.name).read_bytes() == native.read_bytes()
    with pytest.raises(RuntimeError, match='overwrite refused'):
        child.copy_supplemental_artifacts(root, 'urban_blocks_u01', 7, 'full', campaign)
    child.preserve_supplemental_artifacts(root, campaign)
    assert all(row['state'] == 'ALREADY_PRESERVED' for row in
               json.loads((root / 'supplemental_preservation.json').read_text())['files'])
    trace.write_text('new partial observations\n')
    child.preserve_supplemental_artifacts(root, campaign)
    assert (root / 'artifacts' / trace.name).read_text() == 'partial observations\n'
    assert trace.read_text() == 'new partial observations\n'
    records = json.loads((root / 'supplemental_preservation.json').read_text())['files']
    assert any(row['state'] == 'PRESERVED_IN_SCRATCH' for row in records)


def test_partial_odometry_preserved_without_audit(tmp_path):
    scratch = tmp_path / 'scratch'
    scratch.mkdir()
    trace = scratch / 'forest_cluster_f01_run8_adaptive.attempt1.odometry.csv'
    trace.write_text('partial\n')
    root = tmp_path / 'out'
    child.preserve_supplemental_artifacts(root, SimpleNamespace(TMPDIR=str(scratch)))
    assert (root / 'artifacts' / trace.name).read_text() == 'partial\n'
    assert trace.exists()
