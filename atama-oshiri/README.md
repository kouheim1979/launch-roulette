# あたまとおしり

最初の文字（あたま）と最後の文字（おしり）が決まったお題に、あいだを埋めて言葉をつくる言葉あそびゲーム。

- ひとりで：60秒でたくさん答えてスコアを競う
- みんなで：お題を出して口で答える早い者勝ち
- 文字数しばりモードあり

## Webアプリとして

ビルド不要の静的サイトです。スマホのブラウザで開いて「ホーム画面に追加」すると、アプリのように全画面で起動し、オフラインでも遊べます（PWA）。

## 公開（GitHub Pages）

`main` に push すると `.github/workflows/atama-oshiri-pages.yml` が `atama-oshiri/` を GitHub Pages の `/launch-roulette/atama-oshiri/` に公開します（トップの `/launch-roulette/` はゲームへ自動で移動します）。
初回だけ、リポジトリの Settings → Pages → Build and deployment の Source を「GitHub Actions」にしてください。

公開先: `https://kouheim1979.github.io/launch-roulette/atama-oshiri/`

## ローカルで動かす

```sh
cd atama-oshiri
python3 -m http.server 8000
# http://localhost:8000 を開く
```
