from __future__ import annotations
from core.plugins.base import Plugin
from core.plugins.registry import PluginRegistry

class DummyPlugin(Plugin):
    name = "dummy"
    version = "0.1.0"

def test_plugin_registry_register():
    registry = PluginRegistry()
    plugin = DummyPlugin()
    registry.register(plugin)
    assert registry.get("dummy") is plugin

def test_plugin_registry_list_plugins():
    registry = PluginRegistry()
    registry.register(DummyPlugin())
    assert len(registry.list_plugins()) == 1

def test_plugin_registry_notify_does_not_raise():
    registry = PluginRegistry()
    registry.register(DummyPlugin())
    registry.notify_repair_start({"error": "test"})
    registry.notify_repair_complete({"ok": True})
