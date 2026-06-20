import yfinance as yf
import pandas as pd
import difflib
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

# 業界(セクター)の英語→日本語ラベル
SECTOR_LABEL = {
    "Technology": "テクノロジー",
    "Financial Services": "金融",
    "Consumer Cyclical": "一般消費財",
    "Consumer Defensive": "生活必需品",
    "Healthcare": "ヘルスケア",
    "Communication Services": "通信サービス",
    "Industrials": "資本財・サービス",
    "Energy": "エネルギー",
    "Basic Materials": "素材",
    "Utilities": "公益事業",
    "Real Estate": "不動産",
}

# 業界(日本語ラベル)ごとの代表的な銘柄リスト [(ティッカー, 表示名), ...]
# おすすめ画面はこのリストを株価一括ダウンロードでスクリーニングする（高速化のため）。
SECTOR_TICKERS = {
    "テクノロジー": [
        ("AAPL", "Apple"), ("MSFT", "Microsoft"), ("NVDA", "NVIDIA"),
        ("AVGO", "Broadcom"), ("ORCL", "Oracle"), ("CRM", "Salesforce"),
        ("ADBE", "Adobe"), ("AMD", "AMD"), ("CSCO", "Cisco"),
        ("ACN", "Accenture"), ("TXN", "Texas Instruments"), ("QCOM", "Qualcomm"),
        ("INTC", "Intel"), ("IBM", "IBM"), ("INTU", "Intuit"),
        ("NOW", "ServiceNow"), ("AMAT", "Applied Materials"), ("MU", "Micron"),
        ("ADI", "Analog Devices"), ("LRCX", "Lam Research"), ("KLAC", "KLA"),
        ("SNPS", "Synopsys"), ("CDNS", "Cadence"), ("PANW", "Palo Alto Networks"),
        ("ANET", "Arista Networks"), ("DELL", "Dell"), ("6758.T", "ソニーグループ"),
        ("6861.T", "キーエンス"),
    ],
    "金融": [
        ("JPM", "JPMorgan Chase"), ("BAC", "Bank of America"), ("WFC", "Wells Fargo"),
        ("GS", "Goldman Sachs"), ("MS", "Morgan Stanley"), ("C", "Citigroup"),
        ("BLK", "BlackRock"), ("SCHW", "Charles Schwab"), ("AXP", "American Express"),
        ("SPGI", "S&P Global"), ("CB", "Chubb"), ("PGR", "Progressive"),
        ("BX", "Blackstone"), ("V", "Visa"), ("MA", "Mastercard"),
        ("PYPL", "PayPal"), ("COF", "Capital One"), ("USB", "U.S. Bancorp"),
        ("PNC", "PNC Financial"), ("TFC", "Truist"), ("AIG", "AIG"),
        ("MET", "MetLife"), ("AFL", "Aflac"), ("ALL", "Allstate"),
        ("TRV", "Travelers"), ("8306.T", "三菱UFJ"), ("8316.T", "三井住友FG"),
    ],
    "一般消費財": [
        ("AMZN", "Amazon"), ("TSLA", "Tesla"), ("HD", "Home Depot"),
        ("MCD", "McDonald's"), ("NKE", "Nike"), ("LOW", "Lowe's"),
        ("SBUX", "Starbucks"), ("TJX", "TJX"), ("BKNG", "Booking"),
        ("ABNB", "Airbnb"), ("MAR", "Marriott"), ("GM", "General Motors"),
        ("F", "Ford"), ("CMG", "Chipotle"), ("ORLY", "O'Reilly"),
        ("AZO", "AutoZone"), ("ROST", "Ross Stores"), ("YUM", "Yum! Brands"),
        ("LULU", "Lululemon"), ("DHI", "D.R. Horton"), ("LEN", "Lennar"),
        ("EBAY", "eBay"), ("7203.T", "トヨタ自動車"), ("9983.T", "ファーストリテイリング"),
    ],
    "生活必需品": [
        ("PG", "Procter & Gamble"), ("KO", "Coca-Cola"), ("PEP", "PepsiCo"),
        ("COST", "Costco"), ("WMT", "Walmart"), ("MDLZ", "Mondelez"),
        ("CL", "Colgate-Palmolive"), ("MO", "Altria"), ("PM", "Philip Morris"),
        ("KMB", "Kimberly-Clark"), ("GIS", "General Mills"), ("KHC", "Kraft Heinz"),
        ("HSY", "Hershey"), ("STZ", "Constellation Brands"), ("SYY", "Sysco"),
        ("KR", "Kroger"), ("ADM", "Archer-Daniels"), ("K", "Kellanova"),
        ("CHD", "Church & Dwight"), ("MKC", "McCormick"), ("CLX", "Clorox"),
        ("2914.T", "日本たばこ産業"),
    ],
    "ヘルスケア": [
        ("LLY", "Eli Lilly"), ("UNH", "UnitedHealth"), ("JNJ", "Johnson & Johnson"),
        ("MRK", "Merck"), ("ABBV", "AbbVie"), ("TMO", "Thermo Fisher"),
        ("ABT", "Abbott"), ("DHR", "Danaher"), ("PFE", "Pfizer"),
        ("AMGN", "Amgen"), ("BMY", "Bristol Myers"), ("GILD", "Gilead"),
        ("CVS", "CVS Health"), ("MDT", "Medtronic"), ("ISRG", "Intuitive Surgical"),
        ("VRTX", "Vertex"), ("REGN", "Regeneron"), ("CI", "Cigna"),
        ("ZTS", "Zoetis"), ("BSX", "Boston Scientific"), ("HCA", "HCA Healthcare"),
        ("HUM", "Humana"), ("BIIB", "Biogen"), ("4502.T", "武田薬品工業"),
    ],
    "通信サービス": [
        ("GOOGL", "Alphabet"), ("META", "Meta Platforms"), ("NFLX", "Netflix"),
        ("DIS", "Disney"), ("CMCSA", "Comcast"), ("T", "AT&T"),
        ("VZ", "Verizon"), ("TMUS", "T-Mobile"), ("CHTR", "Charter"),
        ("EA", "Electronic Arts"), ("WBD", "Warner Bros. Discovery"), ("TTWO", "Take-Two"),
        ("OMC", "Omnicom"), ("LYV", "Live Nation"), ("PARA", "Paramount"),
        ("FOXA", "Fox"), ("9432.T", "NTT"), ("9433.T", "KDDI"),
        ("9984.T", "ソフトバンクグループ"),
    ],
    "資本財・サービス": [
        ("CAT", "Caterpillar"), ("BA", "Boeing"), ("HON", "Honeywell"),
        ("UNP", "Union Pacific"), ("GE", "GE Aerospace"), ("UPS", "UPS"),
        ("RTX", "RTX"), ("LMT", "Lockheed Martin"), ("DE", "Deere"),
        ("MMM", "3M"), ("EMR", "Emerson"), ("ETN", "Eaton"),
        ("ITW", "Illinois Tool Works"), ("CSX", "CSX"), ("NSC", "Norfolk Southern"),
        ("FDX", "FedEx"), ("GD", "General Dynamics"), ("NOC", "Northrop Grumman"),
        ("WM", "Waste Management"), ("PH", "Parker Hannifin"), ("ADP", "ADP"),
        ("CMI", "Cummins"), ("6501.T", "日立製作所"),
    ],
    "エネルギー": [
        ("XOM", "ExxonMobil"), ("CVX", "Chevron"), ("COP", "ConocoPhillips"),
        ("SLB", "SLB"), ("EOG", "EOG Resources"), ("MPC", "Marathon Petroleum"),
        ("PSX", "Phillips 66"), ("VLO", "Valero"), ("OXY", "Occidental"),
        ("WMB", "Williams"), ("KMI", "Kinder Morgan"), ("HAL", "Halliburton"),
        ("DVN", "Devon Energy"), ("HES", "Hess"), ("BKR", "Baker Hughes"),
        ("FANG", "Diamondback"), ("OKE", "ONEOK"),
    ],
    "素材": [
        ("LIN", "Linde"), ("APD", "Air Products"), ("SHW", "Sherwin-Williams"),
        ("FCX", "Freeport-McMoRan"), ("NEM", "Newmont"), ("ECL", "Ecolab"),
        ("DOW", "Dow"), ("DD", "DuPont"), ("NUE", "Nucor"),
        ("PPG", "PPG Industries"), ("VMC", "Vulcan Materials"), ("MLM", "Martin Marietta"),
        ("ALB", "Albemarle"), ("CF", "CF Industries"), ("MOS", "Mosaic"),
    ],
    "公益事業": [
        ("NEE", "NextEra Energy"), ("DUK", "Duke Energy"), ("SO", "Southern Company"),
        ("D", "Dominion"), ("AEP", "American Electric Power"), ("EXC", "Exelon"),
        ("SRE", "Sempra"), ("XEL", "Xcel Energy"), ("ED", "Consolidated Edison"),
        ("PEG", "Public Service Enterprise"), ("WEC", "WEC Energy"), ("ES", "Eversource"),
        ("AEE", "Ameren"), ("DTE", "DTE Energy"), ("PPL", "PPL"),
    ],
    "不動産": [
        ("PLD", "Prologis"), ("AMT", "American Tower"), ("EQIX", "Equinix"),
        ("CCI", "Crown Castle"), ("PSA", "Public Storage"), ("O", "Realty Income"),
        ("SPG", "Simon Property"), ("WELL", "Welltower"), ("DLR", "Digital Realty"),
        ("VTR", "Ventas"), ("AVB", "AvalonBay"), ("EQR", "Equity Residential"),
        ("ESS", "Essex Property"), ("MAA", "Mid-America"), ("ARE", "Alexandria"),
    ],
}


