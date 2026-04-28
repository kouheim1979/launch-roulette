from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import pandas as pd
import yfinance as yf


class DataProviderError(Exception):
    """Base exception for data provider errors."""


class SymbolValidationError(DataProviderError):
    """Raised when symbol input is invalid."""


class DataFetchError(DataProviderError):
    """Raised when fetching data fails."""


@dataclass
class StockDataBundle:
    ticker: str
    price_df: pd.DataFrame
    company_info: dict[str, Any]
    news_headlines: list[str]


class YFinanceProvider:
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0) -> None:
        self.max_retries = max_retries
        self.retry_delay = retry_delay

    @staticmethod
    def normalize_symbol(raw_symbol: str) -> str:
        if raw_symbol is None:
            raise SymbolValidationError("銘柄コード / ティッカーが入力されていません。")

        symbol = raw_symbol.strip().upper()
        if not symbol:
            raise SymbolValidationError("銘柄コード / ティッカーが入力されていません。")

        if symbol.isdigit() and len(symbol) == 4:
            return f"{symbol}.T"
        return symbol

    def _download_history(self, ticker: str, period: str) -> pd.DataFrame:
        last_exception: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                data = yf.download(
                    ticker,
                    period=period,
                    interval="1d",
                    progress=False,
                    auto_adjust=False,
                    threads=False,
                )
                if isinstance(data, pd.DataFrame) and not data.empty:
                    data = data.reset_index()
                    if "Date" not in data.columns:
                        raise DataFetchError("日付列の取得に失敗しました。")
                    return data
            except Exception as exc:  # noqa: BLE001
                last_exception = exc

            if attempt < self.max_retries:
                time.sleep(self.retry_delay)

        message = "株価データの取得に失敗しました。時間をおいて再実行してください。"
        if last_exception:
            raise DataFetchError(f"{message} 原因: {last_exception}") from last_exception
        raise DataFetchError(message)

    @staticmethod
    def _extract_news_headlines(news_items: list[dict[str, Any]] | None) -> list[str]:
        if not news_items:
            return []
        headlines: list[str] = []
        for item in news_items[:20]:
            title = str(item.get("title", "")).strip()
            if title:
                headlines.append(title)
        return headlines

    def fetch(self, raw_symbol: str, period: str) -> StockDataBundle:
        ticker = self.normalize_symbol(raw_symbol)
        history = self._download_history(ticker=ticker, period=period)
        if history.empty:
            raise DataFetchError("株価データが空です。銘柄や期間を確認してください。")

        tk = yf.Ticker(ticker)
        try:
            info = tk.info if isinstance(tk.info, dict) else {}
        except Exception:  # noqa: BLE001
            info = {}
        try:
            news = tk.news if isinstance(tk.news, list) else []
        except Exception:  # noqa: BLE001
            news = []

        return StockDataBundle(
            ticker=ticker,
            price_df=history,
            company_info=info,
            news_headlines=self._extract_news_headlines(news),
        )
