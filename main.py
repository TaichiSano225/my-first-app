import os
import threading
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import (
    SECTOR_TICKERS,
    fetch_history,
    fetch_stock_detail,
    market_overview,
    quotes,
    resolve_ticker,
    screen_recommendations,
    suggest,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """起動時に全銘柄の株価を裏で先読みし、初回のおすすめ表示を速くする。"""
    def _warm():
        try:
            screen_recommendations(300000)
        except Exception:
            pass

    threading.Thread(target=_warm, daemon=True).start()
    yield


app = FastAPI(title="株価チェッカー", lifespan=lifespan)

# React 開発サーバー(Vite, ポート5173)からの API 呼び出しを許可する
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API はすべて /api 配下に置く（フロントは /api/... を呼ぶ）
api = APIRouter(prefix="/api")


@api.get("/sectors")
def sectors_json():
    """おすすめ画面のセレクト用に、業界(セクター)の一覧を返す。"""
    return {"sectors": list(SECTOR_TICKERS.keys())}


@api.get("/suggest")
def suggest_json(q: str = ""):
    """検索オートコンプリート用に、東証銘柄の候補を返す。"""
    return {"results": suggest(q)}


@api.get("/market")
def market_json():
    """主要指数・為替（日経平均・ダウ・S&P500・ドル円）の概況を返す。"""
    return {"market": market_overview()}


@api.get("/quotes")
def quotes_json(symbols: str = "", dividend: int = 0):
    """複数銘柄の現在値・前日比（dividend=1 で配当も）をまとめて返す。"""
    syms = [s.strip() for s in symbols.split(",") if s.strip()]
    return {"quotes": quotes(syms, with_dividend=bool(dividend))}


@api.get("/recommendations")
def recommendations_json(sector: str = "", budget: int = 300000):
    """予算内で買えるおすすめ銘柄を「買い時」順（日本企業優先）で返す。

    sector を省略すると全業界が対象。
    例: GET /api/recommendations?budget=300000
        GET /api/recommendations?sector=テクノロジー&budget=300000
    """
    budget = max(0, budget)
    stocks = screen_recommendations(budget, sector or None)
    return {"sector": sector, "budget": budget, "stocks": stocks}


@api.get("/history/{symbol}")
def history_json(symbol: str, range: str = "6mo"):
    """銘柄の株価推移をチャート用に返す。range=1mo/3mo/6mo/1y/5y/max"""
    return {"symbol": symbol, "range": range, "points": fetch_history(symbol, range)}


@api.get("/stock/{symbol}")
def stock_json(symbol: str):
    """銘柄の詳細情報（株価・買い時・アナリスト予想・企業概要・ニュース）を返す。"""
    ticker = resolve_ticker(symbol, interactive=False)
    if not ticker:
        raise HTTPException(status_code=404, detail=f"'{symbol}' に一致する銘柄が見つかりませんでした。")

    data = fetch_stock_detail(ticker)
    if data is None:
        raise HTTPException(status_code=404, detail=f"'{symbol}' の株価データを取得できませんでした。")

    return data


app.include_router(api)

# React のビルド成果物を配信する（存在する場合のみ）。
# - 単一コンテナ配信（Render など）: static/ に dist を置くので FastAPI が配信
# - ローカルの2コンテナ構成: static/ が無いので nginx 側が配信する
_static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
if os.path.isdir(_static_dir):
    app.mount("/", StaticFiles(directory=_static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
