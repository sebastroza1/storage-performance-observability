from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def plot(results_path: Path, output_path: Path) -> None:
    data = json.loads(results_path.read_text(encoding="utf-8"))
    cases = data["cases"]
    names = [case["name"] for case in cases]
    throughput = [case["throughput_mib_s"] for case in cases]
    p95 = [case["latency_ms_p95"] for case in cases]
    figure, axes = plt.subplots(2, 1, figsize=(11, 8), constrained_layout=True)
    axes[0].barh(names, throughput, color="#2c7fb8")
    axes[0].set_xlabel("Observed throughput (MiB/s)")
    axes[0].set_title("Bounded local storage workload throughput")
    axes[0].grid(axis="x", alpha=0.25)
    axes[1].barh(names, p95, color="#f28e2b")
    axes[1].set_xlabel("Observed block-operation p95 latency (ms)")
    axes[1].set_title("Tail latency by workload")
    axes[1].grid(axis="x", alpha=0.25)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(output_path, dpi=150)
    plt.close(figure)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, default=Path("reports/results.json"))
    parser.add_argument("--output", type=Path, default=Path("reports/benchmark.png"))
    args = parser.parse_args()
    plot(args.results, args.output)
    print(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

