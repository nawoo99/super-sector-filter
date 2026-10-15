#!/usr/bin/env python3
"""Show user-numbered building-corner targets; keep all flight settings unchanged.

Building labels B1..B16 run left-to-right, top-to-bottom in the picture. They
are not the existing geometry IDs, which are deliberately left unchanged.
"""
import argparse
import hashlib
import json
from pathlib import Path

import plot_scenario7_waypoint_proposal_v2 as previous
from matplotlib.lines import Line2D
from matplotlib.text import Annotation

plotting = previous.plotting
DEFAULT_OUTPUT = Path('/root/share/scenario7_waypoint_proposal_v3_20260924')
CORNER_OFFSET_M = 2.
REQUESTS = ((1, 'upper_left', -1, 1), (8, 'upper_right', 1, 1),
            (9, 'lower_left', -1, -1), (16, 'lower_right', 1, -1))


def requested_urban_points(document):
    buildings = sorted(document['boxes'], key=lambda box: (-box['cy'], box['cx']))
    if len(buildings) != 16 or document['cylinders']:
        raise ValueError('Expected the unchanged sixteen-building urban map')
    labels = [dict(display_number=i, geometry_id=b['id'], cx=b['cx'], cy=b['cy'])
              for i, b in enumerate(buildings, 1)]
    points, bindings = [(0., 0.)], []
    for index, (number, corner, sx, sy) in enumerate(REQUESTS, 1):
        box = buildings[number-1]
        corner_xy = (box['cx']+sx*box['size_x']/2, box['cy']+sy*box['size_y']/2)
        point = (corner_xy[0]+sx*CORNER_OFFSET_M, corner_xy[1]+sy*CORNER_OFFSET_M)
        points.append(point)
        bindings.append(dict(waypoint=index, building_display_number=number,
                             geometry_id=box['id'], requested_corner=corner,
                             physical_corner_xy=corner_xy,
                             outward_axis_offset_m=CORNER_OFFSET_M, waypoint_xy=point))
    points.append((0., 0.))
    return tuple(points), labels, bindings


def draw(ax, proposal, document):
    previous.draw(ax, proposal, document)
    for text in ax.texts:
        if isinstance(text, Annotation) and text.get_text():
            label = text.get_text()
            if label.startswith('S / 5'):
                text.set_text(label.replace('S / 5', 'S / F', 1))
            elif label[0].isdigit():
                text.set_text('WP'+label)
    for building in proposal.get('building_display_labels', []):
        ax.text(building['cx'], building['cy'], f"B{building['display_number']}",
                ha='center', va='center', color='white', weight='bold',
                fontsize=11, zorder=5)


def finish(fig, output):
    fig.suptitle('Waypoint proposal v3 - requested urban building corners',
                 y=.98, fontsize=16, weight='bold', color=plotting.INK)
    handles = [
        Line2D([0], [0], color=plotting.BLUE, linestyle='--', lw=2,
               label='Waypoint order (not a flight path)'),
        Line2D([0], [0], color='#aeb5bd', linestyle=':', lw=1.5,
               label='Previous proposal (v2)'),
        Line2D([0], [0], color='#d99514', marker='*', linestyle='None',
               markersize=11, label='Start / finish'),
    ]
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5, .057),
               ncol=1 if len(fig.axes) == 1 else 3, fontsize=9,
               frameon=False, labelcolor=plotting.INK)
    fig.text(.5, .032, 'Urban: B1-B16 are numbered left-to-right, top-to-bottom; goals are 2 m outward in each corner axis.',
             ha='center', fontsize=8.5, color=plotting.INK)
    fig.text(.5, .013, 'PROPOSAL ONLY - not installed, not flown. Dashed lines show visit order; obstacle avoidance is left to the planner.',
             ha='center', fontsize=8.5, color='#8b3e30')
    fig.savefig(output, dpi=190, facecolor='white')
    plotting.plt.close(fig)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if output.exists():
        parser.error('Existing output refused; previous proposal images are preserved')
    records, documents = [], []
    for index, original in enumerate(plotting.PROPOSALS):
        path = plotting.PACKAGE / 'pcd/seed_maps' / (original['map']+'_geometry.json')
        content = path.read_bytes()
        document = json.loads(content)
        if document['map'] != original['map']:
            raise ValueError('Geometry identity mismatch')
        if index == 0:
            points, labels, bindings = requested_urban_points(document)
            title = 'URBAN: B1 upper-left -> B8 upper-right -> B9 lower-left -> B16 lower-right'
        else:
            points, labels, bindings = previous.WAYPOINTS[index], [], []
            title = 'FOREST: wider-spaced zigzag (unchanged from v2)'
        lengths = previous.leg_lengths(points)
        record = dict(original, title=title, points=points,
                      order='S -> WP1 -> WP2 -> WP3 -> WP4 -> S',
                      previous_proposal_points_xy=previous.WAYPOINTS[index],
                      previous_leg_lengths_m=previous.leg_lengths(previous.WAYPOINTS[index]),
                      leg_lengths_m=lengths, nominal_connector_length_m=sum(lengths),
                      building_display_labels=labels, requested_building_corners=bindings,
                      geometry=str(path), geometry_sha256=hashlib.sha256(content).hexdigest(),
                      validation=previous.validate_proposal(document, points))
        records.append(record)
        documents.append(document)
    output.mkdir(parents=True, exist_ok=False)
    for record, document in zip(records, documents):
        fig, ax = plotting.plt.subplots(figsize=(11, 11))
        fig.subplots_adjust(left=.08, right=.94, bottom=.24, top=.87)
        draw(ax, record, document)
        finish(fig, output/record['filename'])
    fig, axes = plotting.plt.subplots(1, 2, figsize=(18, 10))
    fig.subplots_adjust(left=.055, right=.98, wspace=.16, bottom=.21, top=.86)
    for ax, record, document in zip(axes, records, documents):
        draw(ax, record, document)
    finish(fig, output/'urban_forest_waypoint_proposal.png')
    metadata = dict(schema='scenario7-waypoint-plot-proposal-v3',
                    mission_files_changed=False, planner_changed=False, map_assets_changed=False,
                    flight_runs=0, proposed_flight_z_m=1.5,
                    building_display_numbering='Rows from top to bottom; each row left to right; 1..16',
                    geometry_building_ids_unchanged=True, forest_waypoints_unchanged_from_v2=True,
                    lines='Visit-order connectors only, not collision-free paths or observed trajectories',
                    proposals=records)
    (output/'waypoint_proposals.json').write_text(json.dumps(metadata, indent=2)+'\n')
    for path in sorted(output.glob('*.png')):
        print(path)


if __name__ == '__main__':
    main()
