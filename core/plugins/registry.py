from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from core.plugins.manifest import PluginManifest


@dataclass
class PluginRegistry:
    manifests: dict[str, PluginManifest] = field(default_factory=dict)
    enabled: set[str] = field(default_factory=set)

    def register(self, manifest: PluginManifest) -> None:
        self.manifests[manifest.name] = manifest
        if manifest.enabled_by_default:
            self.enabled.add(manifest.name)

    def enable(self, name: str) -> None:
        if name not in self.manifests:
            raise KeyError(f"unknown plugin: {name}")
        self.enabled.add(name)

    def disable(self, name: str) -> None:
        self.enabled.discard(name)

    def is_enabled(self, name: str) -> bool:
        return name in self.enabled

    def enabled_hook_commands(self, event_name: str) -> list[str]:
        commands: list[str] = []
        for name in sorted(self.enabled):
            manifest = self.manifests.get(name)
            if manifest is None:
                continue
            for item in manifest.hook_commands.get(event_name, []):
                p = Path(item)
                if not p.is_absolute():
                    p = Path(manifest.root_dir) / item
                commands.append(str(p))
        return commands

    def list_plugins(self) -> list[dict]:
        out = []
        for name, m in sorted(self.manifests.items()):
            out.append({
                "name": name,
                "version": m.version,
                "enabled": name in self.enabled,
                "skills": m.skills,
                "agents": m.agents,
                "hooks": m.hooks,
                "hook_commands": m.hook_commands,
            })
        return out
