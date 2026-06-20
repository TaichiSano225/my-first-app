from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app import fetch_stock_data, resolve_ticker, screen_stocks

app = FastAPI(title="株価チェッカー")
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


def _round2(value):
    """数値を小数2桁に丸める。値が None ならそのまま None を返す。"""
    return round(value, 2) if value is not None else None


@app.get("/stock/{symbol}")
def stock_json(symbol: str):
    """銘柄の株価情報を JSON で返す。

    例: {"symbol": "AAPL", "name": "Apple Inc.", "price": 203.52,
         "prev_close": 201.0, "change": 2.52, "change_pct": 1.25, "currency": "USD"}
    """
    ticker = resolve_ticker(symbol, interactive=False)
    if not ticker:
        raise HTTPException(status_code=404, detail=f"'{symbol}' に一致する銘柄が見つかりませんでした。")

    data = fetch_stock_data(ticker)
    if data is None or data.get("current") is None:
        raise HTTPException(status_code=404, detail=f"'{symbol}' の株価データを取得できませんでした。")

    return {
        "symbol": data["ticker"],
        "name": data["name"],
        "price": _round2(data["current"]),
        "prev_close": _round2(data["prev_close"]),
        "change": _round2(data["change"]),
        "change_pct": _round2(data["change_pct"]),
        "currency": data["currency"],
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
