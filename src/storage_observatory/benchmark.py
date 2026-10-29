from __future__ import annotations

import argparse
import concurrent.futures
import csv
import dataclasses
import json
import math
import os
import platform
import random
import shutil
import statistics
import time
from pathlib import Path
from typing import Any

MIB = 1024 * 1024
MAX_CASE_BYTES = 256 * MIB
MAX_CONCURRENCY = 8


@dataclasses.dataclass(frozen=True)
class Workload:
    name: str
    operation: str
    access: str
    file_size: int
    block_size: int
    concurrency: int
    max_random_ops: int = 2048

    def validate(self) -> None:
        if self.operation not in {"read", "write"}:
            raise ValueError("operation must be read or write")
        if self.access not in {"sequential", "random"}:
            raise ValueError("access must be sequential or random")
        if self.file_size <= 0 or self.block_size <= 0 or self.block_size > self.file_size:
            raise ValueError("invalid file or block size")
        if self.file_size * self.concurrency > MAX_CASE_BYTES:
            raise ValueError("case exceeds 256 MiB safety limit")
        if not 1 <= self.concurrency <= MAX_CONCURRENCY:
            raise ValueError("concurrency must be between 1 and 8")
        if self.max_random_ops <= 0:
            raise ValueError("max_random_ops must be positive")


@dataclasses.dataclass
class WorkerResult:
    latencies_ms: list[float]
    bytes_processed: int
    successes: int
    failures: int


def quick_workloads() -> list[Workload]:
    return [
        Workload("small-seq-write-4k-c1", "write", "sequential", 4 * MIB, 4 * 1024, 1),
        Workload("small-seq-read-4k-c1", "read", "sequential", 4 * MIB, 4 * 1024, 1),
        Workload("medium-seq-write-1m-c1", "write", "sequential", 32 * MIB, MIB, 1),
        Workload("medium-seq-read-1m-c1", "read", "sequential", 32 * MIB, MIB, 1),
        Workload("random-write-4k-c1", "write", "random", 16 * MIB, 4 * 1024, 1),
        Workload("random-read-4k-c1", "read", "random", 16 * MIB, 4 * 1024, 1),
        Workload("random-read-4k-c4", "read", "random", 8 * MIB, 4 * 1024, 4),
        Workload("seq-write-64k-c4", "write", "sequential", 8 * MIB, 64 * 1024, 4),
    ]


def percentile(values: list[float], quantile: float) -> float:
    if not values:
        return 0.0
    if not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile must be between zero and one")
    ordered = sorted(values)
    rank = max(1, math.ceil(quantile * len(ordered)))
    return ordered[rank - 1]


def run_case(workload: Workload, work_root: Path) -> dict[str, Any]:
    workload.validate()
    case_dir = work_root / workload.name
    if case_dir.exists():
        shutil.rmtree(case_dir)
    case_dir.mkdir(parents=True)
    paths = [case_dir / f"worker-{index}.bin" for index in range(workload.concurrency)]
    try:
        if workload.operation == "read" or workload.access == "random":
            for path in paths:
                _create_fixture(path, workload.file_size, workload.block_size)
        started = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=workload.concurrency) as executor:
            futures = [executor.submit(_run_worker, workload, path, index)
                       for index, path in enumerate(paths)]
            workers = [future.result() for future in futures]
        elapsed = time.perf_counter() - started
    finally:
        shutil.rmtree(case_dir, ignore_errors=True)

    latencies = [latency for worker in workers for latency in worker.latencies_ms]
    successes = sum(worker.successes for worker in workers)
    failures = sum(worker.failures for worker in workers)
    total = successes + failures
    processed = sum(worker.bytes_processed for worker in workers)
    return {
        **dataclasses.asdict(workload),
        "elapsed_seconds": round(elapsed, 6),
        "bytes_processed": processed,
        "throughput_mib_s": round((processed / MIB) / elapsed, 3) if elapsed else 0.0,
        "operations_per_second": round(successes / elapsed, 3) if elapsed else 0.0,
        "latency_ms_mean": round(statistics.fmean(latencies), 6) if latencies else 0.0,
        "latency_ms_p50": round(percentile(latencies, 0.50), 6),
        "latency_ms_p95": round(percentile(latencies, 0.95), 6),
        "latency_ms_p99": round(percentile(latencies, 0.99), 6),
        "requests_total": total,
        "successes": successes,
        "failures": failures,
        "error_rate": round(failures / total, 8) if total else 0.0,
        "availability_observed": round(successes / total, 8) if total else 0.0,
        "sync_policy": "flush_and_fsync_once_per_writer",
    }


