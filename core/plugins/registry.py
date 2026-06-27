from __future__ import annotations
import importlib
from pathlib import Path
from typing import Any
import yaml
from .base import Plugin
from core.experts.base import RepairExpert
from core.mimo.tools import Tool
from core.util.logging import get_logger

logger = get_logger("plugins.registry")

class PluginRegistry:
    def __init__(self) -> None:
        self._plugins: dict[str, Plugin] = {}
        self._experts: list[RepairExpert] = []
        self._tools: list[Tool] = []

    def register(self, plugin: Plugin) -> None:
        if not isinstance(plugin, Plugin):
            raise TypeError(f"Expected Plugin instance, got {type(plugin).__name__}")
        self._plugins[plugin.name] = plugin
        self._experts.extend(plugin.register_experts())
        self._tools.extend(plugin.register_tools())

    def get(self, name: str) -> Plugin | None:
        return self._plugins.get(name)

    def list_plugins(self) -> list[Plugin]:
        return list(self._plugins.values())

    def get_experts(self) -> list[RepairExpert]:
        return list(self._experts)

    def get_tools(self) -> list[Tool]:
        return list(self._tools)

    def notify_repair_start(self, context: dict[str, Any]) -> None:
        for plugin in self._plugins.values():
            try:
                plugin.on_repair_start(context)
            except Exception as exc:
                logger.warning("Plugin %s.on_repair_start failed: %s", plugin.name, exc)

    def notify_repair_complete(self, result: dict[str, Any]) -> None:
        for plugin in self._plugins.values():
            try:
                plugin.on_repair_complete(result)
            except Exception as exc:
                logger.warning("Plugin %s.on_repair_complete failed: %s", plugin.name, exc)


def load_plugins_from_config(config_path: str | None = None) -> PluginRegistry:
    registry = PluginRegistry()
    if config_path is None:
        from core.mimo.config import get_config
        config = get_config()
        config_path = getattr(config, "plugins_path", None)
    if config_path and Path(config_path).exists():
        try:
            with open(config_path) as f:
                cfg = yaml.safe_load(f) or {}
            for plugin_spec in cfg.get("plugins", []):
                if isinstance(plugin_spec, str):
                    module_path = plugin_spec
                elif isinstance(plugin_spec, dict):
                    module_path = plugin_spec.get("module", "")
                else:
                    continue
                try:
                    mod = importlib.import_module(module_path)
                    plugin_cls = getattr(mod, "Plugin", None)
                    if plugin_cls and issubclass(plugin_cls, Plugin):
                        registry.register(plugin_cls())
                except Exception as exc:
                    logger.warning("Failed to load plugin %s: %s", module_path, exc)
                    continue
        except Exception as exc:
            logger.warning("Failed to load plugin config %s: %s", config_path, exc)
    try:
        from core.plugins.builtin.python_hotfix import PythonHotfixPlugin
        registry.register(PythonHotfixPlugin())
    except Exception as exc:
        logger.warning("Failed to load builtin plugin PythonHotfixPlugin: %s", exc)
    return registry
