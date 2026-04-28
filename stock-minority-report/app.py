from __future__ import annotations

import os
import traceback
from typing import Any

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

from src.aggregator import AggregateResult, aggregate_reports
from src.ai_agents import AgentConfig, run_agent
from src.charts import create_price_figure, create_rsi_figure
from src.data_provider import DataFetchError, SymbolValidationError, YFinanceProvider
from src.indicators import IndicatorError, enrich_with_indicators
from src.scoring import ScoringError, calculate_quant_score

load_dotenv()


AGENTS = [
    ("Precog A / Technical", "テクニカル分析官", "短期〜中期"),
    ("Precog B / Fundamental", "ファンダメンタル分析官", "中期"),
    ("Precog C / Risk", "リスク審査官", "短期〜中期"),
    ("Precog D / Sentiment", "ニュース・センチメント分析官", "短期"),
]


def sentiment_from_headlines(headlines: list[str]) -> float:
    positive_words = ["gain", "beat", "growth", "up", "strong", "record", "surge", "expand"]
    negative_words = ["miss", "down", "risk", "weak", "lawsuit", "fall", "decline", "cut"]

    if not headlines:
        return 0.0

    pos = 0
    neg = 0
    for h in headlines:
        text = h.lower()
        pos += sum(1 for w in positive_words if w in text)
        neg += sum(1 for w in negative_words if w in text)

    total = pos + neg
    if total == 0:
        return 0.0
    return (pos - neg) / total


def get_latest_metrics(df: pd.DataFrame) -> dict[str, Any]:
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) >= 2 else latest
    prev_close = float(prev["Close"])
    close = float(latest["Close"])
    diff = close - prev_close
    diff_pct = (diff / prev_close * 100) if prev_close else 0.0

    return {
        "close": close,
        "diff": diff,
        "diff_pct": diff_pct,
        "rsi_14": float(latest.get("rsi_14", 50.0)),
        "return_20d_pct": float(latest.get("return_20d_pct", 0.0)),
        "deviation_25d_pct": float(latest.get("deviation_25d_pct", 0.0)),
        "volume_ratio_20": float(latest.get("volume_ratio_20", 1.0)),
        "volatility_20_annualized": float(latest.get("volatility_20_annualized", 0.0)),
    }


def view_color(view: str) -> str:
    if view == "bullish":
        return "#1DB954"
    if view == "bearish":
        return "#E74C3C"
    return "#F1C40F"


def render_agent_card(report: dict[str, Any]) -> None:
    color = view_color(str(report.get("view", "neutral")))
    st.markdown(
        f"""
<div style="border:1px solid {color}; border-radius:12px; padding:12px; margin-bottom:12px;">
  <h4 style="margin:0 0 8px 0; color:{color};">{report.get("agent_name")} ({report.get("view")})</h4>
  <p><b>役割:</b> {report.get("role")} / <b>確信度:</b> {report.get("confidence")}</p>
  <p>{report.get("summary")}</p>
</div>
        """,
        unsafe_allow_html=True,
    )
    st.write("**プラス要因**", report.get("positive_factors", []))
    st.write("**マイナス要因**", report.get("negative_factors", []))
    st.write("**監視ポイント**", report.get("watchpoints", []))


