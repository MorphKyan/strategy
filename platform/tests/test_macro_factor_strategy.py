import copy
from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest

from src.platform_core.models import PortfolioState
from src.platform_core.strategies.macro_factor_es import RiskParityMacroFactorStrategy
from src.platform_core.strategy import StrategyContext


def _context(count=3):
    prices = pd.DataFrame(100 * np.exp(np.random.default_rng(42).normal(0, .01, (45, count)).cumsum(axis=0)),
                          index=pd.bdate_range("2024-01-01", periods=45), columns=list("ABC")[:count])
    return StrategyContext(
        date=prices.index[-1], assets={a: None for a in prices}, bars={}, state=PortfolioState(cash=10000),
        data=SimpleNamespace(get_price_frame=lambda *args, **kwargs: prices.copy()),
        params={"min_periods": 20, "rolling_window": 30, "init_calc_days": 0},
    )


@pytest.mark.parametrize("count", [1, 2, 3])
def test_macro_factor_accepts_small_universe_and_restores_betas(count):
    context = _context(count)
    strategy = RiskParityMacroFactorStrategy()
    strategy.initialize(context)
    first = strategy._inverse_vol_target(context, list(context.assets))
    assert np.isfinite(list(first.weights.values())).all()
    assert np.asarray(context.runtime["macro_factor_betas"]).shape == (count, min(count, 3))
    restarted = RiskParityMacroFactorStrategy()
    restored = copy.copy(context)
    restored.runtime = copy.deepcopy(context.runtime)
    assert restarted._inverse_vol_target(restored, list(context.assets)).weights == pytest.approx(
        strategy._inverse_vol_target(context, list(context.assets)).weights)


def test_pca_sign_choice_cannot_cancel_smoothed_factor_exposures(monkeypatch):
    context = _context()
    context.params["lambda_beta"] = 0.5
    strategy = RiskParityMacroFactorStrategy()
    strategy._inverse_vol_target(context, list(context.assets))
    previous = np.asarray(context.runtime["macro_factor_betas"])
    original_svd = np.linalg.svd

    def equivalent_svd(values, *args, **kwargs):
        u, s, vt = original_svd(values, *args, **kwargs)
        if values.shape[0] > values.shape[1]:
            return -u, s, -vt
        return u, s, vt

    monkeypatch.setattr(np.linalg, "svd", equivalent_svd)
    strategy._inverse_vol_target(context, list(context.assets))
    assert np.asarray(context.runtime["macro_factor_betas"]) == pytest.approx(previous)


def test_failed_pca_does_not_fabricate_a_factor_matrix(monkeypatch):
    context = _context()
    original_svd = np.linalg.svd

    def fail_svd(values, *args, **kwargs):
        if values.shape[0] > values.shape[1]:
            raise np.linalg.LinAlgError("SVD did not converge")
        return original_svd(values, *args, **kwargs)

    monkeypatch.setattr(np.linalg, "svd", fail_svd)
    with pytest.raises(np.linalg.LinAlgError):
        RiskParityMacroFactorStrategy()._inverse_vol_target(context, list(context.assets))


def test_changed_universe_cannot_reuse_another_assets_factor_rows():
    context = _context()
    context.params["lambda_beta"] = 1.0
    strategy = RiskParityMacroFactorStrategy()
    strategy._inverse_vol_target(context, ["A", "B"])
    strategy._inverse_vol_target(context, ["B", "C"])
    returns = context.data.get_price_frame()[["B", "C"]].pct_change().dropna().tail(30).to_numpy()
    _, _, vt = np.linalg.svd(returns - returns.mean(axis=0), full_matrices=False)
    assert context.runtime["macro_factor_universe"] == ["B", "C"]
    assert np.asarray(context.runtime["macro_factor_betas"]) == pytest.approx(vt.T)


def test_failed_optimization_preserves_last_successful_factor_state(monkeypatch):
    from src.platform_core.strategies import macro_factor_es

    context = _context()
    strategy = RiskParityMacroFactorStrategy()
    strategy._inverse_vol_target(context, list(context.assets))
    previous = copy.deepcopy(context.runtime)
    monkeypatch.setattr(macro_factor_es, "minimize", lambda *args, **kwargs: SimpleNamespace(
        success=False, x=np.full(3, 1 / 3), message="injected failure"))
    with pytest.raises(RuntimeError, match="solver failed"):
        strategy._inverse_vol_target(context, list(context.assets))
    assert context.runtime == previous


def test_factor_es_decomposition_uses_joint_loss_tail_and_preserves_negative_contributions():
    # 相同尾部同时决定所有资产的贡献，不能分别取每列的最差收益。
    returns = np.array([[-.10, .04], [-.02, -.08], [.03, .01], [.05, .02]])
    weights = np.array([.8, .2])
    es, asset, factor, residual = RiskParityMacroFactorStrategy._risk_contributions(
        returns, weights, np.eye(2), .75)
    assert es == pytest.approx(.072)
    assert asset == pytest.approx([.08, -.008])
    assert factor == pytest.approx(asset)
    assert asset.sum() == pytest.approx(es)
    assert factor.sum() + residual == pytest.approx(es)


def test_unexplained_factor_tail_risk_is_not_dropped():
    returns = np.array([[-.10, -.02], [.03, .01], [.05, .02], [-.01, .04]])
    es, asset, factor, residual = RiskParityMacroFactorStrategy._risk_contributions(
        returns, np.array([.5, .5]), np.array([[1.], [0.]]), .75)
    assert factor == pytest.approx([.05])
    assert residual == pytest.approx(.01)
    assert asset.sum() == pytest.approx(es)


def test_factor_optimizer_cannot_read_future_prices():
    context = _context()
    context.date = context.data.get_price_frame().index[-5]
    strategy = RiskParityMacroFactorStrategy()
    first = strategy._inverse_vol_target(context, list(context.assets))
    original = context.data.get_price_frame()
    original.loc[original.index > context.date] *= 10
    context.data = SimpleNamespace(get_price_frame=lambda *args, **kwargs: original.copy())
    context.runtime.clear()
    assert strategy._inverse_vol_target(context, list(context.assets)).weights == pytest.approx(first.weights)
