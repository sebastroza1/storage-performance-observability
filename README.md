# Storage Performance & Observability

A bounded, reproducible storage experiment that measures sequential and random
reads/writes across file sizes, block sizes, and concurrency levels, then exports
the observed results as JSON, CSV, a chart, and Prometheus metrics.

This repository emphasizes evidence over dashboards: the benchmark records every
successful and failed block operation, throughput, operations per second, error
ratio, observed availability, and mean/p50/p95/p99 latency. The fixture lifecycle
is constrained to an explicit ignored work directory.

## Quick start

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements-dev.txt
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python -m pytest
.\.venv\Scripts\python -m storage_observatory.benchmark
.\.venv\Scripts\python -m storage_observatory.plot_results
```

Linux uses the same module commands after `source .venv/bin/activate` and
`export PYTHONPATH="$PWD/src"`.

Outputs:

- `reports/results.json`: schema-versioned results and host context.
- `reports/results.csv`: one flat record per workload.
- `reports/benchmark.png`: throughput and p95-latency comparison.
- `reports/RESULTS.md`: interpretation of the executed run.
- `reports/METHODOLOGY.md`: controls, calculations, and validity limits.

## Workload safety

The quick profile creates only named temporary fixtures under `artifacts/benchmark`.
A case cannot exceed 256 MiB across workers, concurrency cannot exceed eight, and
random operations are capped. Each case removes fixtures even when it fails. The
tool does not access raw devices or production paths by default.

## Prometheus

After generating `reports/results.json`:

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python -m storage_observatory.metrics_service --port 8000
```

Metrics include requests, successes, failures, throughput, operations per second,
error ratio, observed availability, health, and latency quantiles. The included
Prometheus configuration defines high-error-rate and high-p95-latency alerts.

```bash
docker compose up --build
```

The metrics endpoint binds to loopback port 8000 and Prometheus to loopback 9090.
An alert rule present in YAML is only **configured**; it is not called validated
until `promtool` loads it and a controlled time series satisfies its `for` period.
See the executed-evidence report for the actual validation level.

## What the numbers do not mean

- This is not `fio`, direct I/O, raw-device testing, or a distributed benchmark.
- Filesystem cache and fixture creation affect read results.
- One run does not establish a regression baseline or service-level objective.
- Block-call latency excludes fixture setup; write wall time includes one final
  `fsync` per worker, while individual latency samples do not.
- "Observed availability" is successes divided by attempted operations during this
  bounded run. It is not long-term service availability.
- Results from different hardware should not be compared as equivalent.

## License

MIT
