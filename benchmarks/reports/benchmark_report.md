# TermOrganism Benchmark Report

## Summary

- Total cases: 20
- Passed: 20
- Failed: 0
- Success rate: 100.00%
- Median fix time: 10559.483 ms
- Mean fix time: 13893.137 ms
- False positive rate: 0.00%

## Category Breakdown

| Category | Total | Passed | Failed | Success Rate | Median Time (ms) | Mean Time (ms) |
|---|---:|---:|---:|---:|---:|---:|
| cross_file | 5 | 5 | 0 | 100.00% | 24810.794 | 25048.189 |
| dependency | 5 | 5 | 0 | 100.00% | 9474.491 | 9561.803 |
| runtime | 5 | 5 | 0 | 100.00% | 12154.092 | 11801.636 |
| shell | 5 | 5 | 0 | 100.00% | 9206.183 | 9160.918 |

## Case Results

| Case ID | Category | Success | Strategy | Kind | Provider | Caller | Target File | Duration (ms) |
|---|---|---|---|---|---|---|---:|
| runtime_missing_file_basic | runtime | PASS | guard_exists | runtime_file_missing |  |  | /root/TermOrganismGitFork/demo/broken_runtime.py | 12378.706 |
| runtime_missing_nested_read | runtime | PASS | guard_exists | runtime_file_missing |  |  | /root/TermOrganismGitFork/demo/runtime_missing_nested_read.py | 11228.037 |
| runtime_missing_config_open | runtime | PASS | try_except_recovery | runtime_file_missing |  |  | /root/TermOrganismGitFork/demo/runtime_missing_config_open.py | 10780.492 |
| runtime_missing_write_parent | runtime | PASS | try_except_recovery | runtime_file_missing |  |  | /root/TermOrganismGitFork/demo/runtime_missing_write_parent.py | 12466.853 |
| runtime_missing_env_file | runtime | PASS | guard_exists | runtime_file_missing |  |  | /root/TermOrganismGitFork/demo/runtime_missing_env_file.py | 12154.092 |
| dependency_missing_import_basic | dependency | PASS | unknown | dependency_install |  |  | /root/TermOrganismGitFork/demo/broken_import.py | 8846.997 |
| dependency_missing_from_import | dependency | PASS | unknown | dependency_install |  |  | /root/TermOrganismGitFork/demo/dependency_missing_from_import.py | 10338.474 |
| dependency_missing_alias | dependency | PASS | unknown | dependency_install |  |  | /root/TermOrganismGitFork/demo/dependency_missing_alias.py | 9977.698 |
| dependency_missing_submodule | dependency | PASS | unknown | dependency_install |  |  | /root/TermOrganismGitFork/demo/dependency_missing_submodule.py | 9171.357 |
| dependency_missing_plain_import | dependency | PASS | unknown | dependency_install |  |  | /root/TermOrganismGitFork/demo/dependency_missing_plain_import.py | 9474.491 |
| shell_missing_command_basic | shell | PASS | unknown | shell_command_missing |  |  | /root/TermOrganismGitFork/demo/broken_shell_bat.txt | 9435.164 |
| shell_missing_alpha | shell | PASS | unknown | shell_command_missing |  |  | /root/TermOrganismGitFork/demo/shell_missing_alpha.txt | 8318.817 |
| shell_missing_beta | shell | PASS | unknown | shell_command_missing |  |  | /root/TermOrganismGitFork/demo/shell_missing_beta.txt | 9131.284 |
| shell_missing_gamma | shell | PASS | unknown | shell_command_missing |  |  | /root/TermOrganismGitFork/demo/shell_missing_gamma.txt | 9206.183 |
| shell_missing_delta | shell | PASS | unknown | shell_command_missing |  |  | /root/TermOrganismGitFork/demo/shell_missing_delta.txt | 9713.141 |
| cross_file_force_semantic_provider | cross_file | PASS | guard_exists | runtime_file_missing | /root/TermOrganismGitFork/demo/helper_mod.py | /root/TermOrganismGitFork/demo/cross_file_dep.py | /root/TermOrganismGitFork/demo/helper_mod.py | 25404.615 |
| cross_file_cfg_provider | cross_file | PASS | guard_exists | runtime_file_missing | /root/TermOrganismGitFork/demo/helper_cfg.py | /root/TermOrganismGitFork/demo/cross_file_cfg.py | /root/TermOrganismGitFork/demo/helper_cfg.py | 24782.888 |
| cross_file_template_provider | cross_file | PASS | guard_exists | runtime_file_missing | /root/TermOrganismGitFork/demo/helper_template.py | /root/TermOrganismGitFork/demo/cross_file_template.py | /root/TermOrganismGitFork/demo/helper_template.py | 25794.684 |
| cross_file_data_provider | cross_file | PASS | guard_exists | runtime_file_missing | /root/TermOrganismGitFork/demo/helper_data.py | /root/TermOrganismGitFork/demo/cross_file_data.py | /root/TermOrganismGitFork/demo/helper_data.py | 24447.964 |
| cross_file_logs_provider | cross_file | PASS | guard_exists | runtime_file_missing | /root/TermOrganismGitFork/demo/helper_logs.py | /root/TermOrganismGitFork/demo/cross_file_logs.py | /root/TermOrganismGitFork/demo/helper_logs.py | 24810.794 |