def _create_fixture(path: Path, size: int, block_size: int) -> None:
    block = _data_block(block_size)
    remaining = size
    with path.open("wb", buffering=0) as output:
        while remaining:
            piece = block[: min(len(block), remaining)]
            output.write(piece)
            remaining -= len(piece)
        os.fsync(output.fileno())


def _data_block(size: int) -> bytes:
    seed = bytes(range(256))
    return (seed * (size // len(seed) + 1))[:size]


def _run_worker(workload: Workload, path: Path, worker_index: int) -> WorkerResult:
    operation_count = (workload.file_size + workload.block_size - 1) // workload.block_size
    if workload.access == "random":
        operation_count = min(operation_count, workload.max_random_ops)
    latencies: list[float] = []
    successes = failures = processed = 0
    mode = "rb" if workload.operation == "read" else ("r+b" if workload.access == "random" else "wb")
    try:
        with path.open(mode, buffering=0) as stream:
            rng = random.Random(0xC0FFEE + worker_index)
            block = _data_block(workload.block_size)
            block_slots = max(1, workload.file_size // workload.block_size)
            for index in range(operation_count):
                offset = index * workload.block_size
                if workload.access == "random":
                    offset = rng.randrange(block_slots) * workload.block_size
                    stream.seek(offset)
                count = min(workload.block_size, workload.file_size - offset)
                started = time.perf_counter_ns()
                try:
                    if workload.operation == "read":
                        data = stream.read(count)
                        if len(data) != count:
                            raise OSError(f"short read: expected {count}, received {len(data)}")
                    else:
                        written = stream.write(block[:count])
                        if written != count:
                            raise OSError(f"short write: expected {count}, wrote {written}")
                    latencies.append((time.perf_counter_ns() - started) / 1_000_000.0)
                    successes += 1
                    processed += count
                except OSError:
                    failures += 1
            if workload.operation == "write":
                stream.flush()
                os.fsync(stream.fileno())
    except OSError:
        failures += operation_count
    return WorkerResult(latencies, processed, successes, failures)


def hardware_report(path: Path) -> dict[str, Any]:
    usage = shutil.disk_usage(path)
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "processor": platform.processor() or "not reported",
        "logical_cpu_count": os.cpu_count(),
        "workdir_filesystem_path": str(path.resolve()),
        "disk_total_bytes": usage.total,
        "disk_free_bytes_before": usage.free,
        "timer": "time.perf_counter_ns",
    }


def run_suite(workloads: list[Workload], work_root: Path) -> dict[str, Any]:
    work_root.mkdir(parents=True, exist_ok=True)
    started_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    hardware = hardware_report(work_root)
    results = [run_case(workload, work_root) for workload in workloads]
    hardware["disk_free_bytes_after"] = shutil.disk_usage(work_root).free
    return {
        "schema_version": 1,
        "started_at_utc": started_at,
        "method": "python-unbuffered-file-io",
        "hardware": hardware,
        "cases": results,
        "summary": {
            "requests_total": sum(case["requests_total"] for case in results),
            "successes": sum(case["successes"] for case in results),
            "failures": sum(case["failures"] for case in results),
        },
    }


def write_results(results: dict[str, Any], json_path: Path, csv_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    cases = results["cases"]
    with csv_path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=list(cases[0].keys()))
        writer.writeheader()
        writer.writerows(cases)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded local storage workloads")
    parser.add_argument("--workdir", type=Path, default=Path("artifacts/benchmark"))
    parser.add_argument("--json", type=Path, default=Path("reports/results.json"))
    parser.add_argument("--csv", type=Path, default=Path("reports/results.csv"))
    args = parser.parse_args()
    results = run_suite(quick_workloads(), args.workdir)
    write_results(results, args.json, args.csv)
    print(json.dumps(results["summary"], indent=2))
    return 0 if results["summary"]["failures"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())

