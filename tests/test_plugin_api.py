from __future__ import annotations
from core.plugins.base import Plugin

class DummyPlugin(Plugin):
    name = "dummy"
    version = "0.1.0"
    def register_experts(self):
        return []
    def register_tools(self):
        return []

def test_plugin_has_name():
    plugin = DummyPlugin()
    assert plugin.name == "dummy"

def test_plugin_register_experts_returns_list():
    plugin = DummyPlugin()
    assert plugin.register_experts() == []

def test_plugin_register_tools_returns_list():
    plugin = DummyPlugin()
    assert plugin.register_tools() == []

def test_plugin_on_repair_start_does_not_raise():
    plugin = DummyPlugin()
    plugin.on_repair_start({"error": "test"})

def test_plugin_on_repair_complete_does_not_raise():
    plugin = DummyPlugin()
    plugin.on_repair_complete({"ok": True})