def main() -> None:
    st.set_page_config(page_title="Stock Minority Report", layout="wide")
    st.title("📊 Stock Minority Report")
    st.caption(
        "本アプリは投資判断の補助を目的とした分析ダッシュボードです。"
        "売買推奨・利益保証・自動売買は行いません。"
    )

    st.markdown(
        """
<style>
.block-container {padding-top: 1.2rem;}
h1, h2, h3 {letter-spacing: 0.5px;}
</style>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.header("設定")
        symbol_input = st.text_input("銘柄コード / ティッカー", value="AAPL")
        period = st.selectbox("取得期間", ["3mo", "6mo", "1y", "2y", "5y"], index=2)

        providers = ["rule-based", "openai", "anthropic", "gemini"]
        agent_settings: list[AgentConfig] = []

        for idx, (agent_name, role, horizon) in enumerate(AGENTS):
            st.subheader(agent_name)
            provider = st.selectbox(
                f"{agent_name} provider",
                providers,
                index=0,
                key=f"provider_{idx}",
            )
            default_model = os.getenv(
                {
                    "openai": "OPENAI_MODEL",
                    "anthropic": "ANTHROPIC_MODEL",
                    "gemini": "GEMINI_MODEL",
                }.get(provider, "OPENAI_MODEL"),
                "",
            )
            model = st.text_input(f"{agent_name} model", value=default_model, key=f"model_{idx}")
            agent_settings.append(
                AgentConfig(
                    agent_name=agent_name,
                    role=role,
                    time_horizon=horizon,
                    provider=provider,
                    model=model,
                )
            )

        run_button = st.button("分析実行", type="primary")

    if not run_button:
        st.info("サイドバーで条件を設定し『分析実行』を押してください。")
        return

    try:
        provider = YFinanceProvider(max_retries=3, retry_delay=1.0)
        data_bundle = provider.fetch(symbol_input, period)

        indicator_df = enrich_with_indicators(data_bundle.price_df)
        score_result = calculate_quant_score(indicator_df)
        metrics = get_latest_metrics(indicator_df)

        context = {
            "ticker": data_bundle.ticker,
            "company_name": data_bundle.company_info.get("longName", "N/A"),
            "sector": data_bundle.company_info.get("sector", "N/A"),
            "trailingPE": data_bundle.company_info.get("trailingPE"),
            "priceToBook": data_bundle.company_info.get("priceToBook"),
            "returnOnEquity": data_bundle.company_info.get("returnOnEquity"),
            "marketCap": data_bundle.company_info.get("marketCap"),
            "dividendYield": data_bundle.company_info.get("dividendYield"),
            "news_headlines": data_bundle.news_headlines[:10],
            **metrics,
        }
        context["sentiment_score"] = sentiment_from_headlines(data_bundle.news_headlines)

        reports = [run_agent(cfg, context) for cfg in agent_settings]
        aggregated: AggregateResult = aggregate_reports(reports)

        c1, c2, c3, c4, c5, c6 = st.columns(6)
        c1.metric("Ticker", data_bundle.ticker)
        c2.metric("終値", f"{metrics['close']:.2f}")
        c3.metric("前日比", f"{metrics['diff']:.2f} ({metrics['diff_pct']:.2f}%)")
        c4.metric("分析上の強さ", f"{score_result.score}/100")
        c5.metric("RSI", f"{metrics['rsi_14']:.2f}")
        c6.metric("20日騰落率", f"{metrics['return_20d_pct']:.2f}%")

        c7, c8 = st.columns(2)
        c7.metric("25日線乖離率", f"{metrics['deviation_25d_pct']:.2f}%")
        c8.metric("出来高倍率", f"{metrics['volume_ratio_20']:.2f}x")

        st.plotly_chart(create_price_figure(indicator_df, data_bundle.ticker), use_container_width=True)
        st.plotly_chart(create_rsi_figure(indicator_df, data_bundle.ticker), use_container_width=True)

        pcol, ncol = st.columns(2)
        with pcol:
            st.subheader("量的分析のプラス要因")
            st.write(score_result.positives)
        with ncol:
            st.subheader("量的分析のマイナス要因")
            st.write(score_result.negatives)

        st.subheader("各Precogの独立判断")
        for rep in reports:
            render_agent_card(rep)

        st.subheader("Majority Report")
        st.success(f"見解: {aggregated.majority_view} / 合意スコア: {aggregated.consensus_score}%")
        st.write("理由:", aggregated.majority_reasons)

        st.subheader("Minority Report")
        if aggregated.minority_view == "少数意見なし":
            st.info("少数意見なし（全員一致）")
        else:
            st.warning(f"少数意見: {aggregated.minority_view}")
            st.write("理由:", aggregated.minority_reasons)

        st.subheader("全体監視ポイント")
        st.error(aggregated.watchpoints)

        st.subheader("デバッグ用コンテキスト")
        st.json(
            {
                "context": context,
                "view_counts": aggregated.view_counts,
                "aggregate_summary": aggregated.summary,
                "reports": reports,
            }
        )

    except SymbolValidationError as exc:
        st.error(str(exc))
    except DataFetchError as exc:
        st.error(f"株価データ取得失敗: {exc}")
    except IndicatorError as exc:
        st.error(f"指標計算エラー: {exc}")
    except ScoringError as exc:
        st.error(f"スコア計算エラー: {exc}")
    except Exception as exc:  # noqa: BLE001
        st.error(f"予期しない例外が発生しました: {exc}")
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
