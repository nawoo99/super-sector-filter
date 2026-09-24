#!/usr/bin/env python3
"""Select a frozen mission without modifying legacy flight code or policy.

An isolated native run_one function inherits every argument and conditional.
Only its default waypoint TXT is substituted; a private LOOP_WPS binding feeds
the same mission to the existing monitor. Launch and deferred mission startup
already share waypoint_data_name in the pinned source.
"""
from __future__ import annotations

import ast
import inspect
import math
from pathlib import Path
import re

import scenario7_campaign_support as support

CAMPAIGN_SHA256 = '867b071cf54bbd77eff79251ca2252c8a650310a7b331ff9825bf5890731ef30'
MISSION_MODULE = support.PACKAGE / 'scripts/scenario7_missions.py'
EXPECTED_MISSIONS = {name: 'loop24' for name in support.ORIGINAL_MAPS}
EXPECTED_MISSIONS.update(urban_blocks_u01='urban_building_corners_v3',
                         forest_cluster_f01='forest_wide_zigzag_v2')
RUN_ONE_REPLACEMENTS = ((
    '                waypoint_data_name = "loop24.txt"',
    '                waypoint_data_name = SCENARIO7_MISSION["mission_file_basename"]',
),)


def validate_context(context):
    if not isinstance(context, dict):
        raise ValueError('Mission context must be a mapping')
    name, mission = context.get('map'), context.get('mission')
    if name not in EXPECTED_MISSIONS or mission != EXPECTED_MISSIONS[name]:
        raise ValueError('Unexpected map/mission identity')
    filename = context.get('mission_file_basename')
    if filename != mission + '.txt' or not re.fullmatch('[a-z0-9_]+\\.txt', filename):
        raise ValueError('Invalid mission filename')
    goals = context.get('waypoints_xyz')
    if (not isinstance(goals, list) or len(goals) != 5 or context.get('goal_count') != len(goals)
            or any(not isinstance(row, list) or len(row) != 3 for row in goals)
            or any(type(x) not in (int, float) or not math.isfinite(x) for row in goals for x in row)
            or any(row[2] != 1.5 for row in goals)
            or context.get('initial_position_xyz') != [0, 0, 1.5]
            or context.get('switch_distance_m') != 1.5):
        raise ValueError('Invalid fixed-height mission goals or switch distance')
    expected_wps = ';'.join(','.join(f'{x:g}' for x in row[:2]) for row in goals)
    if context.get('wps') != expected_wps:
        raise ValueError('Monitor XY waypoints do not match mission goals')
    path = Path(context.get('mission_file', ''))
    if path.name != filename or support.sha256(path) != context.get('mission_sha256'):
        raise ValueError('Selected mission TXT changed')
    rows = [[float(x) for x in line.split()] for line in path.read_text().splitlines() if line.strip()]
    if rows != [row + [context['switch_distance_m']] for row in goals]:
        raise ValueError('Mission TXT and monitor goals disagree')
    return context


def mission_context(map_name):
    from scenario7_missions import mission_context as load
    return validate_context(load(map_name))


def mission_binding(context):
    """Stable JSON metadata compared between ON preflight and OFF repetitions."""
    validate_context(context)
    return {key: context[key] for key in (
        'map', 'mission', 'mission_file_basename', 'mission_file', 'mission_sha256',
        'registry_path', 'registry_sha256', 'wps', 'waypoints_xyz', 'initial_position_xyz',
        'goal_count', 'switch_distance_m')}


def asset_paths(context):
    validate_context(context)
    for path, expected in context['assets_sha256'].items():
        if support.sha256(path) != expected:
            raise ValueError('Mission asset changed: ' + path)
    registry = Path(context['registry_path'])
    if support.sha256(registry) != context['registry_sha256']:
        raise ValueError('Mission registry changed')
    return {Path(__file__).resolve(), MISSION_MODULE, registry,
            *(Path(path) for path in context['assets_sha256']), Path(context['mission_file'])}


def adapted_run_one_source(campaign):
    path = Path(campaign.__file__).resolve()
    if support.sha256(path) != CAMPAIGN_SHA256:
        raise ValueError('Frozen native campaign changed; review mission adapter')
    source = path.read_text()
    definitions = [node for node in ast.parse(source).body
                   if isinstance(node, ast.FunctionDef) and node.name == 'run_one']
    if len(definitions) != 1:
        raise ValueError('Expected one native run_one function')
    selected = ast.get_source_segment(source, definitions[0])
    for old, new in RUN_ONE_REPLACEMENTS:
        if selected.count(old) != 1:
            raise ValueError('Native mission substitution cardinality changed')
        selected = selected.replace(old, new, 1)
    return selected


def build_run_one(campaign, context):
    validate_context(context)
    namespace = dict(vars(campaign))
    namespace.update(LOOP_WPS=context['wps'], SCENARIO7_MISSION=context)
    exec(compile(adapted_run_one_source(campaign), str(Path(__file__).resolve()), 'exec'), namespace)
    return namespace['run_one']


def run_one(campaign, context, *args, **kwargs):
    bound = inspect.signature(campaign.run_one).bind(*args, **kwargs)
    if bound.arguments['map_name'] != context.get('map'):
        raise ValueError('Flight map differs from selected mission')
    # A fresh namespace takes the current scratch directory/monitor binding;
    # legacy campaign globals and helpers remain unchanged.
    return build_run_one(campaign, context)(*args, **kwargs)
