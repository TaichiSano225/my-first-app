from flask import Flask, render_template, request

from app import fetch_stock_data, resolve_ticker, screen_stocks

app = Flask(__name__)


@app.route("/")
def index():
    query = request.args.get("q", "").strip()
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

    return render_template("index.html", query=query, result=result, error=error)


@app.route("/recommend")
def recommend():
    budget_raw = request.args.get("budget", "").strip()
    rows = None
    error = None
    budget = 500000

    if budget_raw:
        try:
            budget = int(budget_raw.replace(",", "").replace("万", "0000"))
        except ValueError:
            error = f"予算の指定が不正です: {budget_raw}"

    if error is None and budget_raw:
        try:
            rows = screen_stocks(budget)
        except Exception as e:
            error = f"スクリーニング中にエラーが発生しました: {e}"

    return render_template(
        "recommend.html", budget=budget, budget_raw=budget_raw, rows=rows, error=error
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
