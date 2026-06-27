from __future__ import annotations

import importlib
from pathlib import Path
from core.plugins.manifest import PluginManifest
from core.plugins.registry import PluginRegistry


class PluginLoader:
    def __init__(self, plugins_root: str | Path = "plugins") -> None:
        self.plugins_root = Path(plugins_root)

    def discover(self) -> list[PluginManifest]:
        manifests: list[PluginManifest] = []
        if not self.plugins_root.exists():
            return manifests
        for path in self.plugins_root.rglob("plugin.json"):
            manifests.append(PluginManifest.from_file(path))
        return manifests

    def load_into(self, registry: PluginRegistry) -> PluginRegistry:
        for manifest in self.discover():
            if not manifest.entry_point:
                continue
            module_path, class_name = manifest.entry_point.rsplit(":", 1)
            mod = importlib.import_module(module_path)
            plugin_cls = getattr(mod, class_name)
            registry.register(plugin_cls())
        return registry
