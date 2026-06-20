import yfinance as yf
import sys
import os
import re

# 社名末尾によくある法人格・属性語（マッチ判定の際に無視する）
_NAME_NOISE = {
    "INC", "CORP", "CORPORATION", "CO", "COMPANY", "LTD", "LIMITED", "PLC",
    "SA", "AG", "NV", "HOLDINGS", "HOLDING", "GROUP", "THE", "REIT", "TRUST",
    "USD", "JPY", "CLASS", "R",
}


# 予算スクリーニング用のウォッチリスト（主要銘柄）
DEFAULT_WATCHLIST = [
    # 米国株
    "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "KO", "PFE", "INTC",
    # 日本株
    "7203.T", "6758.T", "9984.T", "8306.T", "9432.T", "8058.T", "7974.T",
]

# アナリスト評価のスコアと日本語ラベル
REC_SCORE = {
    "strong_buy": 5, "buy": 4, "outperform": 4,
    "hold": 3, "neutral": 3,
    "underperform": 2, "sell": 2, "strong_sell": 1,
}
REC_LABEL = {
    "strong_buy": "強い買い", "buy": "買い", "outperform": "やや買い",
    "hold": "中立", "neutral": "中立",
    "underperform": "やや売り", "sell": "売り", "strong_sell": "強い売り",
    "none": "評価なし", "": "評価なし", None: "評価なし",
}


def get_latest_price(stock, info=None):
    """できるだけ最新の株価を返す。fast_info を優先し、無ければ info にフォールバック。"""
    try:
        lp = stock.fast_info.last_price
        if lp:
            return float(lp)
    except Exception:
        pass
    info = info if info is not None else stock.info
    return info.get("currentPrice") or info.get("regularMarketPrice")


def _match_score(query: str, result: dict) -> float:
    """検索結果が query にどれだけ一致するかをスコア化する（大きいほど良い）。"""
    q = query.strip().upper()
    name = (result.get("longname") or result.get("shortname") or "").upper()
    words = [w for w in re.split(r"[^A-Z0-9]+", name) if w]
    core = [w for w in words if w not in _NAME_NOISE]  # 法人格などを除いた中核語

    if " ".join(words) == q:
        score = 100          # 社名が完全一致
    elif core and " ".join(core) == q:
        score = 90           # 法人格を除けば一致（例: "NTT" ≒ "NTT INC"）
    elif words and words[0] == q:
        score = 60           # 先頭語が一致
    elif q in words:
        score = 40           # いずれかの語と一致
    elif q.replace(" ", "") in name.replace(" ", ""):
        score = 10           # 部分一致
    else:
        score = 0

    # 同点時は余計な語が少ない（=より素直な一致の）方を優先
    score -= 0.1 * len(words)
    # Yahoo の関連度スコアをごく弱い最終タイブレークに
    score += 1e-6 * (result.get("score") or 0)
    return score


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

    # 社名のマッチ度が高い順に並べ替える（例: "NTT" で NTT DC REIT より NTT, Inc. を優先）
    equities.sort(key=lambda r: _match_score(query, r), reverse=True)

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


def fetch_stock_data(ticker: str) -> dict | None:
    """銘柄の株価情報を辞書で返す（CLI/Web 共通）。取得できなければ None。"""
    stock = yf.Ticker(ticker)
    info = stock.info

    current = get_latest_price(stock, info)
    if current is None:
        return None

    name = info.get("longName") or info.get("shortName") or ticker
    currency = info.get("currency", "")
    prev_close = info.get("previousClose") or info.get("regularMarketPreviousClose")
    change = current - prev_close if prev_close is not None else None
    change_pct = (change / prev_close * 100) if change is not None and prev_close else None

    market_cap = info.get("marketCap")
    cap_str = None
    if market_cap:
        cap_str = f"{market_cap / 1e12:.2f}兆" if market_cap >= 1e12 else f"{market_cap / 1e8:.0f}億"

    return {
        "ticker": ticker.upper(),
        "name": name,
        "currency": currency,
        "current": current,
        "prev_close": prev_close,
        "change": change,
        "change_pct": change_pct,
        "high_52w": info.get("fiftyTwoWeekHigh"),
        "low_52w": info.get("fiftyTwoWeekLow"),
        "market_cap_str": cap_str,
    }


def get_stock_info(ticker: str) -> None:
    data = fetch_stock_data(ticker)
    if data is None:
        print(f"'{ticker}' の株価データを取得できませんでした。")
        return

    name = data["name"]
    currency = data["currency"]
    current = data["current"]
    prev_close = data["prev_close"]
    change = data["change"]
    change_pct = data["change_pct"]
    sign = "+" if change is not None and change >= 0 else ""

    print(f"\n{'=' * 45}")
    print(f"  {name} ({ticker.upper()})")
    print(f"{'=' * 45}")
    print(f"  現在値:   {current:,.2f} {currency}")
    if change is not None:
        print(f"  前日比:   {sign}{change:,.2f} ({sign}{change_pct:.2f}%)")
    print(f"  前日終値: {prev_close:,.2f} {currency}" if prev_close else "")

    high_52w = data["high_52w"]
    low_52w = data["low_52w"]
    if high_52w and low_52w:
        print(f"  52週高値: {high_52w:,.2f} {currency}")
        print(f"  52週安値: {low_52w:,.2f} {currency}")

    if data["market_cap_str"]:
        print(f"  時価総額: {data['market_cap_str']} {currency}")

    print(f"{'=' * 45}\n")


