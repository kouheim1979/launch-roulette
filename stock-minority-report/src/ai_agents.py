from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import google.generativeai as genai
from anthropic import Anthropic
from openai import OpenAI


@dataclass(frozen=True)
class AgentConfig:
    agent_name: str
    role: str
    time_horizon: str
    provider: str
    model: str


class AIAgentError(Exception):
    """Raised when AI agent execution fails."""


def _safe_int(value: Any, default: int = 50) -> int:
    try:
        num = int(value)
    except (TypeError, ValueError):
        num = default
    return max(0, min(100, num))


def _default_payload(config: AgentConfig) -> dict[str, Any]:
    return {
        "agent_name": config.agent_name,
        "role": config.role,
        "view": "neutral",
        "confidence": 50,
        "summary": "データ不足またはAI呼び出し失敗のため、中立評価を返します。",
        "positive_factors": ["大きな偏りを避けるため中立で評価"],
        "negative_factors": ["追加データが必要"],
        "watchpoints": ["次回データ更新時に再評価"],
        "time_horizon": config.time_horizon,
    }


def _validate_response_json(result: dict[str, Any], config: AgentConfig) -> dict[str, Any]:
    payload = _default_payload(config)
    payload.update(result)

    if payload.get("view") not in {"bullish", "neutral", "bearish"}:
        payload["view"] = "neutral"
    payload["confidence"] = _safe_int(payload.get("confidence"), default=50)

    for key in ["positive_factors", "negative_factors", "watchpoints"]:
        val = payload.get(key)
        if not isinstance(val, list):
            payload[key] = [str(val)] if val else []

    payload["agent_name"] = config.agent_name
    payload["role"] = config.role
    payload["time_horizon"] = config.time_horizon
    return payload


def _build_prompt(config: AgentConfig, context: dict[str, Any]) -> str:
    return (
        "あなたは株式分析ダッシュボードのAIエージェントです。"
        "売買推奨はせず、分析材料と注意点のみを返してください。\n"
        "必ずJSONのみを返してください。\n"
        "出力形式:\n"
        "{\n"
        f'  "agent_name": "{config.agent_name}",\n'
        f'  "role": "{config.role}",\n'
        '  "view": "bullish | neutral | bearish",\n'
        '  "confidence": 0,\n'
        '  "summary": "1〜3文の要約",\n'
        '  "positive_factors": ["..."],\n'
        '  "negative_factors": ["..."],\n'
        '  "watchpoints": ["..."],\n'
        f'  "time_horizon": "{config.time_horizon}"\n'
        "}\n"
        f"コンテキスト: {json.dumps(context, ensure_ascii=False)}"
    )


def _call_openai(model: str, prompt: str, api_key: str) -> str:
    client = OpenAI(api_key=api_key, timeout=20.0)
    resp = client.responses.create(
        model=model,
        input=prompt,
        temperature=0.2,
    )
    return resp.output_text


def _call_anthropic(model: str, prompt: str, api_key: str) -> str:
    client = Anthropic(api_key=api_key, timeout=20.0)
    resp = client.messages.create(
        model=model,
        max_tokens=800,
        temperature=0.2,
        messages=[{"role": "user", "content": prompt}],
    )
    chunks: list[str] = []
    for item in resp.content:
        text = getattr(item, "text", "")
        if text:
            chunks.append(text)
    return "".join(chunks)


def _call_gemini(model: str, prompt: str, api_key: str) -> str:
    genai.configure(api_key=api_key)
    client = genai.GenerativeModel(model)
    resp = client.generate_content(prompt)
    text = getattr(resp, "text", "")
    if not text:
        raise AIAgentError("Geminiのレスポンスが空です。")
    return text


def _extract_json(text: str) -> dict[str, Any]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.replace("```json", "").replace("```", "").strip()
    return json.loads(stripped)


