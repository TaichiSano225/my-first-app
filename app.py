import yfinance as yf
import sys


def get_stock_info(ticker: str) -> None:
    stock = yf.Ticker(ticker)
    info = stock.info

    name = info.get("longName") or info.get("shortName") or ticker
    currency = info.get("currency", "")
    current = info.get("currentPrice") or info.get("regularMarketPrice")
    prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")

    if current is None:
        print(f"'{ticker}' の株価データを取得できませんでした。ティッカーシンボルを確認してください。")
        return

    change = current - prev_close if prev_close else None
    change_pct = (change / prev_close * 100) if change and prev_close else None
    sign = "+" if change and change >= 0 else ""

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
        tickers = sys.argv[1:]
    else:
        user_input = input("ティッカーシンボルを入力してください (例: AAPL, 7203.T): ").strip()
        if not user_input:
            print("入力がありませんでした。")
            return
        tickers = [t.strip() for t in user_input.split(",")]

    for ticker in tickers:
        if ticker:
            get_stock_info(ticker)


if __name__ == "__main__":
    main()
