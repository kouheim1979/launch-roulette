import pandas as pd

from src.scoring import calculate_quant_score


def _df_from_row(row: dict) -> pd.DataFrame:
    return pd.DataFrame([row])


def test_score_range() -> None:
    row = {
        "Close": 100,
        "ma_5": 99,
        "ma_25": 98,
        "ma_75": 95,
        "rsi_14": 55,
        "volume_ratio_20": 1.2,
        "return_20d_pct": 4,
        "deviation_25d_pct": 2,
        "volatility_20_annualized": 18,
    }
    result = calculate_quant_score(_df_from_row(row))
    assert 0 <= result.score <= 100


def test_strong_conditions_high_score() -> None:
    row = {
        "Close": 120,
        "ma_5": 118,
        "ma_25": 110,
        "ma_75": 100,
        "rsi_14": 58,
        "volume_ratio_20": 1.4,
        "return_20d_pct": 12,
        "deviation_25d_pct": 6,
        "volatility_20_annualized": 19,
    }
    result = calculate_quant_score(_df_from_row(row))
    assert result.score >= 70


def test_weak_conditions_low_score() -> None:
    row = {
        "Close": 80,
        "ma_5": 82,
        "ma_25": 90,
        "ma_75": 95,
        "rsi_14": 82,
        "volume_ratio_20": 0.6,
        "return_20d_pct": -14,
        "deviation_25d_pct": 15,
        "volatility_20_annualized": 55,
    }
    result = calculate_quant_score(_df_from_row(row))
    assert result.score <= 40
