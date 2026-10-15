#!/usr/bin/env python3
"""Visualize v2 waypoint feedback without installing missions or running ROS.

The unchanged map solids and deterministic offline connectivity checks are the
only inputs to proposal validation. A witness is not a flight-qualified path.
Run with PYTHONNOUSERSITE=1 to use the system Matplotlib/NumPy combination.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import gen_scenario7_maps as geometry
import plot_scenario7_waypoint_proposal as plotting
from matplotlib.lines import Line2D
from matplotlib.text import Annotation


DEFAULT_OUTPUT = Path('/root/share/scenario7_waypoint_proposal_v2_20260924')
WAYPOINTS = (
    ((0, 0), (-13, 13), (13, 13), (-13, -13), (13, -13), (0, 0)),
    ((0, 0), (-24, 22), (24, 22), (-24, -22), (24, -22), (0, 0)),
)
TITLES = ('URBAN: block-crossing zigzag', 'FOREST: wider-spaced zigzag')


def leg_lengths(points):
    return [math.dist(a, b) for a, b in zip(points, points[1:])]


def validate_proposal(document, points):
    geometry.validate_geometry(document)
    previous = geometry.LOOP_WAYPOINTS
    try:
        geometry.LOOP_WAYPOINTS = tuple(points)
        routes = geometry.offline_routes(document)
        audit = geometry.route_audit(document, routes)
    finally:
        geometry.LOOP_WAYPOINTS = previous
    margins = []
    for point in points:
        distances = [geometry.point_box_distance(point, box) for box in document['boxes']]
        distances += [max(0., math.dist(point, (c['x'], c['y']))-c['r'])
                      for c in document['cylinders']]
        margins.append(min(distances)-geometry.BODY_RADIUS_M)
    if min(margins) < 1.:
        raise ValueError('Proposal endpoint body clearance is below 1 m')
    return dict(endpoint_body_clearances_m=margins, geometric_audit=audit,
                geometric_witness_xy=routes,
                witness_is_not_supplied_to_planner=True)


def draw(ax, proposal, document):
    previous_reference = plotting.OLD_LOOP
    try:
        plotting.OLD_LOOP = proposal['previous_proposal_points_xy']
        plotting.draw_map(ax, proposal, document)
    finally:
        plotting.OLD_LOOP = previous_reference
    for text in ax.texts:
        if isinstance(text, Annotation) and text.get_text():
            # Wider goals remain inside the axes; keep their labels inside too.
            if text.xy[0] >= 16:
                _, y = text.get_position()
                text.set_position((-8, y))
                text.set_horizontalalignment('right')
        elif text.get_text().startswith('Nominal connector length:'):
            lengths = proposal['leg_lengths_m']
            text.set_text(f'Leg spacing: {min(lengths):.1f}-{max(lengths):.1f} m | '
                          f'Nominal total: {sum(lengths):.1f} m | z = 1.5 m')


def finish(fig, output):
    fig.suptitle('Waypoint proposal v2 - urban zigzag and wider forest spacing',
                 y=.98, fontsize=16, weight='bold', color=plotting.INK)
    handles = [
        Line2D([0], [0], color=plotting.BLUE, linestyle='--', lw=2,
               label='New waypoint order (v2; not a flight path)'),
        Line2D([0], [0], color='#aeb5bd', linestyle=':', lw=1.5,
               label='Previous waypoint proposal (v1)'),
        Line2D([0], [0], color='#d99514', marker='*', linestyle='None',
               markersize=11, label='Start / finish'),
    ]
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5, .055),
               ncol=1 if len(fig.axes) == 1 else 3, fontsize=9,
               frameon=False, labelcolor=plotting.INK)
    fig.text(.5, .022,
             'PROPOSAL ONLY - not installed, not flown. Dashed lines may cross obstacles; the planner must avoid them.',
             ha='center', fontsize=8.7, color='#8b3e30')
    fig.savefig(output, dpi=190, facecolor='white')
    plotting.plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if output.exists():
        parser.error('Existing output refused; previous images are preserved')
    records, documents = [], []
    for index, original in enumerate(plotting.PROPOSALS):
        path = plotting.PACKAGE / 'pcd/seed_maps' / (original['map']+'_geometry.json')
        content = path.read_bytes()
        document = json.loads(content)
        if document['map'] != original['map']:
            raise ValueError('Geometry identity mismatch')
        points = WAYPOINTS[index]
        lengths, previous_lengths = leg_lengths(points), leg_lengths(original['points'])
        if index == 1 and not all(new > old for new, old in zip(lengths, previous_lengths)):
            raise ValueError('Every forest leg must be longer than the corresponding v1 leg')
        record = dict(original, title=TITLES[index], points=points,
                      order='S -> 1 -> 2 -> 3 -> 4 -> 5 (= S)',
                      previous_proposal_points_xy=original['points'],
                      previous_leg_lengths_m=previous_lengths, leg_lengths_m=lengths,
                      nominal_connector_length_m=sum(lengths),
                      geometry=str(path), geometry_sha256=hashlib.sha256(content).hexdigest(),
                      validation=validate_proposal(document, points))
        records.append(record)
        documents.append(document)
    output.mkdir(parents=True, exist_ok=False)
    for record, document in zip(records, documents):
        fig, ax = plotting.plt.subplots(figsize=(10, 11))
        fig.subplots_adjust(left=.08, right=.94, bottom=.24, top=.87)
        draw(ax, record, document)
        finish(fig, output/record['filename'])
    fig, axes = plotting.plt.subplots(1, 2, figsize=(17, 10))
    fig.subplots_adjust(left=.055, right=.98, wspace=.16, bottom=.21, top=.86)
    for ax, record, document in zip(axes, records, documents):
        draw(ax, record, document)
    finish(fig, output/'urban_forest_waypoint_proposal.png')
    metadata = dict(schema='scenario7-waypoint-plot-proposal-v2',
                    mission_files_changed=False, planner_changed=False, map_assets_changed=False,
                    flight_runs=0, proposed_flight_z_m=1.5,
                    lines='Waypoint visit-order connectors only, not safe paths or observed trajectories',
                    proposals=records)
    (output/'waypoint_proposals.json').write_text(json.dumps(metadata, indent=2)+'\n')
    for path in sorted(output.glob('*.png')):
        print(path)


if __name__ == '__main__':
    main()
