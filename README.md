# Stock Pulse — 株価チェッカー

React（フロントエンド）+ FastAPI（バックエンド）で作る株価チェッカーです。
会社名から株価・買い時・企業情報を調べたり、予算と業界からおすすめ銘柄を探したりできます。
株価データは [yfinance](https://pypi.org/project/yfinance/)（Yahoo Finance）から取得します。

## 主な機能

### 🔍 銘柄を検索
- **あいまいな入力でOK** — 「apple」「トヨタ」「スタバ」「microsft（タイプミス）」などでも類推して表示
- **現在価格・前日比**
- **買い時の判定** — 52週レンジ内の位置と移動平均線から「買い時／中立／高値圏」を表示
- **今後の予想** — アナリストの目標株価・上振れ余地・評価
- **企業概要** — どんな会社かの説明
- **最近のトピック** — 関連ニュースの見出し

### 💡 予算でおすすめ
- **業界を選んで予算を入力** すると、その業界で買える銘柄を **買い時順に 20〜30 社** 表示
- 株価を一括取得して集計するので **数秒で表示**

> ⚠️ いずれも Yahoo Finance のデータに基づく参考情報です。投資はご自身の判断と責任で行ってください。

## 構成

```
my-first-app/
├── main.py              # backend: FastAPI（API エントリ）
├── app.py               # backend: 株価取得・買い時判定・スクリーニング
├── requirements.txt
├── Dockerfile           # backend イメージ（uvicorn で起動）
├── docker-compose.yml   # backend + frontend をまとめて起動
└── frontend/            # React アプリ（Vite）
    ├── Dockerfile       # frontend イメージ（ビルド → nginx で配信）
    ├── nginx.conf       # 静的配信 + /api をバックエンドへ中継
    └── src/
        ├── App.jsx          # タブ（検索 / おすすめ）
        ├── StockSearch.jsx  # 銘柄検索の画面
        ├── Recommend.jsx    # 予算おすすめの画面
        ├── RangeBar.jsx     # 52週レンジ表示
        └── utils.js         # 共通処理
```

- **backend コンテナ**: FastAPI（株価 API）。ポート 8000。
- **frontend コンテナ**: React のビルド成果物を nginx で配信。ポート 3000。
  `/api/...` へのリクエストは nginx が backend へ中継するため、ブラウザは frontend だけと通信すれば動きます（CORS 不要）。

## 起動方法（Docker Compose）

**Docker さえ入っていれば**、Python や Node.js を用意せずに起動できます。

```bash
# 1. リポジトリを取得
git clone https://github.com/TaichiSano225/my-first-app.git
cd my-first-app

# 2. 両方のコンテナをビルドして起動
docker compose up --build
```

起動後、ブラウザで <http://localhost:3000> を開きます。

- 停止: `Ctrl+C`（バックグラウンド起動した場合は `docker compose down`）
- バックグラウンド起動: `docker compose up --build -d`

## 開発（ホットリロード）

画面を編集しながら確認したいときは、Vite の開発サーバーを使います。

```bash
# ターミナル1: バックエンドだけ起動
docker compose up backend          # → http://localhost:8000

# ターミナル2: フロントエンドを開発モードで起動
cd frontend
npm install                        # 初回だけ
npm run dev                        # → http://localhost:5173
```

開発サーバー（5173）への `/api` 呼び出しは、Vite が backend（8000）へ転送します。

## API

| メソッド・パス | 説明 |
| --- | --- |
| `GET /stock/{symbol}` | 銘柄の詳細（株価・買い時・予想・企業概要・ニュース）を返す |
| `GET /sectors` | 業界（セクター）の一覧を返す |
| `GET /recommendations?sector=...&budget=...` | 指定業界で予算内・買い時順のおすすめ銘柄を返す |
| `GET /docs` | API ドキュメント（Swagger UI） |

リクエスト例:

```bash
curl "http://localhost:8000/stock/apple"
curl "http://localhost:8000/recommendations?sector=テクノロジー&budget=300000"
```

## 注意事項

- 株価データは Yahoo Finance から取得しており、リアルタイムではなく遅延がある場合があります。
- データ取得のためインターネット接続が必要です。
- 「買い時」やおすすめは株価データに基づく簡易的な目安であり、投資助言ではありません。
