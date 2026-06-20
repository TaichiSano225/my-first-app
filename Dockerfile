FROM python:3.11-slim

# Python の出力をバッファリングしない / .pyc を作らない
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 依存だけ先にインストールしてレイヤキャッシュを効かせる
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリ本体をコピー
COPY app.py main.py jp_stocks.json ./
COPY templates ./templates

EXPOSE 8000

# 本番起動（リロードなし）
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
