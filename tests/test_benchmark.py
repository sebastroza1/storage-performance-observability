from pathlib import Path

import pytest

from storage_observatory.benchmark import MIB, Workload, percentile, run_case, run_suite


def test_percentile_uses_nearest_rank() -> None:
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.50) == 2.0
    assert percentile([1.0, 2.0, 3.0, 4.0], 0.99) == 4.0
    assert percentile([], 0.95) == 0.0


def test_workload_safety_limits() -> None:
    with pytest.raises(ValueError, match="256 MiB"):
        Workload("too-large", "read", "sequential", 64 * MIB, 4096, 8).validate()
    with pytest.raises(ValueError, match="concurrency"):
        Workload("too-wide", "read", "sequential", MIB, 4096, 9).validate()


@pytest.mark.parametrize("operation", ["read", "write"])
@pytest.mark.parametrize("access", ["sequential", "random"])
def test_tiny_workloads_execute_and_cleanup(tmp_path: Path, operation: str, access: str) -> None:
    workload = Workload(f"{operation}-{access}", operation, access, 64 * 1024, 4096, 2, 16)
    result = run_case(workload, tmp_path)
    assert result["failures"] == 0
    assert result["successes"] > 0
    assert result["throughput_mib_s"] > 0
    assert result["latency_ms_p99"] >= result["latency_ms_p50"]
    assert not (tmp_path / workload.name).exists()


def test_suite_reports_hardware_and_totals(tmp_path: Path) -> None:
    result = run_suite([Workload("tiny", "write", "sequential", 32 * 1024, 4096, 1)], tmp_path)
    assert result["schema_version"] == 1
    assert result["summary"]["failures"] == 0
    assert result["hardware"]["logical_cpu_count"] >= 1

