# my-first-app

会社名またはティッカーシンボルから株価情報を取得するコマンドラインツールです。
データ取得には [yfinance](https://pypi.org/project/yfinance/)（Yahoo Finance）を利用しています。

## セットアップ

```bash
pip install -r requirements.txt
```

## Webアプリ（FastAPI）

[FastAPI](https://fastapi.tiangolo.com/) 製の Web アプリです。ブラウザから銘柄を入力して株価を確認できます。

### 起動方法

```bash
# どちらでも起動できます
python main.py
# または uvicorn で（自動リロード付き）
uvicorn main:app --reload
```

起動後、ブラウザで <http://localhost:8000> を開きます。
API ドキュメント（Swagger UI）は <http://localhost:8000/docs> で確認できます。

### 画面（HTML）

- **株価検索** (`/`): 会社名・ティッカーを入力して最新株価を表示。
- **予算で銘柄を探す** (`/recommend`): 予算（円）を入力すると、予算内で購入可能な銘柄をアナリスト評価順に表示。

### API（JSON）

| メソッド・パス | 説明 |
| --- | --- |
| `GET /stock/{symbol}` | 指定銘柄の株価を JSON で返す |

リクエスト例:

```bash
curl http://localhost:8000/stock/AAPL
```

レスポンス例:

```json
{
  "symbol": "AAPL",
  "name": "Apple Inc.",
  "price": 203.52,
  "prev_close": 201.00,
  "change": 2.52,
  "change_pct": 1.25,
  "currency": "USD"
}
```

銘柄が見つからない場合は HTTP 404 を返します。

> 日本語の会社名（例: 「トヨタ」）は Yahoo Finance の検索が対応していない場合があります。
> 日本株は `7203.T` のようにティッカーで直接指定してください。

---

## React + FastAPI（Docker Compose で起動）

React 製のフロントエンドと FastAPI 製のバックエンドを、それぞれ別コンテナで動かす構成です。
**Docker さえ入っていれば**、Python や Node.js を用意しなくても、どのPCでも同じように起動できます。

### 構成

```
my-first-app/
├── Dockerfile           # backend: FastAPI を uvicorn で起動
├── docker-compose.yml   # backend + frontend をまとめて起動
└── frontend/            # React アプリ
    ├── Dockerfile       # frontend: React をビルドし nginx で配信
    └── nginx.conf       # 静的配信 + /api をバックエンドへ中継
```

- **backend コンテナ**: FastAPI（株価取得 API）。ポート 8000。
- **frontend コンテナ**: React のビルド成果物を nginx で配信。ポート 3000。
  `/api/...` へのリクエストは nginx が backend コンテナへ中継するため、ブラウザは frontend だけと通信すれば動きます（CORS 設定が不要）。

### 起動方法

```bash
# 1. リポジトリを取得
git clone https://github.com/TaichiSano225/my-first-app.git
cd my-first-app

# 2. 両方のコンテナをビルドして起動
docker compose up --build
```

起動後、ブラウザで <http://localhost:3000> を開きます。銘柄を入力して検索すると、会社名・現在価格・前日終値・前日比が表示されます。

| URL | 内容 |
| --- | --- |
| <http://localhost:3000> | React の画面（銘柄入力 → 株価表示） |
| <http://localhost:3000/api/stock/AAPL> | frontend 経由で叩いた API（nginx が中継） |
| <http://localhost:8000/stock/AAPL> | backend を直接叩いた API |
| <http://localhost:8000/docs> | API ドキュメント（Swagger UI） |

停止は `Ctrl+C`、コンテナの削除は別ターミナルで `docker compose down`。
バックグラウンドで起動するなら `docker compose up --build -d` を使います。

### フロントエンドだけ開発する場合（ホットリロード）

画面を編集しながら確認したいときは、Vite の開発サーバーを使います。

```bash
# ターミナル1: バックエンドだけ起動
docker compose up backend

# ターミナル2: フロントエンドを開発モードで起動
cd frontend
npm install   # 初回だけ
npm run dev   # → http://localhost:5173
```

開発サーバー（5173）への `/api` 呼び出しは、Vite が backend（8000）へ転送します。

---

## コマンドラインでの使い方

### 1. 引数で指定する

会社名やティッカーを引数として渡します。複数同時に指定できます。

```bash
python app.py AAPL
python app.py Apple トヨタ
python app.py 7203.T
```

### 2. 対話モードで入力する

引数なしで実行すると、入力を求められます。

```bash
python app.py
```

```
会社名またはティッカーを入力してください (例: Apple, トヨタ, AAPL): Apple
```

カンマ区切りで複数の銘柄をまとめて入力できます。

```
会社名またはティッカーを入力してください (例: Apple, トヨタ, AAPL): Apple, トヨタ, AAPL
```

会社名で複数の候補が見つかった場合は、対話モードでは一覧から番号を選択できます
（Enter のみで先頭の候補を選択）。

> 株価は `fast_info` を用いて可能な限り最新の値を取得します。

### 3. 予算から購入候補を表示する（推奨銘柄モード）

予算内で購入可能な銘柄を、Yahoo Finance のアナリスト評価順に表示します。
デフォルトの予算は 50 万円、対象は主要銘柄のウォッチリストです。

```bash
# 予算50万円（デフォルト）で表示
python app.py --recommend

# 予算を指定（「30万」「300000」「300,000」いずれもOK）
python app.py --recommend --budget 300000
python app.py -r -b 30万

# 対象銘柄を自分で指定する
python app.py --recommend AAPL MSFT 7203.T
```

出力例:

```
========================================================================
  予算 500,000 円で購入可能な銘柄（アナリスト評価順）
========================================================================
  銘柄         評価           上振れ        最低購入額  購入可能数
  --------------------------------------------------------------------
★ MSFT       強い買い        +48%      61,188円  8株
★ NVDA       強い買い        +42%      33,979円  14株
★ 7203.T     買い          +33%     277,650円  1単元(100株)
  --------------------------------------------------------------------
  ★ 本日の注目（買い評価）: ...
```

- **評価**: アナリストのコンセンサス（強い買い / 買い / 中立 / 売り など）。`★` は買い以上。
- **上振れ**: 目標株価平均に対する現在値からの上振れ余地。
- **最低購入額**: 1単元あたりの購入金額（日本株は単元株 100 株、米国株は 1 株）。米ドル建ては円換算して比較します。
- 予算内で 1 単元すら買えない銘柄は除外されます。

> ⚠️ **注意**: 本機能は Yahoo Finance のアナリスト評価データに基づく**参考情報**であり、投資助言ではありません。投資判断はご自身の責任で行ってください。

## 入力例

| 入力 | 説明 |
| --- | --- |
| `AAPL` | ティッカーを直接指定 |
| `Apple` | 英語の会社名で検索 |
| `トヨタ` | 日本語の会社名で検索 |
| `7203.T` | 日本株のティッカー（`.T` は東証） |

## 出力例

```
=============================================
  Apple Inc. (AAPL)
=============================================
  現在値:   195.89 USD
  前日比:   +2.34 (+1.21%)
  前日終値: 193.55 USD
  52週高値: 237.49 USD
  52週安値: 164.08 USD
  時価総額: 2.98兆 USD
=============================================
```

表示される項目: 現在値 / 前日比 / 前日終値 / 52週高値・安値 / 時価総額

## 注意事項

- 株価データは Yahoo Finance から取得しており、リアルタイムではなく遅延がある場合があります。
- ネットワーク接続が必要です。
- 銘柄が見つからない場合は、その旨が表示されます。
