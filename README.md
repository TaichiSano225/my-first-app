# Stock Pulse — 株価チェッカー

React（フロントエンド）+ FastAPI（バックエンド）で作る株価チェッカーです。
会社名から株価・買い時・企業情報を調べたり、予算と業界からおすすめ銘柄を探したりできます。
株価データは [yfinance](https://pypi.org/project/yfinance/)（Yahoo Finance）から取得します。

## 主な機能

### 🔍 銘柄を検索
- **あいまいな入力でOK** — 「apple」「トヨタ」「スタバ」「microsft（タイプミス）」などでも類推して表示
- **東証の全上場銘柄（約4,000社）に対応** — 日本語の会社名（例: 理研計器）や証券コード（例: 7734）で検索可能
- **現在価格・前日比**
- **買い時の判定** — 52週レンジ内の位置と移動平均線から「買い時／中立／高値圏」を判定し、**その根拠を文章で説明**
- **値動きの考察** — 直近の値動き・トレンド・ニュースから「なぜ動いたか」を推測して表示
- **今後の予想** — アナリストの目標株価・上振れ余地・評価
- **配当** — 配当利回り・1株あたり年間配当・1単元(100株)保有時の年間配当・配当性向・権利確定日
- **株主優待** — 日本株は Yahoo!ファイナンスの優待・配当ページへのリンクを表示（優待データは外部で確認）
- **企業概要（日本語）** — どんな会社かの説明
- **最近のトピック（日本語）** — 関連ニュースの見出し

### 💡 予算でおすすめ
- **予算を入力** すると、**日本企業**の中から買える銘柄を **買い時順に最大30社** 表示
- 固定リストではなく、**その時点の株価（市場状況）に基づいて動的に抽出**
- 業界を選んで絞り込むことも可能
- **企業名をクリックすると別タブで詳細**（どんな企業か・買い時・予想・ニュース）を表示
- 株価は一括取得＋キャッシュ＋起動時の先読みで **すばやく表示**

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

起動後、ブラウザで <https://localhost:3000> を開きます（**HTTPS**）。

> 🔒 自己署名証明書を使っているため、初回は「この接続ではプライバシーが保護されません」などの警告が出ます。
> 「詳細設定 →（このサイトに）アクセスする」で続行してください（ローカル/LAN 用のため問題ありません）。

- 停止: `Ctrl+C`（バックグラウンド起動した場合は `docker compose down`）
- バックグラウンド起動: `docker compose up --build -d`
- `http://localhost:3000` でアクセスしても自動で `https` に転送されます。

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

API はすべて `/api` 配下にあります。

| メソッド・パス | 説明 |
| --- | --- |
| `GET /api/stock/{symbol}` | 銘柄の詳細（株価・買い時・予想・配当・企業概要・ニュース）を返す |
| `GET /api/history/{symbol}?range=1mo\|3mo\|6mo\|1y\|5y\|max` | チャート用の株価推移を返す |
| `GET /api/sectors` | 業界（セクター）の一覧を返す |
| `GET /api/recommendations?budget=...&sector=...` | 予算内・買い時順（日本企業）のおすすめ銘柄を返す。`sector` は省略可（省略時は全業界） |
| `GET /docs` | API ドキュメント（Swagger UI） |

リクエスト例:

```bash
curl "http://localhost:8000/api/stock/apple"
curl "http://localhost:8000/api/recommendations?budget=500000"
curl "http://localhost:8000/api/recommendations?sector=テクノロジー&budget=300000"
```

## スマホで見る・インターネットに公開する

フロントエンドは API を相対パス（`/api`）で呼ぶため、どのホスト名・IPでアクセスしても動きます。

### 同じPCのブラウザ
<https://localhost:3000>（自己署名証明書のため初回は警告が出ます。続行でOK）

### スマホ（同じWi-Fi）から見る — WSL2 の場合
WSL2 は Windows 内の仮想ネットワークのため、スマホからは直接見えません。Windows 側で
ポート転送とファイアウォール許可を一度だけ設定します（PowerShell を**管理者**で実行）。

```powershell
# WSL の IP は WSL 内で `hostname -I` で確認（例: 172.27.174.148）
netsh interface portproxy add v4tov4 listenport=3000 listenaddress=0.0.0.0 connectport=3000 connectaddress=<WSLのIP>
netsh advfirewall firewall add rule name="StockPulse" dir=in action=allow protocol=TCP localport=3000
```

その後、スマホのブラウザで `https://<WindowsのLAN IP>:3000`（`ipconfig` で確認。例: `192.168.0.x`）を開きます。
※ 自己署名証明書のため警告が出ますが、続行すれば表示できます。
※ WSL の IP は再起動で変わることがあります。変わったら `portproxy` を設定し直してください。

### インターネットに公開する
- **手軽（ポート開放不要）**: [Cloudflare Tunnel](https://developers.cloudflare.com/cloudflare-tunnel/)。
  `cloudflared tunnel --url https://localhost:3000 --no-tls-verify` を実行すると、一時的な公開 URL（https）が発行され、外部から閲覧できます。
  ※ PC と Docker が起動している間だけ有効です。
- **恒久運用**: VPS に本リポジトリを置いて `docker compose up -d`、または下記の Render に無料デプロイ。

## クラウドに無料デプロイ（Render）

PC を起動していなくても 24 時間アクセスできるようにするには、クラウドにデプロイします。
本リポジトリには **React と FastAPI を 1 コンテナにまとめた構成**（`Dockerfile.web`）と
[Render](https://render.com) 用の `render.yaml` を同梱しています。

手順:

1. このリポジトリを GitHub に push する（済み）。
2. [Render](https://render.com) に GitHub アカウントで登録する。
3. ダッシュボードで **New → Blueprint** を選び、本リポジトリを指定する。
   `render.yaml` が読み込まれ、Web サービスが自動で作られる。
4. **Apply** を押すとビルド＆デプロイが始まり、`https://stock-pulse-xxxx.onrender.com` のような
   **正式HTTPSの公開URL**が発行される（証明書の警告なし）。

メモ:
- **無料プラン**は 15 分アクセスが無いとスリープし、次のアクセスで起動に数十秒かかります（個人利用なら十分）。
- 起動直後は全銘柄の株価を裏で先読みするため、最初の「おすすめ」表示まで少し時間がかかります。
- ローカルでも同じ 1 コンテナ構成を確認できます: `docker build -f Dockerfile.web -t stock-pulse-web . && docker run --rm -p 8000:8000 stock-pulse-web` → <http://localhost:8000>

## 注意事項

- 株価データは Yahoo Finance から取得しており、リアルタイムではなく遅延がある場合があります。
- データ取得のためインターネット接続が必要です。
- 「買い時」やおすすめは株価データに基づく簡易的な目安であり、投資助言ではありません。
