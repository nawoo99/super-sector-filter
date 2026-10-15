#!/usr/bin/env python3
"""Plot the discussed waypoint proposals; never install missions or run flights.

Use system Python with PYTHONNOUSERSITE=1 for the installed Matplotlib/NumPy pair.
All obstacle positions come from the original scenario geometry files. Dashed
connectors encode visit order, not a collision-free route or measured trajectory.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, Rectangle


PACKAGE = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path('/root/share/scenario7_waypoint_proposal_20260924')
OLD_LOOP = ((0, 0), (24, 24), (-24, 24), (-24, -24), (24, -24), (0, 0))
PROPOSALS = (
    dict(map='urban_blocks_u01', label='U1', title='URBAN: internal-street loop',
         subtitle='16 buildings | 6 x 8 m footprint | height 6 m',
         filename='urban_waypoint_proposal.png',
         points=((0, 0), (13, 0), (13, 13), (-13, 13), (-13, -13),
                 (13, -13), (13, 0), (0, 0)),
         order='S -> 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 (= S)'),
    dict(map='forest_cluster_f01', label='F1', title='FOREST: interior zigzag',
         subtitle='410 trunks | diameter 1 m | height 4 m',
         filename='forest_waypoint_proposal.png',
         points=((0, 0), (-12, 12), (15, 13.5), (-16.5, -14),
                 (19.5, -16), (0, 0)),
         order='S -> 1 -> 2 -> 3 -> 4 -> 5 (= S)'),
)
BLUE = '#0876c9'
INK = '#233447'


def nominal_length(points):
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def draw_map(ax, proposal, document):
    for box in document['boxes']:
        ax.add_patch(Rectangle((box['cx']-box['size_x']/2,
                                box['cy']-box['size_y']/2),
                               box['size_x'], box['size_y'],
                               facecolor='#6c7a8a', edgecolor='#4e5f72', lw=.6))
    for trunk in document['cylinders']:
        color = '#438253' if trunk.get('role') != 'background' else '#a4b9a7'
        ax.add_patch(Circle((trunk['x'], trunk['y']), trunk['r'],
                            facecolor=color, edgecolor='none'))
    ax.plot(*zip(*OLD_LOOP), color='#aeb5bd', linestyle=':', lw=1.5,
            alpha=.8, zorder=2)
    points = proposal['points']
    ax.plot(*zip(*points), color=BLUE, linestyle='--', lw=2.0, alpha=.88, zorder=3)
    for start, end in zip(points, points[1:]):
        # Distinct locations make the two opposite directions on the shared
        # urban S--1/6 segment legible without moving any waypoint or segment.
        a = tuple(x+.28*(y-x) for x, y in zip(start, end))
        b = tuple(x+.42*(y-x) for x, y in zip(start, end))
        ax.annotate('', xy=b, xytext=a, zorder=4,
                    arrowprops=dict(arrowstyle='-|>', color=BLUE, lw=1.7,
                                    mutation_scale=14))
    visits = {}
    for index, point in enumerate(points):
        visits.setdefault(point, []).append('S' if index == 0 else str(index))
    for point, labels in visits.items():
        start = point == points[0]
        ax.scatter(*point, s=200 if start else 85, marker='*' if start else 'o',
                   color='#d99514' if start else BLUE, edgecolors='white',
                   linewidths=1.3, zorder=6)
        label = ' / '.join(labels) + f'  ({point[0]:g}, {point[1]:g})'
        # Labels are callouts, not additional coordinates or targets.
        ax.annotate(label, point, xytext=(8, 9 if point[1] >= 0 else -18),
                    textcoords='offset points', color=INK, fontsize=9,
                    weight='bold', zorder=7,
                    bbox=dict(boxstyle='round,pad=.22', fc='white',
                              ec='#ccd5df', alpha=.94, lw=.6))
    ax.set(xlim=(-32, 32), ylim=(-32, 32), aspect='equal',
           xlabel='x (m)', ylabel='y (m)')
    ax.set_xticks(range(-30, 31, 10))
    ax.set_yticks(range(-30, 31, 10))
    ax.tick_params(labelsize=9, colors=INK)
    ax.grid(alpha=.15, zorder=0)
    ax.set_axisbelow(True)
    ax.set_facecolor('#fafcfe')
    for spine in ax.spines.values():
        spine.set_color('#a9b8c7')
    ax.set_title(proposal['title']+'\n'+proposal['subtitle'],
                 fontsize=13, color=INK, pad=15)
    ax.text(.5, -.12, proposal['order'], ha='center', va='top',
            transform=ax.transAxes, fontsize=10, weight='bold', color=INK)
    ax.text(.5, -.165,
            f"Nominal connector length: {nominal_length(points):.1f} m | z = 1.5 m",
            ha='center', va='top', transform=ax.transAxes, fontsize=9, color=INK)


def finish_figure(fig, title, path):
    fig.suptitle(title, y=.98, fontsize=17, weight='bold', color=INK)
    handles = [
        Line2D([0], [0], color=BLUE, linestyle='--', lw=2,
               label='Proposed waypoint order (not a flight path)'),
        Line2D([0], [0], color='#aeb5bd', linestyle=':', lw=1.5,
               label='Previous loop24'),
        Line2D([0], [0], color='#d99514', marker='*', linestyle='None',
               markersize=11, label='Start / finish'),
    ]
    fig.legend(handles=handles, loc='lower center', bbox_to_anchor=(.5, .055),
               ncol=1 if len(fig.axes) == 1 else 3, fontsize=9,
               frameon=False, labelcolor=INK)
    fig.text(.5, .022,
             'PROPOSAL ONLY - not installed, not flown. Dashed lines may cross obstacles; the planner must avoid them.',
             ha='center', fontsize=8.7, color='#8b3e30')
    fig.savefig(path, dpi=190, facecolor='white')
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    records = []
    documents = []
    for proposal in PROPOSALS:
        path = PACKAGE / 'pcd/seed_maps' / (proposal['map']+'_geometry.json')
        content = path.read_bytes()
        doc = json.loads(content)
        if doc['map'] != proposal['map']:
            raise ValueError('Geometry identity mismatch')
        documents.append(doc)
        records.append(dict(proposal, geometry=str(path),
                            geometry_sha256=hashlib.sha256(content).hexdigest(),
                            nominal_connector_length_m=nominal_length(proposal['points'])))
        fig, ax = plt.subplots(figsize=(10, 11))
        fig.subplots_adjust(left=.08, right=.94, bottom=.24, top=.87)
        draw_map(ax, proposal, doc)
        finish_figure(fig, 'Proposed mission waypoints', output/proposal['filename'])
    fig, axes = plt.subplots(1, 2, figsize=(17, 10))
    fig.subplots_adjust(left=.055, right=.98, wspace=.16, bottom=.21, top=.86)
    for ax, proposal, doc in zip(axes, PROPOSALS, documents):
        draw_map(ax, proposal, doc)
    finish_figure(fig, 'Urban and forest - proposed mission waypoints',
                  output/'urban_forest_waypoint_proposal.png')
    metadata = dict(schema='scenario7-waypoint-plot-proposal-v1',
                    mission_files_changed=False, planner_changed=False, flight_runs=0,
                    lines='Waypoint visit-order connectors only, not safe paths or observed trajectories',
                    proposed_flight_z_m=1.5, old_loop_xy=OLD_LOOP, proposals=records)
    (output/'waypoint_proposals.json').write_text(json.dumps(metadata, indent=2)+'\n')
    for path in sorted(output.glob('*.png')):
        print(path)


if __name__ == '__main__':
    main()
