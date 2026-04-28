from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any

VALID_VIEWS = {"bullish", "neutral", "bearish"}


@dataclass
class AggregateResult:
    majority_view: str
    minority_view: str
    consensus_score: float
    view_counts: dict[str, int]
    majority_reasons: list[str]
    minority_reasons: list[str]
    watchpoints: list[str]
    summary: str


def aggregate_reports(reports: list[dict[str, Any]]) -> AggregateResult:
    if not reports:
        raise ValueError("AIレポートが空です。")

    sanitized: list[dict[str, Any]] = []
    for report in reports:
        view = str(report.get("view", "neutral")).lower()
        if view not in VALID_VIEWS:
            view = "neutral"
        confidence = int(report.get("confidence", 50))
        confidence = max(0, min(100, confidence))
        sanitized.append({**report, "view": view, "confidence": confidence})

    view_counts = Counter(item["view"] for item in sanitized)

    sorted_majority = sorted(view_counts.items(), key=lambda x: (-x[1], x[0]))
    majority_view = sorted_majority[0][0]

    minority_candidates = [v for v, c in view_counts.items() if c == min(view_counts.values())]
    if len(view_counts) == 1:
        minority_view = "少数意見なし"
    else:
        minority_view = sorted(minority_candidates)[0]

    weighted_map: dict[str, float] = defaultdict(float)
    for item in sanitized:
        weighted_map[item["view"]] += float(item["confidence"])

    total_conf = sum(item["confidence"] for item in sanitized)
    majority_conf = weighted_map.get(majority_view, 0.0)
    consensus_score = round((majority_conf / total_conf) * 100, 2) if total_conf > 0 else 0.0

    majority_reasons: list[str] = []
    minority_reasons: list[str] = []
    watchpoints: list[str] = []

    for item in sanitized:
        summary = str(item.get("summary", "")).strip()
        if item["view"] == majority_view and summary:
            majority_reasons.append(f"{item.get('agent_name', 'Agent')}: {summary}")
        if minority_view != "少数意見なし" and item["view"] == minority_view and summary:
            minority_reasons.append(f"{item.get('agent_name', 'Agent')}: {summary}")

        for wp in item.get("watchpoints", []):
            wp_text = str(wp).strip()
            if wp_text:
                watchpoints.append(wp_text)

    unique_watchpoints = list(dict.fromkeys(watchpoints))

    if minority_view == "少数意見なし":
        summary = f"4つの視点が一致し、主要見解は {majority_view} です。"
    else:
        summary = (
            f"主要見解は {majority_view}（{view_counts[majority_view]}件）です。"
            f" 一方で少数見解 {minority_view} も存在し、反対シナリオの監視が必要です。"
        )

    return AggregateResult(
        majority_view=majority_view,
        minority_view=minority_view,
        consensus_score=consensus_score,
        view_counts=dict(view_counts),
        majority_reasons=majority_reasons,
        minority_reasons=minority_reasons,
        watchpoints=unique_watchpoints,
        summary=summary,
    )