def to_jpy(amount: float, currency: str, rates_cache: dict) -> float | None:
    """指定通貨の金額を日本円に換算する。"""
    if not currency or currency == "JPY":
        return amount
    if currency not in rates_cache:
        try:
            rates_cache[currency] = float(yf.Ticker(f"{currency}JPY=X").fast_info.last_price)
        except Exception:
            rates_cache[currency] = None
    rate = rates_cache[currency]
    return amount * rate if rate else None


def lot_size(ticker: str) -> int:
    """最低購入単位（株数）。日本株(.T)は単元株100株、それ以外は1株。"""
    return 100 if ticker.upper().endswith(".T") else 1


def screen_stocks(budget_jpy: int = 500000, candidates: list[str] | None = None) -> list[dict]:
    """予算内で購入可能な銘柄を、アナリスト評価順に並べた一覧を返す（CLI/Web 共通）。"""
    candidates = candidates or DEFAULT_WATCHLIST
    rates: dict = {}
    rows = []

    for ticker in candidates:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            price = get_latest_price(stock, info)
            if not price:
                continue
            currency = info.get("currency", "")
            price_jpy = to_jpy(price, currency, rates)
            if not price_jpy:
                continue

            units = lot_size(ticker)
            min_cost = price_jpy * units  # 最低購入金額
            if min_cost > budget_jpy:
                continue  # 1単元すら買えない

            rec_key = info.get("recommendationKey") or "none"
            target = info.get("targetMeanPrice")
            upside = ((target - price) / price * 100) if target else None
            name = info.get("longName") or info.get("shortName") or ticker

            rows.append({
                "ticker": ticker,
                "name": name,
                "price_jpy": price_jpy,
                "min_cost": min_cost,
                "units": units,
                "affordable": int(budget_jpy // min_cost),  # 買える単元数
                "rec_key": rec_key,
                "rec_label": REC_LABEL.get(rec_key, rec_key),
                "rec_score": REC_SCORE.get(rec_key, 0),
                "is_buy": REC_SCORE.get(rec_key, 0) >= 4,
                "upside": upside,
            })
        except Exception:
            continue

    # アナリスト評価スコア降順、次に上振れ余地（upside）降順で並べ替え
    rows.sort(key=lambda r: (r["rec_score"], r["upside"] or -999), reverse=True)
    return rows


def recommend_stocks(budget_jpy: int = 500000, candidates: list[str] | None = None) -> None:
    """予算内で購入可能な銘柄を、アナリスト評価順に表示する。"""
    n = len(candidates or DEFAULT_WATCHLIST)
    print(f"\n予算 {budget_jpy:,} 円で購入候補をスクリーニング中... ({n}銘柄)\n")

    rows = screen_stocks(budget_jpy, candidates)

    if not rows:
        print("予算内で購入可能な銘柄が見つかりませんでした。")
        return

    print(f"{'=' * 72}")
    print(f"  予算 {budget_jpy:,} 円で購入可能な銘柄（アナリスト評価順）")
    print(f"{'=' * 72}")
    print(f"  {'銘柄':<10} {'評価':<8} {'上振れ':>7} {'最低購入額':>12}  購入可能数")
    print(f"  {'-' * 68}")
    for r in rows:
        mark = "★" if r["rec_score"] >= 4 else " "
        label = REC_LABEL.get(r["rec_key"], r["rec_key"])
        upside = f"{r['upside']:+.0f}%" if r["upside"] is not None else "  -  "
        if r["units"] == 100:
            qty = f"{r['affordable']}単元({r['affordable'] * 100}株)"
        else:
            qty = f"{r['affordable']}株"
        print(f"{mark} {r['ticker']:<10} {label:<8} {upside:>7} {r['min_cost']:>11,.0f}円  {qty}")

    print(f"  {'-' * 68}")
    buys = [r for r in rows if r["rec_score"] >= 4]
    if buys:
        names = "、".join(r["name"] for r in buys[:3])
        print(f"  ★ 本日の注目（買い評価）: {names}")
    print(f"{'=' * 72}")
    print("  ※ Yahoo Finance のアナリスト評価に基づく参考情報です。投資助言ではありません。")
    print("  ※ 投資はご自身の判断と責任で行ってください。")
    print(f"{'=' * 72}\n")


def main() -> None:
    args = sys.argv[1:]

    # 推奨銘柄モード
    if args and args[0] in ("--recommend", "-r", "おすすめ"):
        rest = args[1:]
        budget = 500000
        candidates: list[str] = []
        i = 0
        while i < len(rest):
            if rest[i] in ("--budget", "-b") and i + 1 < len(rest):
                try:
                    budget = int(rest[i + 1].replace(",", "").replace("万", "0000"))
                except ValueError:
                    print(f"予算の指定が不正です: {rest[i + 1]}")
                    return
                i += 2
            else:
                candidates.append(rest[i])
                i += 1
        recommend_stocks(budget, candidates or None)
        return

    if args:
        queries = args
    else:
        user_input = input("会社名またはティッカーを入力してください (例: Apple, トヨタ, AAPL): ").strip()
        if not user_input:
            print("入力がありませんでした。")
            return
        queries = [q.strip() for q in user_input.split(",")]

    interactive = len(args) == 0
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
