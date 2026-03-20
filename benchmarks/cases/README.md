# Benchmark Cases

Each case directory should contain:

- `input_target.txt` or a direct target path in manifest
- `expected.json`
- optional `notes.txt`

`expected.json` schema:

```json
{
  "id": "runtime_missing_file_basic",
  "category": "runtime",
  "target": "demo/broken_runtime.py",
  "expect": {
    "result_present": true,
    "strategy_in": ["guard_exists", "try_except_recovery", "touch_only"],
    "target_file_contains": ["broken_runtime.py", "helper_mod.py"],
    "provider_contains": ["helper_mod.py"],
    "caller_contains": ["cross_file_dep.py"],
    "sandbox_ok": true,
    "contract_ok": true,
    "behavioral_ok": true
  }
}
```
