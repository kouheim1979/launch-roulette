# Stock Minority Report

## 1. アプリ概要
Stock Minority Report は、4つの独立した分析エージェント（Precog）から株式データを多面的に分析し、**Majority Report（多数意見）** と **Minority Report（少数意見）** を比較表示する、個人向けの株式分析ダッシュボードです。

> 重要: 本アプリは投資助言ではありません。売買推奨、自動売買、利益保証を目的としません。

## 2. 注意事項
- 本アプリの結果は分析材料であり、投資判断はご自身で行ってください。
- APIキーがなくても rule-based fallback で動作します。
- データ取得元（yfinance）の一時障害時は取得失敗する場合があります。

## 3. 機能一覧
- 日本株4桁コードを `.T` に正規化（例: `7203` -> `7203.T`）
- 米国株ティッカー対応（例: `AAPL`）
- yfinance による価格・企業情報・ニュース見出し取得
- テクニカル指標算出
  - 5/25/75日移動平均
  - RSI(14)
  - MACD / MACD Signal
  - 1日騰落率 / 20営業日騰落率
  - 25日線乖離率
  - 出来高20日平均 / 比率
  - 20日年率換算ボラティリティ
- 量的スコア（0〜100）
- 4 Precog 分析（OpenAI / Anthropic / Gemini / rule-based）
- AI失敗時の自動 fallback
- 集約表示
  - majority_view
  - minority_view
  - consensus_score
  - view_counts
  - majority_reasons
  - minority_reasons
  - watchpoints
- Plotly チャート
  - ローソク足 + 移動平均 + 出来高
  - RSI

## 4. ファイル構成
```text
stock-minority-report/
├─ app.py
├─ requirements.txt
├─ .env.example
├─ README.md
├─ .gitignore
├─ Dockerfile
├─ pyproject.toml
├─ .github/
│  └─ workflows/
│     └─ ci.yml
├─ src/
│  ├─ __init__.py
│  ├─ data_provider.py
│  ├─ indicators.py
│  ├─ scoring.py
│  ├─ ai_agents.py
│  ├─ aggregator.py
│  └─ charts.py
└─ tests/
   ├─ test_indicators.py
   ├─ test_scoring.py
   └─ test_aggregator.py
```

## 5. Windows PowerShellでのセットアップ
```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

## 6. APIキーなしで動かす方法
1. `.env` を作成（空でも可）
2. サイドバーで各Precogの provider を `rule-based` に設定
3. 分析実行

APIキー未設定でもアプリは落ちず、rule-based fallback を返します。

## 7. OpenAI / Claude / Gemini を使う方法
`.env` にキーを設定します。

```env
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...
GEMINI_API_KEY=...

OPENAI_MODEL=gpt-4.1-mini
ANTHROPIC_MODEL=claude-3-5-sonnet-latest
GEMINI_MODEL=gemini-1.5-pro
```

サイドバーで provider / model を指定し、分析実行してください。

## 8. 起動方法
```bash
pip install -r requirements.txt
streamlit run app.py
```

Docker起動:
```bash
docker build -t stock-minority-report .
docker run -p 8501:8501 --env-file .env stock-minority-report
```

## 9. 使い方
1. 銘柄コード / ティッカーを入力
2. 期間を選択（3mo, 6mo, 1y, 2y, 5y）
3. 各Precogの provider / model を指定
4. 「分析実行」ボタンを押下
5. メトリクス、チャート、各Precog判定、Majority/Minorityを確認

## 10. トラブルシューティング
- **銘柄入力エラー**: 空欄では実行不可。4桁数字か有効ティッカーを入力。
- **株価取得失敗**: ネットワークまたはyfinance一時障害。時間をおいて再試行。
- **指標計算エラー**: 期間を長めに変更（例: 1y）。
- **AI JSONエラー**: 自動でrule-based fallbackされます。
- **モデル名未入力**: fallbackされます。

## 11. 今後の拡張案
- センチメントをニュース本文ベースへ拡張
- ポートフォリオ監視（複数銘柄同時表示）
- 比較銘柄ベンチマーク
- バックテスト風の分析強化（推奨はしない）

## 12. J-Quants API対応方針
- `src/data_provider.py` をデータ取得層として分離済みです。
- 将来 `JQuantsProvider` を追加し、`YFinanceProvider` と差し替え可能な構造にできます。
- `fetch()` の戻り値を共通 `StockDataBundle` に統一しているため、UI/指標/AI側を変更せず拡張可能です。