def _rule_based_report(config: AgentConfig, context: dict[str, Any], reason: str = "") -> dict[str, Any]:
    rsi = float(context.get("rsi_14", 50))
    ret20 = float(context.get("return_20d_pct", 0))
    dev = float(context.get("deviation_25d_pct", 0))
    vol_ratio = float(context.get("volume_ratio_20", 1))
    volatility = float(context.get("volatility_20_annualized", 20))
    sentiment = float(context.get("sentiment_score", 0))

    view = "neutral"
    confidence = 55
    positives: list[str] = []
    negatives: list[str] = []
    watchpoints: list[str] = []

    if "Technical" in config.agent_name:
        if ret20 > 5 and rsi < 70:
            view = "bullish"
            confidence = 70
            positives.extend(["20日騰落率がプラス", "RSIが過熱圏外"])
        elif ret20 < -5:
            view = "bearish"
            confidence = 70
            negatives.extend(["20日騰落率がマイナス", "トレンドが弱い"])

    elif "Fundamental" in config.agent_name:
        pe = context.get("trailingPE")
        roe = context.get("returnOnEquity")
        div = context.get("dividendYield")
        if isinstance(roe, (int, float)) and roe > 0.1:
            positives.append("ROEが比較的高い")
        if isinstance(div, (int, float)) and div > 0.02:
            positives.append("配当利回りが一定水準")
        if isinstance(pe, (int, float)) and pe > 35:
            negatives.append("PERが高め")
        if positives and not negatives:
            view = "bullish"
            confidence = 63
        elif negatives and not positives:
            view = "bearish"
            confidence = 60

    elif "Risk" in config.agent_name:
        if rsi > 75 or volatility > 45 or dev > 12:
            view = "bearish"
            confidence = 72
            negatives.extend(["過熱または高ボラティリティ", "急反落リスク"])
            watchpoints.append("短期的な利益確定売りに注意")
        elif rsi < 35 and ret20 < 0:
            view = "neutral"
            confidence = 58
            watchpoints.append("下落継続か反発かの見極めが必要")

    elif "Sentiment" in config.agent_name:
        if sentiment > 0.2:
            view = "bullish"
            confidence = 62
            positives.append("ニュース見出しはややポジティブ")
        elif sentiment < -0.2:
            view = "bearish"
            confidence = 62
            negatives.append("ニュース見出しはややネガティブ")

    if vol_ratio < 0.8:
        watchpoints.append("出来高減少でトレンドの持続性に注意")
    if not positives:
        positives.append("明確な好材料は限定的")
    if not negatives:
        negatives.append("明確な悪材料は限定的")
    if not watchpoints:
        watchpoints.append("次回決算・マクロイベントを監視")

    fallback_info = f"（fallback理由: {reason}）" if reason else ""
    summary = f"{config.role}として{view}寄りに評価。主要指標を踏まえた暫定判断です。{fallback_info}"

    return {
        "agent_name": config.agent_name,
        "role": config.role,
        "view": view,
        "confidence": confidence,
        "summary": summary,
        "positive_factors": positives,
        "negative_factors": negatives,
        "watchpoints": watchpoints,
        "time_horizon": config.time_horizon,
    }


def run_agent(config: AgentConfig, context: dict[str, Any]) -> dict[str, Any]:
    provider = config.provider.lower().strip()
    model = config.model.strip()

    if not model:
        return _rule_based_report(config, context, reason="モデル名未入力")

    if provider == "rule-based":
        return _rule_based_report(config, context)

    prompt = _build_prompt(config, context)

    try:
        if provider == "openai":
            api_key = os.getenv("OPENAI_API_KEY", "").strip()
            if not api_key:
                return _rule_based_report(config, context, reason="OPENAI_API_KEY未設定")
            raw = _call_openai(model=model, prompt=prompt, api_key=api_key)
        elif provider == "anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
            if not api_key:
                return _rule_based_report(config, context, reason="ANTHROPIC_API_KEY未設定")
            raw = _call_anthropic(model=model, prompt=prompt, api_key=api_key)
        elif provider == "gemini":
            api_key = os.getenv("GEMINI_API_KEY", "").strip()
            if not api_key:
                return _rule_based_report(config, context, reason="GEMINI_API_KEY未設定")
            raw = _call_gemini(model=model, prompt=prompt, api_key=api_key)
        else:
            return _rule_based_report(config, context, reason="未対応プロバイダ")

        parsed = _extract_json(raw)
        return _validate_response_json(parsed, config)
    except TimeoutError:
        return _rule_based_report(config, context, reason="AI呼び出しタイムアウト")
    except json.JSONDecodeError:
        return _rule_based_report(config, context, reason="AI応答がJSONでない")
    except Exception as exc:  # noqa: BLE001
        return _rule_based_report(config, context, reason=f"AI呼び出し失敗: {exc}")
