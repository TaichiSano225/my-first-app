import yfinance as yf
import sys
import os


def resolve_ticker(query: str, interactive: bool = True) -> str | None:
    """会社名またはティッカーシンボルからティッカーを返す。"""
    # まずティッカーとして直接試す（エラー出力を抑制）
    devnull = open(os.devnull, "w")
    old_stderr = sys.stderr
    sys.stderr = devnull
    try:
        info = yf.Ticker(query).info
        has_price = bool(info.get("currentPrice") or info.get("regularMarketPrice"))
    finally:
        sys.stderr = old_stderr
        devnull.close()

    if has_price:
        return query

    # 会社名として検索
    results = yf.Search(query).quotes
    equities = [r for r in results if r.get("quoteType") == "EQUITY"]
    if not equities:
        return None

    if len(equities) == 1 or not interactive:
        return equities[0]["symbol"]

    # 複数候補がある場合は選ばせる
    print(f"\n'{query}' の検索結果:")
    for i, r in enumerate(equities[:5], 1):
        name = r.get("longname") or r.get("shortname", "")
        exch = r.get("exchDisp", "")
        print(f"  {i}. {r['symbol']:<12} {name} ({exch})")

    choice = input("番号を選んでください (1-5, Enterで1番): ").strip()
    idx = int(choice) - 1 if choice.isdigit() else 0
    idx = max(0, min(idx, len(equities) - 1))
    return equities[idx]["symbol"]


def get_stock_info(ticker: str) -> None:
    stock = yf.Ticker(ticker)
    info = stock.info

    name = info.get("longName") or info.get("shortName") or ticker
    currency = info.get("currency", "")
    current = info.get("currentPrice") or info.get("regularMarketPrice")
    prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

    if current is None:
        print(f"'{ticker}' の株価データを取得できませんでした。")
        return

    change = current - prev_close if prev_close is not None else None
    change_pct = (change / prev_close * 100) if change is not None and prev_close else None
    sign = "+" if change is not None and change >= 0 else ""

    print(f"\n{'=' * 45}")
    print(f"  {name} ({ticker.upper()})")
    print(f"{'=' * 45}")
    print(f"  現在値:   {current:,.2f} {currency}")
    if change is not None:
        print(f"  前日比:   {sign}{change:,.2f} ({sign}{change_pct:.2f}%)")
    print(f"  前日終値: {prev_close:,.2f} {currency}" if prev_close else "")

    high_52w = info.get("fiftyTwoWeekHigh")
    low_52w = info.get("fiftyTwoWeekLow")
    if high_52w and low_52w:
        print(f"  52週高値: {high_52w:,.2f} {currency}")
        print(f"  52週安値: {low_52w:,.2f} {currency}")

    market_cap = info.get("marketCap")
    if market_cap:
        cap_str = f"{market_cap / 1e12:.2f}兆" if market_cap >= 1e12 else f"{market_cap / 1e8:.0f}億"
        print(f"  時価総額: {cap_str} {currency}")

    print(f"{'=' * 45}\n")


def main() -> None:
    if len(sys.argv) > 1:
        queries = sys.argv[1:]
    else:
        user_input = input("会社名またはティッカーを入力してください (例: Apple, トヨタ, AAPL): ").strip()
        if not user_input:
            print("入力がありませんでした。")
            return
        queries = [q.strip() for q in user_input.split(",")]

    interactive = len(sys.argv) == 1
    for query in queries:
        if not query:
            continue
        ticker = resolve_ticker(query, interactive=interactive)
        if ticker:
            get_stock_info(ticker)
        else:
            print(f"'{query}' に一致する銘柄が見つかりませんでした。")


if __name__ == "__main__":
    main()