# よく検索される日本語名・別名 → ティッカー（Yahoo検索が苦手な入力を補う）
JP_ALIASES = {
    "トヨタ": "7203.T", "とよた": "7203.T", "toyota": "7203.T",
    "ソニー": "6758.T", "そにー": "6758.T", "sony": "6758.T",
    "任天堂": "7974.T", "ニンテンドー": "7974.T", "nintendo": "7974.T",
    "ソフトバンク": "9984.T", "softbank": "9984.T",
    "キーエンス": "6861.T", "keyence": "6861.T",
    "三菱ufj": "8306.T", "三菱UFJ": "8306.T", "三井住友": "8316.T",
    "ntt": "9432.T", "kddi": "9433.T", "au": "9433.T",
    "ファーストリテイリング": "9983.T", "ユニクロ": "9983.T", "uniqlo": "9983.T",
    "日立": "6501.T", "ひたち": "6501.T", "hitachi": "6501.T",
    "武田薬品": "4502.T", "タケダ": "4502.T", "takeda": "4502.T",
    "jt": "2914.T", "日本たばこ": "2914.T",
    "アップル": "AAPL", "あっぷる": "AAPL",
    "マイクロソフト": "MSFT", "エヌビディア": "NVDA",
    "グーグル": "GOOGL", "アルファベット": "GOOGL",
    "アマゾン": "AMZN", "テスラ": "TSLA",
    "メタ": "META", "フェイスブック": "META", "facebook": "META",
    "ネットフリックス": "NFLX", "コカコーラ": "KO", "コカ・コーラ": "KO",
    "ペプシ": "PEP", "ナイキ": "NKE", "スターバックス": "SBUX", "スタバ": "SBUX",
    "マクドナルド": "MCD", "マック": "MCD", "ディズニー": "DIS",
    "インテル": "INTC", "アムド": "AMD", "オラクル": "ORCL",
}

