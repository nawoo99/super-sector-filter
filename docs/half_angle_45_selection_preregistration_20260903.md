# Selection and confirmatory-use record for the 45-degree half-angle

Date frozen: 2026-09-03 (Asia/Seoul)

## Decision

The next controlled side-entry topology experiment will use a common nominal
half-angle of 45 degrees for Sector and Adaptive. Full remains the unfiltered
360-degree reference. The angle is now frozen before the side-entry topology
flight results are observed.

## Why 45 degrees was selected

The 2026-09-02 60/45/30-degree campaign was exploratory. It did not produce a
completion or collision difference: Sector and Adaptive both completed 27/27
without a static-PCD collision. The angle is therefore not selected because it
already demonstrated a safety-rate advantage.

Forty-five degrees provided the most informative balance among the secondary
screening metrics:

- Sector produced two of nine descriptive low-clearance rows below 0.20 m,
  whereas Adaptive produced zero; the worst-clearance difference favored
  Adaptive by 0.053 m, the largest of the three angles.
- Adaptive reduced mean mission time by 5.450% relative to Sector, also the
  largest of the three angles.
- Adaptive reduced measured DDS rate by 21.313%, retaining a material
  communication difference.
- Sixty degrees had a larger DDS reduction (25.852%) but no low-clearance
  separation. Thirty degrees had a smaller DDS reduction (15.133%), did not
  improve the primary outcome and increased both algorithm and end-to-end
  core-seconds relative to Sector in this screen.

Thus 45 degrees is an operating-point choice based on margin, time and
communication balance, not a post-hoc claim of improved completion or collision
rate.

## Evidence separation

The 54 rows used to choose the angle remain exploratory and must not be pooled
into the confirmatory side-entry result. Only flights run after the topology,
code, profiles, metrics and stopping rule are frozen may be labelled
confirmatory.

The primary outcomes remain:

1. mission completion;
2. source-static-PCD collision occurrence.

Secondary outcomes are static-PCD clearance, mission time, DDS cloud plus
verdict rate, ROG compute, algorithm and end-to-end CPU, and Adaptive transition
counts. A 0.20 m clearance cutoff is descriptive and is not a collision label.

## Next experiment boundary

The side-entry topology will be a deterministic relative-geometry overlay on
the existing Map7/Map9/Map10 loop, not a new random-map generalization study.
One identical placement rule will be applied without per-map outcome tuning.
The rule and its offline visibility/passability checks must be appended here
before any topology flight is run. If the rule changes after a flight, it
becomes a new explicitly versioned exploratory topology; failed rows are never
deleted or relabelled.

Initial screening will use one Full/Sector/Adaptive run on Map7, followed by a
rotating Map7/Map9/Map10 n=3 campaign only if the geometry and runtime gates
pass. The per-call optimizer phase trace will be disabled for performance
comparisons; cgroup and ordinary memory accounting remain enabled. OOM
reproduction is a separate diagnostic experiment.

## Source exploratory evidence

- `docs/half_angle_operating_envelope_20260902.md`
- `results/half_angle_sweep_maps7_9_10_sector_adaptive_n3_summary_20260902.csv`
- `results/half_angle_sweep_maps7_9_10_sector_adaptive_n3_reductions_20260902.csv`
