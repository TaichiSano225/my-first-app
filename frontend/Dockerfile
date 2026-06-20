# --- ビルド工程: React を静的ファイル(HTML/JS/CSS)に変換する ---
FROM node:22-slim AS build
WORKDIR /app

# 依存だけ先に入れてレイヤキャッシュを効かせる
COPY package.json package-lock.json ./
RUN npm ci

# ソースをコピーして本番ビルド → /app/dist が成果物
COPY . .
RUN npm run build

# --- 配信工程: 軽量な nginx で静的ファイルを配る ---
FROM nginx:1.27-alpine

# 自前の nginx 設定（静的配信 + /api をバックエンドへ中継）
COPY nginx.conf /etc/nginx/conf.d/default.conf

# ビルド成果物だけを配信ディレクトリにコピー
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
