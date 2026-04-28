from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def create_price_figure(df: pd.DataFrame, ticker: str) -> go.Figure:
    fig = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.07,
        row_heights=[0.7, 0.3],
    )

    fig.add_trace(
        go.Candlestick(
            x=df["Date"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            name="Candlestick",
        ),
        row=1,
        col=1,
    )

    fig.add_trace(go.Scatter(x=df["Date"], y=df["ma_5"], name="MA5", mode="lines"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["ma_25"], name="MA25", mode="lines"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["ma_75"], name="MA75", mode="lines"), row=1, col=1)

    fig.add_trace(
        go.Bar(x=df["Date"], y=df["Volume"], name="Volume", marker_color="#3A6EA5"),
        row=2,
        col=1,
    )

    fig.update_layout(
        title=f"{ticker} Price / Moving Averages / Volume",
        xaxis_rangeslider_visible=False,
        template="plotly_dark",
        height=700,
    )
    return fig


def create_rsi_figure(df: pd.DataFrame, ticker: str) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["Date"], y=df["rsi_14"], mode="lines", name="RSI 14"))
    fig.add_hline(y=70, line_dash="dash", line_color="red")
    fig.add_hline(y=30, line_dash="dash", line_color="green")
    fig.update_layout(
        title=f"{ticker} RSI (14)",
        yaxis_title="RSI",
        template="plotly_dark",
        height=300,
    )
    return fig
