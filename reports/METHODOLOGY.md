# Benchmark methodology

## Question

How do operation type, access pattern, block size, file size, and concurrency
change observed local file-I/O throughput and block-operation tail latency?

## Controlled workload

The quick profile runs eight cases using only `artifacts/benchmark`, which is
ignored by Git. Each case is capped at 256 MiB across workers, concurrency is
capped at eight, random work is capped at 2,048 operations per worker, and all
fixtures are deleted in `finally` cleanup. It never opens a raw device or writes
outside the selected directory.

Reads use deterministic fixtures created and `fsync`ed before the timer. Writes
use unbuffered Python file objects and call `flush` plus `fsync` once per worker
after block operations. Individual latency samples time each `read` or `write`
call; the case wall clock includes thread setup and final writer synchronization.
Throughput is successful bytes divided by wall time. Operations per second uses
successful block calls. Percentiles use the nearest-rank definition.

## Variables

- Small sequential: 4 MiB files, 4 KiB blocks, concurrency 1.
- Medium sequential: 32 MiB files, 1 MiB blocks, concurrency 1.
- Random: 16 MiB files at concurrency 1 or 8 MiB per worker at concurrency 4,
  4 KiB blocks, maximum 2,048 operations per worker.
- Concurrent sequential write: 8 MiB per worker, 64 KiB blocks, concurrency 4.

## Interpretation boundaries

This is a Python application-level, buffered-filesystem benchmark—not `fio`,
direct I/O, a distributed-storage benchmark, or a device specification. Fixture
creation can warm the operating-system cache. Antivirus, OneDrive synchronization,
background load, CPU frequency, filesystem allocation, and storage firmware can
affect results. Random offsets are deterministic for repeatability but are not a
production trace. Compare repeated runs on the same controlled host before calling
a change a regression.

`fio` was not installed on the execution host. It remains the appropriate next
tool for queue-depth, direct-I/O, and durable-device studies.

