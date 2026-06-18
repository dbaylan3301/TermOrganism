from pytest import approx
from plugins.scalpbot.risk import calculate_sl_tp, calculate_pnl, check_exit


def test_calculate_sl_tp_long():
    entry = 100.0
    atr = 2.0
    sl, tp = calculate_sl_tp(entry, atr, "LONG", sl_mult=1.5, tp_mult=1.7)
    assert sl < entry
    assert tp > entry
    assert entry - sl == approx(atr * 1.5)
    assert tp - entry == approx(atr * 1.7)


def test_calculate_sl_tp_short():
    entry = 100.0
    atr = 2.0
    sl, tp = calculate_sl_tp(entry, atr, "SHORT", sl_mult=1.5, tp_mult=1.7)
    assert sl > entry
    assert tp < entry
    assert sl - entry == approx(atr * 1.5)
    assert entry - tp == approx(atr * 1.7)


def test_calculate_pnl_long():
    entry = 100.0
    current = 102.0
    pnl_pct = calculate_pnl(entry, current, "LONG", leverage=5)
    assert pnl_pct == approx(10.0)


def test_calculate_pnl_short():
    entry = 100.0
    current = 98.0
    pnl_pct = calculate_pnl(entry, current, "SHORT", leverage=5)
    assert pnl_pct == approx(10.0)


def test_check_exit_sl_hit():
    entry = 100.0
    current = 97.0
    sl = 98.0
    tp = 105.0
    assert check_exit(entry, current, sl, tp, "LONG") == "SL"


def test_check_exit_tp_hit():
    entry = 100.0
    current = 106.0
    sl = 98.0
    tp = 105.0
    assert check_exit(entry, current, sl, tp, "LONG") == "TP"


def test_check_exit_no_exit():
    entry = 100.0
    current = 101.0
    sl = 98.0
    tp = 105.0
    assert check_exit(entry, current, sl, tp, "LONG") is None
