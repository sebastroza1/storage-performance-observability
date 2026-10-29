from prometheus_client import generate_latest

from storage_observatory.metrics_service import build_registry


def sample_results(error_rate: float = 0.0) -> dict:
    failures = 1 if error_rate else 0
    return {
        "schema_version": 1,
        "summary": {"requests_total": 10, "successes": 10 - failures, "failures": failures},
        "cases": [{
            "name": "sample", "operation": "read", "access": "sequential", "concurrency": 1,
            "requests_total": 10, "successes": 10 - failures, "failures": failures,
            "throughput_mib_s": 100.0, "operations_per_second": 1000.0,
            "error_rate": error_rate, "availability_observed": 1.0 - error_rate,
            "latency_ms_p50": 1.0, "latency_ms_p95": 2.0, "latency_ms_p99": 3.0,
        }],
    }


def test_prometheus_exposition_contains_required_metrics() -> None:
    text = generate_latest(build_registry(sample_results())).decode()
    assert "storage_benchmark_requests_total" in text
    assert "storage_benchmark_failures_total" in text
    assert 'quantile="p95"' in text
    assert "storage_benchmark_results_healthy 1.0" in text


def test_unhealthy_results_change_health_metric() -> None:
    text = generate_latest(build_registry(sample_results(0.1))).decode()
    assert "storage_benchmark_results_healthy 0.0" in text

