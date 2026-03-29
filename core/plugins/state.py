from __future__ import annotations

from pathlib import Path
import json
from typing import Any
from core.plugins.registry import PluginRegistry

DEFAULT_STATE = {
    "enabled": [],
    "disabled": [],
}


def load_plugin_state(path: str | Path = ".termorganism/plugins_state.json") -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return dict(DEFAULT_STATE)
    data = json.loads(p.read_text(encoding="utf-8"))
    data.setdefault("enabled", [])
    data.setdefault("disabled", [])
    return data


def save_plugin_state(state: dict[str, Any], path: str | Path = ".termorganism/plugins_state.json") -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2), encoding="utf-8")
    return p


def apply_plugin_state(registry: PluginRegistry, state: dict[str, Any]) -> PluginRegistry:
    for name in state.get("disabled", []):
        if name in registry.manifests:
            registry.disable(name)
    for name in state.get("enabled", []):
        if name in registry.manifests:
            registry.enable(name)
    return registry


def set_plugin_enabled(name: str, enabled: bool, path: str | Path = ".termorganism/plugins_state.json") -> dict[str, Any]:
    state = load_plugin_state(path)
    enabled_set = set(state.get("enabled", []))
    disabled_set = set(state.get("disabled", []))

    if enabled:
        enabled_set.add(name)
        disabled_set.discard(name)
    else:
        disabled_set.add(name)
        enabled_set.discard(name)

    out = {
        "enabled": sorted(enabled_set),
        "disabled": sorted(disabled_set),
    }
    save_plugin_state(out, path)
    return out
