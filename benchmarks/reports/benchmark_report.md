# TermOrganism Benchmark Report

## Summary

- Total cases: 20
- Passed: 20
- Failed: 0
- Success rate: 100.00%
- Median fix time: 18273.992 ms
- Mean fix time: 21107.773 ms
- False positive rate: 0.00%

## Category Breakdown

| Category | Total | Passed | Failed | Success Rate | Median Time (ms) | Mean Time (ms) |
|---|---:|---:|---:|---:|---:|---:|
| cross_file | 5 | 5 | 0 | 100.00% | 35126.562 | 36302.855 |
| dependency | 5 | 5 | 0 | 100.00% | 14156.630 | 13469.666 |
| runtime | 5 | 5 | 0 | 100.00% | 21382.337 | 23267.469 |
| shell | 5 | 5 | 0 | 100.00% | 11451.917 | 11391.102 |

## Case Results

| Case ID | Category | Success | Strategy | Kind | Provider | Caller | Target File | Duration (ms) |
|---|---|---|---|---|---|---|---:|
| runtime_missing_file_basic | runtime | PASS | guard_exists | runtime_file_missing |  |  | /root/TermOrganismGitFork/demo/broken_runtime.py | 21076.205 |
| runtime_missing_nested_read | runtime | PASS | guard_exists | runtime_file_missing |  |  | /root/TermOrganismGitFork/demo/runtime_missing_nested_read.py | 29686.679 |
| runtime_missing_config_open | runtime | PASS | try_except_recovery | runtime_file_missing |  |  | /root/TermOrganismGitFork/demo/runtime_missing_config_open.py | 23171.393 |
| runtime_missing_write_parent | runtime | PASS | try_except_recovery | runtime_file_missing |  |  | /root/TermOrganismGitFork/demo/runtime_missing_write_parent.py | 21020.730 |
| runtime_missing_env_file | runtime | PASS | guard_exists | runtime_file_missing |  |  | /root/TermOrganismGitFork/demo/runtime_missing_env_file.py | 21382.337 |
| dependency_missing_import_basic | dependency | PASS | unknown | dependency_install |  |  | /root/TermOrganismGitFork/demo/broken_import.py | 15527.253 |
| dependency_missing_from_import | dependency | PASS | unknown | dependency_install |  |  | /root/TermOrganismGitFork/demo/dependency_missing_from_import.py | 14727.337 |
| dependency_missing_alias | dependency | PASS | unknown | dependency_install |  |  | /root/TermOrganismGitFork/demo/dependency_missing_alias.py | 14156.630 |
| dependency_missing_submodule | dependency | PASS | unknown | dependency_install |  |  | /root/TermOrganismGitFork/demo/dependency_missing_submodule.py | 11088.542 |
| dependency_missing_plain_import | dependency | PASS | unknown | dependency_install |  |  | /root/TermOrganismGitFork/demo/dependency_missing_plain_import.py | 11848.568 |
| shell_missing_command_basic | shell | PASS | unknown | shell_command_missing |  |  | /root/TermOrganismGitFork/demo/broken_shell_bat.txt | 10387.660 |
| shell_missing_alpha | shell | PASS | unknown | shell_command_missing |  |  | /root/TermOrganismGitFork/demo/shell_missing_alpha.txt | 10937.655 |
| shell_missing_beta | shell | PASS | unknown | shell_command_missing |  |  | /root/TermOrganismGitFork/demo/shell_missing_beta.txt | 11529.668 |
| shell_missing_gamma | shell | PASS | unknown | shell_command_missing |  |  | /root/TermOrganismGitFork/demo/shell_missing_gamma.txt | 11451.917 |
| shell_missing_delta | shell | PASS | unknown | shell_command_missing |  |  | /root/TermOrganismGitFork/demo/shell_missing_delta.txt | 12648.608 |
| cross_file_force_semantic_provider | cross_file | PASS | guard_exists | runtime_file_missing | /root/TermOrganismGitFork/demo/helper_mod.py | /root/TermOrganismGitFork/demo/cross_file_dep.py | /root/TermOrganismGitFork/demo/helper_mod.py | 34218.787 |
| cross_file_cfg_provider | cross_file | PASS | guard_exists | runtime_file_missing | /root/TermOrganismGitFork/demo/helper_cfg.py | /root/TermOrganismGitFork/demo/cross_file_cfg.py | /root/TermOrganismGitFork/demo/helper_cfg.py | 36708.253 |
| cross_file_template_provider | cross_file | PASS | guard_exists | runtime_file_missing | /root/TermOrganismGitFork/demo/helper_template.py | /root/TermOrganismGitFork/demo/cross_file_template.py | /root/TermOrganismGitFork/demo/helper_template.py | 42217.068 |
| cross_file_data_provider | cross_file | PASS | guard_exists | runtime_file_missing | /root/TermOrganismGitFork/demo/helper_data.py | /root/TermOrganismGitFork/demo/cross_file_data.py | /root/TermOrganismGitFork/demo/helper_data.py | 35126.562 |
| cross_file_logs_provider | cross_file | PASS | guard_exists | runtime_file_missing | /root/TermOrganismGitFork/demo/helper_logs.py | /root/TermOrganismGitFork/demo/cross_file_logs.py | /root/TermOrganismGitFork/demo/helper_logs.py | 33243.603 |
