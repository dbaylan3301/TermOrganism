from __future__ import annotations

import json
import sys

from core.plugins import PluginLoader, PluginRegistry
from core.plugins.state import load_plugin_state, save_plugin_state, apply_plugin_state, set_plugin_enabled


def _load_registry() -> PluginRegistry:
    registry = PluginRegistry()
    PluginLoader("plugins").load_into(registry)
    apply_plugin_state(registry, load_plugin_state())
    return registry


def cmd_list() -> int:
    registry = _load_registry()
    print(json.dumps({
        "success": True,
        "plugins": registry.list_plugins(),
        "state": load_plugin_state(),
    }))
    return 0


def cmd_enable(name: str) -> int:
    state = set_plugin_enabled(name, True)
    registry = _load_registry()
    print(json.dumps({
        "success": True,
        "action": "enable",
        "plugin": name,
        "state": state,
        "plugins": registry.list_plugins(),
        "note": "restart daemon to reload plugin state",
    }))
    return 0


def cmd_disable(name: str) -> int:
    state = set_plugin_enabled(name, False)
    registry = _load_registry()
    print(json.dumps({
        "success": True,
        "action": "disable",
        "plugin": name,
        "state": state,
        "plugins": registry.list_plugins(),
        "note": "restart daemon to reload plugin state",
    }))
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv or sys.argv
    if len(argv) < 2:
        print(json.dumps({"success": False, "error": "usage: python -m core.plugins.cli list|enable <name>|disable <name>"}))
        return 1

    cmd = argv[1]
    if cmd == "list":
        return cmd_list()
    if cmd == "enable":
        if len(argv) < 3:
            print(json.dumps({"success": False, "error": "missing plugin name"}))
            return 1
        return cmd_enable(argv[2])
    if cmd == "disable":
        if len(argv) < 3:
            print(json.dumps({"success": False, "error": "missing plugin name"}))
            return 1
        return cmd_disable(argv[2])

    print(json.dumps({"success": False, "error": f"unknown command: {cmd}"}))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
