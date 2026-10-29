# Execution hardware

Captured by `reports/results.json` on 2026-10-29:

- Platform: Windows 11 10.0.22631
- Processor string: AMD64 Family 23 Model 24 Stepping 1, AuthenticAMD
- Logical processors: 8
- Python: 3.12.14
- Benchmark filesystem total: 1,999,354,077,184 bytes
- Free space before: 1,049,201,704,960 bytes
- Free space after: 1,049,201,704,960 bytes
- Clock: `time.perf_counter_ns`
- Work path: repository-local `artifacts/benchmark`

The broader machine audit identified the processor as an AMD Ryzen 5 3550H with
4 physical cores / 8 threads and approximately 29.94 GiB RAM. Those values were
collected outside the benchmark; the JSON keeps only facts observable with the
Python standard library.

