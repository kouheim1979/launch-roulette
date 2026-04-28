from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


class ScoringError(Exception):
    """Raised when quantitative scoring fails."""


@dataclass
class ScoreResult:
    score: int
    positives: list[str]
    negatives: list[str]


def calculate_quant_score(indicator_df: pd.DataFrame) -> ScoreResult:
    if indicator_df is None or indicator_df.empty:
        raise ScoringError("指標データが空のためスコア計算ができません。")

    latest = indicator_df.iloc[-1]
    score = 50
    positives: list[str] = []
    negatives: list[str] = []

    close = float(latest.get("Close", 0))
    ma_5 = float(latest.get("ma_5", 0))
    ma_25 = float(latest.get("ma_25", 0))
    ma_75 = float(latest.get("ma_75", 0))
    rsi_14 = float(latest.get("rsi_14", 50))
    volume_ratio = float(latest.get("volume_ratio_20", 1))
    return_20d = float(latest.get("return_20d_pct", 0))
    dev_25d = float(latest.get("deviation_25d_pct", 0))
    vol20 = float(latest.get("volatility_20_annualized", 20))

    if close > ma_25:
        score += 10
        positives.append("終値が25日移動平均を上回る")
    else:
        score -= 8
        negatives.append("終値が25日移動平均を下回る")

    if ma_5 > ma_25:
        score += 8
        positives.append("5日移動平均が25日移動平均を上回る")
    else:
        score -= 6
        negatives.append("5日移動平均が25日移動平均を下回る")

    if ma_25 > ma_75:
        score += 8
        positives.append("25日移動平均が75日移動平均を上回る")
    else:
        score -= 6
        negatives.append("25日移動平均が75日移動平均を下回る")

    if 45 <= rsi_14 <= 65:
        score += 8
        positives.append("RSIが45〜65の中立〜健全ゾーン")
    elif rsi_14 > 75:
        score -= 10
        negatives.append("RSIが75超で過熱懸念")
    elif rsi_14 < 25:
        score -= 10
        negatives.append("RSIが25未満で弱含み")

    if volume_ratio > 1.1:
        score += 6
        positives.append("出来高が20日平均より増加")
    elif volume_ratio < 0.8:
        score -= 4
        negatives.append("出来高が20日平均を下回る")

    if return_20d > 0:
        score += 8
        positives.append("20営業日騰落率がプラス")
    else:
        score -= 7
        negatives.append("20営業日騰落率がマイナス")

    if dev_25d > 12:
        score -= 8
        negatives.append("25日線からの上方乖離が大きい")
    elif dev_25d < -12:
        score -= 6
        negatives.append("25日線からの下方乖離が大きい")

    if vol20 > 45:
        score -= 10
        negatives.append("20日年率換算ボラティリティが高すぎる")
    elif vol20 < 20:
        score += 4
        positives.append("ボラティリティが比較的安定")

    score = max(0, min(100, score))
    return ScoreResult(score=score, positives=positives, negatives=negatives)
