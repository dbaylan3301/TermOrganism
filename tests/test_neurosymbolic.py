"""Tests for Neuro-Symbolic AI components."""

import os
import shutil
import pytest
import torch
import numpy as np
import pandas as pd
from plugins.scalpbot.ai.neural.scalp_brain import ScalpBrain
from plugins.scalpbot.ai.symbolic.rule_engine import SymbolicRuleEngine
from plugins.scalpbot.ai.symbolic.fuzzy_logic import FuzzyTradingSystem
from plugins.scalpbot.ai.hybrid.neuro_symbolic import NeuroSymbolicTrader
from plugins.scalpbot.ai.forge.ai_forge import AIForge
from plugins.scalpbot.ai.forge.monitor import BrainMonitor


FORGE_WORKSPACE = "/tmp/forge_test"


@pytest.fixture(autouse=True)
def cleanup_forge_workspace():
    yield
    if os.path.exists(FORGE_WORKSPACE):
        shutil.rmtree(FORGE_WORKSPACE, ignore_errors=True)


def test_scalp_brain():
    model = ScalpBrain(input_dim=32, hidden_dim=64, num_lstm_layers=1, num_transformer_layers=1)
    x = torch.randn(2, 50, 32)
    output = model(x)
    assert output.meta_prediction.shape == (2, 3)
    assert output.actor_logits.shape == (2, 3)
    assert output.critic_value.shape == (2, 1)
    assert model.count_parameters() > 0


def test_symbolic_rule_engine():
    engine = SymbolicRuleEngine()
    context = {'ema_score': 28, 'volume_score': 22, 'rsi': 45, 'risk_reward': 2.2, 'atr_pct': 0.3}
    decision = engine.evaluate(context)
    assert decision.action in ["LONG", "SHORT", "HOLD"]
    assert 0 <= decision.confidence <= 1


def test_fuzzy_logic():
    fuzzy = FuzzyTradingSystem()
    action, conf = fuzzy.evaluate(rsi=45, volume_ratio=1.8, momentum=0.15)
    assert action in ["strong_buy", "buy", "hold", "sell", "strong_sell"]
    assert 0 <= conf <= 1


def test_neuro_symbolic():
    model = NeuroSymbolicTrader(input_dim=32, hidden_dim=64)
    x = torch.randn(1, 50, 32)
    indicators = {'ema_score': 28, 'volume_score': 22, 'rsi': 45, 'vol_ratio': 1.8, 'momentum': 0.15}
    decision = model.make_decision(x, indicators)
    assert decision.action in ["LONG", "SHORT", "HOLD"]
    assert 0 <= decision.confidence <= 1


def test_ai_forge():
    forge = AIForge(workspace=FORGE_WORKSPACE)
    status = forge.show_status()
    assert status['forge_active'] is True

    path = forge.create_module('test_module', 'x = 1')
    assert os.path.exists(path)


def test_brain_monitor():
    monitor = BrainMonitor()
    monitor.record_metric('confidence', 0.85)
    monitor.record_decision({'action': 'LONG', 'confidence': 0.85})
    summary = monitor.get_summary()
    assert summary['total_metrics'] == 1
    assert summary['total_decisions'] == 1
