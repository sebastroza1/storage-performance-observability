#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH="$(cd "$(dirname "$0")/.." && pwd)/src"
python -m pytest
python -m storage_observatory.benchmark
python -m storage_observatory.plot_results

