import yfinance as yf
import pandas as pd
import difflib
import json
import time
import sys
import os
import re

try:
    from deep_translator import GoogleTranslator
except Exception:  # ライブラリ未導入でも英語表示で動作させる
    GoogleTranslator = None

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

# 日本の主要銘柄 [(ティッカー, 表示名, 業界)]。おすすめはこの中から市場状況で動的に抽出する。
JAPAN_TICKERS = [
    # テクノロジー
    ("6758.T", "ソニーグループ", "テクノロジー"), ("6861.T", "キーエンス", "テクノロジー"),
    ("6098.T", "リクルート", "テクノロジー"), ("6981.T", "村田製作所", "テクノロジー"),
    ("8035.T", "東京エレクトロン", "テクノロジー"), ("6594.T", "ニデック", "テクノロジー"),
    ("6857.T", "アドバンテスト", "テクノロジー"), ("6920.T", "レーザーテック", "テクノロジー"),
    ("6503.T", "三菱電機", "テクノロジー"), ("6702.T", "富士通", "テクノロジー"),
    ("6752.T", "パナソニック", "テクノロジー"), ("6645.T", "オムロン", "テクノロジー"),
    ("6971.T", "京セラ", "テクノロジー"), ("6701.T", "NEC", "テクノロジー"),
    ("6724.T", "セイコーエプソン", "テクノロジー"), ("7751.T", "キヤノン", "テクノロジー"),
    ("7752.T", "リコー", "テクノロジー"), ("6770.T", "アルプスアルパイン", "テクノロジー"),
    ("6963.T", "ローム", "テクノロジー"), ("6762.T", "TDK", "テクノロジー"),
    ("6273.T", "SMC", "テクノロジー"), ("4307.T", "野村総合研究所", "テクノロジー"),
    ("9613.T", "NTTデータグループ", "テクノロジー"), ("4704.T", "トレンドマイクロ", "テクノロジー"),
    ("6532.T", "ベイカレント", "テクノロジー"), ("5802.T", "住友電気工業", "テクノロジー"),
    # 金融
    ("8306.T", "三菱UFJ", "金融"), ("8316.T", "三井住友FG", "金融"),
    ("8411.T", "みずほFG", "金融"), ("8766.T", "東京海上HD", "金融"),
    ("8591.T", "オリックス", "金融"), ("8604.T", "野村HD", "金融"),
    ("8750.T", "第一生命HD", "金融"), ("8725.T", "MS&AD", "金融"),
    ("8630.T", "SOMPO HD", "金融"), ("8473.T", "SBI HD", "金融"),
    ("8697.T", "日本取引所グループ", "金融"),
    # 一般消費財
    ("7203.T", "トヨタ自動車", "一般消費財"), ("7267.T", "ホンダ", "一般消費財"),
    ("7201.T", "日産自動車", "一般消費財"), ("7269.T", "スズキ", "一般消費財"),
    ("9983.T", "ファーストリテイリング", "一般消費財"), ("7974.T", "任天堂", "一般消費財"),
    ("4661.T", "オリエンタルランド", "一般消費財"), ("7832.T", "バンダイナムコHD", "一般消費財"),
    ("9843.T", "ニトリHD", "一般消費財"), ("3092.T", "ZOZO", "一般消費財"),
    ("5108.T", "ブリヂストン", "一般消費財"), ("6902.T", "デンソー", "一般消費財"),
    ("4755.T", "楽天グループ", "一般消費財"),
    # 生活必需品
    ("3382.T", "セブン&アイ", "生活必需品"), ("2914.T", "日本たばこ産業", "生活必需品"),
    ("2802.T", "味の素", "生活必需品"), ("2503.T", "キリンHD", "生活必需品"),
    ("4452.T", "花王", "生活必需品"), ("4911.T", "資生堂", "生活必需品"),
    ("8113.T", "ユニ・チャーム", "生活必需品"), ("2269.T", "明治HD", "生活必需品"),
    ("2801.T", "キッコーマン", "生活必需品"), ("2587.T", "サントリー食品", "生活必需品"),
    ("8267.T", "イオン", "生活必需品"),
    # ヘルスケア
    ("4502.T", "武田薬品工業", "ヘルスケア"), ("4503.T", "アステラス製薬", "ヘルスケア"),
    ("4519.T", "中外製薬", "ヘルスケア"), ("4568.T", "第一三共", "ヘルスケア"),
    ("4543.T", "テルモ", "ヘルスケア"), ("4523.T", "エーザイ", "ヘルスケア"),
    ("4578.T", "大塚HD", "ヘルスケア"), ("4507.T", "塩野義製薬", "ヘルスケア"),
    ("7741.T", "HOYA", "ヘルスケア"), ("7733.T", "オリンパス", "ヘルスケア"),
    ("4901.T", "富士フイルムHD", "ヘルスケア"), ("4151.T", "協和キリン", "ヘルスケア"),
    # 通信サービス
    ("9432.T", "NTT", "通信サービス"), ("9433.T", "KDDI", "通信サービス"),
    ("9984.T", "ソフトバンクグループ", "通信サービス"), ("9434.T", "ソフトバンク", "通信サービス"),
    ("9766.T", "コナミグループ", "通信サービス"), ("4324.T", "電通グループ", "通信サービス"),
    ("2432.T", "ディー・エヌ・エー", "通信サービス"), ("3659.T", "ネクソン", "通信サービス"),
    ("4689.T", "LINEヤフー", "通信サービス"),
    # 資本財・サービス
    ("6301.T", "コマツ", "資本財・サービス"), ("7011.T", "三菱重工業", "資本財・サービス"),
    ("6501.T", "日立製作所", "資本財・サービス"), ("8001.T", "伊藤忠商事", "資本財・サービス"),
    ("8058.T", "三菱商事", "資本財・サービス"), ("8031.T", "三井物産", "資本財・サービス"),
    ("8053.T", "住友商事", "資本財・サービス"), ("8002.T", "丸紅", "資本財・サービス"),
    ("2768.T", "双日", "資本財・サービス"), ("9101.T", "日本郵船", "資本財・サービス"),
    ("9104.T", "商船三井", "資本財・サービス"), ("9107.T", "川崎汽船", "資本財・サービス"),
    ("6367.T", "ダイキン工業", "資本財・サービス"), ("6954.T", "ファナック", "資本財・サービス"),
    ("6326.T", "クボタ", "資本財・サービス"), ("7012.T", "川崎重工業", "資本財・サービス"),
    ("7013.T", "IHI", "資本財・サービス"), ("6506.T", "安川電機", "資本財・サービス"),
    ("6504.T", "富士電機", "資本財・サービス"), ("9020.T", "JR東日本", "資本財・サービス"),
    ("9022.T", "JR東海", "資本財・サービス"), ("9201.T", "日本航空", "資本財・サービス"),
    ("9202.T", "ANA HD", "資本財・サービス"), ("6178.T", "日本郵政", "資本財・サービス"),
    # 素材
    ("4063.T", "信越化学工業", "素材"), ("5401.T", "日本製鉄", "素材"),
    ("5411.T", "JFE HD", "素材"), ("3407.T", "旭化成", "素材"),
    ("4188.T", "三菱ケミカルG", "素材"), ("4005.T", "住友化学", "素材"),
    ("3402.T", "東レ", "素材"), ("5713.T", "住友金属鉱山", "素材"),
    ("6988.T", "日東電工", "素材"),
    # エネルギー
    ("1605.T", "INPEX", "エネルギー"), ("5020.T", "ENEOS HD", "エネルギー"),
    ("5019.T", "出光興産", "エネルギー"),
    # 公益事業
    ("9531.T", "東京ガス", "公益事業"), ("9501.T", "東京電力HD", "公益事業"),
    ("9503.T", "関西電力", "公益事業"),
    # 不動産
    ("8801.T", "三井不動産", "不動産"), ("8802.T", "三菱地所", "不動産"),
    ("8830.T", "住友不動産", "不動産"), ("1925.T", "大和ハウス工業", "不動産"),
    ("1928.T", "積水ハウス", "不動産"),
]

