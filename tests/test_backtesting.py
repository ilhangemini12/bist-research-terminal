import pandas as pd
import pytest
from bist_terminal.backtesting.engine import metrics,point_in_time_guard,universe_guard,turnover


def test_metrics_include_required_core():
    r=metrics(pd.Series([0.01,-0.005,0.02,0.0]))
    assert {'cagr','total_return','annualized_volatility','sharpe','sortino','max_drawdown','win_rate'} <= set(r)


def test_lookahead_blocked():
    with pytest.raises(ValueError, match='LOOK_AHEAD_BIAS_BLOCKED'):
        point_in_time_guard('2026-08-10','2026-08-01')


def test_survivorship_warning():
    assert universe_guard(False).startswith('BACKTEST BIASED')


def test_turnover_known_weights():
    w=pd.DataFrame([[1,0],[0.5,0.5],[0,1]],columns=['A','B'])
    assert turnover(w)==0.5
