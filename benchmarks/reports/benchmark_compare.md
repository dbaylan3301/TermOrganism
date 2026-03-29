# Benchmark mode comparison

| Mode | Return Code | Cases | Timeout Count | Success Rate | Median ms | Mean ms | Avg Confidence |
|---|---:|---:|---:|---:|---:|---:|---:|
| normal | 0 | 20 | - | 1.000 | 16178.171 | 23465.089 | - |
| fast | 0 | 20 | - | 1.000 | 18273.992 | 21107.773 | - |

## Category breakdown

| Category | Count | Normal Success | Fast Success | Normal Median ms | Fast Median ms | Normal Mean ms | Fast Mean ms | Normal Avg Confidence | Fast Avg Confidence |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| cross_file | 5 | 1.000 | 1.000 | 43276.605 | 35126.562 | 45623.963 | 36302.855 | - | - |
| dependency | 5 | 1.000 | 1.000 | 14227.177 | 14156.630 | 14288.675 | 13469.666 | - | - |
| runtime | 5 | 1.000 | 1.000 | 19774.066 | 21382.337 | 20343.560 | 23267.469 | - | - |
| shell | 5 | 1.000 | 1.000 | 13529.662 | 11451.917 | 13604.156 | 11391.102 | - | - |

## Fastest improvements

| Case | Category | Normal ms | Fast ms | Delta ms | Normal Confidence | Fast Confidence |
|---|---|---:|---:|---:|---:|---:|
| cross_file_force_semantic_provider | cross_file | 54282.874 | 34218.787 | -20064.087 | - | - |
| cross_file_data_provider | cross_file | 45731.317 | 35126.562 | -10604.755 | - | - |
| cross_file_logs_provider | cross_file | 43276.605 | 33243.603 | -10033.002 | - | - |
| cross_file_cfg_provider | cross_file | 42642.252 | 36708.253 | -5933.999 | - | - |
| shell_missing_alpha | shell | 14199.836 | 10937.655 | -3262.181 | - | - |

## Largest regressions

| Case | Category | Normal ms | Fast ms | Delta ms | Normal Confidence | Fast Confidence |
|---|---|---:|---:|---:|---:|---:|
| runtime_missing_nested_read | runtime | 22666.879 | 29686.679 | 7019.800 | - | - |
| runtime_missing_config_open | runtime | 18364.862 | 23171.393 | 4806.531 | - | - |
| runtime_missing_write_parent | runtime | 17688.842 | 21020.730 | 3331.888 | - | - |
| runtime_missing_env_file | runtime | 19774.066 | 21382.337 | 1608.271 | - | - |
| dependency_missing_import_basic | dependency | 14271.844 | 15527.253 | 1255.409 | - | - |

## Case-by-case

| Case | Category | Normal OK | Fast OK | Normal ms | Fast ms | Delta ms | Normal Confidence | Fast Confidence |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| cross_file_cfg_provider | cross_file | True | True | 42642.252 | 36708.253 | -5933.999 | - | - |
| cross_file_data_provider | cross_file | True | True | 45731.317 | 35126.562 | -10604.755 | - | - |
| cross_file_force_semantic_provider | cross_file | True | True | 54282.874 | 34218.787 | -20064.087 | - | - |
| cross_file_logs_provider | cross_file | True | True | 43276.605 | 33243.603 | -10033.002 | - | - |
| cross_file_template_provider | cross_file | True | True | 42186.768 | 42217.068 | 30.300 | - | - |
| dependency_missing_alias | dependency | True | True | 14667.499 | 14156.630 | -510.869 | - | - |
| dependency_missing_from_import | dependency | True | True | 14221.245 | 14727.337 | 506.092 | - | - |
| dependency_missing_import_basic | dependency | True | True | 14271.844 | 15527.253 | 1255.409 | - | - |
| dependency_missing_plain_import | dependency | True | True | 14055.609 | 11848.568 | -2207.041 | - | - |
| dependency_missing_submodule | dependency | True | True | 14227.177 | 11088.542 | -3138.635 | - | - |
| runtime_missing_config_open | runtime | True | True | 18364.862 | 23171.393 | 4806.531 | - | - |
| runtime_missing_env_file | runtime | True | True | 19774.066 | 21382.337 | 1608.271 | - | - |
| runtime_missing_file_basic | runtime | True | True | 23223.151 | 21076.205 | -2146.946 | - | - |
| runtime_missing_nested_read | runtime | True | True | 22666.879 | 29686.679 | 7019.800 | - | - |
| runtime_missing_write_parent | runtime | True | True | 17688.842 | 21020.730 | 3331.888 | - | - |
| shell_missing_alpha | shell | True | True | 14199.836 | 10937.655 | -3262.181 | - | - |
| shell_missing_beta | shell | True | True | 13529.662 | 11529.668 | -1999.994 | - | - |
| shell_missing_command_basic | shell | True | True | 13162.903 | 10387.660 | -2775.243 | - | - |
| shell_missing_delta | shell | True | True | 13190.399 | 12648.608 | -541.791 | - | - |
| shell_missing_gamma | shell | True | True | 13937.982 | 11451.917 | -2486.065 | - | - |

## Artifacts

- normal summary: `/root/TermOrganismGitFork/benchmarks/results/benchmark_summary.normal.json`
- fast summary: `/root/TermOrganismGitFork/benchmarks/results/benchmark_summary.fast.json`
- normal cases: `/root/TermOrganismGitFork/benchmarks/results/case_results.normal.json`
- fast cases: `/root/TermOrganismGitFork/benchmarks/results/case_results.fast.json`
- normal stdout: `/root/TermOrganismGitFork/benchmarks/results/benchmark_normal.stdout.txt`
- fast stdout: `/root/TermOrganismGitFork/benchmarks/results/benchmark_fast.stdout.txt`
- normal stderr: `/root/TermOrganismGitFork/benchmarks/results/benchmark_normal.stderr.txt`
- fast stderr: `/root/TermOrganismGitFork/benchmarks/results/benchmark_fast.stderr.txt`

## Notes

- `TERMORGANISM_FAST=1` was used for fast mode.
- Confidence is collected by recursively scanning each case payload for `confidence.score`.
- Existing `benchmarks/runner.py` remains untouched; this compare wrapper is additive.