_CATALOG = None  # 表示名(小文字) → ティッカー のキャッシュ


def _catalog() -> dict:
    """SECTOR_TICKERS から「表示名→ティッカー」の辞書を組み立てる（初回のみ）。"""
    global _CATALOG
    if _CATALOG is None:
        cat = {}
        for entries in SECTOR_TICKERS.values():
            for ticker, name in entries:
                cat[name.lower()] = ticker
        _CATALOG = cat
    return _CATALOG


def _local_resolve(query: str) -> str | None:
    """ローカルの別名辞書・あいまい一致で銘柄を類推する（日本語名やタイプミス対策）。"""
    q = query.strip().lower()
    if not q:
        return None

    # 1. 日本語/別名の完全一致
    if q in JP_ALIASES:
        return JP_ALIASES[q]

    cat = _catalog()

    # 2. 表示名の完全一致
    if q in cat:
        return cat[q]

    # 3. 前方一致（候補が1つに絞れる場合のみ）
    if len(q) >= 3:
        starts = sorted({t for name, t in cat.items() if name.startswith(q)})
        if len(starts) == 1:
            return starts[0]

    # 4. あいまい一致（"microsft" → "microsoft" のようなタイプミスを吸収）
    close = difflib.get_close_matches(q, list(cat.keys()), n=1, cutoff=0.72)
    if close:
        return cat[close[0]]

    # 5. 部分一致（候補が1つに絞れる場合のみ）
    contains = sorted({t for name, t in cat.items() if q in name})
    if len(contains) == 1:
        return contains[0]

    return None


