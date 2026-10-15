#!/usr/bin/env python3
"""Task Manager-style plots of recorded whole-host CPU, without new flights.

Example:
  python3 -s scripts/native_campaign/plot_normal_host_cpu.py \
    --output-dir /root/share/here/cpu_gpu_diagnostic_20260916

These are Linux busy-time counters, not Windows processor-utility readings.
Whole-host data include background software and observers, so the differences
are not a controlled estimate of the filter's computational savings.
"""

import argparse
import json
import math
from pathlib import Path
from statistics import mean

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, PercentFormatter


MODES = ("full", "sector", "adaptive")
BLUE = "#0078d4"
GRID = "#cce4f5"
TEXT = "#173b55"


def load_series(input_dir):
    rows = [json.loads(line) for line in
            (input_dir / "telemetry.jsonl").read_text().splitlines() if line.strip()]
    summaries = {r["mode"]: r for r in
                 json.loads((input_dir / "summary.json").read_text())["results"]}
    logical_cpus = json.loads((input_dir / "plan.json").read_text())["logical_cpus"]
    series = {}
    for mode in MODES:
        samples = [r for r in rows if r["mode"] == mode and r["campaign_active"]]
        if len(samples) < 2:
            raise ValueError(f"Insufficient active samples: {mode}")
        times = [r["monotonic_s"] - samples[0]["monotonic_s"] for r in samples]
        values = [r["host_cpu_pct"] for r in samples]
        if not all(math.isfinite(v) and 0 <= v <= 100 for v in values):
            raise ValueError(f"Invalid whole-host CPU percentage: {mode}")
        if not all(a < b for a, b in zip(times, times[1:])):
            raise ValueError(f"Non-increasing timestamps: {mode}")
        expected = summaries[mode]["host_cpu_pct"]
        if (len(values) != expected["n"] or
                not math.isclose(mean(values), expected["mean"], abs_tol=1e-9) or
                not math.isclose(max(values), expected["max"], abs_tol=1e-9)):
            raise ValueError(f"Telemetry does not match saved summary: {mode}")
        series[mode] = (times, values)
    return logical_cpus, series


def draw_panel(ax, mode, times, values, xmax):
    ax.set_title(mode.capitalize(), loc="left", color=TEXT, fontsize=17, pad=14)
    ax.set_xlim(0, xmax)
    ax.set_ylim(0, 100)
    ax.xaxis.set_major_locator(MultipleLocator(10))
    ax.xaxis.set_minor_locator(MultipleLocator(5))
    ax.yaxis.set_major_locator(MultipleLocator(20))
    ax.yaxis.set_minor_locator(MultipleLocator(10))
    ax.yaxis.set_major_formatter(PercentFormatter(xmax=100, decimals=0))
    ax.set_axisbelow(True)
    ax.grid(which="major", color=GRID, linewidth=0.7)
    ax.grid(which="minor", color=GRID, linewidth=0.45)
    ax.fill_between(times, values, 0, color=BLUE, alpha=0.13, linewidth=0)
    ax.plot(times, values, color=BLUE, linewidth=1.15)
    for spine in ax.spines.values():
        spine.set_color(BLUE)
        spine.set_linewidth(0.7)
    ax.tick_params(axis="both", which="both", length=0, labelcolor=TEXT, pad=7)
    ax.set_xlabel("Elapsed time from first active sample (s)", color=TEXT, labelpad=9)
    ax.text(0, -0.29, f"Average  {mean(values):.2f}%", transform=ax.transAxes,
            fontsize=16, color=TEXT)
    ax.text(1, -0.29, f"Peak  {max(values):.2f}%", transform=ax.transAxes,
            ha="right", fontsize=12, color=TEXT)
    ax.text(0, -0.39, f"{len(values)} samples  |  {times[-1]:.1f} s recorded",
            transform=ax.transAxes, fontsize=9, color="#607586")


def make_figure(modes, series, logical_cpus, xmax):
    fig, axes = plt.subplots(1, len(modes), squeeze=False,
                             figsize=(14.8 if len(modes) == 3 else 7.5, 5.5))
    fig.subplots_adjust(left=0.055 if len(modes) == 3 else 0.10,
                        right=0.98, top=0.76, bottom=0.30, wspace=0.23)
    fig.text(0.055, 0.94, "CPU | Whole PC", fontsize=24, color=TEXT)
    fig.text(0.055, 0.87,
             f"Normal R1 / seed1  |  One run per mode  |  {logical_cpus} logical CPUs = 100%",
             fontsize=11, color=TEXT)
    for ax, mode in zip(axes[0], modes):
        draw_panel(ax, mode, *series[mode], xmax)
    fig.text(0.055, 0.085,
             "Includes background applications, simulation and measurement processes.",
             fontsize=9, color="#607586")
    fig.text(0.055, 0.044,
             "Recorded Linux CPU busy time (~1 Hz); no smoothing. Peak = maximum sampled value.",
             fontsize=9, color="#607586")
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", type=Path, default=
                        Path(__file__).resolve().parents[2] /
                        "results/normal_cpu_gpu_diagnostic_20260916")
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    logical_cpus, series = load_series(args.input_dir)
    xmax = math.ceil(max(t[-1] for t, _ in series.values()) / 10) * 10
    args.output_dir.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10,
                         "pdf.fonttype": 42, "figure.facecolor": "white"})
    for modes, name in [(MODES, "cpu_whole_pc_comparison"),
                        *(([mode], f"cpu_whole_pc_{mode}") for mode in MODES)]:
        fig = make_figure(modes, series, logical_cpus, xmax)
        for extension in ("png", "pdf"):
            output = args.output_dir / f"{name}.{extension}"
            fig.savefig(output, dpi=220, facecolor="white")
            print(output)
        plt.close(fig)
    for mode, (times, values) in series.items():
        print(f"Verified {mode}: n={len(values)}, span={times[-1]:.3f}s, "
              f"mean={mean(values):.6f}%, max={max(values):.6f}%")


if __name__ == "__main__":
    main()
