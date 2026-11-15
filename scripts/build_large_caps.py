"""おすすめ・検索で使う大型株リスト（large_caps.json）を生成するスクリプト。

日本株は東証全銘柄（jp_stocks.json）から売買代金の大きい銘柄を候補にし、
米国株は S&P 500 構成銘柄を候補にして、時価総額のしきい値以上の銘柄だけを残す。
業界は yfinance の sector を app.py の SECTOR_LABEL で日本語化して付与する。

使い方（リポジトリのルートで実行）:
    python scripts/build_large_caps.py
"""

import csv
import io
import json
import logging
import sys
import time
import unicodedata
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import yfinance as yf
from yfinance.exceptions import YFRateLimitError

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from app import SECTOR_LABEL  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

SP500_CSV_URL = "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/main/data/constituents.csv"
# S&P 500 には含まれないが日本から人気のある海外大型株（ADR など）
EXTRA_US_TICKERS = [
    "TSM", "ASML", "NVO", "ARM", "SHOP", "SONY", "TM", "BABA", "SAP", "AZN",
    "NVS", "SHEL", "BP", "UL", "HSBC", "MELI", "SE", "SPOT", "RIVN", "COIN",
    "SNOW", "NET", "CRWD", "ZS", "RBLX", "MRNA", "CCJ", "PLTR", "TEAM", "HOOD",
]
JP_MIN_MARKET_CAP = 300_000_000_000  # 3000億円
US_MIN_MARKET_CAP = 10_000_000_000  # 100億ドル
JP_CANDIDATE_COUNT = 500  # 売買代金上位から時価総額を調べる件数
MAX_RETRIES = 5
JP_CHUNK_SIZE = 100
# 同じ会社の別クラス株（重複表示を避けるため除外）
EXCLUDED_TICKERS = {"GOOG", "FOX", "NWS", "BRK-A"}
FETCH_WORKERS = 2
NAME_SUFFIXES = [
    ", Inc.", " Inc.", " Inc", ", Incorporated", " Corporation", " Corp.", " Corp",
    " Co., Ltd.", " Company", " plc", " PLC", " N.V.", " S.A.", " Ltd.", " Limited",
    " Holdings", " Group",
]


def load_sp500_tickers() -> list[str]:
    """S&P 500 構成銘柄のティッカー一覧を取得する（yfinance 形式: BRK.B → BRK-B）。

    Returns:
        ティッカーのリスト
    """
    with urllib.request.urlopen(SP500_CSV_URL, timeout=30) as response:
        text = response.read().decode("utf-8")
    reader = csv.DictReader(io.StringIO(text))
    return [row["Symbol"].replace(".", "-") for row in reader]


def select_jp_candidates(jp_stocks: dict[str, str]) -> list[str]:
    """東証全銘柄から直近の平均売買代金が大きい順に候補を選ぶ。

    Args:
        jp_stocks: 証券コード → 社名 の辞書

    Returns:
        "コード.T" 形式のティッカーのリスト
    """
    tickers = [f"{code}.T" for code in jp_stocks if code.isdigit()]
    turnover: dict[str, float] = {}
    for start in range(0, len(tickers), JP_CHUNK_SIZE):
        chunk = tickers[start:start + JP_CHUNK_SIZE]
        logger.info("日本株の売買代金を取得中 %d/%d", start, len(tickers))
        for attempt in range(MAX_RETRIES):
            chunk_turnover = fetch_turnover(tickers=chunk)
            # 一時的なエラー（Invalid Crumb など）でまとめて欠けた場合は再取得する
            if len(chunk_turnover) >= len(chunk) * 0.5:
                break
            logger.warning("取得できた銘柄が少ないため再試行します（%d/%d 件）", len(chunk_turnover), len(chunk))
            time.sleep(10 * (attempt + 1))
        turnover.update(chunk_turnover)
    ranked = sorted(turnover, key=lambda t: turnover[t], reverse=True)
    return ranked[:JP_CANDIDATE_COUNT]