def compute_timing(price, high, low, ma200) -> dict:
    """株価の「買い時」を簡易判定する（参考情報）。

    52週レンジ内での位置と、200日移動平均線との位置関係からスコアを出す。
    安値圏・移動平均割れほど「買い時」と判断する。
    """
    # 52週レンジ内の位置（0%=年初来安値, 100%=年初来高値）
    range_pct = None
    if high and low and high > low:
        range_pct = (price - low) / (high - low) * 100

    score = 0
    reasons = []
    if range_pct is not None:
        if range_pct <= 25:
            score += 2
            reasons.append("52週レンジの下位25%（安値圏）")
        elif range_pct <= 50:
            score += 1
            reasons.append("52週レンジの中央より下")
        elif range_pct >= 85:
            score -= 1
            reasons.append("52週高値に接近（高値圏）")

    if ma200:
        if price < ma200:
            score += 1
            reasons.append("200日移動平均を下回る")
        elif price > ma200 * 1.1:
            score -= 1
            reasons.append("200日移動平均を10%以上上回る")

    if score >= 2:
        label = "買い時"
    elif score >= 1:
        label = "やや買い時"
    elif score <= -1:
        label = "高値圏"
    else:
        label = "中立"

    return {
        "timing_label": label,
        "timing_score": score,
        "timing_reason": "・".join(reasons) if reasons else "目立った割安・割高シグナルなし",
        "range_pct": round(range_pct, 1) if range_pct is not None else None,
    }


