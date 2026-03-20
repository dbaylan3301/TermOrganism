# TermOrganism Benchmark Report

## Summary

- Total cases: 4
- Passed: 4
- Failed: 0
- Success rate: 100.00%
- Median fix time: 10154.212 ms
- Mean fix time: 12478.536 ms
- False positive rate: 0.00%

## Category Breakdown

| Category | Total | Passed | Failed | Success Rate | Median Time (ms) | Mean Time (ms) |
|---|---:|---:|---:|---:|---:|---:|
| cross_file | 1 | 1 | 0 | 100.00% | 21690.477 | 21690.477 |
| dependency | 1 | 1 | 0 | 100.00% | 7915.244 | 7915.244 |
| runtime | 1 | 1 | 0 | 100.00% | 12032.041 | 12032.041 |
| shell | 1 | 1 | 0 | 100.00% | 8276.383 | 8276.383 |

## Case Results

| Case ID | Category | Success | Strategy | Kind | Provider | Caller | Target File | Duration (ms) |
|---|---|---|---|---|---|---|---:|
| runtime_missing_file_basic | runtime | PASS | guard_exists | runtime_file_missing |  |  | /root/TermOrganismGitFork/demo/broken_runtime.py | 12032.041 |
| dependency_missing_import_basic | dependency | PASS | unknown | dependency_install |  |  | /root/TermOrganismGitFork/demo/broken_import.py | 7915.244 |
| shell_missing_command_basic | shell | PASS | unknown | shell_command_missing |  |  | /root/TermOrganismGitFork/demo/broken_shell_bat.txt | 8276.383 |
| cross_file_force_semantic_provider | cross_file | PASS | guard_exists | runtime_file_missing | /root/TermOrganismGitFork/demo/helper_mod.py | /root/TermOrganismGitFork/demo/cross_file_dep.py | /root/TermOrganismGitFork/demo/helper_mod.py | 21690.477 |
