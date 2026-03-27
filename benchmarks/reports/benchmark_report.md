# TermOrganism Benchmark Report

## Summary

- Total cases: 20
- Passed: 20
- Failed: 0
- Success rate: 100.00%
- Median fix time: 12392.673 ms
- Mean fix time: 16623.799 ms
- False positive rate: 0.00%

## Category Breakdown

| Category | Total | Passed | Failed | Success Rate | Median Time (ms) | Mean Time (ms) |
|---|---:|---:|---:|---:|---:|---:|
| cross_file | 5 | 5 | 0 | 100.00% | 29861.725 | 29671.168 |
| dependency | 5 | 5 | 0 | 100.00% | 11560.714 | 11025.797 |
| runtime | 5 | 5 | 0 | 100.00% | 14858.897 | 14946.440 |
| shell | 5 | 5 | 0 | 100.00% | 10860.521 | 10851.789 |

## Case Results

| Case ID | Category | Success | Strategy | Kind | Provider | Caller | Target File | Duration (ms) |
|---|---|---|---|---|---|---|---:|
| runtime_missing_file_basic | runtime | PASS | guard_exists | runtime_file_missing |  |  | /root/TermOrganismGitFork/demo/broken_runtime.py | 14858.897 |
| runtime_missing_nested_read | runtime | PASS | guard_exists | runtime_file_missing |  |  | /root/TermOrganismGitFork/demo/runtime_missing_nested_read.py | 16158.381 |
| runtime_missing_config_open | runtime | PASS | try_except_recovery | runtime_file_missing |  |  | /root/TermOrganismGitFork/demo/runtime_missing_config_open.py | 14759.186 |
| runtime_missing_write_parent | runtime | PASS | try_except_recovery | runtime_file_missing |  |  | /root/TermOrganismGitFork/demo/runtime_missing_write_parent.py | 12727.835 |
| runtime_missing_env_file | runtime | PASS | guard_exists | runtime_file_missing |  |  | /root/TermOrganismGitFork/demo/runtime_missing_env_file.py | 16227.901 |
| dependency_missing_import_basic | dependency | PASS | unknown | dependency_install |  |  | /root/TermOrganismGitFork/demo/broken_import.py | 12057.510 |
| dependency_missing_from_import | dependency | PASS | unknown | dependency_install |  |  | /root/TermOrganismGitFork/demo/dependency_missing_from_import.py | 11924.792 |
| dependency_missing_alias | dependency | PASS | unknown | dependency_install |  |  | /root/TermOrganismGitFork/demo/dependency_missing_alias.py | 10948.643 |
| dependency_missing_submodule | dependency | PASS | unknown | dependency_install |  |  | /root/TermOrganismGitFork/demo/dependency_missing_submodule.py | 11560.714 |
| dependency_missing_plain_import | dependency | PASS | unknown | dependency_install |  |  | /root/TermOrganismGitFork/demo/dependency_missing_plain_import.py | 8637.325 |
| shell_missing_command_basic | shell | PASS | unknown | shell_command_missing |  |  | /root/TermOrganismGitFork/demo/broken_shell_bat.txt | 10679.194 |
| shell_missing_alpha | shell | PASS | unknown | shell_command_missing |  |  | /root/TermOrganismGitFork/demo/shell_missing_alpha.txt | 10967.881 |
| shell_missing_beta | shell | PASS | unknown | shell_command_missing |  |  | /root/TermOrganismGitFork/demo/shell_missing_beta.txt | 10860.521 |
| shell_missing_gamma | shell | PASS | unknown | shell_command_missing |  |  | /root/TermOrganismGitFork/demo/shell_missing_gamma.txt | 10777.223 |
| shell_missing_delta | shell | PASS | unknown | shell_command_missing |  |  | /root/TermOrganismGitFork/demo/shell_missing_delta.txt | 10974.127 |
| cross_file_force_semantic_provider | cross_file | PASS | guard_exists | runtime_file_missing | /root/TermOrganismGitFork/demo/helper_mod.py | /root/TermOrganismGitFork/demo/cross_file_dep.py | /root/TermOrganismGitFork/demo/helper_mod.py | 29861.725 |
| cross_file_cfg_provider | cross_file | PASS | guard_exists | runtime_file_missing | /root/TermOrganismGitFork/demo/helper_cfg.py | /root/TermOrganismGitFork/demo/cross_file_cfg.py | /root/TermOrganismGitFork/demo/helper_cfg.py | 27545.882 |
| cross_file_template_provider | cross_file | PASS | guard_exists | runtime_file_missing | /root/TermOrganismGitFork/demo/helper_template.py | /root/TermOrganismGitFork/demo/cross_file_template.py | /root/TermOrganismGitFork/demo/helper_template.py | 31522.448 |
| cross_file_data_provider | cross_file | PASS | guard_exists | runtime_file_missing | /root/TermOrganismGitFork/demo/helper_data.py | /root/TermOrganismGitFork/demo/cross_file_data.py | /root/TermOrganismGitFork/demo/helper_data.py | 30044.302 |
| cross_file_logs_provider | cross_file | PASS | guard_exists | runtime_file_missing | /root/TermOrganismGitFork/demo/helper_logs.py | /root/TermOrganismGitFork/demo/cross_file_logs.py | /root/TermOrganismGitFork/demo/helper_logs.py | 29381.485 |
