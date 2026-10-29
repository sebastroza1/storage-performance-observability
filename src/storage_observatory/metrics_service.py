from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from prometheus_client import CollectorRegistry, Gauge, start_http_server


def build_registry(results: dict[str, Any]) -> CollectorRegistry:
    registry = CollectorRegistry()
    labels = ["workload", "operation", "access", "concurrency"]
    requests = Gauge("storage_benchmark_requests_total", "Observed block operations", labels, registry=registry)
    successes = Gauge("storage_benchmark_successes_total", "Successful block operations", labels, registry=registry)
    failures = Gauge("storage_benchmark_failures_total", "Failed block operations", labels, registry=registry)
    throughput = Gauge("storage_benchmark_throughput_mib_per_second", "Observed throughput", labels, registry=registry)
    iops = Gauge("storage_benchmark_operations_per_second", "Observed operations per second", labels, registry=registry)
    error_rate = Gauge("storage_benchmark_error_ratio", "Observed error ratio", labels, registry=registry)
    availability = Gauge("storage_benchmark_availability_ratio", "Observed success ratio", labels, registry=registry)
    latency = Gauge("storage_benchmark_latency_milliseconds", "Observed block latency quantile",
                    labels + ["quantile"], registry=registry)
    health = Gauge("storage_benchmark_results_healthy", "One when result data loaded and all cases succeeded",
                   registry=registry)
    for case in results["cases"]:
        values = [case["name"], case["operation"], case["access"], str(case["concurrency"])]
        requests.labels(*values).set(case["requests_total"])
        successes.labels(*values).set(case["successes"])
        failures.labels(*values).set(case["failures"])
        throughput.labels(*values).set(case["throughput_mib_s"])
        iops.labels(*values).set(case["operations_per_second"])
        error_rate.labels(*values).set(case["error_rate"])
        availability.labels(*values).set(case["availability_observed"])
        for quantile in ("p50", "p95", "p99"):
            latency.labels(*values, quantile).set(case[f"latency_ms_{quantile}"])
    health.set(1 if results["summary"]["failures"] == 0 else 0)
    return registry


def load_results(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or not isinstance(data.get("cases"), list):
        raise ValueError("unsupported result schema")
    return data


def main() -> int:
    parser = argparse.ArgumentParser(description="Expose benchmark evidence to Prometheus")
    parser.add_argument("--results", type=Path, default=Path("reports/results.json"))
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        raise ValueError("port must be between 1024 and 65535")
    registry = build_registry(load_results(args.results))
    server, thread = start_http_server(args.port, registry=registry)
    print(f"metrics listening on 0.0.0.0:{args.port}", flush=True)
    try:
        thread.join()
    except KeyboardInterrupt:
        server.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

