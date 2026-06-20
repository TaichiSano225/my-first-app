# --- ビルド工程: React を静的ファイル(HTML/JS/CSS)に変換する ---
FROM node:22-slim AS build
WORKDIR /app

# 依存だけ先に入れてレイヤキャッシュを効かせる
COPY package.json package-lock.json ./
RUN npm ci

# ソースをコピーして本番ビルド → /app/dist が成果物
COPY . .
RUN npm run build

# --- 配信工程: 軽量な nginx で静的ファイルを HTTPS で配る ---
FROM nginx:1.27-alpine

# HTTPS 用の自己署名証明書を生成する（LAN/ローカル向け。ブラウザは初回警告を出す）
RUN apk add --no-cache openssl && \
    mkdir -p /etc/nginx/certs && \
    openssl req -x509 -nodes -newkey rsa:2048 -days 825 \
      -keyout /etc/nginx/certs/server.key \
      -out /etc/nginx/certs/server.crt \
      -subj "/CN=stock-pulse" \
      -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

# 自前の nginx 設定（HTTPS 配信 + /api をバックエンドへ中継）
COPY nginx.conf /etc/nginx/conf.d/default.conf

# ビルド成果物だけを配信ディレクトリにコピー
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 443
