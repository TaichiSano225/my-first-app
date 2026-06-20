import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import (
    SECTOR_TICKERS,
    fetch_history,
    fetch_stock_data,
    fetch_stock_detail,
    resolve_ticker,
    screen_recommendations,
    screen_stocks,
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
templates = Jinja2Templates(directory="templates")

# React 開発サーバー(Vite, ポート5173)からの API 呼び出しを許可する
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
def index(request: Request, q: str = ""):
    query = q.strip()
    result = None
    error = None

    if query:
        try:
            ticker = resolve_ticker(query, interactive=False)
            if not ticker:
                error = f"'{query}' に一致する銘柄が見つかりませんでした。"
            else:
                result = fetch_stock_data(ticker)
                if result is None:
                    error = f"'{query}' の株価データを取得できませんでした。"
        except Exception as e:
            error = f"取得中にエラーが発生しました: {e}"

    return templates.TemplateResponse(
        request, "index.html", {"query": query, "result": result, "error": error}
    )


@app.get("/recommend", response_class=HTMLResponse)
def recommend(request: Request, budget: str = ""):
    budget_raw = budget.strip()
    rows = None
    error = None
    budget_jpy = 500000

    if budget_raw:
        try:
            budget_jpy = int(budget_raw.replace(",", "").replace("万", "0000"))
        except ValueError:
            error = f"予算の指定が不正です: {budget_raw}"

    if error is None and budget_raw:
        try:
            rows = screen_stocks(budget_jpy)
        except Exception as e:
            error = f"スクリーニング中にエラーが発生しました: {e}"

    return templates.TemplateResponse(
        request,
        "recommend.html",
        {"budget": budget_jpy, "budget_raw": budget_raw, "rows": rows, "error": error},
    )


@app.get("/sectors")
def sectors_json():
    """おすすめ画面のセレクト用に、業界(セクター)の一覧を返す。"""
    return {"sectors": list(SECTOR_TICKERS.keys())}


@app.get("/recommendations")
def recommendations_json(sector: str = "", budget: int = 300000):
    """予算内で買えるおすすめ銘柄を「買い時」順（日本企業優先）で返す。

    sector を省略すると全業界が対象。
    例: GET /recommendations?budget=300000
        GET /recommendations?sector=テクノロジー&budget=300000
    """
    budget = max(0, budget)
    stocks = screen_recommendations(budget, sector or None)
    return {"sector": sector, "budget": budget, "stocks": stocks}


@app.get("/history/{symbol}")
def history_json(symbol: str, range: str = "6mo"):
    """銘柄の株価推移をチャート用に返す。range=1mo/3mo/6mo/1y/5y/max"""
    return {"symbol": symbol, "range": range, "points": fetch_history(symbol, range)}


@app.get("/stock/{symbol}")
def stock_json(symbol: str):
    """銘柄の詳細情報（株価・買い時・アナリスト予想・企業概要・ニュース）を返す。"""
    ticker = resolve_ticker(symbol, interactive=False)
    if not ticker:
        raise HTTPException(status_code=404, detail=f"'{symbol}' に一致する銘柄が見つかりませんでした。")

    data = fetch_stock_detail(ticker)
    if data is None:
        raise HTTPException(status_code=404, detail=f"'{symbol}' の株価データを取得できませんでした。")

    return data


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