def buy_timing(info: dict, price: float) -> dict:
    """info 辞書から買い時を判定する（CLI/HTML 用の薄いラッパー）。"""
    return compute_timing(
        price,
        info.get("fiftyTwoWeekHigh"),
        info.get("fiftyTwoWeekLow"),
        info.get("twoHundredDayAverage"),
    )


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

    # 会社名として検索（あいまいな入力でも Yahoo の検索が類推してくれる）
    try:
        results = yf.Search(query).quotes
    except Exception:
        results = []

    equities = [r for r in results if r.get("quoteType") == "EQUITY" and r.get("symbol")]
    # 株式が見つからなければ ETF などシンボルを持つ候補にフォールバック
    if not equities:
        equities = [r for r in results if r.get("symbol")]

    # Yahoo の検索で見つからない場合は、ローカル辞書であいまい解決を試みる
    # （日本語の会社名や、つづり間違いに対応）
    if not equities:
        return _local_resolve(query)

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

            sector = info.get("sector") or ""
            timing = buy_timing(info, price)

            rows.append({
                "ticker": ticker,
                "name": name,
                "sector": SECTOR_LABEL.get(sector, sector or "その他"),
                "price_jpy": price_jpy,
                "min_cost": min_cost,
                "units": units,
                "affordable": int(budget_jpy // min_cost),  # 買える単元数
                "rec_key": rec_key,
                "rec_label": REC_LABEL.get(rec_key, rec_key),
                "rec_score": REC_SCORE.get(rec_key, 0),
                "is_buy": REC_SCORE.get(rec_key, 0) >= 4,
                "upside": upside,
                "timing_label": timing["timing_label"],
                "timing_score": timing["timing_score"],
                "timing_reason": timing["timing_reason"],
                "range_pct": timing["range_pct"],
            })
        except Exception:
            continue

    # アナリスト評価スコア降順、次に上振れ余地（upside）降順で並べ替え
    rows.sort(key=lambda r: (r["rec_score"], r["upside"] or -999), reverse=True)
    return rows


def _r2(value):
    """値があれば小数2桁に丸める。None ならそのまま None。"""
    return round(value, 2) if value is not None else None


_FX_RATE_CACHE: dict = {}


def usd_to_jpy_rate() -> float:
    """USD→JPY の為替レートを返す（取得失敗時はフォールバック値）。"""
    if "USDJPY" not in _FX_RATE_CACHE:
        rate = None
        try:
            df = yf.download("JPY=X", period="5d", interval="1d", progress=False)
            rate = float(df["Close"].dropna().iloc[-1])
        except Exception:
            rate = None
        _FX_RATE_CACHE["USDJPY"] = rate or 150.0  # 取得できなければ概算値
    return _FX_RATE_CACHE["USDJPY"]


def screen_sector(sector_jp: str, budget_jpy: int = 300000, limit: int = 30) -> list[dict]:
    """指定した業界の銘柄を、予算内で買えるものに絞り「買い時」順で返す。

    株価は yfinance の一括ダウンロード（1リクエスト）で取得するため高速。
    アナリスト評価などの重い info 取得は行わず、価格データだけで判定する。
    """
    entries = SECTOR_TICKERS.get(sector_jp, [])
    if not entries:
        return []

    tickers = [t for t, _ in entries]
    names = dict(entries)

    # 1リクエストで全銘柄の1年分の日足を取得
    data = yf.download(
        tickers, period="1y", interval="1d",
        group_by="ticker", auto_adjust=True, progress=False, threads=True,
    )
    if data is None or data.empty:
        return []

    rate = usd_to_jpy_rate()
    multi = isinstance(data.columns, pd.MultiIndex)
    rows = []

    for ticker in tickers:
        try:
            df = data[ticker] if multi else data
            close = df["Close"].dropna()
            if close.empty:
                continue
            price = float(close.iloc[-1])
            prev = float(close.iloc[-2]) if len(close) >= 2 else None
            high = float(df["High"].dropna().max())
            low = float(df["Low"].dropna().min())
            ma200 = float(close.tail(200).mean())
        except Exception:
            continue

        is_jp = ticker.endswith(".T")
        units = 100 if is_jp else 1
        price_jpy = price if is_jp else price * rate
        min_cost = price_jpy * units
        if min_cost <= 0 or min_cost > budget_jpy:
            continue  # 1単元すら買えない

        timing = compute_timing(price, high, low, ma200)
        change_pct = ((price - prev) / prev * 100) if prev else None

        rows.append({
            "ticker": ticker,
            "name": names.get(ticker, ticker),
            "sector": sector_jp,
            "currency": "JPY" if is_jp else "USD",
            "price_jpy": round(price_jpy),
            "min_cost": round(min_cost),
            "units": units,
            "affordable": int(budget_jpy // min_cost),
            "change_pct": _r2(change_pct),
            "timing_label": timing["timing_label"],
            "timing_score": timing["timing_score"],
            "timing_reason": timing["timing_reason"],
            "range_pct": timing["range_pct"],
        })

    # 買い時スコア降順 → 同点ならレンジ内位置が低い（割安）順
    rows.sort(key=lambda r: (r["timing_score"], -(r["range_pct"] if r["range_pct"] is not None else 50)),
              reverse=True)
    return rows[:limit]


def _fetch_news(stock, limit: int = 5) -> list[dict]:
    """銘柄に関する最近のニュース見出しを返す（新旧フォーマット両対応）。"""
    try:
        items = stock.news or []
    except Exception:
        return []

    out = []
    for it in items[:limit]:
        content = it.get("content") if isinstance(it.get("content"), dict) else it
        title = content.get("title") or it.get("title")
        if not title:
            continue

        # リンク（複数の入れ子フォーマットに対応）
        link = it.get("link") or ""
        for key in ("clickThroughUrl", "canonicalUrl"):
            val = content.get(key)
            if isinstance(val, dict) and val.get("url"):
                link = val["url"]
                break

        # 配信元
        publisher = it.get("publisher") or ""
        prov = content.get("provider")
        if isinstance(prov, dict) and prov.get("displayName"):
            publisher = prov["displayName"]

        out.append({"title": title, "link": link, "publisher": publisher})
    return out


def fetch_stock_detail(ticker: str) -> dict | None:
    """1銘柄の詳細情報（株価・買い時・アナリスト予想・企業概要・ニュース）を返す。"""
    base = fetch_stock_data(ticker)
    if base is None or base.get("current") is None:
        return None

    stock = yf.Ticker(ticker)
    info = stock.info
    price = base["current"]

    timing = buy_timing(info, price)
    target = info.get("targetMeanPrice")
    upside = ((target - price) / price * 100) if target else None
    rec_key = info.get("recommendationKey") or "none"
    sector_en = info.get("sector") or ""

    return {
        "symbol": base["ticker"],
        "name": base["name"],
        "price": _r2(base["current"]),
        "prev_close": _r2(base["prev_close"]),
        "change": _r2(base["change"]),
        "change_pct": _r2(base["change_pct"]),
        "currency": base["currency"],
        "sector": SECTOR_LABEL.get(sector_en, sector_en or ""),
        "industry": info.get("industry") or "",
        "summary": info.get("longBusinessSummary") or "",
        "high_52w": _r2(base["high_52w"]),
        "low_52w": _r2(base["low_52w"]),
        "market_cap_str": base["market_cap_str"],
        # 買い時
        "timing_label": timing["timing_label"],
        "timing_reason": timing["timing_reason"],
        "range_pct": timing["range_pct"],
        # アナリスト予想（今後の値動きの目安）
        "target_mean": _r2(target),
        "target_high": _r2(info.get("targetHighPrice")),
        "target_low": _r2(info.get("targetLowPrice")),
        "upside": _r2(upside),
        "rec_label": REC_LABEL.get(rec_key, rec_key),
        # 最近のトピック
        "news": _fetch_news(stock),
    }


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
