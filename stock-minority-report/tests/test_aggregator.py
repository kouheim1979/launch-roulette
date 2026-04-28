from src.aggregator import aggregate_reports


def _report(agent: str, view: str, confidence: int = 60) -> dict:
    return {
        "agent_name": agent,
        "role": "role",
        "view": view,
        "confidence": confidence,
        "summary": f"{agent} summary",
        "positive_factors": ["p"],
        "negative_factors": ["n"],
        "watchpoints": [f"wp-{agent}"],
        "time_horizon": "短期",
    }


def test_majority_view_is_correct() -> None:
    reports = [
        _report("A", "bullish"),
        _report("B", "bullish"),
        _report("C", "neutral"),
        _report("D", "bearish"),
    ]
    result = aggregate_reports(reports)
    assert result.majority_view == "bullish"


def test_minority_view_is_correct() -> None:
    reports = [
        _report("A", "bullish"),
        _report("B", "bullish"),
        _report("C", "neutral"),
        _report("D", "neutral"),
    ]
    result = aggregate_reports(reports)
    assert result.minority_view == "bullish" or result.minority_view == "neutral"


def test_no_minority_when_unanimous() -> None:
    reports = [
        _report("A", "neutral"),
        _report("B", "neutral"),
        _report("C", "neutral"),
        _report("D", "neutral"),
    ]
    result = aggregate_reports(reports)
    assert result.minority_view == "少数意見なし"
