$ErrorActionPreference = 'Stop'
$python = Join-Path $PSScriptRoot '..\.venv\Scripts\python.exe'
$env:PYTHONPATH = Join-Path $PSScriptRoot '..\src'
& $python -m pytest
& $python -m storage_observatory.benchmark
& $python -m storage_observatory.plot_results

