from __future__ import annotations

import numpy as np
import pandas as pd


class IndicatorError(Exception):
    """Raised when indicator computation fails."""


REQUIRED_COLUMNS = {"Date", "Open", "High", "Low", "Close", "Volume"}


def _validate_input(price_df: pd.DataFrame) -> None:
    if price_df is None or price_df.empty:
        raise IndicatorError("株価データが空のため、指標計算ができません。")

    missing = REQUIRED_COLUMNS.difference(set(price_df.columns))
    if missing:
        raise IndicatorError(f"必要な列が不足しています: {sorted(missing)}")


def calculate_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50.0)


def enrich_with_indicators(price_df: pd.DataFrame) -> pd.DataFrame:
    _validate_input(price_df)
    df = price_df.copy()

    for col in ["Open", "High", "Low", "Close", "Volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df[["Open", "High", "Low", "Close"]].isna().all(axis=None):
        raise IndicatorError("価格データの変換に失敗しました。")

    df = df.sort_values("Date").reset_index(drop=True)

    df["ma_5"] = df["Close"].rolling(window=5, min_periods=1).mean()
    df["ma_25"] = df["Close"].rolling(window=25, min_periods=1).mean()
    df["ma_75"] = df["Close"].rolling(window=75, min_periods=1).mean()

    df["rsi_14"] = calculate_rsi(df["Close"], period=14)

    ema_12 = df["Close"].ewm(span=12, adjust=False).mean()
    ema_26 = df["Close"].ewm(span=26, adjust=False).mean()
    df["macd"] = ema_12 - ema_26
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()

    df["return_1d_pct"] = df["Close"].pct_change(1) * 100
    df["return_20d_pct"] = df["Close"].pct_change(20) * 100

    df["deviation_25d_pct"] = ((df["Close"] - df["ma_25"]) / df["ma_25"].replace(0, np.nan)) * 100

    df["volume_ma_20"] = df["Volume"].rolling(window=20, min_periods=1).mean()
    df["volume_ratio_20"] = df["Volume"] / df["volume_ma_20"].replace(0, np.nan)

    daily_return = df["Close"].pct_change()
    df["volatility_20_annualized"] = daily_return.rolling(window=20).std() * np.sqrt(252) * 100

    numeric_cols = [
        "return_1d_pct",
        "return_20d_pct",
        "deviation_25d_pct",
        "volume_ratio_20",
        "volatility_20_annualized",
    ]
    df[numeric_cols] = df[numeric_cols].replace([np.inf, -np.inf], np.nan)
    return df