_UNIVERSE = None  # おすすめ用の日本株ユニバース [(ticker, name, sector)]（重複除去済み）


def _universe() -> list[tuple]:
    """おすすめ対象の日本株ユニバースを組み立てる（初回のみ）。"""
    global _UNIVERSE
    if _UNIVERSE is None:
        seen = set()
        universe = []
        for ticker, name, sector in JAPAN_TICKERS:
            if ticker not in seen:
                seen.add(ticker)
                universe.append((ticker, name, sector))
        _UNIVERSE = universe
    return _UNIVERSE


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


# 東証の全上場銘柄（コード→社名）。日本語社名での検索に使う。
_JP_STOCKS = None        # {"7203": "トヨタ自動車", ...}
_JP_NAME_INDEX = None    # 正規化社名 -> "コード.T"
_JP_NAME_LIST = None     # 正規化社名のリスト（あいまい一致用）


def _norm(s: str) -> str:
    """社名の表記ゆれを吸収するための正規化（小文字化・空白/中点の除去）。"""
    return (
        s.strip().lower()
        .replace(" ", "").replace("　", "")
        .replace("・", "").replace("（", "(").replace("）", ")")
    )


def _load_jp_stocks() -> dict:
    """東証の全上場銘柄リスト（jp_stocks.json）を読み込む（初回のみ）。"""
    global _JP_STOCKS, _JP_NAME_INDEX, _JP_NAME_LIST
    if _JP_STOCKS is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jp_stocks.json")
        try:
            with open(path, encoding="utf-8") as f:
                _JP_STOCKS = json.load(f)
        except Exception:
            _JP_STOCKS = {}
        index = {}
        for code, name in _JP_STOCKS.items():
            index[_norm(name)] = f"{code}.T"
        _JP_NAME_INDEX = index
        _JP_NAME_LIST = list(index.keys())
    return _JP_STOCKS