def fetch_turnover(tickers: list[str]) -> dict[str, float]:
    """銘柄群の直近1か月の平均売買代金を取得する。

    Args:
        tickers: yfinance 形式のティッカーのリスト

    Returns:
        ティッカー → 平均売買代金 の辞書（取得できた銘柄のみ）
    """
    data = yf.download(
        tickers, period="1mo", interval="1d",
        group_by="ticker", auto_adjust=True, progress=False, threads=True,
    )
    result: dict[str, float] = {}
    for ticker in tickers:
        try:
            frame = data[ticker]
            value = float((frame["Close"] * frame["Volume"]).dropna().mean())
        except Exception:
            continue
        if value > 0:
            result[ticker] = value
    return result


def fetch_profile(ticker: str) -> dict | None:
    """銘柄の時価総額・業界・社名を取得する。取得できなければ None。

    Args:
        ticker: yfinance 形式のティッカー

    Returns:
        {"ticker", "name", "sector", "market_cap"} の辞書、または None
    """
    info = None
    for attempt in range(MAX_RETRIES):
        try:
            info = yf.Ticker(ticker).info
            if info.get("marketCap"):
                break
            # 一時的なエラー時は時価総額が欠けた情報が返ることがあるため再取得する
            logger.warning("時価総額が取得できないため再試行します: %s", ticker)
            time.sleep(5 * (attempt + 1))
        except YFRateLimitError:
            wait_seconds = 30 * (attempt + 1)
            logger.warning("レート制限のため %d 秒待機します: %s", wait_seconds, ticker)
            time.sleep(wait_seconds)
        except Exception:
            logger.warning("情報を取得できませんでした: %s", ticker)
            return None
    if info is None:
        logger.warning("再試行しても取得できませんでした: %s", ticker)
        return None
    market_cap = info.get("marketCap")
    sector = SECTOR_LABEL.get(info.get("sector") or "")
    if not market_cap or not sector:
        logger.warning("時価総額または業界が不明のため除外します: %s", ticker)
        return None
    return {
        "ticker": ticker,
        "name": info.get("shortName") or info.get("longName") or ticker,
        "sector": sector,
        "market_cap": int(market_cap),
    }


def clean_us_name(name: str) -> str:
    """英語社名から法人格などの末尾表記を取り除く。

    Args:
        name: yfinance の社名

    Returns:
        短くした社名
    """
    cleaned = name.strip()
    for suffix in NAME_SUFFIXES:
        if cleaned.endswith(suffix):
            cleaned = cleaned[: -len(suffix)].rstrip(" ,")
    return cleaned or name


def main() -> None:
    """大型株リストを生成して large_caps.json に保存する。"""
    with open(ROOT_DIR / "jp_stocks.json", encoding="utf-8") as f:
        jp_stocks: dict[str, str] = json.load(f)

    jp_candidates = select_jp_candidates(jp_stocks=jp_stocks)
    us_candidates = [
        t for t in dict.fromkeys(load_sp500_tickers() + EXTRA_US_TICKERS)
        if t not in EXCLUDED_TICKERS
    ]
    candidates = jp_candidates + us_candidates
    logger.info("時価総額を取得中: 日本 %d 件, 米国 %d 件", len(jp_candidates), len(us_candidates))

    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as executor:
        profiles = [p for p in executor.map(fetch_profile, candidates) if p]

    results = []
    for profile in profiles:
        is_jp = profile["ticker"].endswith(".T")
        threshold = JP_MIN_MARKET_CAP if is_jp else US_MIN_MARKET_CAP
        if profile["market_cap"] < threshold:
            continue
        if is_jp:
            code = profile["ticker"].removesuffix(".T")
            # 東証の社名は全角英数字を含むため NFKC で半角に揃える（例: ＭＳ＆ＡＤ → MS&AD）
            profile["name"] = unicodedata.normalize("NFKC", jp_stocks.get(code, profile["name"]))
        else:
            profile["name"] = clean_us_name(name=profile["name"])
        results.append(profile)

    results.sort(key=lambda p: p["market_cap"], reverse=True)
    output_path = ROOT_DIR / "large_caps.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=1)
    jp_count = sum(1 for p in results if p["ticker"].endswith(".T"))
    logger.info("保存しました: %s（日本 %d 件, 米国 %d 件）", output_path, jp_count, len(results) - jp_count)


if __name__ == "__main__":
    main()
