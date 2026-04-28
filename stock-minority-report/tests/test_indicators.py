import pandas as pd
import pytest

from src.indicators import IndicatorError, enrich_with_indicators


def _sample_df(rows: int = 100) -> pd.DataFrame:
    dates = pd.date_range("2024-01-01", periods=rows, freq="D")
    base = pd.Series(range(rows), dtype="float") + 100
    return pd.DataFrame(
        {
            "Date": dates,
            "Open": base + 0.5,
            "High": base + 1.0,
            "Low": base - 1.0,
            "Close": base,
            "Volume": 1000 + (base * 2),
        }
    )


def test_rsi_is_calculated() -> None:
    df = _sample_df(120)
    out = enrich_with_indicators(df)
    assert "rsi_14" in out.columns
    assert out["rsi_14"].notna().all()


def test_moving_average_columns_added() -> None:
    df = _sample_df(120)
    out = enrich_with_indicators(df)
    for col in ["ma_5", "ma_25", "ma_75"]:
        assert col in out.columns


def test_empty_data_raises_exception() -> None:
    with pytest.raises(IndicatorError):
        enrich_with_indicators(pd.DataFrame())