def _local_resolve(query: str, fuzzy: bool = True) -> str | None:
    """ローカル辞書（別名・東証全銘柄・タイプミス）で銘柄を類推する。

    fuzzy=False なら完全一致のみ（Yahoo 検索より前に呼ぶ高速・高精度パス）。
    """
    q = query.strip()
    if not q:
        return None
    ql = q.lower()
    _load_jp_stocks()

    # 1. 証券コード4桁 → 東証(.T)
    if re.fullmatch(r"\d{4}", q) and q in _JP_STOCKS:
        return f"{q}.T"

    # 2. 日本語/別名の完全一致
    if ql in JP_ALIASES:
        return JP_ALIASES[ql]

    cat = _catalog()

    # 3. 表示名（英語カタログ）の完全一致
    if ql in cat:
        return cat[ql]

    # 4. 東証の社名と完全一致（例: 理研計器 → 7734.T）
    nq = _norm(q)
    if nq in _JP_NAME_INDEX:
        return _JP_NAME_INDEX[nq]

    if not fuzzy:
        return None

    # 5. 英語カタログの前方一致（候補が1つに絞れる場合）
    if len(ql) >= 3:
        starts = sorted({t for name, t in cat.items() if name.startswith(ql)})
        if len(starts) == 1:
            return starts[0]

    # 6. 東証の社名 部分一致（候補が1つに絞れる場合）
    if nq:
        jp_contains = sorted({t for name, t in _JP_NAME_INDEX.items() if nq in name})
        if len(jp_contains) == 1:
            return jp_contains[0]

    # 7. あいまい一致（"microsft" → "microsoft" など英語のタイプミス）
    close = difflib.get_close_matches(ql, list(cat.keys()), n=1, cutoff=0.72)
    if close:
        return cat[close[0]]

    # 8. あいまい一致（日本語社名のゆれ）
    close_jp = difflib.get_close_matches(nq, _JP_NAME_LIST, n=1, cutoff=0.8)
    if close_jp:
        return _JP_NAME_INDEX[close_jp[0]]

    # 9. 英語カタログの部分一致（候補が1つに絞れる場合）
    contains = sorted({t for name, t in cat.items() if ql in name})
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

    # 根拠を文章（説明文）で組み立てる
    sentences = []
    if range_pct is not None:
        if range_pct <= 25:
            zone = "安値圏にあります"
        elif range_pct <= 50:
            zone = "中央より下のやや安い水準です"
        elif range_pct < 85:
            zone = "中央より上のやや高い水準です"
        else:
            zone = "高値圏にあります"
        sentences.append(
            f"現在値は過去52週の値動きのうち下から約{range_pct:.0f}%の位置にあり、{zone}。"
        )
    if ma200:
        diff = (price - ma200) / ma200 * 100
        if diff <= -3:
            sentences.append(
                f"200日移動平均を約{abs(diff):.0f}%下回っており、中期トレンドに対して割安感があります。"
            )
        elif diff >= 10:
            sentences.append(
                f"200日移動平均を約{diff:.0f}%上回っており、やや過熱感があります。"
            )
        else:
            sentences.append(
                f"200日移動平均とほぼ同水準（{diff:+.0f}%）で推移しています。"
            )

    conclusion = {
        "買い時": "総合すると、割安・売られすぎのサインが出ており、現時点では買い時と判断できます。",
        "やや買い時": "総合すると、ややディスカウントされた水準で、押し目買いを検討できる場面です。",
        "中立": "総合すると、目立った割安・割高シグナルはなく、中立的な水準です。",
        "高値圏": "総合すると、高値圏にあり、新規の買いには慎重さが求められます。",
    }[label]

    if sentences:
        sentences.append(conclusion)
        detail = "".join(sentences)
    else:
        detail = "株価データが不足しているため、買い時の判断材料が十分にありません。"

    return {
        "timing_label": label,
        "timing_score": score,
        "timing_reason": "・".join(reasons) if reasons else "目立った割安・割高シグナルなし",
        "timing_detail": detail,
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
    """会社名・証券コード・ティッカーシンボルからティッカーを返す。"""
    q = query.strip()
    if not q:
        return None

    # 証券コード4桁はそのまま東証(.T)として扱う（例: 7734 → 7734.T）
    if re.fullmatch(r"\d{4}", q):
        return f"{q}.T"

    # まずティッカーとして直接試す（エラー出力を抑制）
    devnull = open(os.devnull, "w")
    old_stderr = sys.stderr
    sys.stderr = devnull
    try:
        info = yf.Ticker(q).info
        has_price = bool(info.get("currentPrice") or info.get("regularMarketPrice"))
    finally:
        sys.stderr = old_stderr
        devnull.close()

    if has_price:
        return q

    # 別名・東証全銘柄の「完全一致」を Yahoo 検索より先に試す
    # （日本語社名は Yahoo 検索がほぼ拾えないため。例: 理研計器 → 7734.T）
    exact = _local_resolve(q, fuzzy=False)
    if exact:
        return exact

    # 会社名として検索（あいまいな入力でも Yahoo の検索が類推してくれる）
    try:
        results = yf.Search(q).quotes
    except Exception:
        results = []

    equities = [r for r in results if r.get("quoteType") == "EQUITY" and r.get("symbol")]
    # 株式が見つからなければ ETF などシンボルを持つ候補にフォールバック
    if not equities:
        equities = [r for r in results if r.get("symbol")]

    # Yahoo の検索で見つからない場合は、ローカル辞書であいまい解決を試みる
    # （日本語の会社名や、つづり間違いに対応）
    if not equities:
        return _local_resolve(q, fuzzy=True)

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


_TRANS_CACHE: dict = {}


def _translate_ja(text: str) -> str:
    """英語テキストを日本語に翻訳する（失敗時は原文のまま返す）。"""
    if not text or GoogleTranslator is None:
        return text
    key = text[:120]
    if key in _TRANS_CACHE:
        return _TRANS_CACHE[key]
    try:
        out = GoogleTranslator(source="auto", target="ja").translate(text[:4500]) or text
    except Exception:
        out = text
    _TRANS_CACHE[key] = out
    return out


def _translate_many_ja(texts: list[str]) -> list[str]:
    """複数テキストをまとめて日本語に翻訳する（失敗時は原文のまま）。"""
    if not texts or GoogleTranslator is None:
        return texts
    try:
        out = GoogleTranslator(source="auto", target="ja").translate_batch(texts)
        return [o or t for o, t in zip(out, texts)]
    except Exception:
        return texts


# 株価一括ダウンロードのキャッシュ（同じ銘柄群への連続アクセスを高速化）
_PRICE_CACHE: dict = {}
_PRICE_TTL = 600  # 秒


def _download_prices(tickers: list[str]):
    """銘柄群の1年分の日足を一括取得する（TTL付きキャッシュ）。"""
    key = tuple(sorted(tickers))
    now = time.time()
    cached = _PRICE_CACHE.get(key)
    if cached and now - cached[0] < _PRICE_TTL:
        return cached[1]
    data = yf.download(
        list(tickers), period="1y", interval="1d",
        group_by="ticker", auto_adjust=True, progress=False, threads=True,
    )
    _PRICE_CACHE[key] = (now, data)
    return data


def screen_recommendations(budget_jpy: int = 300000, sector_jp: str | None = None,
                           limit: int = 30) -> list[dict]:
    """日本株ユニバース（業界指定があればその業界）から、予算内で買える銘柄を
    その時点の市場状況（株価）に基づく「買い時」順で抽出して返す。

    価格は一括ダウンロード＋キャッシュで取得するため高速。
    """
    pool = _universe()
    if sector_jp:
        pool = [u for u in pool if u[2] == sector_jp]
    if not pool:
        return []

    tickers = [t for t, _, _ in pool]
    meta = {t: (name, sector) for t, name, sector in pool}

    data = _download_prices(tickers)
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
        name, sector = meta[ticker]

        rows.append({
            "ticker": ticker,
            "name": name,
            "sector": sector,
            "is_jp": is_jp,
            "currency": "JPY" if is_jp else "USD",
            "price_jpy": round(price_jpy),
            "min_cost": round(min_cost),
            "units": units,
            "affordable": int(budget_jpy // min_cost),
            "change_pct": _r2(change_pct),
            "timing_label": timing["timing_label"],
            "timing_score": timing["timing_score"],
            "timing_reason": timing["timing_reason"],
            "timing_detail": timing["timing_detail"],
            "range_pct": timing["range_pct"],
        })

    # 買い時スコア降順 → 同点ならレンジ内位置が低い（割安）順
    rows.sort(
        key=lambda r: (
            r["timing_score"],
            -(r["range_pct"] if r["range_pct"] is not None else 50),
        ),
        reverse=True,
    )
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


def _movement_analysis(change_pct, range_pct, news) -> str:
    """直近の値動き・トレンド・ニュースから「なぜ動いたか」を推測する考察文。"""
    parts = []

    # 直近の値動き
    if change_pct is not None:
        if change_pct >= 3:
            move = f"前日比 +{change_pct:.1f}% と大きく上昇しました"
        elif change_pct > 0.3:
            move = f"前日比 +{change_pct:.1f}% と上昇しました"
        elif change_pct <= -3:
            move = f"前日比 {change_pct:.1f}% と大きく下落しました"
        elif change_pct < -0.3:
            move = f"前日比 {change_pct:.1f}% と下落しました"
        else:
            move = f"前日比 {change_pct:+.1f}% とほぼ横ばいでした"
        parts.append(f"直近の株価は{move}。")

    # 1年のトレンド文脈
    if range_pct is not None:
        if range_pct >= 75:
            parts.append("ここ1年では高値圏にあり、上昇基調が続いています。")
        elif range_pct <= 25:
            parts.append("ここ1年では安値圏にあり、調整・下落基調が続いています。")
        else:
            parts.append("ここ1年ではレンジの中ほどで推移しています。")

    # ニュースを材料として推測
    titles = [n["title"] for n in (news or [])[:2] if n.get("title")]
    if titles:
        joined = "」「".join(titles)
        parts.append(
            f"背景としては、最近報じられた「{joined}」といったトピックが材料視された可能性があります。"
        )

    if not parts:
        return ""

    parts.append("（公開情報からの推測であり、実際の変動要因とは異なる場合があります。）")
    return "".join(parts)


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

    # 企業概要・ニュース見出しを日本語に翻訳する
    summary = _translate_ja(info.get("longBusinessSummary") or "")
    news = _fetch_news(stock)
    if news:
        ja_titles = _translate_many_ja([n["title"] for n in news])
        for n, title in zip(news, ja_titles):
            n["title"] = title

    # 値動きの考察（翻訳済みニュースを材料に推測）
    analysis = _movement_analysis(base["change_pct"], timing["range_pct"], news)

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
        "summary": summary,
        "high_52w": _r2(base["high_52w"]),
        "low_52w": _r2(base["low_52w"]),
        "market_cap_str": base["market_cap_str"],
        # 買い時
        "timing_label": timing["timing_label"],
        "timing_reason": timing["timing_reason"],
        "timing_detail": timing["timing_detail"],
        "movement_analysis": analysis,
        "range_pct": timing["range_pct"],
        # アナリスト予想（今後の値動きの目安）
        "target_mean": _r2(target),
        "target_high": _r2(info.get("targetHighPrice")),
        "target_low": _r2(info.get("targetLowPrice")),
        "upside": _r2(upside),
        "rec_label": REC_LABEL.get(rec_key, rec_key),
        # 最近のトピック
        "news": news,
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
