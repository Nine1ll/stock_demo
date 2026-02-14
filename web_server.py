#!/usr/bin/env python3
"""Unified web server for stock analysis app + resilient intelligence APIs.

Environment variables:
- FINNHUB_API_KEY: quote + company news
- ALPHA_VANTAGE_API_KEY: fundamentals (+news fallback)
- SEC_USER_AGENT: required by SEC endpoints (include contact)
- ALERT_POLL_SECONDS: background polling interval (default 300)
- SMTP_HOST/SMTP_PORT/SMTP_USER/SMTP_PASS/SMTP_FROM/SMTP_TLS: optional mail sender
- ONESIGNAL_APP_ID/ONESIGNAL_API_KEY: optional OneSignal push sender
- DART_API_KEY: optional Korea DART filings API key
- APP_DATA_DIR: override runtime data directory (sqlite, cache files)
"""

from __future__ import annotations

import argparse
import gzip
import io
import json
import os
import re
import smtplib
import sqlite3
import ssl
import threading
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent
data_dir_raw = os.getenv("APP_DATA_DIR", "").strip()
if data_dir_raw:
    data_dir_candidate = Path(data_dir_raw).expanduser()
    if not data_dir_candidate.is_absolute():
        data_dir_candidate = ROOT_DIR / data_dir_candidate
    DATA_DIR = data_dir_candidate
else:
    DATA_DIR = ROOT_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DATA_DIR / "stock_app.db"
SECTOR_SEED_PATH = DATA_DIR / "sector_seed.json"
DEFAULT_SEC_USER_AGENT = "stock-intel-app/1.0 (contact: example@example.com)"
DEFAULT_HEADERS = {
    "User-Agent": "stock-intel-app/1.0",
    "Accept": "application/json,text/plain,*/*",
}
ALLOWED_MARKETS = {"US", "KR"}
ALLOWED_LOOKUP_MARKETS = {"US", "KR", "ALL"}
KR_TICKER_PROFILE = {
    "018880": {"name": "한온시스템", "sector": "기계장비", "industry": "자동차부품"},
    "088350": {"name": "한화생명", "sector": "금융", "industry": "생명보험"},
    "009830": {"name": "한화솔루션", "sector": "화학", "industry": "화학/태양광"},
    "130660": {"name": "한전산업", "sector": "에너지", "industry": "전력설비/에너지서비스"},
    "373220": {"name": "LG에너지솔루션", "sector": "2차전지", "industry": "이차전지"},
    "006400": {"name": "삼성SDI", "sector": "2차전지", "industry": "이차전지"},
    "036540": {"name": "SFA반도체", "sector": "반도체", "industry": "반도체 및 반도체장비"},
    "005380": {"name": "현대차", "sector": "자동차", "industry": "자동차"},
    "000270": {"name": "기아", "sector": "자동차", "industry": "자동차"},
    "012330": {"name": "현대모비스", "sector": "자동차", "industry": "자동차부품"},
    "204320": {"name": "HL만도", "sector": "자동차", "industry": "자동차부품"},
    "009540": {"name": "HD한국조선해양", "sector": "조선방산", "industry": "조선"},
    "032830": {"name": "삼성생명", "sector": "금융", "industry": "생명보험"},
    "001510": {"name": "SK증권", "sector": "증권", "industry": "증권"},
    "006800": {"name": "미래에셋증권", "sector": "증권", "industry": "증권"},
    "039490": {"name": "키움증권", "sector": "증권", "industry": "증권"},
    "016360": {"name": "삼성증권", "sector": "증권", "industry": "증권"},
    "005940": {"name": "NH투자증권", "sector": "증권", "industry": "증권"},
    "003540": {"name": "대신증권", "sector": "증권", "industry": "증권"},
}
DEFAULT_RULES = {
    "price_change_pct": 5.0,
    "hype_score_jump": 15.0,
    "new_filing": 1.0,
}
CACHE: Dict[str, Tuple[float, Any]] = {}
CACHE_LOCK = threading.Lock()
ALERT_THREAD_STOP = threading.Event()


def log_event(event: str, **fields: Any) -> None:
    payload = {"event": event, "time": utc_now_iso()}
    payload.update(fields)
    try:
        print(json.dumps(payload, ensure_ascii=False), flush=True)
    except Exception:
        # Never fail request flow due to logging.
        pass


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_env_file(path: Path, override: bool = False) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        if not key:
            continue
        current = os.environ.get(key)
        if override or key not in os.environ or current is None or str(current).strip() == "":
            os.environ[key] = val


def decode_http_body(raw: bytes, content_encoding: str, content_type: str = "") -> str:
    data = raw
    encoding = (content_encoding or "").lower()
    if "gzip" in encoding or raw[:2] == b"\x1f\x8b":
        data = gzip.decompress(raw)

    charset = ""
    m = re.search(r"charset=([A-Za-z0-9_\-]+)", str(content_type or ""), flags=re.IGNORECASE)
    if m:
        charset = m.group(1).strip().strip(";").lower()

    tried = set()
    for enc in [charset, "utf-8", "cp949", "euc-kr", "latin-1"]:
        if not enc or enc in tried:
            continue
        tried.add(enc)
        try:
            return data.decode(enc, errors="replace")
        except Exception:
            continue
    return data.decode("utf-8", errors="replace")


def http_get_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 20) -> Any:
    req_headers = dict(DEFAULT_HEADERS)
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
        content = decode_http_body(
            resp.read(),
            resp.headers.get("Content-Encoding", ""),
            resp.headers.get("Content-Type", ""),
        )
        return json.loads(content)


def http_get_text(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 20) -> str:
    req_headers = dict(DEFAULT_HEADERS)
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, headers=req_headers)
    with urllib.request.urlopen(req, timeout=timeout, context=ssl.create_default_context()) as resp:
        return decode_http_body(
            resp.read(),
            resp.headers.get("Content-Encoding", ""),
            resp.headers.get("Content-Type", ""),
        )


def clean_ticker(value: str) -> str:
    return (value or "").strip().upper()


def clean_market(value: str) -> str:
    market = (value or "US").strip().upper()
    return market if market in ALLOWED_MARKETS else "US"


def clean_lookup_market(value: str) -> str:
    market = (value or "US").strip().upper()
    return market if market in ALLOWED_LOOKUP_MARKETS else "US"


def symbol_for_yahoo(ticker: str, market: str) -> str:
    if market == "KR":
        raw = re.sub(r"[^0-9]", "", ticker)
        if len(raw) != 6:
            return ticker
        return f"{raw}.KS"
    return ticker


def normalize_kr_ticker(ticker: str) -> str:
    raw = re.sub(r"[^0-9]", "", ticker or "")
    return raw.zfill(6) if raw else ""


def state_key_for_market(market: str, key: str) -> str:
    return f"{market}:{key}"


def find_first_number(text: str, pattern: str) -> Optional[float]:
    m = re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    if not m:
        return None
    s = m.group(1).replace(",", "").strip()
    try:
        return float(s)
    except Exception:
        return None


def to_float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).replace(",", "").replace("%", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def cache_get_or_set(key: str, ttl_seconds: int, producer: Callable[[], Any]) -> Any:
    now = datetime.now(timezone.utc).timestamp()
    with CACHE_LOCK:
        hit = CACHE.get(key)
        if hit and hit[0] >= now:
            return hit[1]

    value = producer()
    with CACHE_LOCK:
        CACHE[key] = (now + max(1, ttl_seconds), value)
    return value


def provider_error(source: str, error: str) -> Dict[str, Any]:
    return {"ok": False, "source": source, "error": error}


def normalize_search_key(text: str) -> str:
    return re.sub(r"[\s\W_]+", "", str(text or "").lower(), flags=re.UNICODE)


def canonical_sector(sector: str, name: str = "", industry: str = "") -> str:
    raw_sector = str(sector or "").strip()
    raw_name = str(name or "").strip()
    raw_industry = str(industry or "").strip()
    text = normalize_search_key(f"{raw_sector} {raw_name} {raw_industry}")

    def has_any(keywords: List[str]) -> bool:
        return any(normalize_search_key(k) in text for k in keywords if k)

    # Priority: specific theme sectors first.
    if has_any(["원자력", "원전", "nuclear", "smr", "uranium", "두산에너빌리티", "한전기술", "한전kps"]):
        return "원자력"
    if has_any(["반도체", "semiconductor", "hbm", "dram", "nand", "파운드리", "chip"]):
        return "반도체"
    if has_any(["휴머노이드", "humanoid", "로봇", "robotics", "robot", "automation"]):
        return "휴머노이드"
    if has_any(["자동차", "auto", "automotive", "vehicle", "모빌리티", "ev", "자율주행"]):
        return "자동차"
    if has_any(["2차전지", "이차전지", "secondarybattery", "batterycell", "배터리소재", "bms"]):
        return "2차전지"
    if has_any(["it서비스", "itservice", "itservices", "softwareitservices", "software&itservices", "si", "systemintegration", "erp", "클라우드서비스"]):
        return "IT서비스"
    if has_any(["게임", "gaming", "game", "videogame", "mmorpg", "rpg", "엔씨소프트", "카카오게임즈", "넷마블", "크래프톤"]):
        return "게임/콘텐츠"
    if has_any(["증권", "securities", "broker", "brokerage", "capitalmarkets", "미래에셋증권", "키움증권", "sk증권", "nh투자증권", "삼성증권"]):
        return "증권"
    if has_any(["금융", "finance", "financial", "bank", "banking", "insurance", "보험", "금융지주", "카카오뱅크", "인터넷은행"]):
        return "금융"
    if has_any(["ai", "인공지능", "llm", "gpu", "클라우드", "platform", "internet", "software", "saas"]):
        return "AI"

    mapping = {
        "technology": "AI",
        "semiconductors": "반도체",
        "인터넷플랫폼": "인터넷플랫폼",
        "로보틱스": "휴머노이드",
        "robotics": "휴머노이드",
        "consumer cyclical": "자동차",
        "capital goods": "기계장비",
        "financial services": "금융",
        "healthcare": "바이오",
        "communication services": "게임/콘텐츠",
        "basic materials": "화학",
        "utilities": "에너지",
    }
    mapped = mapping.get(raw_sector.lower(), "")
    if mapped:
        return mapped
    if raw_sector:
        return raw_sector
    return "기타"


def load_sector_seed() -> List[Dict[str, Any]]:
    def producer() -> List[Dict[str, Any]]:
        if not SECTOR_SEED_PATH.exists():
            return []
        try:
            data = json.loads(SECTOR_SEED_PATH.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    return cache_get_or_set("sector:seed", 3600, producer)


def find_company_name_from_seed(ticker: str, market: str) -> str:
    t = (ticker or "").strip().upper()
    m = (market or "US").strip().upper()
    if not t:
        return ""
    for item in load_sector_seed():
        im = str(item.get("market", "")).strip().upper()
        if im != m:
            continue
        it = str(item.get("ticker", "")).strip().upper()
        if m == "KR":
            it = normalize_kr_ticker(it)
            t_cmp = normalize_kr_ticker(t)
        else:
            t_cmp = t
        if it == t_cmp:
            return str(item.get("name", "")).strip()
    return ""


def find_sector_from_seed(ticker: str, market: str) -> str:
    t = (ticker or "").strip().upper()
    m = (market or "US").strip().upper()
    if not t:
        return ""
    for item in load_sector_seed():
        im = str(item.get("market", "")).strip().upper()
        if im != m:
            continue
        it = str(item.get("ticker", "")).strip().upper()
        if m == "KR":
            it = normalize_kr_ticker(it)
            t_cmp = normalize_kr_ticker(t)
        else:
            t_cmp = t
        if it == t_cmp:
            return canonical_sector(str(item.get("sector", "")).strip(), str(item.get("name", "")).strip(), "")
    if m == "KR":
        profile = KR_TICKER_PROFILE.get(normalize_kr_ticker(t), {})
        return canonical_sector(str(profile.get("sector", "")).strip(), str(profile.get("name", "")).strip(), str(profile.get("industry", "")).strip())
    return ""


def infer_industry_from_sector(sector: str, market: str) -> str:
    s = (sector or "").strip()
    if not s:
        return ""
    if market == "KR":
        mapping = {
            "반도체": "반도체 및 반도체장비",
            "자동차": "자동차 및 부품",
            "2차전지": "이차전지 및 소재",
            "바이오": "제약 및 바이오",
            "인터넷플랫폼": "인터넷 서비스",
            "금융": "은행/금융지주",
            "증권": "증권/자본시장",
            "조선방산": "조선/방산",
            "화학": "화학/정유",
            "철강": "철강/금속",
            "유통": "유통/소매",
            "통신": "통신서비스",
            "엔터테인먼트": "미디어/엔터",
            "건설인프라": "건설/인프라",
            "기계장비": "기계/장비",
            "지주": "지주회사",
            "로보틱스": "로봇/자동화",
        }
        return mapping.get(s, s)
    return s


def normalize_kr_sector_text(sector: str) -> str:
    s = (sector or "").strip()
    if not s:
        return ""
    mapping = {
        "technology": "인터넷플랫폼",
        "it services": "IT서비스",
        "software & it services": "IT서비스",
        "semiconductors": "반도체",
        "consumer cyclical": "자동차",
        "capital goods": "기계장비",
        "consumer defensive": "유통",
        "financial services": "금융",
        "capital markets": "증권",
        "securities": "증권",
        "brokerage": "증권",
        "energy": "에너지",
        "industrials": "건설인프라",
        "basic materials": "화학",
        "communication services": "통신",
        "healthcare": "바이오",
        "utilities": "에너지",
        "real estate": "건설인프라",
    }
    key = s.lower()
    return mapping.get(key, s)


def normalize_kr_industry_text(industry: str, sector_hint: str = "") -> str:
    s = (industry or "").strip()
    if not s:
        return ""
    mapping = {
        "auto parts": "자동차부품",
        "automakers": "자동차",
        "semiconductors": "반도체",
        "specialty chemicals": "화학소재",
        "insurance - life": "생명보험",
        "banks - regional": "은행",
        "internet content & information": "인터넷서비스",
        "electrical equipment & parts": "전기장비",
        "oil & gas refining & marketing": "정유",
    }
    key = s.lower()
    out = mapping.get(key, s)
    if not out:
        return infer_industry_from_sector(sector_hint, "KR")
    return out


def get_kr_profile(ticker: str) -> Dict[str, str]:
    return KR_TICKER_PROFILE.get(normalize_kr_ticker(ticker), {})


def resolve_company_name(ticker: str, market: str) -> str:
    t = (ticker or "").strip().upper()
    m = clean_market(market)
    if not t:
        return ""

    def producer() -> str:
        from_seed = find_company_name_from_seed(t, m)
        if from_seed:
            return from_seed

        if m == "KR":
            code = normalize_kr_ticker(t)
            profile = get_kr_profile(code)
            if profile.get("name"):
                return str(profile.get("name"))
            if code:
                for row in get_dart_company_index():
                    if (row.get("stock_code") or "") == code:
                        return (row.get("corp_name") or "").strip()
                naver_name = fetch_company_name_naver(code)
                if naver_name:
                    return naver_name
            return code or t

        quote = fetch_quote_yahoo(t, m)
        if quote.get("ok"):
            name = str(quote.get("name") or "").strip()
            if name:
                return name
        return t

    return cache_get_or_set(f"company-name:{m}:{t}", 21600, producer)


def fetch_company_name_naver(ticker: str) -> str:
    code = normalize_kr_ticker(ticker)
    if not code:
        return ""
    url = f"https://finance.naver.com/item/main.naver?code={urllib.parse.quote(code)}"
    try:
        html = http_get_text(url, timeout=10)
    except Exception:
        return ""
    title = ""
    m = re.search(r"<title>\s*([^<]+?)\s*:\s*네이버", html, flags=re.IGNORECASE)
    if m:
        title = m.group(1).strip()
    if not title:
        m2 = re.search(r'<div class="wrap_company">.*?<h2>([^<]+)</h2>', html, flags=re.IGNORECASE | re.DOTALL)
        if m2:
            title = re.sub(r"\s+", " ", m2.group(1)).strip()
    return title


def fetch_quote_naver(ticker: str, market: str) -> Dict[str, Any]:
    if market != "KR":
        return provider_error("naver_finance", "Naver quote is for KR market only")
    code = normalize_kr_ticker(ticker)
    if not code:
        return provider_error("naver_finance", "Invalid KR ticker format")
    url = f"https://finance.naver.com/item/main.naver?code={urllib.parse.quote(code)}"
    try:
        html = http_get_text(url, timeout=12)
    except Exception as exc:
        return provider_error("naver_finance", str(exc))

    current = find_first_number(html, r'no_today[^>]*>.*?<span class="blind">([0-9,]+)</span>')
    if current is None:
        return provider_error("naver_finance", "No current price found")
    change = find_first_number(html, r'no_exday[^>]*>.*?<span class="blind">([+-]?[0-9,]+)</span>')
    pct = find_first_number(html, r'no_exday[^>]*>.*?<span class="blind">([+-]?[0-9]+(?:\.[0-9]+)?)%</span>')
    high = find_first_number(html, r"고가[^0-9]{0,20}([0-9,]+)")
    low = find_first_number(html, r"저가[^0-9]{0,20}([0-9,]+)")
    if pct is None and current and change is not None:
        base = current - change
        if base:
            pct = (change / base) * 100.0
    previous_close = (current - change) if (current is not None and change is not None) else None

    # Naver markup can change frequently; backfill missing fields from Yahoo KR quote.
    yahoo_backfill = None
    if pct is None or high is None or low is None or previous_close is None:
        yahoo_backfill = fetch_quote_yahoo(code, "KR")
        if yahoo_backfill.get("ok"):
            if pct is None:
                pct = yahoo_backfill.get("percent_change")
            if high is None:
                high = yahoo_backfill.get("high")
            if low is None:
                low = yahoo_backfill.get("low")
            if change is None:
                change = yahoo_backfill.get("change")
            if previous_close is None:
                previous_close = yahoo_backfill.get("previous_close")

    return {
        "ok": True,
        "source": "naver_finance+yahoo_backfill" if yahoo_backfill and yahoo_backfill.get("ok") else "naver_finance",
        "as_of": utc_now_iso(),
        "ticker": code,
        "market": "KR",
        "symbol": code,
        "name": resolve_company_name(code, "KR"),
        "current_price": current,
        "change": change,
        "percent_change": pct,
        "previous_close": previous_close,
        "high": high,
        "low": low,
    }


def fetch_fundamentals_naver(ticker: str, market: str) -> Dict[str, Any]:
    if market != "KR":
        return provider_error("naver_finance", "Naver fundamentals are for KR market only")
    code = normalize_kr_ticker(ticker)
    if not code:
        return provider_error("naver_finance", "Invalid KR ticker format")
    url = f"https://finance.naver.com/item/main.naver?code={urllib.parse.quote(code)}"
    try:
        html = http_get_text(url, timeout=12)
    except Exception as exc:
        return provider_error("naver_finance", str(exc))

    # Naver usually exposes fixed ids such as _per / _pbr.
    per = find_first_number(html, r'id="_per"[^>]*>\s*([0-9,]+(?:\.[0-9]+)?)')
    pbr = find_first_number(html, r'id="_pbr"[^>]*>\s*([0-9,]+(?:\.[0-9]+)?)')
    if per is None:
        per = find_first_number(html, r"PER[^0-9<]{0,20}([0-9]+(?:\.[0-9]+)?)")
    if pbr is None:
        pbr = find_first_number(html, r"PBR[^0-9<]{0,20}([0-9]+(?:\.[0-9]+)?)")
    mcap = find_first_number(html, r"시가총액[^0-9<]*([0-9,]+)")

    return {
        "ok": True,
        "source": "naver_finance",
        "as_of": utc_now_iso(),
        "ticker": code,
        "market": "KR",
        "symbol": code,
        "name": resolve_company_name(code, "KR"),
        "sector": None,
        "industry": None,
        "market_cap": mcap,
        "pe_ratio": per,
        "pb_ratio": pbr,
        "operating_margin_ttm": None,
        "roe": None,
    }


def fetch_news_naver_finance(ticker: str, market: str) -> Dict[str, Any]:
    if market != "KR":
        return provider_error("naver_finance_news", "Naver finance news is for KR market only")
    code = normalize_kr_ticker(ticker)
    if not code:
        return provider_error("naver_finance_news", "Invalid KR ticker format")
    url = f"https://finance.naver.com/item/news_news.naver?code={urllib.parse.quote(code)}&page=1"
    try:
        html = http_get_text(url, timeout=12)
    except Exception as exc:
        return provider_error("naver_finance_news", str(exc))

    # Parse item links from table rows.
    rows = re.findall(
        r'<a href="(/item/news_read\\.naver\\?article_id=[^"]+)"[^>]*>(.*?)</a>.*?<td class="date">([^<]+)</td>',
        html,
        flags=re.IGNORECASE | re.DOTALL,
    )
    items = []
    for href, title_html, date_txt in rows[:15]:
        title = re.sub(r"<[^>]+>", "", title_html).strip()
        items.append(
            {
                "headline": title,
                "source": "Naver Finance",
                "url": f"https://finance.naver.com{href}",
                "summary": "",
                "datetime": date_txt.strip(),
            }
        )
    return {"ok": True, "source": "naver_finance_news", "ticker": code, "market": "KR", "count": len(items), "items": items}


def fetch_related_stocks_naver(ticker: str, market: str, limit: int = 20) -> Dict[str, Any]:
    if market != "KR":
        return provider_error("naver_related", "Naver related stocks are for KR market only")
    code = normalize_kr_ticker(ticker)
    if not code:
        return provider_error("naver_related", "Invalid KR ticker format")
    def parse_rows(html: str) -> List[Tuple[str, str]]:
        return re.findall(
            r'href="/item/main\.naver\?code=([0-9]{6})"[^>]*>([^<]+)</a>',
            html,
            flags=re.IGNORECASE,
        )

    out: List[Dict[str, Any]] = []
    seen = set()
    html_blobs: List[str] = []

    def append_rows(rows: List[Tuple[str, str]], source: str) -> None:
        for peer_code, peer_name in rows:
            pc = normalize_kr_ticker(peer_code)
            if not pc or pc == code:
                continue
            if pc in seen:
                continue
            seen.add(pc)
            clean_name = re.sub(r"\s+", " ", peer_name).strip()
            peer_sector = find_sector_from_seed(pc, "KR")
            if not peer_sector:
                peer_sector = canonical_sector("", clean_name, "")
            out.append(
                {
                    "ticker": pc,
                    "name": clean_name,
                    "sector": peer_sector or "기타",
                    "market": "KR",
                    "source": source,
                    "rank": 0.0,
                }
            )
            if len(out) >= max(1, min(limit, 60)):
                break

    errors: List[str] = []
    main_url = f"https://finance.naver.com/item/main.naver?code={urllib.parse.quote(code)}"
    try:
        main_html = http_get_text(main_url, timeout=12)
        html_blobs.append(main_html)
    except Exception as exc:
        errors.append(str(exc))

    # 동일업종 비교는 종종 기업정보(coinfo) 화면에만 포함되므로 2차 파싱.
    if len(out) < 3:
        coinfo_url = f"https://finance.naver.com/item/coinfo.naver?code={urllib.parse.quote(code)}"
        try:
            coinfo_html = http_get_text(coinfo_url, timeout=12)
            html_blobs.append(coinfo_html)
        except Exception as exc:
            errors.append(str(exc))

    # Naver 동일업종 상세 페이지(upjong)까지 추적해 소형주 피어를 보강.
    if html_blobs:
        nos = set()
        for html in html_blobs:
            for no in re.findall(r"/sise/sise_group_detail\.naver\?type=upjong&no=([0-9]+)", html, flags=re.IGNORECASE):
                if no:
                    nos.add(no)
        for no in sorted(nos)[:3]:
            upjong_url = f"https://finance.naver.com/sise/sise_group_detail.naver?type=upjong&no={urllib.parse.quote(no)}"
            try:
                upjong_html = http_get_text(upjong_url, timeout=12)
                append_rows(parse_rows(upjong_html), "naver_related_upjong")
            except Exception as exc:
                errors.append(str(exc))
            if len(out) >= max(1, min(limit, 60)):
                break

    # Last fallback: coinfo links (less precise than upjong, so only if upjong yielded none).
    if not out and len(html_blobs) >= 2:
        append_rows(parse_rows(html_blobs[-1]), "naver_related_coinfo")

    if not out:
        return provider_error("naver_related", "; ".join(errors) if errors else "No related stocks found")
    return {"ok": True, "source": "naver_related", "ticker": code, "market": "KR", "count": len(out), "items": out}


def get_related_stocks(ticker: str, market: str = "US", limit: int = 20) -> Dict[str, Any]:
    t = clean_ticker(ticker)
    m = clean_market(market)
    lim = max(1, min(limit, 60))
    if not t:
        return {"ok": False, "error": "ticker is required"}

    def producer() -> Dict[str, Any]:
        tried: List[Dict[str, str]] = []
        if m == "KR":
            out = fetch_related_stocks_naver(t, m, limit=lim)
            if out.get("ok"):
                return out
            tried.append({"source": out.get("source", "naver_related"), "status": "fail", "error": out.get("error", "")})
        return {"ok": False, "error": "No related-stock provider result", "providers_tried": tried}

    return cache_get_or_set(f"related-stocks:{m}:{t}:{lim}", 600, producer)


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with db_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
              user_id TEXT PRIMARY KEY,
              created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS watchlist (
              user_id TEXT NOT NULL,
              ticker TEXT NOT NULL,
              market TEXT NOT NULL DEFAULT 'US',
              notes TEXT NOT NULL DEFAULT '',
              created_at TEXT NOT NULL,
              PRIMARY KEY (user_id, ticker, market)
            );

            CREATE TABLE IF NOT EXISTS alert_rules (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id TEXT NOT NULL,
              ticker TEXT NOT NULL,
              market TEXT NOT NULL DEFAULT 'US',
              rule_type TEXT NOT NULL,
              threshold REAL NOT NULL,
              enabled INTEGER NOT NULL DEFAULT 1,
              created_at TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              UNIQUE(user_id, ticker, market, rule_type)
            );

            CREATE TABLE IF NOT EXISTS user_channels (
              user_id TEXT PRIMARY KEY,
              email TEXT NOT NULL DEFAULT '',
              webhook_url TEXT NOT NULL DEFAULT '',
              onesignal_external_id TEXT NOT NULL DEFAULT '',
              push_enabled INTEGER NOT NULL DEFAULT 0,
              updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS notifications (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id TEXT NOT NULL,
              ticker TEXT NOT NULL,
              market TEXT NOT NULL DEFAULT 'US',
              kind TEXT NOT NULL,
              message TEXT NOT NULL,
              payload_json TEXT NOT NULL,
              created_at TEXT NOT NULL,
              delivered_email INTEGER NOT NULL DEFAULT 0,
              delivered_webhook INTEGER NOT NULL DEFAULT 0,
              delivered_push INTEGER NOT NULL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS alert_state (
              user_id TEXT NOT NULL,
              ticker TEXT NOT NULL,
              market TEXT NOT NULL DEFAULT 'US',
              state_key TEXT NOT NULL,
              state_value TEXT NOT NULL,
              updated_at TEXT NOT NULL,
              PRIMARY KEY (user_id, ticker, state_key)
            );
            """
        )
        # Lightweight migration for existing DBs
        watch_cols = {r["name"] for r in conn.execute("PRAGMA table_info(watchlist)").fetchall()}
        if "market" not in watch_cols:
            conn.execute("ALTER TABLE watchlist ADD COLUMN market TEXT NOT NULL DEFAULT 'US'")
        rule_cols = {r["name"] for r in conn.execute("PRAGMA table_info(alert_rules)").fetchall()}
        if "market" not in rule_cols:
            conn.execute("ALTER TABLE alert_rules ADD COLUMN market TEXT NOT NULL DEFAULT 'US'")
        channel_cols = {r["name"] for r in conn.execute("PRAGMA table_info(user_channels)").fetchall()}
        if "onesignal_external_id" not in channel_cols:
            conn.execute("ALTER TABLE user_channels ADD COLUMN onesignal_external_id TEXT NOT NULL DEFAULT ''")
        if "push_enabled" not in channel_cols:
            conn.execute("ALTER TABLE user_channels ADD COLUMN push_enabled INTEGER NOT NULL DEFAULT 0")
        notif_cols = {r["name"] for r in conn.execute("PRAGMA table_info(notifications)").fetchall()}
        if "market" not in notif_cols:
            conn.execute("ALTER TABLE notifications ADD COLUMN market TEXT NOT NULL DEFAULT 'US'")
        if "delivered_push" not in notif_cols:
            conn.execute("ALTER TABLE notifications ADD COLUMN delivered_push INTEGER NOT NULL DEFAULT 0")
        state_cols = {r["name"] for r in conn.execute("PRAGMA table_info(alert_state)").fetchall()}
        if "market" not in state_cols:
            conn.execute("ALTER TABLE alert_state ADD COLUMN market TEXT NOT NULL DEFAULT 'US'")

        # Align watchlist PK with market-aware design: (user_id, ticker, market)
        watch_pk = [
            r["name"]
            for r in sorted(
                conn.execute("PRAGMA table_info(watchlist)").fetchall(),
                key=lambda x: int(x["pk"] or 0),
            )
            if int(r["pk"] or 0) > 0
        ]
        if watch_pk != ["user_id", "ticker", "market"]:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS watchlist_v2 (
                  user_id TEXT NOT NULL,
                  ticker TEXT NOT NULL,
                  market TEXT NOT NULL DEFAULT 'US',
                  notes TEXT NOT NULL DEFAULT '',
                  created_at TEXT NOT NULL,
                  PRIMARY KEY (user_id, ticker, market)
                );
                INSERT OR IGNORE INTO watchlist_v2(user_id, ticker, market, notes, created_at)
                SELECT user_id, ticker, COALESCE(NULLIF(market, ''), 'US'), notes, created_at
                FROM watchlist;
                DROP TABLE watchlist;
                ALTER TABLE watchlist_v2 RENAME TO watchlist;
                """
            )

        # Align alert_rules UNIQUE with market-aware design: (user_id, ticker, market, rule_type)
        unique_ok = False
        for idx in conn.execute("PRAGMA index_list(alert_rules)").fetchall():
            if int(idx["unique"] or 0) != 1:
                continue
            cols = [c["name"] for c in conn.execute(f"PRAGMA index_info('{idx['name']}')").fetchall()]
            if cols == ["user_id", "ticker", "market", "rule_type"]:
                unique_ok = True
                break
        if not unique_ok:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS alert_rules_v2 (
                  id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id TEXT NOT NULL,
                  ticker TEXT NOT NULL,
                  market TEXT NOT NULL DEFAULT 'US',
                  rule_type TEXT NOT NULL,
                  threshold REAL NOT NULL,
                  enabled INTEGER NOT NULL DEFAULT 1,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  UNIQUE(user_id, ticker, market, rule_type)
                );
                INSERT OR IGNORE INTO alert_rules_v2(id, user_id, ticker, market, rule_type, threshold, enabled, created_at, updated_at)
                SELECT id, user_id, ticker, COALESCE(NULLIF(market, ''), 'US'), rule_type, threshold, enabled, created_at, updated_at
                FROM alert_rules;
                DROP TABLE alert_rules;
                ALTER TABLE alert_rules_v2 RENAME TO alert_rules;
                """
            )


def ensure_user(user_id: str) -> None:
    now = utc_now_iso()
    with db_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO users(user_id, created_at) VALUES (?, ?)",
            (user_id, now),
        )


def list_watchlist(user_id: str) -> List[Dict[str, Any]]:
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT user_id, ticker, market, notes, created_at FROM watchlist WHERE user_id = ? ORDER BY market, ticker",
            (user_id,),
        ).fetchall()
        out: List[Dict[str, Any]] = []
        for row in rows:
            rec = dict(row)
            rec["company_name"] = resolve_company_name(str(rec.get("ticker") or ""), str(rec.get("market") or "US"))
            out.append(rec)
        return out


def upsert_default_rules(user_id: str, ticker: str, market: str, price_change: float, hype_jump: float, filing_enabled: bool) -> None:
    now = utc_now_iso()
    rules = [
        ("price_change_pct", float(price_change), 1),
        ("hype_score_jump", float(hype_jump), 1),
        ("new_filing", 1.0, 1 if filing_enabled else 0),
    ]
    with db_conn() as conn:
        for rule_type, threshold, enabled in rules:
            conn.execute(
                """
                INSERT INTO alert_rules(user_id, ticker, market, rule_type, threshold, enabled, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(user_id, ticker, market, rule_type)
                DO UPDATE SET threshold = excluded.threshold, enabled = excluded.enabled, updated_at = excluded.updated_at
                """,
                (user_id, ticker, market, rule_type, threshold, enabled, now, now),
            )


def add_watch_item(user_id: str, ticker: str, market: str, notes: str = "") -> None:
    ensure_user(user_id)
    now = utc_now_iso()
    with db_conn() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO watchlist(user_id, ticker, market, notes, created_at) VALUES (?, ?, ?, ?, ?)",
            (user_id, ticker, market, notes, now),
        )
        conn.execute(
            "UPDATE watchlist SET notes = ? WHERE user_id = ? AND ticker = ? AND market = ?",
            (notes, user_id, ticker, market),
        )
    upsert_default_rules(
        user_id,
        ticker,
        market,
        price_change=DEFAULT_RULES["price_change_pct"],
        hype_jump=DEFAULT_RULES["hype_score_jump"],
        filing_enabled=True,
    )


def delete_watch_item(user_id: str, ticker: str, market: str) -> None:
    with db_conn() as conn:
        conn.execute("DELETE FROM watchlist WHERE user_id = ? AND ticker = ? AND market = ?", (user_id, ticker, market))


def list_alerts(user_id: str) -> List[Dict[str, Any]]:
    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, ticker, market, rule_type, threshold, enabled, created_at, updated_at
            FROM alert_rules
            WHERE user_id = ?
            ORDER BY market, ticker, rule_type
            """,
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_channels(user_id: str) -> Dict[str, Any]:
    with db_conn() as conn:
        row = conn.execute(
            "SELECT user_id, email, webhook_url, onesignal_external_id, push_enabled, updated_at FROM user_channels WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        if not row:
            return {"user_id": user_id, "email": "", "webhook_url": "", "onesignal_external_id": "", "push_enabled": 0}
        return dict(row)


def set_channels(user_id: str, email: str, webhook_url: str, onesignal_external_id: str = "", push_enabled: bool = False) -> None:
    ensure_user(user_id)
    now = utc_now_iso()
    with db_conn() as conn:
        conn.execute(
            """
            INSERT INTO user_channels(user_id, email, webhook_url, onesignal_external_id, push_enabled, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id)
            DO UPDATE SET
              email = excluded.email,
              webhook_url = excluded.webhook_url,
              onesignal_external_id = excluded.onesignal_external_id,
              push_enabled = excluded.push_enabled,
              updated_at = excluded.updated_at
            """,
            (user_id, email.strip(), webhook_url.strip(), onesignal_external_id.strip(), 1 if push_enabled else 0, now),
        )


def list_notifications(user_id: str, limit: int = 40) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 200))
    with db_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, ticker, market, kind, message, payload_json, created_at, delivered_email, delivered_webhook, delivered_push
            FROM notifications
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (user_id, limit),
        ).fetchall()
        out = []
        for r in rows:
            row = dict(r)
            try:
                row["payload"] = json.loads(row.pop("payload_json"))
            except Exception:
                row["payload"] = {}
            out.append(row)
        return out


def get_state(user_id: str, ticker: str, market: str, key: str) -> Optional[str]:
    mkey = state_key_for_market(market, key)
    with db_conn() as conn:
        row = conn.execute(
            "SELECT state_value FROM alert_state WHERE user_id = ? AND ticker = ? AND state_key = ?",
            (user_id, ticker, mkey),
        ).fetchone()
        return row["state_value"] if row else None


def set_state(user_id: str, ticker: str, market: str, key: str, value: str) -> None:
    now = utc_now_iso()
    mkey = state_key_for_market(market, key)
    with db_conn() as conn:
        conn.execute(
            """
            INSERT INTO alert_state(user_id, ticker, market, state_key, state_value, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id, ticker, state_key)
            DO UPDATE SET state_value = excluded.state_value, updated_at = excluded.updated_at
            """,
            (user_id, ticker, market, mkey, value, now),
        )


def send_email_notification(to_email: str, subject: str, body: str) -> bool:
    host = os.getenv("SMTP_HOST", "").strip()
    if not host or not to_email:
        return False
    port = int(os.getenv("SMTP_PORT", "587"))
    user = os.getenv("SMTP_USER", "").strip()
    password = os.getenv("SMTP_PASS", "").strip()
    sender = os.getenv("SMTP_FROM", user or "noreply@example.com").strip()
    use_tls = os.getenv("SMTP_TLS", "1").strip() != "0"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(host, port, timeout=15) as server:
            if use_tls:
                server.starttls()
            if user:
                server.login(user, password)
            server.send_message(msg)
        return True
    except Exception:
        return False


def send_webhook_notification(url: str, payload: Dict[str, Any]) -> bool:
    if not url:
        return False
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "stock-intel-app/1.0"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=12, context=ssl.create_default_context()) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def send_onesignal_notification(external_user_id: str, heading: str, content: str) -> bool:
    app_id = os.getenv("ONESIGNAL_APP_ID", "").strip()
    api_key = os.getenv("ONESIGNAL_API_KEY", "").strip()
    if not app_id or not api_key or not external_user_id:
        return False

    payload = {
        "app_id": app_id,
        "target_channel": "push",
        "include_aliases": {"external_id": [external_user_id]},
        "contents": {"en": content},
        "headings": {"en": heading},
    }
    req = urllib.request.Request(
        "https://api.onesignal.com/notifications",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Key {api_key}",
            "User-Agent": "stock-intel-app/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=12, context=ssl.create_default_context()) as resp:
            return 200 <= resp.status < 300
    except Exception:
        return False


def create_notification(user_id: str, ticker: str, market: str, kind: str, message: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    now = utc_now_iso()
    channels = get_channels(user_id)
    email_sent = send_email_notification(channels.get("email", ""), f"[Stock Alert] {ticker} {kind}", message)
    webhook_sent = send_webhook_notification(
        channels.get("webhook_url", ""),
        {
            "user_id": user_id,
            "ticker": ticker,
            "kind": kind,
            "message": message,
            "payload": payload,
            "time": now,
        },
    )
    push_sent = False
    if int(channels.get("push_enabled", 0) or 0) == 1:
        ext_id = channels.get("onesignal_external_id", "") or user_id
        push_sent = send_onesignal_notification(str(ext_id), f"{ticker} {kind}", message)

    with db_conn() as conn:
        conn.execute(
            """
            INSERT INTO notifications(user_id, ticker, market, kind, message, payload_json, created_at, delivered_email, delivered_webhook, delivered_push)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                ticker,
                market,
                kind,
                message,
                json.dumps(payload, ensure_ascii=False),
                now,
                1 if email_sent else 0,
                1 if webhook_sent else 0,
                1 if push_sent else 0,
            ),
        )

    return {"ok": True, "email_sent": email_sent, "webhook_sent": webhook_sent, "push_sent": push_sent}


def fetch_quote_finnhub(ticker: str, market: str) -> Dict[str, Any]:
    if market != "US":
        return provider_error("finnhub", "Finnhub quote is currently configured for US market only")
    key = os.getenv("FINNHUB_API_KEY", "").strip()
    if not key:
        return provider_error("finnhub", "FINNHUB_API_KEY is not set")
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={urllib.parse.quote(ticker)}&token={urllib.parse.quote(key)}"
        data = http_get_json(url, timeout=12)
    except Exception as exc:
        return provider_error("finnhub", str(exc))
    if not isinstance(data, dict) or data.get("c") in (None, 0):
        return provider_error("finnhub", "No usable quote payload")
    return {
        "ok": True,
        "source": "finnhub",
        "as_of": utc_now_iso(),
        "ticker": ticker,
        "current_price": data.get("c"),
        "change": data.get("d"),
        "percent_change": data.get("dp"),
        "high": data.get("h"),
        "low": data.get("l"),
        "open": data.get("o"),
        "previous_close": data.get("pc"),
        "timestamp": data.get("t"),
    }


def fetch_quote_yahoo(ticker: str, market: str) -> Dict[str, Any]:
    try:
        symbol = symbol_for_yahoo(ticker, market)
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={urllib.parse.quote(symbol)}"
        data = http_get_json(url, timeout=12)
        result = (data.get("quoteResponse", {}).get("result", []) or [None])[0]
    except Exception as exc:
        return provider_error("yahoo", str(exc))
    if not result:
        return provider_error("yahoo", "No result")
    return {
        "ok": True,
        "source": "yahoo",
        "as_of": utc_now_iso(),
        "ticker": ticker,
        "market": market,
        "symbol": symbol_for_yahoo(ticker, market),
        "name": result.get("shortName") or result.get("longName"),
        "current_price": result.get("regularMarketPrice"),
        "change": result.get("regularMarketChange"),
        "percent_change": result.get("regularMarketChangePercent"),
        "high": result.get("regularMarketDayHigh"),
        "low": result.get("regularMarketDayLow"),
        "open": result.get("regularMarketOpen"),
        "previous_close": result.get("regularMarketPreviousClose"),
        "timestamp": result.get("regularMarketTime"),
    }


def get_quote(ticker: str, market: str = "US") -> Dict[str, Any]:
    def producer() -> Dict[str, Any]:
        tried: List[Dict[str, str]] = []
        providers = (fetch_quote_naver, fetch_quote_yahoo) if market == "KR" else (fetch_quote_finnhub, fetch_quote_yahoo)
        for provider in providers:
            out = provider(ticker, market)
            if out.get("ok"):
                out["providers_tried"] = tried + [{"source": out.get("source", "unknown"), "status": "ok"}]
                out["market"] = market
                if not str(out.get("name") or "").strip():
                    out["name"] = resolve_company_name(ticker, market)
                cur = to_float_or_none(out.get("current_price"))
                prev = to_float_or_none(out.get("previous_close"))
                if cur is not None and prev not in (None, 0):
                    out["change"] = round(cur - prev, 4)
                    out["percent_change"] = round(((cur - prev) / prev) * 100.0, 4)
                return out
            tried.append({"source": out.get("source", "unknown"), "status": "fail", "error": out.get("error", "")})
        return {"ok": False, "error": "All quote providers failed", "providers_tried": tried}

    return cache_get_or_set(f"quote:{market}:{ticker}", 20, producer)


def fetch_price_history_yahoo(ticker: str, market: str, period: str = "3mo", interval: str = "1d") -> Dict[str, Any]:
    symbol = symbol_for_yahoo(ticker, market)
    range_val = period if period in {"1mo", "3mo"} else "3mo"
    interval_val = interval if interval in {"1d", "1wk"} else "1d"
    try:
        url = (
            "https://query1.finance.yahoo.com/v8/finance/chart/"
            f"{urllib.parse.quote(symbol)}?range={urllib.parse.quote(range_val)}&interval={urllib.parse.quote(interval_val)}"
        )
        data = http_get_json(url, timeout=15)
        result = (data.get("chart", {}).get("result", []) or [None])[0]
    except Exception as exc:
        return provider_error("yahoo_history", str(exc))
    if not result:
        return provider_error("yahoo_history", "No history result")

    ts = result.get("timestamp") or []
    quote = (((result.get("indicators") or {}).get("quote") or [{}])[0]) or {}
    closes = quote.get("close") or []
    highs = quote.get("high") or []
    lows = quote.get("low") or []
    opens = quote.get("open") or []
    volumes = quote.get("volume") or []

    points: List[Dict[str, Any]] = []
    for i, t in enumerate(ts):
        c = closes[i] if i < len(closes) else None
        if c is None:
            continue
        try:
            dt = datetime.fromtimestamp(int(t), tz=timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            dt = ""
        points.append(
            {
                "date": dt,
                "close": c,
                "open": opens[i] if i < len(opens) else None,
                "high": highs[i] if i < len(highs) else None,
                "low": lows[i] if i < len(lows) else None,
                "volume": volumes[i] if i < len(volumes) else None,
            }
        )
    if not points:
        return provider_error("yahoo_history", "No usable history points")
    return {
        "ok": True,
        "source": "yahoo_history",
        "ticker": ticker,
        "market": market,
        "symbol": symbol,
        "period": range_val,
        "interval": interval_val,
        "count": len(points),
        "points": points,
        "as_of": utc_now_iso(),
    }


def get_price_history(ticker: str, market: str = "US", period: str = "3mo") -> Dict[str, Any]:
    p = period if period in {"1mo", "3mo"} else "3mo"

    def producer() -> Dict[str, Any]:
        out = fetch_price_history_yahoo(ticker, market, period=p, interval="1d")
        if out.get("ok"):
            return out
        return {"ok": False, "error": "Price history provider failed", "providers_tried": [out]}

    return cache_get_or_set(f"history:{market}:{ticker}:{p}", 600, producer)


def nested_value(obj: Dict[str, Any], *keys: str) -> Any:
    cur: Any = obj
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)
    if isinstance(cur, dict):
        return cur.get("raw") if "raw" in cur else cur.get("fmt")
    return cur


def fetch_fundamentals_alpha(ticker: str, market: str) -> Dict[str, Any]:
    if market != "US":
        return provider_error("alpha_vantage", "Alpha Vantage fundamentals are currently configured for US market only")
    key = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
    if not key:
        return provider_error("alpha_vantage", "ALPHA_VANTAGE_API_KEY is not set")
    try:
        url = (
            "https://www.alphavantage.co/query?function=OVERVIEW"
            f"&symbol={urllib.parse.quote(ticker)}&apikey={urllib.parse.quote(key)}"
        )
        data = http_get_json(url, timeout=15)
    except Exception as exc:
        return provider_error("alpha_vantage", str(exc))
    if not isinstance(data, dict) or "Symbol" not in data:
        return provider_error("alpha_vantage", str(data.get("Note") if isinstance(data, dict) else "No data"))
    return {
        "ok": True,
        "source": "alpha_vantage",
        "as_of": utc_now_iso(),
        "ticker": data.get("Symbol"),
        "name": data.get("Name"),
        "sector": data.get("Sector"),
        "industry": data.get("Industry"),
        "market_cap": data.get("MarketCapitalization"),
        "pe_ratio": data.get("PERatio"),
        "pb_ratio": data.get("PriceToBookRatio"),
        "operating_margin_ttm": data.get("OperatingMarginTTM"),
        "roe": data.get("ReturnOnEquityTTM"),
    }


def fetch_fundamentals_yahoo(ticker: str, market: str) -> Dict[str, Any]:
    modules = "summaryProfile,defaultKeyStatistics,financialData,price"
    try:
        url = (
            "https://query2.finance.yahoo.com/v10/finance/quoteSummary/"
            f"{urllib.parse.quote(symbol_for_yahoo(ticker, market))}?modules={urllib.parse.quote(modules)}"
        )
        data = http_get_json(url, timeout=15)
        result = (data.get("quoteSummary", {}).get("result", []) or [None])[0]
    except Exception as exc:
        return provider_error("yahoo", str(exc))
    if not result:
        return provider_error("yahoo", "No fundamentals result")
    return {
        "ok": True,
        "source": "yahoo",
        "as_of": utc_now_iso(),
        "ticker": ticker,
        "market": market,
        "symbol": symbol_for_yahoo(ticker, market),
        "name": nested_value(result, "price", "longName") or nested_value(result, "price", "shortName"),
        "sector": nested_value(result, "summaryProfile", "sector"),
        "industry": nested_value(result, "summaryProfile", "industry"),
        "market_cap": nested_value(result, "price", "marketCap"),
        "pe_ratio": nested_value(result, "defaultKeyStatistics", "trailingPE"),
        "pb_ratio": nested_value(result, "defaultKeyStatistics", "priceToBook"),
        "operating_margin_ttm": nested_value(result, "financialData", "operatingMargins"),
        "roe": nested_value(result, "financialData", "returnOnEquity"),
    }


def get_fundamentals(ticker: str, market: str = "US") -> Dict[str, Any]:
    def producer() -> Dict[str, Any]:
        tried: List[Dict[str, str]] = []
        providers = (fetch_fundamentals_naver, fetch_fundamentals_yahoo) if market == "KR" else (fetch_fundamentals_alpha, fetch_fundamentals_yahoo)
        for provider in providers:
            out = provider(ticker, market)
            if out.get("ok"):
                out["providers_tried"] = tried + [{"source": out.get("source", "unknown"), "status": "ok"}]
                out["market"] = market
                if not str(out.get("name") or "").strip():
                    out["name"] = resolve_company_name(ticker, market)
                if market == "KR":
                    # KR: always try Yahoo as secondary source because Naver often omits sector/industry/ROE.
                    y = fetch_fundamentals_yahoo(ticker, market)
                    if y.get("ok"):
                        for k in ["market_cap", "pe_ratio", "pb_ratio", "roe", "operating_margin_ttm"]:
                            if str(y.get(k) or "").strip():
                                out[k] = y.get(k)
                        if not str(out.get("sector") or "").strip() and str(y.get("sector") or "").strip():
                            out["sector"] = y.get("sector")
                        if not str(out.get("industry") or "").strip() and str(y.get("industry") or "").strip():
                            out["industry"] = y.get("industry")
                        out["source"] = f"{out.get('source', 'naver_finance')}+yahoo_backfill"
                    profile = get_kr_profile(ticker)
                    if str(profile.get("sector") or "").strip():
                        out["sector"] = profile.get("sector")
                    if str(profile.get("industry") or "").strip():
                        out["industry"] = profile.get("industry")
                    if not str(out.get("sector") or "").strip():
                        out["sector"] = find_sector_from_seed(ticker, market)
                    out["sector"] = normalize_kr_sector_text(str(out.get("sector") or ""))
                    if not str(out.get("industry") or "").strip():
                        out["industry"] = infer_industry_from_sector(str(out.get("sector") or ""), market)
                    out["industry"] = normalize_kr_industry_text(str(out.get("industry") or ""), str(out.get("sector") or ""))
                out["sector"] = canonical_sector(
                    str(out.get("sector") or ""),
                    str(out.get("name") or ""),
                    str(out.get("industry") or ""),
                )
                if market == "KR" and not str(out.get("industry") or "").strip():
                    out["industry"] = infer_industry_from_sector(str(out.get("sector") or ""), market)
                return out
            tried.append({"source": out.get("source", "unknown"), "status": "fail", "error": out.get("error", "")})
        return {"ok": False, "error": "All fundamentals providers failed", "providers_tried": tried}

    return cache_get_or_set(f"fundamentals:{market}:{ticker}", 3600, producer)


def fetch_news_google_rss(ticker: str, market: str) -> Dict[str, Any]:
    company = resolve_company_name(ticker, market)
    queries: List[str] = []
    if market == "US":
        queries = [f"{ticker} stock", f"{company} stock"] if company else [f"{ticker} stock"]
    else:
        # KR 소형주는 숫자 티커 검색 적중률이 낮아 회사명/한글 키워드를 우선 사용.
        if company and not re.fullmatch(r"[0-9]{4,6}", company.strip()):
            queries.extend([f"{company} 주가", f"{company} 급등 이유", f"{company} 수혜주"])
        queries.extend([f"{ticker} 주식 코스피 코스닥", f"{ticker} 주식", f"{ticker} stock"])
    deduped: List[str] = []
    seen_q: set = set()
    for q in queries:
        k = q.strip().lower()
        if not k or k in seen_q:
            continue
        seen_q.add(k)
        deduped.append(q)

    items = []
    seen = set()
    for query_text in deduped:
        query = urllib.parse.quote(query_text)
        is_ko = bool(re.search(r"[가-힣]", query_text))
        hl = "ko" if is_ko else "en-US"
        gl = "KR" if market == "KR" or is_ko else "US"
        ceid = "KR:ko" if market == "KR" or is_ko else "US:en"
        url = f"https://news.google.com/rss/search?q={query}&hl={hl}&gl={gl}&ceid={ceid}"
        try:
            xml_text = http_get_text(url, timeout=15)
            root = ET.fromstring(xml_text)
        except Exception:
            continue
        for item in root.findall("./channel/item"):
            link = item.findtext("link", default="")
            if not link or link in seen:
                continue
            seen.add(link)
            items.append(
                {
                    "headline": item.findtext("title", default=""),
                    "source": (item.find("source").text if item.find("source") is not None else "Google News"),
                    "url": link,
                    "summary": "",
                    "datetime": item.findtext("pubDate", default=""),
                }
            )
            if len(items) >= 15:
                break
        if len(items) >= 15:
            break
    return {"ok": True, "source": "google_news_rss", "ticker": ticker, "market": market, "count": len(items), "items": items}


def fetch_news_finnhub(ticker: str, market: str, days: int) -> Dict[str, Any]:
    if market != "US":
        return provider_error("finnhub", "Finnhub news is currently configured for US market only")
    key = os.getenv("FINNHUB_API_KEY", "").strip()
    if not key:
        return provider_error("finnhub", "FINNHUB_API_KEY is not set")
    now = datetime.now(timezone.utc).date()
    from_date = now - timedelta(days=max(1, min(days, 30)))
    try:
        url = (
            "https://finnhub.io/api/v1/company-news"
            f"?symbol={urllib.parse.quote(ticker)}&from={from_date.isoformat()}&to={now.isoformat()}"
            f"&token={urllib.parse.quote(key)}"
        )
        items = http_get_json(url, timeout=15)
    except Exception as exc:
        return provider_error("finnhub", str(exc))
    out = []
    for item in (items or [])[:15]:
        out.append(
            {
                "headline": item.get("headline"),
                "source": item.get("source"),
                "url": item.get("url"),
                "summary": item.get("summary"),
                "datetime": item.get("datetime"),
            }
        )
    return {"ok": True, "source": "finnhub", "ticker": ticker, "count": len(out), "items": out}


def fetch_news_alpha(ticker: str, market: str) -> Dict[str, Any]:
    if market != "US":
        return provider_error("alpha_vantage", "Alpha Vantage news is currently configured for US market only")
    key = os.getenv("ALPHA_VANTAGE_API_KEY", "").strip()
    if not key:
        return provider_error("alpha_vantage", "ALPHA_VANTAGE_API_KEY is not set")
    try:
        url = (
            "https://www.alphavantage.co/query?function=NEWS_SENTIMENT"
            f"&tickers={urllib.parse.quote(ticker)}&limit=15&apikey={urllib.parse.quote(key)}"
        )
        data = http_get_json(url, timeout=20)
    except Exception as exc:
        return provider_error("alpha_vantage", str(exc))
    feed = data.get("feed", []) if isinstance(data, dict) else []
    out = []
    for item in feed[:15]:
        out.append(
            {
                "headline": item.get("title"),
                "source": item.get("source"),
                "url": item.get("url"),
                "summary": item.get("summary"),
                "datetime": item.get("time_published"),
            }
        )
    return {"ok": True, "source": "alpha_vantage", "ticker": ticker, "count": len(out), "items": out}


def get_news(ticker: str, market: str = "US", days: int = 7) -> Dict[str, Any]:
    def producer() -> Dict[str, Any]:
        tried = []
        if market == "KR":
            providers = (
                lambda: fetch_news_naver_finance(ticker, market),
                lambda: fetch_news_google_rss(ticker, market),
            )
        else:
            providers = (
                lambda: fetch_news_finnhub(ticker, market, days),
                lambda: fetch_news_alpha(ticker, market),
                lambda: fetch_news_google_rss(ticker, market),
            )
        for provider in providers:
            out = provider()
            if out.get("ok") and int(out.get("count", 0) or 0) > 0:
                out["providers_tried"] = tried + [{"source": out.get("source", "unknown"), "status": "ok"}]
                out["market"] = market
                return out
            err = out.get("error", "")
            if out.get("ok"):
                err = "empty items"
            tried.append({"source": out.get("source", "unknown"), "status": "fail", "error": err})
        return {"ok": False, "error": "All news providers failed", "providers_tried": tried}

    return cache_get_or_set(f"news:{market}:{ticker}:{days}", 900, producer)


def get_sec_ticker_mapping() -> Dict[str, str]:
    def producer() -> Dict[str, str]:
        headers = {"User-Agent": os.getenv("SEC_USER_AGENT", DEFAULT_SEC_USER_AGENT)}
        data = http_get_json("https://www.sec.gov/files/company_tickers_exchange.json", headers=headers, timeout=20)
        mapping: Dict[str, str] = {}
        for row in data.get("data", []):
            try:
                mapping[str(row[2]).upper()] = str(row[0])
            except Exception:
                pass
        return mapping

    return cache_get_or_set("sec:ticker_mapping", 86400, producer)


def get_dart_company_index() -> List[Dict[str, str]]:
    api_key = os.getenv("DART_API_KEY", "").strip()
    if not api_key:
        return []

    def producer() -> List[Dict[str, str]]:
        url = f"https://opendart.fss.or.kr/api/corpCode.xml?crtfc_key={urllib.parse.quote(api_key)}"
        raw = urllib.request.urlopen(url, timeout=25, context=ssl.create_default_context()).read()
        with zipfile.ZipFile(io.BytesIO(raw)) as zf:
            xml_name = zf.namelist()[0]
            xml_text = zf.read(xml_name).decode("utf-8", errors="replace")
        root = ET.fromstring(xml_text)
        items: List[Dict[str, str]] = []
        for li in root.findall(".//list"):
            stock_code = (li.findtext("stock_code") or "").strip()
            corp_code = (li.findtext("corp_code") or "").strip()
            corp_name = (li.findtext("corp_name") or "").strip()
            if stock_code and corp_code:
                items.append({"stock_code": stock_code, "corp_code": corp_code, "corp_name": corp_name})
        return items

    return cache_get_or_set("dart:company_index", 86400, producer)


def get_dart_corpcode_mapping() -> Dict[str, str]:
    mapping: Dict[str, str] = {}
    for row in get_dart_company_index():
        stock_code = row.get("stock_code", "")
        corp_code = row.get("corp_code", "")
        if stock_code and corp_code:
            mapping[stock_code] = corp_code
    return mapping


def get_kr_filings_dart(ticker: str, limit: int = 10) -> Dict[str, Any]:
    api_key = os.getenv("DART_API_KEY", "").strip()
    if not api_key:
        return {"ok": False, "source": "dart", "error": "DART_API_KEY is not set"}
    code = normalize_kr_ticker(ticker)
    if not code:
        return {"ok": False, "source": "dart", "error": "Invalid KR ticker format"}
    mapping = get_dart_corpcode_mapping()
    corp_code = mapping.get(code)
    if not corp_code:
        return {"ok": False, "source": "dart", "error": f"Ticker {code} not found in DART corp code mapping"}

    end_de = datetime.now(timezone.utc).strftime("%Y%m%d")
    bgn_de = (datetime.now(timezone.utc) - timedelta(days=365)).strftime("%Y%m%d")
    cnt = max(1, min(limit, 100))
    url = (
        "https://opendart.fss.or.kr/api/list.json"
        f"?crtfc_key={urllib.parse.quote(api_key)}"
        f"&corp_code={urllib.parse.quote(corp_code)}"
        f"&bgn_de={bgn_de}&end_de={end_de}"
        "&last_reprt_at=Y"
        "&page_no=1"
        f"&page_count={cnt}"
    )
    try:
        data = http_get_json(url, timeout=20)
    except Exception as exc:
        return {"ok": False, "source": "dart", "error": str(exc)}

    status = str(data.get("status", ""))
    if status not in ("000",):
        return {"ok": False, "source": "dart", "error": data.get("message", f"DART status {status}")}

    items = []
    for item in data.get("list", [])[:cnt]:
        rcp_no = item.get("rcept_no", "")
        filing_url = f"https://dart.fss.or.kr/dsaf001/main.do?rcpNo={rcp_no}" if rcp_no else ""
        items.append(
            {
                "form": item.get("report_nm"),
                "filing_date": item.get("rcept_dt"),
                "accession_number": rcp_no,
                "document": item.get("report_nm"),
                "url": filing_url,
            }
        )
    return {"ok": True, "source": "dart", "ticker": code, "market": "KR", "count": len(items), "items": items}


def get_sec_filings(ticker: str, market: str = "US", limit: int = 10) -> Dict[str, Any]:
    if market == "KR":
        return cache_get_or_set(f"dart:filings:KR:{normalize_kr_ticker(ticker)}:{limit}", 3600, lambda: get_kr_filings_dart(ticker, limit=limit))
    def producer() -> Dict[str, Any]:
        mapping = get_sec_ticker_mapping()
        cik = mapping.get(ticker)
        if not cik:
            return {"ok": False, "source": "sec", "error": f"Ticker {ticker} not found in SEC mapping"}
        cik10 = cik.zfill(10)
        headers = {"User-Agent": os.getenv("SEC_USER_AGENT", DEFAULT_SEC_USER_AGENT)}
        try:
            data = http_get_json(f"https://data.sec.gov/submissions/CIK{cik10}.json", headers=headers, timeout=20)
        except Exception as exc:
            return provider_error("sec", str(exc))
        recent = data.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        docs = recent.get("primaryDocument", [])
        size = min(max(1, min(limit, 50)), len(forms))
        items = []
        for i in range(size):
            acc = str(accessions[i]).replace("-", "") if i < len(accessions) else ""
            doc = docs[i] if i < len(docs) else ""
            url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc}/{doc}" if acc and doc else ""
            items.append(
                {
                    "form": forms[i],
                    "filing_date": filing_dates[i] if i < len(filing_dates) else "",
                    "accession_number": accessions[i] if i < len(accessions) else "",
                    "document": doc,
                    "url": url,
                }
            )
        return {"ok": True, "source": "sec", "ticker": ticker, "cik": cik10, "count": len(items), "items": items}

    return cache_get_or_set(f"sec:filings:{market}:{ticker}:{limit}", 3600, producer)


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "")


def expand_technology_queries(query: str) -> List[str]:
    raw = (query or "").strip()
    if not raw:
        return []
    lowered = raw.lower()
    translated_terms: List[str] = []

    term_map = {
        "전기차": "electric vehicle",
        "자율주행": "autonomous driving",
        "배터리": "battery",
        "이차전지": "secondary battery",
        "2차전지": "secondary battery",
        "반도체": "semiconductor",
        "칩": "chip",
        "로봇": "robotics",
        "로보틱스": "robotics",
        "모빌리티": "mobility",
        "열관리": "thermal management",
        "특허": "patent",
        "핵심기술": "core technology",
        "시장파급력": "market impact",
    }
    for k, v in term_map.items():
        if k in lowered:
            translated_terms.append(v)

    company_map = {
        "한온시스템": "automotive thermal management heat pump electric compressor hvac",
        "현대차": "electric vehicle autonomous driving software defined vehicle",
        "기아": "electric vehicle autonomous driving battery management",
        "삼성전자": "semiconductor hbm ai chip foundry memory",
        "sk하이닉스": "hbm dram nand semiconductor memory",
        "한화솔루션": "solar pv hydrogen energy materials",
        "한화생명": "insurtech underwriting actuarial analytics",
    }
    for k, v in company_map.items():
        if k in lowered:
            translated_terms.append(v)

    candidates = [raw]
    if translated_terms:
        candidates.append(" ".join(dict.fromkeys(translated_terms)))
    candidates.append(f"{raw} technology")
    candidates.append(f"{raw} patent")
    # Deduplicate while preserving order.
    deduped: List[str] = []
    seen = set()
    for c in candidates:
        c = c.strip()
        if not c or c in seen:
            continue
        seen.add(c)
        deduped.append(c)
    return deduped


def fetch_technology_arxiv(query: str, max_results: int) -> Dict[str, Any]:
    q = urllib.parse.quote(f"all:{query}")
    url = (
        "https://export.arxiv.org/api/query?"
        f"search_query={q}&start=0&max_results={max(1, min(max_results, 20))}&sortBy=submittedDate&sortOrder=descending"
    )
    try:
        root = ET.fromstring(http_get_text(url, timeout=25))
    except Exception as exc:
        return provider_error("arxiv", str(exc))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    items = []
    for e in root.findall("a:entry", ns):
        items.append(
            {
                "title": (e.findtext("a:title", default="", namespaces=ns) or "").strip(),
                "summary": (e.findtext("a:summary", default="", namespaces=ns) or "").strip(),
                "published": e.findtext("a:published", default="", namespaces=ns),
                "url": (e.find("a:link", ns).attrib.get("href", "") if e.find("a:link", ns) is not None else ""),
                "authors": [
                    n.findtext("a:name", default="", namespaces=ns)
                    for n in e.findall("a:author", ns)
                    if n.findtext("a:name", default="", namespaces=ns)
                ],
            }
        )
    return {"ok": True, "source": "arxiv", "query": query, "count": len(items), "items": items}


def fetch_technology_crossref(query: str, max_results: int) -> Dict[str, Any]:
    url = (
        "https://api.crossref.org/works?"
        f"query={urllib.parse.quote(query)}&rows={max(1, min(max_results, 20))}&sort=published&order=desc"
    )
    try:
        data = http_get_json(url, timeout=20)
    except Exception as exc:
        return provider_error("crossref", str(exc))
    raw = (data.get("message", {}) if isinstance(data, dict) else {}).get("items", [])
    items = []
    for item in raw[: max(1, min(max_results, 20))]:
        title = (item.get("title", []) or [""])[0]
        date_parts = (((item.get("issued") or {}).get("date-parts") or [[""]])[0])
        published = "-".join(str(x) for x in date_parts if x != "")
        url = item.get("URL") or (f"https://doi.org/{item.get('DOI')}" if item.get("DOI") else "")
        authors = []
        for a in item.get("author", [])[:6]:
            name = f"{a.get('given', '')} {a.get('family', '')}".strip()
            if name:
                authors.append(name)
        items.append({"title": title, "summary": strip_tags(item.get("abstract", "")), "published": published, "url": url, "authors": authors})
    return {"ok": True, "source": "crossref", "query": query, "count": len(items), "items": items}


def get_technology(query: str, max_results: int = 8) -> Dict[str, Any]:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "query is required"}

    def producer() -> Dict[str, Any]:
        tried = []
        best_empty: Optional[Dict[str, Any]] = None
        for candidate in expand_technology_queries(q):
            for provider in (fetch_technology_arxiv, fetch_technology_crossref):
                out = provider(candidate, max_results)
                if out.get("ok"):
                    count = int(out.get("count") or 0)
                    if count > 0:
                        out["providers_tried"] = tried + [{"source": out.get("source", "unknown"), "status": "ok"}]
                        out["original_query"] = q
                        return out
                    if best_empty is None:
                        best_empty = out
                    tried.append({"source": out.get("source", "unknown"), "status": "empty", "query": candidate})
                else:
                    tried.append(
                        {
                            "source": out.get("source", "unknown"),
                            "status": "fail",
                            "error": out.get("error", ""),
                            "query": candidate,
                        }
                    )
        if best_empty is not None:
            best_empty["providers_tried"] = tried
            best_empty["original_query"] = q
            return best_empty
        return {"ok": False, "error": "All technology providers failed", "providers_tried": tried}

    return cache_get_or_set(f"tech:{q}:{max_results}", 21600, producer)


def short_text(value: Any, limit: int = 280) -> str:
    text = str(value or "").strip()
    return text if len(text) <= limit else f"{text[: limit - 3]}..."


def analyze_news_catalyst(news: Dict[str, Any]) -> Dict[str, Any]:
    items = (news.get("items") or []) if news.get("ok") else []
    if not items:
        return {"strong": [], "weak_count": 0, "sample": ""}

    strong_map = {
        "실적": ["실적", "잠정", "어닝", "영업이익", "매출", "순이익", "guidance", "earnings"],
        "수주/계약": ["수주", "계약", "공급", "납품", "단일판매", "파트너십", "deal"],
        "정책/규제": ["정책", "규제", "법안", "승인", "허가", "인허가", "정부", "fda", "approval"],
        "자본정책": ["자사주", "배당", "소각", "증자", "감자", "buyback", "dividend"],
        "M&A/지배구조": ["인수", "합병", "분할", "매각", "지분", "최대주주", "m&a"],
    }
    weak_patterns = [
        "무슨 회사길래",
        "관련주",
        "테마주",
        "주가",
        "상한가",
        "급등 이유",
        "급락 이유",
    ]

    strong_labels: List[str] = []
    weak_count = 0
    sample = ""
    for raw in items[:8]:
        headline = str(raw.get("headline") or "").strip()
        if not headline:
            continue
        if not sample:
            sample = headline
        h = headline.lower()
        matched = False
        for label, kws in strong_map.items():
            if any(k.lower() in h for k in kws):
                strong_labels.append(label)
                matched = True
        if not matched and any(p.lower() in h for p in weak_patterns):
            weak_count += 1

    out_labels: List[str] = []
    seen = set()
    for x in strong_labels:
        if x in seen:
            continue
        seen.add(x)
        out_labels.append(x)
    return {"strong": out_labels, "weak_count": weak_count, "sample": short_text(sample, 80)}


def analyze_filing_catalyst(filings: Dict[str, Any]) -> Dict[str, Any]:
    items = (filings.get("items") or []) if filings.get("ok") else []
    if not items:
        return {"strong": [], "weak": []}

    strong_tokens = [
        "단일판매",
        "공급계약",
        "영업(잠정)실적",
        "주요사항보고서",
        "유상증자",
        "무상증자",
        "자기주식",
        "합병",
        "분할",
        "증권신고서",
        "8-k",
        "10-q",
        "10-k",
    ]
    weak_tokens = [
        "임원ㆍ주요주주특정증권등소유상황보고서",
        "주주총회소집공고",
        "사업보고서",
        "반기보고서",
        "분기보고서",
        "소유상황보고서",
        "proxy",
    ]

    strong: List[str] = []
    weak: List[str] = []
    for raw in items[:5]:
        form = str(raw.get("form") or "").strip()
        if not form:
            continue
        low = form.lower()
        if any(tok.lower() in low for tok in strong_tokens):
            strong.append(form)
        elif any(tok.lower() in low for tok in weak_tokens):
            weak.append(form)
    return {"strong": strong[:2], "weak": weak[:2]}


def infer_technical_price_driver(ticker: str, market: str, quote: Dict[str, Any]) -> str:
    t = clean_ticker(ticker)
    m = clean_market(market)
    if not t:
        return ""
    history = get_price_history(t, market=m, period="1mo")
    if not history.get("ok"):
        return ""
    points = history.get("points") or []
    if len(points) < 6:
        return ""

    latest = points[-1]
    prev = points[-6:-1]
    prev_closes = [to_float_or_none(x.get("close")) for x in prev]
    prev_closes = [x for x in prev_closes if x is not None and x > 0]
    recent_close = to_float_or_none(latest.get("close"))
    reasons: List[str] = []
    if recent_close and prev_closes:
        avg5 = sum(prev_closes) / len(prev_closes)
        if avg5 > 0:
            ret5 = ((recent_close - avg5) / avg5) * 100.0
            if abs(ret5) >= 3.0:
                reasons.append(f"최근 5거래일 기준 {ret5:+.2f}% 움직임으로 단기 추세 강화")

    prev_vols = [to_float_or_none(x.get("volume")) for x in prev]
    prev_vols = [x for x in prev_vols if x is not None and x > 0]
    recent_vol = to_float_or_none(latest.get("volume"))
    if recent_vol and prev_vols:
        avg_vol = sum(prev_vols) / len(prev_vols)
        if avg_vol > 0:
            ratio = recent_vol / avg_vol
            if ratio >= 1.8:
                reasons.append(f"거래량이 5일 평균 대비 {ratio:.2f}배로 급증")

    cur = to_float_or_none(quote.get("current_price"))
    high = to_float_or_none(quote.get("high"))
    low = to_float_or_none(quote.get("low"))
    if cur and high and low and high > low:
        span = high - low
        if span > 0:
            pos = (cur - low) / span
            if pos >= 0.85:
                reasons.append("장중 고가권에서 가격이 유지되며 매수 우위 신호")
            elif pos <= 0.15:
                reasons.append("장중 저가권 체류로 단기 매도 압력이 우세")

    return " / ".join(reasons[:2])


def infer_price_driver(
    quote: Dict[str, Any],
    news: Dict[str, Any],
    filings: Dict[str, Any],
    ticker: str = "",
    market: str = "US",
) -> str:
    reasons: List[str] = []
    pct = to_float(quote.get("percent_change"), 0.0) if quote.get("ok") else 0.0
    if quote.get("ok"):
        if pct >= 2:
            reasons.append(f"당일 등락률 +{pct:.2f}%로 단기 매수 우위")
        elif pct <= -2:
            reasons.append(f"당일 등락률 {pct:.2f}%로 단기 매도 우위")
        else:
            reasons.append(f"당일 등락률 {pct:.2f}%로 박스권")

    news_signal = analyze_news_catalyst(news)
    filing_signal = analyze_filing_catalyst(filings)
    strong_news = news_signal.get("strong") or []
    strong_filing = filing_signal.get("strong") or []
    weak_news_count = int(news_signal.get("weak_count") or 0)
    weak_filing = filing_signal.get("weak") or []

    if strong_news or strong_filing:
        parts: List[str] = []
        if strong_news:
            parts.append(f"뉴스 촉매({', '.join(strong_news[:2])})")
        if strong_filing:
            parts.append(f"공시 촉매({', '.join(short_text(x, 32) for x in strong_filing[:1])})")
        reasons.append(f"직접 촉매 신호: {' + '.join(parts)}")
    elif (weak_news_count > 0) or weak_filing:
        reasons.append("직접 촉매 근거는 약함(테마/관심기사 또는 정기성 공시 비중 높음)")

    t = ticker or str(quote.get("ticker") or "")
    m = market or str(quote.get("market") or "US")
    technical = infer_technical_price_driver(t, m, quote)
    if technical:
        reasons.append(technical)

    if not (strong_news or strong_filing) and abs(pct) >= 8:
        reasons.append("급등락 대비 확정 촉매 확인이 부족해 수급성 변동 가능성에 유의")

    if not reasons:
        return "가격 변동 원인 데이터가 부족합니다."
    return " / ".join(reasons[:3])


def local_intel_summary(
    ticker: str,
    market: str,
    quote: Dict[str, Any],
    fundamentals: Dict[str, Any],
    news: Dict[str, Any],
    filings: Dict[str, Any],
    technology: Dict[str, Any],
) -> Dict[str, Any]:
    key_points: List[str] = []
    risks: List[str] = []

    if quote.get("ok"):
        pct = to_float(quote.get("percent_change"), 0.0)
        price = quote.get("current_price")
        key_points.append(f"현재가 {price}, 일중 등락률 {pct:.2f}%")
        if abs(pct) >= 7:
            risks.append("단기 변동성 확대 구간으로 추격 매수/매도 주의")
    else:
        risks.append("실시간 시세 확보 실패")

    if fundamentals.get("ok"):
        pe = to_float(fundamentals.get("pe_ratio"), 0.0)
        pb = to_float(fundamentals.get("pb_ratio"), 0.0)
        roe = to_float(fundamentals.get("roe"), 0.0)
        key_points.append(f"밸류에이션: P/E {pe:.2f}, P/B {pb:.2f}, ROE {roe:.2f}")
        if pe > 40 or pb > 7:
            risks.append("밸류에이션 부담 구간")
    else:
        risks.append("재무 요약 확보 실패")

    if news.get("ok"):
        items = news.get("items", []) or []
        if items:
            headlines = [short_text(x.get("headline", ""), 90) for x in items[:3]]
            key_points.append("최근 뉴스: " + " | ".join(headlines))
    else:
        risks.append("뉴스 확보 실패")

    if filings.get("ok"):
        items = filings.get("items", []) or []
        if items:
            top = items[0]
            key_points.append(f"최근 공시: {top.get('form', '-')} ({top.get('filing_date', '-')})")
    else:
        if market == "KR" and "DART_API_KEY" in str(filings.get("error", "")):
            risks.append("KR 공시 요약은 DART_API_KEY 설정 필요")
        else:
            risks.append("공시 데이터 확보 실패")

    if technology.get("ok"):
        items = technology.get("items", []) or []
        if items:
            key_points.append("관련 기술: " + " | ".join(short_text(x.get("title", ""), 80) for x in items[:2]))
    else:
        risks.append("기술 자료 확보 실패")

    stance = "관망"
    if quote.get("ok") and fundamentals.get("ok"):
        pct = abs(to_float(quote.get("percent_change"), 0.0))
        pe = to_float(fundamentals.get("pe_ratio"), 0.0)
        roe = to_float(fundamentals.get("roe"), 0.0)
        if roe >= 12 and pe > 0 and pe <= 25 and pct <= 5:
            stance = "분할매수 후보"
        elif pe > 45 or pct >= 10:
            stance = "과열 주의"

    return {
        "overview": f"{ticker}({market}) 인텔리전스 통합 요약",
        "key_points": key_points[:6],
        "risks": risks[:5],
        "price_driver": infer_price_driver(quote, news, filings, ticker=ticker, market=market),
        "stance": stance,
        "confidence": "medium",
        "llm_used": False,
    }


def try_openai_intel_summary(
    ticker: str,
    market: str,
    query: str,
    quote: Dict[str, Any],
    fundamentals: Dict[str, Any],
    news: Dict[str, Any],
    filings: Dict[str, Any],
    technology: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return None
    model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini"

    compact = {
        "ticker": ticker,
        "market": market,
        "query": query,
        "quote": {
            "ok": quote.get("ok"),
            "source": quote.get("source"),
            "current_price": quote.get("current_price"),
            "percent_change": quote.get("percent_change"),
            "high": quote.get("high"),
            "low": quote.get("low"),
        },
        "fundamentals": {
            "ok": fundamentals.get("ok"),
            "source": fundamentals.get("source"),
            "name": fundamentals.get("name"),
            "sector": fundamentals.get("sector"),
            "industry": fundamentals.get("industry"),
            "market_cap": fundamentals.get("market_cap"),
            "pe_ratio": fundamentals.get("pe_ratio"),
            "pb_ratio": fundamentals.get("pb_ratio"),
            "roe": fundamentals.get("roe"),
            "operating_margin_ttm": fundamentals.get("operating_margin_ttm"),
        },
        "news": {
            "ok": news.get("ok"),
            "count": news.get("count"),
            "items": [
                {"headline": n.get("headline"), "source": n.get("source"), "datetime": n.get("datetime"), "url": n.get("url")}
                for n in (news.get("items", []) or [])[:8]
            ],
        },
        "filings": {
            "ok": filings.get("ok"),
            "count": filings.get("count"),
            "items": [
                {"form": f.get("form"), "filing_date": f.get("filing_date"), "url": f.get("url")}
                for f in (filings.get("items", []) or [])[:8]
            ],
        },
        "technology": {
            "ok": technology.get("ok"),
            "count": technology.get("count"),
            "items": [
                {"title": t.get("title"), "published": t.get("published"), "url": t.get("url")}
                for t in (technology.get("items", []) or [])[:8]
            ],
        },
    }

    sys_prompt = (
        "You are a financial research assistant. "
        "Return strict JSON only with keys: overview, key_points, risks, price_driver, stance, confidence. "
        "key_points/risks must be arrays of concise Korean strings. "
        "Do not provide investment guarantee language."
    )
    user_prompt = (
        "다음 데이터를 바탕으로 한국어 요약을 작성하세요. "
        "과장 없이 사실 위주, 핵심 포인트 4~6개, 주요 리스크 3~5개를 제시하세요.\n"
        + json.dumps(compact, ensure_ascii=False)
    )

    payload = {
        "model": model,
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
            "User-Agent": "stock-intel-app/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=25, context=ssl.create_default_context()) as resp:
            raw = json.loads(resp.read().decode("utf-8", errors="replace"))
        content = (((raw.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
        if not content:
            return None
        parsed = json.loads(content)
        out = {
            "overview": short_text(parsed.get("overview"), 280),
            "key_points": [short_text(x, 140) for x in (parsed.get("key_points") or [])[:6]],
            "risks": [short_text(x, 140) for x in (parsed.get("risks") or [])[:5]],
            "price_driver": short_text(parsed.get("price_driver"), 200),
            "stance": short_text(parsed.get("stance"), 80),
            "confidence": short_text(parsed.get("confidence"), 40) or "medium",
            "llm_used": True,
            "model": model,
        }
        if not out["price_driver"]:
            out["price_driver"] = infer_price_driver(quote, news, filings, ticker=ticker, market=market)
        if not out["overview"]:
            return None
        return out
    except Exception:
        return None


def get_intelligence_summary(ticker: str, market: str = "US", query: str = "") -> Dict[str, Any]:
    q = (query or ticker).strip() or ticker

    def producer() -> Dict[str, Any]:
        quote = get_quote(ticker, market=market)
        fundamentals = get_fundamentals(ticker, market=market)
        news = get_news(ticker, market=market, days=7)
        filings = get_sec_filings(ticker, market=market, limit=8)
        technology = get_technology(q, max_results=8)

        llm = try_openai_intel_summary(ticker, market, q, quote, fundamentals, news, filings, technology)
        summary = llm if llm else local_intel_summary(ticker, market, quote, fundamentals, news, filings, technology)

        return {
            "ok": True,
            "ticker": ticker,
            "market": market,
            "query": q,
            "summary": summary,
            "sources": {
                "quote": {"ok": quote.get("ok"), "source": quote.get("source")},
                "fundamentals": {"ok": fundamentals.get("ok"), "source": fundamentals.get("source")},
                "news": {"ok": news.get("ok"), "source": news.get("source"), "count": news.get("count", 0)},
                "filings": {"ok": filings.get("ok"), "source": filings.get("source"), "count": filings.get("count", 0)},
                "technology": {"ok": technology.get("ok"), "source": technology.get("source"), "count": technology.get("count", 0)},
            },
            "time": utc_now_iso(),
        }

    return cache_get_or_set(f"intel-summary:{market}:{ticker}:{q}", 300, producer)


def compute_hype_score(quote: Dict[str, Any], fundamentals: Dict[str, Any], news: Dict[str, Any]) -> float:
    score = 20.0
    pct = abs(float(quote.get("percent_change") or 0)) if quote.get("ok") else 0.0
    pe = float(fundamentals.get("pe_ratio") or 0) if fundamentals.get("ok") else 0.0
    news_count = int(news.get("count") or 0) if news.get("ok") else 0
    if pct >= 8:
        score += 20
    elif pct >= 4:
        score += 10
    if pe >= 60:
        score += 20
    elif pe >= 35:
        score += 10
    if news_count >= 10:
        score += 10
    return max(0.0, min(100.0, score))


def to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    text = str(value).replace(",", "").replace("%", "").strip()
    if text == "":
        return default
    try:
        return float(text)
    except Exception:
        return default


def compute_quality_score(quote: Dict[str, Any], fundamentals: Dict[str, Any]) -> float:
    score = 50.0
    roe = to_float(fundamentals.get("roe"), default=-1)
    opm = to_float(fundamentals.get("operating_margin_ttm"), default=-1)
    pe = to_float(fundamentals.get("pe_ratio"), default=-1)
    pb = to_float(fundamentals.get("pb_ratio"), default=-1)
    pct = abs(to_float(quote.get("percent_change"), default=0))
    mcap = to_float(fundamentals.get("market_cap"), default=0)

    if roe >= 20:
        score += 20
    elif roe >= 12:
        score += 12
    elif roe > 0:
        score += 5
    else:
        score -= 10

    # If margin appears as a ratio (0.15) or percent (15), normalize by threshold.
    if opm >= 15 or opm >= 0.15:
        score += 12
    elif opm >= 8 or opm >= 0.08:
        score += 6
    elif opm >= 0:
        score += 2
    else:
        score -= 8

    if 0 < pe <= 20:
        score += 8
    elif pe > 50:
        score -= 10

    if 0 < pb <= 2.5:
        score += 7
    elif pb > 7:
        score -= 8

    if pct <= 3:
        score += 4
    elif pct >= 12:
        score -= 4

    if mcap >= 50_000_000_000:
        score += 6
    elif mcap >= 10_000_000_000:
        score += 4
    elif mcap >= 2_000_000_000:
        score += 2

    return max(0.0, min(100.0, score))


def compute_tech_moat_score(technology: Dict[str, Any], news: Dict[str, Any], filings: Dict[str, Any]) -> float:
    score = 30.0
    tech_count = int(technology.get("count") or 0) if technology.get("ok") else 0
    news_count = int(news.get("count") or 0) if news.get("ok") else 0
    filing_count = int(filings.get("count") or 0) if filings.get("ok") else 0

    score += min(28.0, tech_count * 3.5)
    score += min(16.0, news_count * 1.3)
    score += min(12.0, filing_count * 2.0)

    forms = [str(i.get("form", "")).lower() for i in filings.get("items", [])]
    if any(("10-k" in f or "10-q" in f or "사업보고서" in f or "분기보고서" in f) for f in forms):
        score += 8

    return max(0.0, min(100.0, score))


def compute_capital_power_score(fundamentals: Dict[str, Any], market: str) -> float:
    score = 45.0
    mcap = to_float(fundamentals.get("market_cap"), default=0.0)
    debt_to_equity = to_float(fundamentals.get("debt_to_equity"), default=-1.0)
    cash_ratio = to_float(fundamentals.get("cash_ratio"), default=-1.0)

    if mcap >= 200_000_000_000:
        score += 28
    elif mcap >= 50_000_000_000:
        score += 22
    elif mcap >= 10_000_000_000:
        score += 16
    elif mcap >= 2_000_000_000:
        score += 10
    elif mcap > 0:
        score += 5
    else:
        score -= 6

    if debt_to_equity >= 0:
        if debt_to_equity <= 80:
            score += 14
        elif debt_to_equity <= 150:
            score += 8
        elif debt_to_equity <= 250:
            score += 2
        else:
            score -= 10

    if cash_ratio >= 1.0:
        score += 8
    elif cash_ratio >= 0.5:
        score += 4
    elif cash_ratio >= 0:
        score += 1

    if market == "KR" and mcap >= 5_000_000_000:
        score += 2

    return max(0.0, min(100.0, score))


def compute_technology_strength_score(
    technology: Dict[str, Any], news: Dict[str, Any], filings: Dict[str, Any], sector: str
) -> float:
    score = 30.0
    tech_count = int(technology.get("count") or 0) if technology.get("ok") else 0
    news_count = int(news.get("count") or 0) if news.get("ok") else 0
    filing_count = int(filings.get("count") or 0) if filings.get("ok") else 0

    score += min(26.0, tech_count * 4.0)
    score += min(12.0, filing_count * 2.0)
    score += min(10.0, news_count * 0.8)

    if sector in {"반도체", "AI", "휴머노이드", "원자력", "자동차", "2차전지"}:
        score += 6
    if tech_count == 0 and filing_count == 0:
        score -= 8

    return max(0.0, min(100.0, score))


def compute_market_impact_score(quote: Dict[str, Any], fundamentals: Dict[str, Any], news: Dict[str, Any]) -> float:
    score = 25.0
    mcap = to_float(fundamentals.get("market_cap"), default=0)
    pct = abs(to_float(quote.get("percent_change"), default=0))
    news_count = int(news.get("count") or 0) if news.get("ok") else 0

    if mcap >= 200_000_000_000:
        score += 35
    elif mcap >= 50_000_000_000:
        score += 26
    elif mcap >= 10_000_000_000:
        score += 18
    elif mcap >= 2_000_000_000:
        score += 10
    else:
        score += 4

    score += min(16.0, news_count * 1.5)

    if 1 <= pct <= 6:
        score += 8
    elif pct > 12:
        score += 3

    return max(0.0, min(100.0, score))


def compute_valuation_score(fundamentals: Dict[str, Any], quality_score: float, hype_score: float) -> float:
    score = 50.0
    pe = to_float(fundamentals.get("pe_ratio"), default=-1)
    pb = to_float(fundamentals.get("pb_ratio"), default=-1)

    if 0 < pe <= 15:
        score += 22
    elif pe <= 25 and pe > 0:
        score += 12
    elif pe > 45:
        score -= 16

    if 0 < pb <= 2:
        score += 15
    elif pb <= 4 and pb > 0:
        score += 8
    elif pb > 8:
        score -= 12

    if quality_score >= 70:
        score += 8
    if hype_score >= 70:
        score -= 12
    elif hype_score >= 50:
        score -= 6

    return max(0.0, min(100.0, score))


def combine_rank(quality: float, moat: float, impact: float, valuation: float, hype: float) -> float:
    rank = (0.27 * quality) + (0.25 * moat) + (0.24 * impact) + (0.24 * valuation) - (0.10 * hype)
    return max(0.0, min(100.0, rank))


def rank_label(rank: float) -> str:
    if rank >= 78:
        return "Strong Undervalued Quality"
    if rank >= 64:
        return "Buy Candidate"
    if rank >= 50:
        return "Fair / Watch"
    return "Weak / Overvalued"


def signal_label(score: float) -> str:
    if score >= 62:
        return "상승 우세"
    if score <= 42:
        return "하락 우세"
    return "중립"


def clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def compute_sector_heat_signal(
    quote: Dict[str, Any],
    news: Dict[str, Any],
    hype: float,
    quality: float,
    capital_power: float,
    valuation: float,
) -> Dict[str, Any]:
    pct = abs(to_float(quote.get("percent_change"), 0.0))
    news_count = int(news.get("count") or 0) if news.get("ok") else 0

    heat = 20.0
    if pct >= 8:
        heat += 22
    elif pct >= 4:
        heat += 12
    heat += min(14.0, news_count * 1.5)
    if hype >= 70:
        heat += 18
    elif hype >= 55:
        heat += 10
    heat = clamp(heat, 0.0, 100.0)

    resilience = (0.36 * quality) + (0.34 * capital_power) + (0.30 * valuation) - (max(0.0, hype - 60.0) * 0.45)
    resilience = clamp(resilience, 0.0, 100.0)

    label = "중립"
    note = "섹터 수급과 기업 체력이 혼재되어 추가 확인이 필요합니다."
    if heat >= 65 and resilience < 52:
        label = "테마동반급등(체력취약)"
        note = "섹터 과열로 동반 상승할 수 있으나 펀더멘털 지지가 약해 변동성 리스크가 큽니다."
    elif heat >= 58 and resilience >= 62:
        label = "섹터상승+체력동반(추세지속후보)"
        note = "섹터 탄력과 기업 체력이 동시에 확인되어 상대적으로 추세 지속 가능성이 높습니다."
    elif resilience >= 66:
        label = "저평가 체력 우위"
        note = "단기 과열은 낮고 체력 점수가 높아 눌림 매수형 후보로 분류됩니다."

    return {
        "heat_score": round(heat, 2),
        "resilience_score": round(resilience, 2),
        "label": label,
        "note": note,
    }


def mean_std(values: List[float]) -> Tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return (mean, var ** 0.5)


def classify_backtest_sector_signal(
    heat_score: float,
    resilience_score: float,
    ret1_pct: float,
    ret5_pct: float,
) -> str:
    if heat_score >= 65 and resilience_score < 52:
        return "테마동반급등(체력취약)"
    if heat_score >= 58 and resilience_score >= 62:
        return "섹터상승+체력동반(추세지속후보)"
    if resilience_score >= 66 and ret1_pct <= 3.5 and ret5_pct <= 8.0:
        return "저평가 체력 우위"
    return "중립"


def compute_backtest_signal_row(points: List[Dict[str, Any]], idx: int, hold_days: int) -> Optional[Dict[str, Any]]:
    if idx < 20 or idx + hold_days >= len(points):
        return None
    close = to_float_or_none(points[idx].get("close"))
    prev_close = to_float_or_none(points[idx - 1].get("close"))
    close_5 = to_float_or_none(points[idx - 5].get("close"))
    future_close = to_float_or_none(points[idx + hold_days].get("close"))
    if close in (None, 0) or prev_close in (None, 0) or close_5 in (None, 0) or future_close in (None, 0):
        return None

    window = points[idx - 20 : idx]
    closes = [to_float_or_none(x.get("close")) for x in window]
    closes = [x for x in closes if x not in (None, 0)]
    if len(closes) < 10:
        return None
    ma20 = sum(closes) / len(closes)
    hi20 = max(closes)

    returns_20: List[float] = []
    for j in range(idx - 20, idx):
        c0 = to_float_or_none(points[j - 1].get("close")) if j > 0 else None
        c1 = to_float_or_none(points[j].get("close"))
        if c0 in (None, 0) or c1 in (None, 0):
            continue
        returns_20.append(((c1 - c0) / c0) * 100.0)
    _, std20 = mean_std(returns_20)

    vols = [to_float_or_none(x.get("volume")) for x in window]
    vols = [x for x in vols if x is not None and x > 0]
    cur_vol = to_float_or_none(points[idx].get("volume"))
    vol_ratio = 1.0
    if vols and cur_vol is not None and cur_vol > 0:
        avg_vol = sum(vols) / len(vols)
        if avg_vol > 0:
            vol_ratio = cur_vol / avg_vol

    ret1 = ((close - prev_close) / prev_close) * 100.0
    ret5 = ((close - close_5) / close_5) * 100.0
    trend = ((close - ma20) / ma20) * 100.0 if ma20 > 0 else 0.0
    dd20 = ((close - hi20) / hi20) * 100.0 if hi20 > 0 else 0.0

    heat = 20.0
    heat += min(28.0, abs(ret1) * 2.4)
    heat += min(18.0, max(0.0, vol_ratio - 1.0) * 18.0)
    heat += min(14.0, max(0.0, ret5) * 1.1)
    heat = clamp(heat, 0.0, 100.0)

    resilience = 55.0
    resilience += min(16.0, max(0.0, trend) * 1.8)
    resilience -= min(18.0, std20 * 2.2)
    if dd20 <= -15:
        resilience -= 12
    elif dd20 <= -8:
        resilience -= 7
    elif dd20 <= -4:
        resilience -= 3
    else:
        resilience += 4
    resilience = clamp(resilience, 0.0, 100.0)

    label = classify_backtest_sector_signal(heat, resilience, ret1, ret5)
    fwd_ret = ((future_close - close) / close) * 100.0

    return {
        "date": str(points[idx].get("date") or ""),
        "close": round(close, 4),
        "ret1_pct": round(ret1, 4),
        "ret5_pct": round(ret5, 4),
        "volatility20": round(std20, 4),
        "trend_vs_ma20_pct": round(trend, 4),
        "drawdown20_pct": round(dd20, 4),
        "heat_score": round(heat, 2),
        "resilience_score": round(resilience, 2),
        "label": label,
        "forward_return_pct": round(fwd_ret, 4),
        "hold_days": hold_days,
    }


def run_backtest_sector_signal(
    ticker: str,
    market: str = "US",
    period: str = "3mo",
    hold_days: int = 5,
) -> Dict[str, Any]:
    hold = max(1, min(hold_days, 20))
    history = get_price_history(ticker, market=market, period=period)
    if not history.get("ok"):
        return {"ok": False, "error": "price history unavailable", "history": history}

    points = history.get("points") or []
    if len(points) < 30:
        return {
            "ok": False,
            "error": "not enough price history",
            "required_points": 30,
            "actual_points": len(points),
        }

    rows: List[Dict[str, Any]] = []
    for i in range(len(points)):
        rec = compute_backtest_signal_row(points, i, hold)
        if rec:
            rows.append(rec)
    if not rows:
        return {"ok": False, "error": "no usable backtest rows"}

    baseline = sum(float(x["forward_return_pct"]) for x in rows) / len(rows)
    labels = [
        "섹터상승+체력동반(추세지속후보)",
        "테마동반급등(체력취약)",
        "저평가 체력 우위",
        "중립",
    ]
    by_label: Dict[str, Dict[str, Any]] = {}
    for label in labels:
        sub = [x for x in rows if x["label"] == label]
        if not sub:
            by_label[label] = {"count": 0, "avg_forward_return_pct": None, "hit_rate_pct": None, "alpha_vs_baseline_pct": None}
            continue
        avg_ret = sum(float(x["forward_return_pct"]) for x in sub) / len(sub)
        hits = len([x for x in sub if float(x["forward_return_pct"]) > 0])
        by_label[label] = {
            "count": len(sub),
            "avg_forward_return_pct": round(avg_ret, 4),
            "hit_rate_pct": round((hits / len(sub)) * 100.0, 2),
            "alpha_vs_baseline_pct": round(avg_ret - baseline, 4),
        }

    latest = rows[-1]
    return {
        "ok": True,
        "ticker": ticker,
        "market": market,
        "period": period if period in {"1mo", "3mo"} else "3mo",
        "hold_days": hold,
        "count": len(rows),
        "baseline_forward_return_pct": round(baseline, 4),
        "latest_signal": latest,
        "stats_by_label": by_label,
        "recent_samples": rows[-12:],
        "source": history.get("source", "yahoo_history"),
        "time": utc_now_iso(),
        "note": "가격/거래량 기반 프록시 백테스트 (펀더멘털 시점정합 전 단계 MVP)",
    }


def get_peer_candidates(ticker: str, market: str, sector: str, limit: int = 5) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    target_t = normalize_kr_ticker(ticker) if market == "KR" else ticker.upper()
    for item in load_sector_seed():
        im = str(item.get("market", "")).upper()
        if im != market:
            continue
        sec = canonical_sector(str(item.get("sector", "")), str(item.get("name", "")), "")
        if sec != sector:
            continue
        t = normalize_kr_ticker(str(item.get("ticker", ""))) if market == "KR" else str(item.get("ticker", "")).upper()
        if t == target_t:
            continue
        out.append({"ticker": t, "name": str(item.get("name", "")), "sector": sec, "market": market})
        if len(out) >= max(1, min(limit, 12)):
            break
    return out


def mean_valid(values: List[Any]) -> Optional[float]:
    nums = [to_float_or_none(v) for v in values]
    nums = [x for x in nums if x is not None]
    if not nums:
        return None
    return sum(nums) / len(nums)


def compute_risk_breakdown(quote: Dict[str, Any], fundamentals: Dict[str, Any], market: str, sector: str) -> Dict[str, float]:
    vol = clamp(abs(to_float(quote.get("percent_change"), 0.0)) / 1.8, 0.0, 10.0)
    fx = 3.0 if market == "US" else 5.0
    if market == "KR" and sector in {"자동차", "반도체", "원자력", "AI"}:
        fx += 1.5
    pe = to_float(fundamentals.get("pe_ratio"), 0.0)
    competition = 5.5
    if sector in {"AI", "반도체", "휴머노이드", "자동차"}:
        competition += 1.5
    if pe >= 35:
        competition += 1.0
    out = {
        "volatility": round(clamp(vol, 0.0, 10.0), 2),
        "fx_sensitivity": round(clamp(fx, 0.0, 10.0), 2),
        "competition": round(clamp(competition, 0.0, 10.0), 2),
    }
    out["total"] = round((out["volatility"] * 0.4) + (out["fx_sensitivity"] * 0.25) + (out["competition"] * 0.35), 2)
    return out


def compute_personalized_signals(
    quote: Dict[str, Any],
    fundamentals: Dict[str, Any],
    news: Dict[str, Any],
    risk: Dict[str, float],
    horizon_pref: str,
    risk_pref: str,
) -> Dict[str, Any]:
    pct = to_float(quote.get("percent_change"), 0.0)
    pe = to_float(fundamentals.get("pe_ratio"), -1.0)
    pb = to_float(fundamentals.get("pb_ratio"), -1.0)
    roe = to_float(fundamentals.get("roe"), -1.0)
    news_count = int(news.get("count") or 0)

    value = 55.0
    if 0 < pe <= 15:
        value += 18
    elif pe > 35:
        value -= 12
    if 0 < pb <= 1.5:
        value += 10
    elif pb > 4:
        value -= 8

    quality = 50.0
    if roe >= 12:
        quality += 18
    elif 0 <= roe < 6:
        quality -= 10

    momentum = 50.0 + clamp(pct * 2.2, -20, 20) + clamp(news_count * 1.2, 0, 12)
    risk_penalty = risk.get("total", 5.0) * 4.0

    horizon_weights = {
        "short": {"value": 0.2, "quality": 0.15, "momentum": 0.5, "risk": -0.25},
        "mid": {"value": 0.35, "quality": 0.25, "momentum": 0.2, "risk": -0.2},
        "long": {"value": 0.3, "quality": 0.4, "momentum": 0.1, "risk": -0.2},
    }
    risk_mult = {"conservative": 1.25, "neutral": 1.0, "aggressive": 0.8}.get(risk_pref, 1.0)
    w_default = horizon_weights.get(horizon_pref, horizon_weights["mid"])

    out: Dict[str, Any] = {}
    for key in ("short", "mid", "long"):
        w = horizon_weights[key]
        score = (
            (value * w["value"])
            + (quality * w["quality"])
            + (momentum * w["momentum"])
            + ((risk_penalty * risk_mult) * w["risk"])
        )
        score = clamp(score, 0, 100)
        reasons = [
            f"모멘텀 점수 {momentum:.1f} (등락률 {pct:.2f}%, 뉴스 {news_count}건)",
            f"밸류 점수 {value:.1f} (PER {pe if pe>0 else '-'} / PBR {pb if pb>0 else '-'})",
            f"리스크 패널티 {risk_penalty * risk_mult:.1f} (총 리스크 {risk.get('total', 0):.1f}/10)",
        ]
        out[key] = {"score": round(score, 2), "label": signal_label(score), "reasons": reasons}
    return out


def compute_relative_comparison(ticker: str, market: str, sector: str, fundamentals: Dict[str, Any]) -> Dict[str, Any]:
    peers = get_peer_candidates(ticker, market, sector, limit=5)
    peer_metrics: List[Dict[str, Any]] = []
    for p in peers:
        f = get_fundamentals(p["ticker"], market=market)
        peer_metrics.append(
            {
                "ticker": p["ticker"],
                "name": p["name"],
                "pe": to_float_or_none(f.get("pe_ratio")),
                "pb": to_float_or_none(f.get("pb_ratio")),
                "roe": to_float_or_none(f.get("roe")),
            }
        )
    avg = {
        "pe": mean_valid([x.get("pe") for x in peer_metrics]),
        "pb": mean_valid([x.get("pb") for x in peer_metrics]),
        "roe": mean_valid([x.get("roe") for x in peer_metrics]),
    }
    main_peer = peer_metrics[0] if peer_metrics else {"ticker": "-", "name": "-", "pe": None, "pb": None, "roe": None}
    return {
        "title": f"{resolve_company_name(ticker, market)} vs 업종 평균 vs 주요 경쟁사",
        "target": {
            "pe": to_float_or_none(fundamentals.get("pe_ratio")),
            "pb": to_float_or_none(fundamentals.get("pb_ratio")),
            "roe": to_float_or_none(fundamentals.get("roe")),
        },
        "sector_average": avg,
        "peer": {"ticker": main_peer.get("ticker"), "name": main_peer.get("name"), "pe": main_peer.get("pe"), "pb": main_peer.get("pb"), "roe": main_peer.get("roe")},
        "peer_count": len(peer_metrics),
    }


def scenario_impact_pct(sector: str, fx_change_pct: float, ev_growth_pct: float) -> float:
    fx_beta = 0.35
    ev_beta = 0.20
    if sector == "자동차":
        ev_beta = 0.55
        fx_beta = 0.45
    elif sector == "2차전지":
        ev_beta = 0.45
        fx_beta = 0.30
    elif sector in {"반도체", "AI"}:
        ev_beta = 0.25
        fx_beta = 0.40
    impact = (ev_growth_pct * ev_beta) - (fx_change_pct * fx_beta)
    return round(clamp(impact, -30.0, 30.0), 2)


def build_value_playbook(
    quote: Dict[str, Any],
    fundamentals: Dict[str, Any],
    relative: Dict[str, Any],
    risk: Dict[str, float],
    quality: float,
    tech_strength: float,
    capital_power: float,
    valuation: float,
    composite: float,
    hype: float,
) -> Dict[str, Any]:
    reasons: List[str] = []
    risks: List[str] = []

    pe = to_float_or_none(fundamentals.get("pe_ratio"))
    pb = to_float_or_none(fundamentals.get("pb_ratio"))
    roe = to_float_or_none(fundamentals.get("roe"))
    opm = to_float_or_none(fundamentals.get("operating_margin_ttm"))
    mcap = to_float_or_none(fundamentals.get("market_cap"))
    avg = relative.get("sector_average", {}) or {}
    avg_pe = to_float_or_none(avg.get("pe"))
    avg_pb = to_float_or_none(avg.get("pb"))
    avg_roe = to_float_or_none(avg.get("roe"))

    if pe and avg_pe and pe < avg_pe:
        reasons.append(f"PER {pe:.2f}가 업종 평균 {avg_pe:.2f} 대비 낮아 상대 저평가 가능성이 있습니다.")
    if pb and avg_pb and pb < avg_pb:
        reasons.append(f"PBR {pb:.2f}가 업종 평균 {avg_pb:.2f}보다 낮아 자산가치 대비 할인 구간입니다.")
    if roe and avg_roe and roe >= avg_roe:
        reasons.append(f"ROE {roe:.2f}가 업종 평균 {avg_roe:.2f} 이상으로 수익성 체력이 유지됩니다.")
    if quality >= 62:
        reasons.append(f"품질 점수 {quality:.1f}점으로 수익성/안정성 지표가 양호합니다.")
    if capital_power >= 60:
        if mcap and mcap > 0:
            reasons.append(f"자본력 점수 {capital_power:.1f}점이며 시가총액 {mcap:,.0f} 수준으로 재무 완충력이 있습니다.")
        else:
            reasons.append(f"자본력 점수 {capital_power:.1f}점으로 재무 체력이 양호합니다.")
    if valuation >= 60:
        reasons.append(f"밸류 점수 {valuation:.1f}점으로 현재 가격대가 펀더멘털 대비 합리적입니다.")
    if tech_strength >= 58:
        reasons.append(f"기술력 점수 {tech_strength:.1f}점으로 기술 경쟁력/사업연결성이 방어됩니다.")

    if pe and avg_pe and pe > avg_pe * 1.3:
        risks.append(f"PER {pe:.2f}가 업종 평균 {avg_pe:.2f} 대비 높아 고평가 함정 가능성이 있습니다.")
    if pb and avg_pb and pb > avg_pb * 1.3:
        risks.append(f"PBR {pb:.2f}가 업종 평균 {avg_pb:.2f}보다 높아 리레이팅 여지가 제한될 수 있습니다.")
    if roe is not None and roe < 6:
        risks.append(f"ROE {roe:.2f}로 수익성 회복 확인이 필요합니다.")
    if opm is not None and opm < 5 and opm >= 0:
        risks.append(f"영업마진 {opm:.2f}로 이익 체력이 약해 하방 리스크가 존재합니다.")
    if risk.get("total", 0.0) >= 6.2:
        risks.append(f"리스크 점수 {risk.get('total', 0.0):.1f}/10으로 변동성·경쟁강도가 높은 구간입니다.")
    if hype >= 65:
        risks.append(f"테마 과열 점수 {hype:.1f}로 단기 급등/급락 리스크가 큽니다.")

    while len(reasons) < 3:
        reasons.append("업종 대비 밸류·품질·자본력의 동시 개선 신호를 추가 확인하세요.")
    while len(risks) < 3:
        risks.append("실적/수주/공시로 추정치가 유지되는지 분기별로 점검이 필요합니다.")

    stance = "관망"
    if composite >= 68 and risk.get("total", 0.0) <= 6.0 and valuation >= 58:
        stance = "매수"
    elif composite < 48 or risk.get("total", 0.0) >= 7.5:
        stance = "비중축소"

    current = to_float(quote.get("current_price"), 0.0)
    buy_below = round(current * 0.97, 2) if current > 0 else None
    take_profit = round(current * 1.12, 2) if current > 0 else None

    return {
        "undervalued_reasons": reasons[:3],
        "value_trap_risks": risks[:3],
        "action": {
            "stance": stance,
            "condition": "분할 접근: 업종 대비 할인 + 실적 유지 + 변동성 완화 동시 충족 시 가중",
            "buy_below": buy_below,
            "take_profit": take_profit,
        },
    }


def build_decision_intel(
    ticker: str,
    market: str,
    horizon_pref: str = "mid",
    risk_pref: str = "neutral",
    fx_change_pct: float = 0.0,
    ev_growth_pct: float = 5.0,
) -> Dict[str, Any]:
    quote = get_quote(ticker, market=market)
    fundamentals = get_fundamentals(ticker, market=market)
    news = get_news(ticker, market=market, days=7)
    filings = get_sec_filings(ticker, market=market, limit=5)

    sector = canonical_sector(str(fundamentals.get("sector") or ""), str(fundamentals.get("name") or resolve_company_name(ticker, market)), str(fundamentals.get("industry") or ""))
    risk = compute_risk_breakdown(quote, fundamentals, market, sector)
    signals = compute_personalized_signals(quote, fundamentals, news, risk, horizon_pref, risk_pref)
    relative = compute_relative_comparison(ticker, market, sector, fundamentals)
    hype = compute_hype_score(quote, fundamentals, news)
    quality = compute_quality_score(quote, fundamentals)
    capital_power = compute_capital_power_score(fundamentals, market)
    market_impact = compute_market_impact_score(quote, fundamentals, news)
    tech_strength = compute_technology_strength_score(get_technology(ticker, max_results=5), news, filings, sector)
    valuation = compute_valuation_score(fundamentals, quality, hype)
    composite = combine_rank(quality, tech_strength, market_impact, valuation, hype)
    sector_heat = compute_sector_heat_signal(quote, news, hype, quality, capital_power, valuation)
    playbook = build_value_playbook(
        quote,
        fundamentals,
        relative,
        risk,
        quality,
        tech_strength,
        capital_power,
        valuation,
        composite,
        hype,
    )

    cur = to_float(quote.get("current_price"), 0.0)
    if cur <= 0:
        cur = 0.0
    impact = scenario_impact_pct(sector, fx_change_pct, ev_growth_pct)
    vol_band = max(0.03, min(0.12, risk.get("volatility", 5.0) / 100.0 * 1.8))
    center = cur * (1.0 + (impact / 100.0))
    low = center * (1.0 - vol_band)
    high = center * (1.0 + vol_band)

    return {
        "ok": True,
        "ticker": ticker,
        "market": market,
        "decision_panel": {
            "today_move_reason": infer_price_driver(quote, news, filings, ticker=ticker, market=market),
            "today_change_pct": to_float(quote.get("percent_change"), 0.0) if quote.get("ok") else 0.0,
            "signals": signals,
            "risk": risk,
            "snapshot": {
                "composite": round(composite, 2),
                "valuation": round(valuation, 2),
                "quality": round(quality, 2),
                "tech_strength": round(tech_strength, 2),
                "capital_power": round(capital_power, 2),
                "market_impact": round(market_impact, 2),
                "hype": round(hype, 2),
            },
            "sector_heat": sector_heat,
            "undervalued_reasons": playbook["undervalued_reasons"],
            "value_trap_risks": playbook["value_trap_risks"],
            "action": playbook["action"],
        },
        "relative_comparison": relative,
        "scenario": {
            "inputs": {"fx_change_pct": fx_change_pct, "ev_growth_pct": ev_growth_pct},
            "expected_impact_pct": impact,
            "target_price_range": {"low": round(low, 2), "high": round(high, 2)},
            "model_note": "단순화된 민감도 모델",
        },
        "meta": {"horizon_pref": horizon_pref, "risk_pref": risk_pref, "sector": sector, "time": utc_now_iso()},
        "sources": {
            "quote": {"ok": quote.get("ok"), "source": quote.get("source")},
            "fundamentals": {"ok": fundamentals.get("ok"), "source": fundamentals.get("source")},
            "news": {"ok": news.get("ok"), "source": news.get("source"), "count": news.get("count", 0)},
            "filings": {"ok": filings.get("ok"), "source": filings.get("source"), "count": filings.get("count", 0)},
        },
    }


def evaluate_undervalued_candidate(ticker: str, market: str) -> Dict[str, Any]:
    quote = get_quote(ticker, market=market)
    fundamentals = get_fundamentals(ticker, market=market)
    news = get_news(ticker, market=market, days=7)
    filings = get_sec_filings(ticker, market=market, limit=5)
    technology = get_technology(ticker, max_results=5)

    sector = canonical_sector(
        str(fundamentals.get("sector") or ""),
        str(fundamentals.get("name") or resolve_company_name(ticker, market)),
        str(fundamentals.get("industry") or ""),
    )
    hype = compute_hype_score(quote, fundamentals, news)
    quality = compute_quality_score(quote, fundamentals)
    moat = compute_technology_strength_score(technology, news, filings, sector)
    capital_power = compute_capital_power_score(fundamentals, market)
    market_impact = compute_market_impact_score(quote, fundamentals, news)
    valuation = compute_valuation_score(fundamentals, quality, hype)
    rank = combine_rank(quality, moat, market_impact, valuation, hype)
    sector_heat = compute_sector_heat_signal(quote, news, hype, quality, capital_power, valuation)
    company_name = str(fundamentals.get("name") or "").strip() or resolve_company_name(ticker, market)

    return {
        "ticker": ticker,
        "company_name": company_name,
        "market": market,
        "label": rank_label(rank),
        "undervalued_rank": round(rank, 2),
        "sector": sector,
        "quality_score": round(quality, 2),
        "tech_moat_score": round(moat, 2),
        "capital_power_score": round(capital_power, 2),
        "market_impact_score": round(market_impact, 2),
        "valuation_score": round(valuation, 2),
        "hype_score": round(hype, 2),
        "sector_heat_score": sector_heat["heat_score"],
        "resilience_score": sector_heat["resilience_score"],
        "sector_heat_label": sector_heat["label"],
        "quote": quote,
        "fundamentals": fundamentals,
    }


def annotate_sector_relative_scores(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    grouped: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
    for item in items:
        market = str(item.get("market") or "US").upper()
        sector = str(item.get("sector") or "").strip()
        if not sector:
            f = item.get("fundamentals", {}) or {}
            sector = canonical_sector(
                str(f.get("sector") or ""),
                str(item.get("company_name") or f.get("name") or ""),
                str(f.get("industry") or ""),
            )
        if not sector:
            sector = "기타" if market == "KR" else "UNCLASSIFIED"
        item["sector"] = sector
        grouped.setdefault((market, sector), []).append(item)

    for (_market, _sector), rows in grouped.items():
        rows.sort(key=lambda x: float(x.get("undervalued_rank", 0.0)), reverse=True)
        n = len(rows)
        for idx, row in enumerate(rows):
            if n <= 1:
                pct = 100.0
            else:
                pct = ((n - idx - 1) / (n - 1)) * 100.0
            row["sector_rank"] = idx + 1
            row["sector_size"] = n
            row["sector_percentile"] = round(pct, 1)
    return items


def get_ranking_for_user(user_id: str, limit: int = 30) -> Dict[str, Any]:
    limit = max(1, min(limit, 200))
    with db_conn() as conn:
        rows = conn.execute(
            "SELECT ticker, market FROM watchlist WHERE user_id = ? ORDER BY market, ticker LIMIT ?",
            (user_id, limit),
        ).fetchall()
    items = []
    for row in rows:
        ticker = row["ticker"]
        market = row["market"]
        try:
            items.append(evaluate_undervalued_candidate(ticker, market))
        except Exception as exc:
            items.append(
                {
                    "ticker": ticker,
                    "market": market,
                    "sector": "",
                    "label": "Error",
                    "undervalued_rank": 0.0,
                    "error": str(exc),
                }
            )
    annotate_sector_relative_scores(items)
    items.sort(key=lambda x: x.get("undervalued_rank", 0), reverse=True)
    return {"ok": True, "user_id": user_id, "count": len(items), "items": items, "time": utc_now_iso()}


def get_sector_overview_for_user(user_id: str, limit: int = 50) -> Dict[str, Any]:
    ranking = get_ranking_for_user(user_id, limit=limit)
    if not ranking.get("ok"):
        return ranking

    grouped: Dict[str, Dict[str, Any]] = {}
    for item in ranking.get("items", []):
        fundamentals = item.get("fundamentals", {}) or {}
        raw_sector = str(fundamentals.get("sector") or "").strip()
        name = str(item.get("company_name") or fundamentals.get("name") or "").strip()
        industry = str(fundamentals.get("industry") or "").strip()
        market = str(item.get("market") or "US")
        sector = canonical_sector(raw_sector, name, industry) if raw_sector else ("기타" if market == "KR" else "UNCLASSIFIED")
        if sector not in grouped:
            grouped[sector] = {"sector": sector, "count": 0, "avg_rank": 0.0, "items": []}
        g = grouped[sector]
        g["count"] += 1
        g["items"].append(
            {
                "ticker": item.get("ticker"),
                "market": market,
                "rank": item.get("undervalued_rank", 0.0),
                "label": item.get("label", ""),
            }
        )

    out = []
    for sector, g in grouped.items():
        ranks = [float(x.get("rank", 0.0)) for x in g["items"]]
        avg_rank = sum(ranks) / len(ranks) if ranks else 0.0
        g["avg_rank"] = round(avg_rank, 2)
        g["items"].sort(key=lambda x: float(x.get("rank", 0.0)), reverse=True)
        out.append(g)

    out.sort(key=lambda x: (x["avg_rank"], x["count"]), reverse=True)
    return {"ok": True, "user_id": user_id, "count": len(out), "sectors": out, "time": utc_now_iso()}


def lookup_company_local(query: str, market: str, limit: int = 20) -> List[Dict[str, Any]]:
    q = normalize_search_key(query)
    if not q:
        return []
    rows = []
    for item in load_sector_seed():
        item_market = str(item.get("market", "")).upper()
        if market != "ALL" and item_market != market:
            continue
        ticker = str(item.get("ticker", ""))
        name = str(item.get("name", ""))
        sector = canonical_sector(str(item.get("sector", "")), name, "")
        text = normalize_search_key(f"{ticker} {name} {sector}")
        if q in text:
            rows.append(
                {
                    "ticker": ticker,
                    "name": name,
                    "sector": sector,
                    "market": item_market,
                    "source": "local_seed",
                }
            )
    return rows[: max(1, min(limit, 100))]


def lookup_company_us_finnhub(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    key = os.getenv("FINNHUB_API_KEY", "").strip()
    if not key:
        return []
    url = (
        "https://finnhub.io/api/v1/search?"
        f"q={urllib.parse.quote(query)}&token={urllib.parse.quote(key)}"
    )
    try:
        data = http_get_json(url, timeout=12)
    except Exception:
        return []
    out = []
    for item in (data.get("result", []) if isinstance(data, dict) else [])[: max(1, min(limit, 50))]:
        symbol = str(item.get("symbol", "")).upper()
        if not symbol or "." in symbol:
            continue
        out.append(
            {
                "ticker": symbol,
                "name": item.get("description", ""),
                "sector": "",
                "market": "US",
                "source": "finnhub_search",
            }
        )
    return out


def lookup_company_us_alias(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    q = normalize_search_key(query)
    if not q:
        return []
    # Common Korean/English aliases for major US names.
    aliases = [
        ("AAPL", "Apple Inc.", ["apple", "애플"]),
        ("MSFT", "Microsoft Corp.", ["microsoft", "마이크로소프트"]),
        ("NVDA", "NVIDIA Corp.", ["nvidia", "엔비디아"]),
        ("TSLA", "Tesla Inc.", ["tesla", "테슬라"]),
        ("AMZN", "Amazon.com Inc.", ["amazon", "아마존"]),
        ("GOOGL", "Alphabet Inc.", ["google", "alphabet", "구글", "알파벳"]),
        ("META", "Meta Platforms", ["meta", "facebook", "페이스북", "메타"]),
        ("NFLX", "Netflix", ["netflix", "넷플릭스"]),
        ("AMD", "Advanced Micro Devices", ["amd"]),
        ("AVGO", "Broadcom Inc.", ["broadcom", "브로드컴"]),
        ("TSM", "Taiwan Semiconductor ADR", ["tsm", "tsmc", "대만반도체"]),
        ("PLTR", "Palantir Technologies", ["palantir", "팔란티어"]),
        ("BRK.B", "Berkshire Hathaway", ["berkshire", "버크셔", "워런버핏", "버핏"]),
        ("JPM", "JPMorgan Chase", ["jpm", "jp모건", "제이피모건"]),
    ]
    out: List[Dict[str, Any]] = []
    lim = max(1, min(limit, 100))
    for ticker, name, terms in aliases:
        match_text = " ".join([ticker, name] + terms)
        if q in normalize_search_key(match_text):
            out.append(
                {
                    "ticker": ticker,
                    "name": name,
                    "sector": find_sector_from_seed(ticker, "US"),
                    "market": "US",
                    "source": "us_alias",
                }
            )
        if len(out) >= lim:
            break
    return out


def yahoo_symbol_to_market_ticker(symbol: str) -> Tuple[str, str]:
    s = str(symbol or "").strip().upper()
    if not s:
        return ("", "")
    if s.endswith(".KS") or s.endswith(".KQ"):
        raw = re.sub(r"[^0-9]", "", s)
        return ("KR", normalize_kr_ticker(raw))
    # For this app we only support KR/US. Drop non-KR exchange suffix symbols such as ".SW".
    if "." in s:
        suffix = s.rsplit(".", 1)[-1]
        if suffix and len(suffix) >= 2:
            return ("", "")
    return ("US", s)


def lookup_company_yahoo(query: str, market: str, limit: int = 20) -> List[Dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    try:
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(q)}&quotesCount=30&newsCount=0"
        data = http_get_json(url, timeout=12)
    except Exception:
        return []

    out: List[Dict[str, Any]] = []
    for item in (data.get("quotes", []) if isinstance(data, dict) else []):
        symbol = str(item.get("symbol", "")).upper()
        if not symbol:
            continue
        item_market, ticker = yahoo_symbol_to_market_ticker(symbol)
        if not item_market or not ticker:
            continue
        if market != "ALL" and item_market != market:
            continue
        out.append(
            {
                "ticker": ticker,
                "name": item.get("shortname") or item.get("longname") or "",
                "sector": "",
                "market": item_market,
                "source": "yahoo_search",
            }
        )
        if len(out) >= max(1, min(limit, 100)):
            break
    return out


def lookup_company_kr_dart(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    q = normalize_search_key(query)
    if not q:
        return []
    out = []
    for row in get_dart_company_index():
        code = row.get("stock_code", "")
        name = row.get("corp_name", "")
        if not code:
            continue
        text = normalize_search_key(f"{code} {name}")
        if q in text:
            out.append({"ticker": code, "name": name, "sector": find_sector_from_seed(code, "KR"), "market": "KR", "source": "dart"})
        if len(out) >= max(1, min(limit, 100)):
            break
    return out


def lookup_company_kr_naver(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    url = f"https://finance.naver.com/search/searchList.naver?query={urllib.parse.quote(q)}"
    try:
        html = http_get_text(url, timeout=12)
    except Exception:
        return []
    rows = re.findall(
        r'href="/item/main\.naver\?code=([0-9]{6})"[^>]*>([^<]+)</a>',
        html,
        flags=re.IGNORECASE,
    )
    out: List[Dict[str, Any]] = []
    seen = set()
    for code, name in rows:
        if code in seen:
            continue
        seen.add(code)
        out.append(
            {
                "ticker": normalize_kr_ticker(code),
                "name": re.sub(r"\s+", " ", name).strip(),
                "sector": find_sector_from_seed(code, "KR"),
                "market": "KR",
                "source": "naver_search",
            }
        )
        if len(out) >= max(1, min(limit, 100)):
            break
    return out


def lookup_company_kr_naver_autocomplete(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    q = (query or "").strip()
    if not q:
        return []
    # Naver finance autocomplete endpoint (JSON/JSONP variants)
    url = (
        "https://ac.finance.naver.com/ac"
        f"?q={urllib.parse.quote(q)}&q_enc=UTF-8&st=111&frm=stock&r_lt=111&t_koreng=1"
    )
    try:
        text = http_get_text(url, timeout=10)
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    seen = set()
    # Fallback regex parser for both JSON and JSONP responses.
    matches = re.findall(r'"([0-9]{6})","([^"]+)"', text)
    for code, name in matches:
        if code in seen:
            continue
        seen.add(code)
        out.append(
            {
                "ticker": normalize_kr_ticker(code),
                "name": re.sub(r"\s+", " ", name).strip(),
                "sector": find_sector_from_seed(code, "KR"),
                "market": "KR",
                "source": "naver_autocomplete",
            }
        )
        if len(out) >= max(1, min(limit, 100)):
            break
    return out


def lookup_company_kr_alias(query: str, limit: int = 20) -> List[Dict[str, Any]]:
    q = normalize_search_key(query)
    if not q:
        return []
    # High-frequency KR names to reduce misses when providers fail intermittently.
    aliases = [
        ("088350", "한화생명", "금융"),
        ("009830", "한화솔루션", "화학"),
        ("130660", "한전산업", "에너지"),
        ("011790", "SKC", "화학"),
        ("034020", "두산에너빌리티", "조선방산"),
        ("001510", "SK증권", "증권"),
        ("006800", "미래에셋증권", "증권"),
        ("039490", "키움증권", "증권"),
        ("016360", "삼성증권", "증권"),
        ("005940", "NH투자증권", "증권"),
        ("051600", "한전KPS", "에너지"),
        ("018880", "한온시스템", "자동차"),
    ]
    out: List[Dict[str, Any]] = []
    for code, name, sector in aliases:
        text = normalize_search_key(f"{code} {name} {sector}")
        if q in text:
            out.append(
                {
                    "ticker": code,
                    "name": name,
                    "sector": canonical_sector(sector, name, ""),
                    "market": "KR",
                    "source": "kr_alias",
                }
            )
        if len(out) >= max(1, min(limit, 100)):
            break
    return out


def dedupe_companies(items: List[Dict[str, Any]], limit: int = 20) -> List[Dict[str, Any]]:
    seen = set()
    out = []
    for item in items:
        key = (item.get("market"), item.get("ticker"))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= max(1, min(limit, 100)):
            break
    return out


def lookup_company(query: str, market: str = "US", limit: int = 20) -> Dict[str, Any]:
    q = (query or "").strip()
    if not q:
        return {"ok": False, "error": "query is required"}
    lookup_market = clean_lookup_market(market)
    local = lookup_company_local(q, lookup_market, limit=limit)
    provider: List[Dict[str, Any]] = []
    if lookup_market in ("US", "ALL"):
        provider.extend(lookup_company_us_alias(q, limit=limit))
        provider.extend(lookup_company_us_finnhub(q, limit=limit))
    if lookup_market in ("KR", "ALL"):
        provider.extend(lookup_company_kr_dart(q, limit=limit))
        provider.extend(lookup_company_kr_naver_autocomplete(q, limit=limit))
        provider.extend(lookup_company_kr_naver(q, limit=limit))
        provider.extend(lookup_company_kr_alias(q, limit=limit))
    provider.extend(lookup_company_yahoo(q, market=lookup_market, limit=limit))
    items = dedupe_companies(local + provider, limit=limit)

    # Last-resort fallback: treat input itself as ticker when providers are unavailable.
    if not items:
        raw = str(q).strip()
        if lookup_market in ("US", "ALL") and re.match(r"^[A-Za-z][A-Za-z0-9.\-]{0,9}$", raw):
            t = raw.upper()
            items.append(
                {
                    "ticker": t,
                    "name": find_company_name_from_seed(t, "US"),
                    "sector": find_sector_from_seed(t, "US"),
                    "market": "US",
                    "source": "input_ticker",
                }
            )
        elif lookup_market in ("KR", "ALL") and re.match(r"^[0-9]{4,6}$", raw):
            t = normalize_kr_ticker(raw)
            items.append(
                {
                    "ticker": t,
                    "name": find_company_name_from_seed(t, "KR") or get_kr_profile(t).get("name", ""),
                    "sector": find_sector_from_seed(t, "KR"),
                    "market": "KR",
                    "source": "input_ticker",
                }
            )

    items = dedupe_companies(items, limit=limit)
    items = sorted(items, key=lambda x: (str(x.get("market", "")), str(x.get("ticker", ""))))
    src_counts: Dict[str, int] = {}
    for it in items:
        src = str(it.get("source") or "unknown")
        src_counts[src] = src_counts.get(src, 0) + 1
    log_event(
        "company_lookup",
        query=q,
        market=lookup_market,
        count=len(items),
        local_count=len(local),
        provider_count=len(provider),
        source_counts=src_counts,
    )
    return {"ok": True, "query": q, "market": lookup_market, "count": len(items), "items": items}


def get_sector_list_for_market(user_id: str, market: str) -> Dict[str, Any]:
    lookup_market = clean_lookup_market(market)
    sectors = set()
    for item in load_sector_seed():
        item_market = str(item.get("market", "")).upper()
        if lookup_market != "ALL" and item_market != lookup_market:
            continue
        if lookup_market == "ALL" and item_market not in ALLOWED_MARKETS:
            continue
        sec = canonical_sector(str(item.get("sector", "")).strip(), str(item.get("name", "")).strip(), "")
        if sec:
            sectors.add(sec)
    overview = get_sector_overview_for_user(user_id, limit=100)
    for sec in overview.get("sectors", []):
        if not sec.get("items"):
            continue
        sec_market = str(sec["items"][0].get("market", "")).upper()
        if lookup_market != "ALL" and sec_market != lookup_market:
            continue
        if lookup_market == "ALL" and sec_market not in ALLOWED_MARKETS:
            continue
        sectors.add(canonical_sector(str(sec.get("sector", "")), "", ""))
    out = sorted([s for s in sectors if s])
    return {"ok": True, "user_id": user_id, "market": lookup_market, "count": len(out), "sectors": out}


def get_sector_seed_items(market: str = "ALL", limit: int = 5000) -> Dict[str, Any]:
    lookup_market = clean_lookup_market(market)
    lim = max(1, min(limit, 20000))
    out: List[Dict[str, Any]] = []
    for item in load_sector_seed():
        item_market = str(item.get("market", "")).upper()
        if lookup_market != "ALL" and item_market != lookup_market:
            continue
        out.append(item)
        if len(out) >= lim:
            break
    return {"ok": True, "market": lookup_market, "count": len(out), "items": out}


def get_sector_stocks(
    user_id: str,
    market: str,
    sector: str,
    limit: int = 30,
    include_ranked: bool = True,
) -> Dict[str, Any]:
    lookup_market = clean_lookup_market(market)
    s = (sector or "").strip().lower()
    if not s:
        return {"ok": False, "error": "sector is required"}
    rows: List[Dict[str, Any]] = []
    for item in load_sector_seed():
        item_market = str(item.get("market", "")).upper()
        if lookup_market != "ALL" and item_market != lookup_market:
            continue
        mapped_sector = canonical_sector(str(item.get("sector", "")), str(item.get("name", "")), "")
        if mapped_sector.lower() != s:
            continue
        rows.append(
            {
                "ticker": item.get("ticker", ""),
                "name": item.get("name", ""),
                "sector": mapped_sector,
                "market": item_market,
                "source": "local_seed",
                "rank": 0.0,
            }
        )
    if include_ranked:
        ranking = get_ranking_for_user(user_id, limit=100)
        for item in ranking.get("items", []):
            item_market = str(item.get("market", "")).upper()
            if lookup_market != "ALL" and item_market != lookup_market:
                continue
            fsec = str((item.get("fundamentals") or {}).get("sector") or "").strip()
            fname = str(item.get("company_name", "") or str((item.get("fundamentals") or {}).get("name") or "")).strip()
            findustry = str((item.get("fundamentals") or {}).get("industry") or "").strip()
            mapped = canonical_sector(fsec, fname, findustry) if fsec else ("기타" if item_market == "KR" else "UNCLASSIFIED")
            if mapped.lower() == s:
                rows.append(
                    {
                        "ticker": item.get("ticker", ""),
                        "name": item.get("company_name", "") or str((item.get("fundamentals") or {}).get("name") or ""),
                        "sector": mapped,
                        "market": item_market,
                        "source": "watchlist_ranked",
                        "rank": float(item.get("undervalued_rank", 0.0)),
                    }
                )
    # dedupe by ticker+market and keep max rank
    merged: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for r in rows:
        key = (str(r.get("market", "")), str(r.get("ticker", "")))
        if key not in merged or float(r.get("rank", 0.0)) > float(merged[key].get("rank", 0.0)):
            merged[key] = r
    out = list(merged.values())
    out.sort(key=lambda x: float(x.get("rank", 0.0)), reverse=True)
    out = out[: max(1, min(limit, 200))]
    return {
        "ok": True,
        "user_id": user_id,
        "market": lookup_market,
        "sector": sector,
        "count": len(out),
        "include_ranked": bool(include_ranked),
        "items": out,
    }


def process_user_ticker(user_id: str, ticker: str, market: str) -> List[Dict[str, Any]]:
    alerts = []
    quote = get_quote(ticker, market=market)
    fundamentals = get_fundamentals(ticker, market=market)
    news = get_news(ticker, market=market, days=3)
    filings = get_sec_filings(ticker, market=market, limit=1)
    hype = compute_hype_score(quote, fundamentals, news)

    prev_hype = get_state(user_id, ticker, market, "last_hype")
    prev_accession = get_state(user_id, ticker, market, "last_filing_accession")

    with db_conn() as conn:
        rules = conn.execute(
            "SELECT rule_type, threshold, enabled FROM alert_rules WHERE user_id = ? AND ticker = ? AND market = ?",
            (user_id, ticker, market),
        ).fetchall()

    for row in rules:
        if int(row["enabled"] or 0) != 1:
            continue
        rule_type = row["rule_type"]
        threshold = float(row["threshold"])

        if rule_type == "price_change_pct" and quote.get("ok"):
            pct = abs(float(quote.get("percent_change") or 0.0))
            if pct >= threshold:
                msg = f"{ticker} 가격 변동률 {pct:.2f}% (기준 {threshold:.2f}%)"
                create_notification(user_id, ticker, market, "price_change_pct", msg, {"quote": quote, "threshold": threshold})
                alerts.append({"kind": "price_change_pct", "message": msg})

        elif rule_type == "hype_score_jump":
            prev = float(prev_hype) if prev_hype is not None else None
            if prev is not None and (hype - prev) >= threshold:
                msg = f"{ticker} 과열 점수 급등 {prev:.1f} -> {hype:.1f} (기준 +{threshold:.1f})"
                create_notification(user_id, ticker, market, "hype_score_jump", msg, {"hype": hype, "prev_hype": prev, "threshold": threshold})
                alerts.append({"kind": "hype_score_jump", "message": msg})

        elif rule_type == "new_filing" and filings.get("ok") and filings.get("items"):
            latest = filings["items"][0].get("accession_number", "")
            if latest and prev_accession and latest != prev_accession:
                msg = (
                    f"{ticker} 신규 공시 감지: {filings['items'][0].get('form', '-')}, "
                    f"{filings['items'][0].get('filing_date', '-')}"
                )
                create_notification(user_id, ticker, market, "new_filing", msg, {"filing": filings["items"][0]})
                alerts.append({"kind": "new_filing", "message": msg})

    set_state(user_id, ticker, market, "last_hype", f"{hype:.4f}")
    if filings.get("ok") and filings.get("items"):
        accession = filings["items"][0].get("accession_number", "")
        if accession:
            set_state(user_id, ticker, market, "last_filing_accession", accession)

    return alerts


def run_alert_scan(user_id: Optional[str] = None) -> Dict[str, Any]:
    with db_conn() as conn:
        if user_id:
            rows = conn.execute("SELECT user_id, ticker, market FROM watchlist WHERE user_id = ? ORDER BY market, ticker", (user_id,)).fetchall()
        else:
            rows = conn.execute("SELECT user_id, ticker, market FROM watchlist ORDER BY user_id, market, ticker").fetchall()

    triggered = []
    for row in rows:
        uid = row["user_id"]
        ticker = row["ticker"]
        market = row["market"]
        try:
            hits = process_user_ticker(uid, ticker, market)
            if hits:
                triggered.append({"user_id": uid, "ticker": ticker, "market": market, "alerts": hits})
        except Exception as exc:
            create_notification(uid, ticker, market, "scan_error", f"자동 수집 오류: {exc}", {"error": str(exc)})

    return {"ok": True, "scanned": len(rows), "triggered": triggered, "time": utc_now_iso()}


def start_alert_worker() -> None:
    interval = max(30, int(os.getenv("ALERT_POLL_SECONDS", "300")))

    def loop() -> None:
        while not ALERT_THREAD_STOP.is_set():
            try:
                run_alert_scan()
            except Exception:
                pass
            ALERT_THREAD_STOP.wait(interval)

    t = threading.Thread(target=loop, name="alert-worker", daemon=True)
    t.start()


def get_providers_status() -> Dict[str, Any]:
    return {
        "ok": True,
        "time": utc_now_iso(),
        "providers": {
            "finnhub": {"configured": bool(os.getenv("FINNHUB_API_KEY", "").strip())},
            "alpha_vantage": {"configured": bool(os.getenv("ALPHA_VANTAGE_API_KEY", "").strip())},
            "sec": {"configured": True, "user_agent": os.getenv("SEC_USER_AGENT", DEFAULT_SEC_USER_AGENT)},
            "yahoo": {"configured": True},
            "naver_finance": {"configured": True},
            "google_news_rss": {"configured": True},
            "arxiv": {"configured": True},
            "crossref": {"configured": True},
            "dart": {"configured": bool(os.getenv("DART_API_KEY", "").strip())},
            "openai": {"configured": bool(os.getenv("OPENAI_API_KEY", "").strip())},
            "onesignal": {
                "configured": bool(os.getenv("ONESIGNAL_APP_ID", "").strip() and os.getenv("ONESIGNAL_API_KEY", "").strip())
            },
        },
        "cache_entries": len(CACHE),
        "db_path": str(DB_PATH),
        "allowed_markets": sorted(ALLOWED_MARKETS),
    }


def json_response(handler: SimpleHTTPRequestHandler, status: int, payload: Dict[str, Any]) -> None:
    content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(content)))
    handler.send_header("Cache-Control", "no-store")
    handler.end_headers()
    handler.wfile.write(content)


def parse_json_body(handler: SimpleHTTPRequestHandler) -> Dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0") or "0")
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8")) if raw else {}


class AppHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path: str) -> str:
        path = path.split("?", 1)[0].split("#", 1)[0]
        path = os.path.normpath(urllib.parse.unquote(path))
        words = [w for w in path.split("/") if w]
        resolved = ROOT_DIR
        for word in words:
            if word in (".", ".."):
                continue
            resolved = resolved / word
        return str(resolved)

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.send_response(HTTPStatus.FOUND)
            self.send_header("Location", "/web/index.html")
            self.end_headers()
            return

        if parsed.path.startswith("/api/"):
            try:
                qs = urllib.parse.parse_qs(parsed.query)
                ticker = clean_ticker((qs.get("ticker") or [""])[0])
                market_raw = (qs.get("market") or ["US"])[0]
                market = clean_market(market_raw)
                lookup_market = clean_lookup_market(market_raw)
                user_id = (qs.get("user_id") or ["default"])[0].strip() or "default"

                if parsed.path == "/api/health":
                    return json_response(self, HTTPStatus.OK, {"ok": True, "time": utc_now_iso()})
                if parsed.path == "/api/providers":
                    return json_response(self, HTTPStatus.OK, get_providers_status())
                if parsed.path == "/api/quote":
                    return json_response(self, HTTPStatus.OK, get_quote(ticker, market=market) if ticker else {"ok": False, "error": "ticker is required"})
                if parsed.path == "/api/price-history":
                    period = (qs.get("period") or ["3mo"])[0]
                    return json_response(
                        self,
                        HTTPStatus.OK,
                        get_price_history(ticker, market=market, period=period) if ticker else {"ok": False, "error": "ticker is required"},
                    )
                if parsed.path == "/api/fundamentals":
                    return json_response(self, HTTPStatus.OK, get_fundamentals(ticker, market=market) if ticker else {"ok": False, "error": "ticker is required"})
                if parsed.path == "/api/news":
                    days = int((qs.get("days") or ["7"])[0])
                    return json_response(self, HTTPStatus.OK, get_news(ticker, market=market, days=days) if ticker else {"ok": False, "error": "ticker is required"})
                if parsed.path == "/api/filings":
                    limit = int((qs.get("limit") or ["10"])[0])
                    return json_response(self, HTTPStatus.OK, get_sec_filings(ticker, market=market, limit=limit) if ticker else {"ok": False, "error": "ticker is required"})
                if parsed.path == "/api/technology":
                    query = (qs.get("query") or [ticker])[0]
                    limit = int((qs.get("limit") or ["8"])[0])
                    return json_response(self, HTTPStatus.OK, get_technology(query, max_results=limit) if query else {"ok": False, "error": "query or ticker is required"})
                if parsed.path == "/api/intel-summary":
                    query = (qs.get("query") or [ticker])[0]
                    return json_response(
                        self,
                        HTTPStatus.OK,
                        get_intelligence_summary(ticker, market=market, query=query) if ticker else {"ok": False, "error": "ticker is required"},
                    )
                if parsed.path == "/api/decision-intel":
                    horizon = str((qs.get("horizon") or ["mid"])[0] or "mid").strip().lower()
                    risk_pref = str((qs.get("risk") or ["neutral"])[0] or "neutral").strip().lower()
                    try:
                        fx_change = float((qs.get("fx_change_pct") or ["0"])[0])
                    except Exception:
                        fx_change = 0.0
                    try:
                        ev_growth = float((qs.get("ev_growth_pct") or ["5"])[0])
                    except Exception:
                        ev_growth = 5.0
                    if not ticker:
                        return json_response(self, HTTPStatus.OK, {"ok": False, "error": "ticker is required"})
                    return json_response(
                        self,
                        HTTPStatus.OK,
                        build_decision_intel(
                            ticker=ticker,
                            market=market,
                            horizon_pref=horizon,
                            risk_pref=risk_pref,
                            fx_change_pct=fx_change,
                            ev_growth_pct=ev_growth,
                        ),
                    )
                if parsed.path == "/api/backtest-sector-signal":
                    period = str((qs.get("period") or ["3mo"])[0] or "3mo")
                    try:
                        hold_days = int((qs.get("hold_days") or ["5"])[0])
                    except Exception:
                        hold_days = 5
                    if not ticker:
                        return json_response(self, HTTPStatus.OK, {"ok": False, "error": "ticker is required"})
                    return json_response(
                        self,
                        HTTPStatus.OK,
                        run_backtest_sector_signal(
                            ticker=ticker,
                            market=market,
                            period=period,
                            hold_days=hold_days,
                        ),
                    )
                if parsed.path == "/api/watchlist":
                    return json_response(self, HTTPStatus.OK, {"ok": True, "items": list_watchlist(user_id)})
                if parsed.path == "/api/company-lookup":
                    query = (qs.get("query") or [""])[0]
                    limit = int((qs.get("limit") or ["20"])[0])
                    return json_response(self, HTTPStatus.OK, lookup_company(query, market=lookup_market, limit=limit))
                if parsed.path == "/api/sector-list":
                    return json_response(self, HTTPStatus.OK, get_sector_list_for_market(user_id, lookup_market))
                if parsed.path == "/api/sector-seed":
                    limit = int((qs.get("limit") or ["5000"])[0])
                    return json_response(self, HTTPStatus.OK, get_sector_seed_items(lookup_market, limit=limit))
                if parsed.path == "/api/sector-stocks":
                    sector = (qs.get("sector") or [""])[0]
                    limit = int((qs.get("limit") or ["30"])[0])
                    include_ranked_raw = str((qs.get("include_ranked") or ["1"])[0] or "1").strip().lower()
                    include_ranked = include_ranked_raw not in {"0", "false", "no", "off"}
                    return json_response(
                        self,
                        HTTPStatus.OK,
                        get_sector_stocks(user_id, lookup_market, sector, limit=limit, include_ranked=include_ranked),
                    )
                if parsed.path == "/api/related-stocks":
                    limit = int((qs.get("limit") or ["20"])[0])
                    return json_response(
                        self,
                        HTTPStatus.OK,
                        get_related_stocks(ticker, market=market, limit=limit) if ticker else {"ok": False, "error": "ticker is required"},
                    )
                if parsed.path == "/api/alerts":
                    return json_response(self, HTTPStatus.OK, {"ok": True, "items": list_alerts(user_id)})
                if parsed.path == "/api/channels":
                    return json_response(self, HTTPStatus.OK, {"ok": True, "channels": get_channels(user_id)})
                if parsed.path == "/api/notifications":
                    limit = int((qs.get("limit") or ["40"])[0])
                    return json_response(self, HTTPStatus.OK, {"ok": True, "items": list_notifications(user_id, limit=limit)})
                if parsed.path == "/api/ranking":
                    limit = int((qs.get("limit") or ["30"])[0])
                    return json_response(self, HTTPStatus.OK, get_ranking_for_user(user_id, limit=limit))
                if parsed.path == "/api/sectors":
                    limit = int((qs.get("limit") or ["50"])[0])
                    return json_response(self, HTTPStatus.OK, get_sector_overview_for_user(user_id, limit=limit))
                if parsed.path == "/api/scan":
                    return json_response(self, HTTPStatus.OK, run_alert_scan(user_id=user_id))
                if parsed.path == "/api/test-notification":
                    ticker = ticker or "TEST"
                    result = create_notification(
                        user_id,
                        ticker,
                        market,
                        "manual_test",
                        f"{ticker} 테스트 알림입니다.",
                        {"source": "manual_test", "time": utc_now_iso()},
                    )
                    return json_response(self, HTTPStatus.OK, {"ok": True, "result": result})

                return json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "Unknown API path"})
            except Exception as exc:
                return json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc), "path": parsed.path})

        super().do_GET()

    def end_headers(self) -> None:
        parsed = urllib.parse.urlparse(getattr(self, "path", "") or "")
        if parsed.path.startswith("/web/"):
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        super().end_headers()

    def do_POST(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if not parsed.path.startswith("/api/"):
            return json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "Unknown API path"})
        try:
            body = parse_json_body(self)
            if parsed.path == "/api/watchlist":
                user_id = str(body.get("user_id") or "default").strip()
                ticker = clean_ticker(str(body.get("ticker") or ""))
                market = clean_market(str(body.get("market") or "US"))
                notes = str(body.get("notes") or "")
                if not ticker:
                    return json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "ticker is required"})
                add_watch_item(user_id, ticker, market, notes)
                return json_response(self, HTTPStatus.OK, {"ok": True, "items": list_watchlist(user_id)})

            if parsed.path == "/api/alerts/defaults":
                user_id = str(body.get("user_id") or "default").strip()
                ticker = clean_ticker(str(body.get("ticker") or ""))
                market = clean_market(str(body.get("market") or "US"))
                if not ticker:
                    return json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "ticker is required"})
                upsert_default_rules(
                    user_id,
                    ticker,
                    market,
                    float(body.get("price_change_pct") or DEFAULT_RULES["price_change_pct"]),
                    float(body.get("hype_score_jump") or DEFAULT_RULES["hype_score_jump"]),
                    bool(body.get("new_filing_enabled", True)),
                )
                return json_response(self, HTTPStatus.OK, {"ok": True, "items": list_alerts(user_id)})

            if parsed.path == "/api/channels":
                user_id = str(body.get("user_id") or "default").strip()
                set_channels(
                    user_id,
                    str(body.get("email") or ""),
                    str(body.get("webhook_url") or ""),
                    str(body.get("onesignal_external_id") or ""),
                    bool(body.get("push_enabled", False)),
                )
                return json_response(self, HTTPStatus.OK, {"ok": True, "channels": get_channels(user_id)})

            if parsed.path == "/api/scan":
                user_id = str(body.get("user_id") or "default").strip()
                return json_response(self, HTTPStatus.OK, run_alert_scan(user_id=user_id))

            if parsed.path == "/api/test-notification":
                user_id = str(body.get("user_id") or "default").strip()
                ticker = clean_ticker(str(body.get("ticker") or "TEST"))
                market = clean_market(str(body.get("market") or "US"))
                result = create_notification(
                    user_id,
                    ticker,
                    market,
                    "manual_test",
                    str(body.get("message") or f"{ticker} 테스트 알림입니다."),
                    {"source": "manual_test", "time": utc_now_iso()},
                )
                return json_response(self, HTTPStatus.OK, {"ok": True, "result": result})

            return json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "Unknown API path"})
        except Exception as exc:
            return json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc), "path": parsed.path})

    def do_DELETE(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != "/api/watchlist":
            return json_response(self, HTTPStatus.NOT_FOUND, {"ok": False, "error": "Unknown API path"})
        try:
            qs = urllib.parse.parse_qs(parsed.query)
            user_id = (qs.get("user_id") or ["default"])[0].strip() or "default"
            ticker = clean_ticker((qs.get("ticker") or [""])[0])
            market = clean_market((qs.get("market") or ["US"])[0])
            if not ticker:
                return json_response(self, HTTPStatus.BAD_REQUEST, {"ok": False, "error": "ticker is required"})
            delete_watch_item(user_id, ticker, market)
            return json_response(self, HTTPStatus.OK, {"ok": True, "items": list_watchlist(user_id)})
        except Exception as exc:
            return json_response(self, HTTPStatus.INTERNAL_SERVER_ERROR, {"ok": False, "error": str(exc), "path": parsed.path})


def build_parser() -> argparse.ArgumentParser:
    host_default = os.getenv("APP_HOST", "").strip() or "0.0.0.0"
    port_raw = os.getenv("PORT", "").strip() or os.getenv("APP_PORT", "").strip() or "8000"
    try:
        port_default = int(port_raw)
    except Exception:
        port_default = 8000
    parser = argparse.ArgumentParser(description="Stock intelligence web server")
    parser.add_argument("--host", default=host_default, help="Host to bind")
    parser.add_argument("--port", type=int, default=port_default, help="Port to bind")
    return parser


def main() -> None:
    load_env_file(ROOT_DIR / ".env", override=False)
    init_db()
    start_alert_worker()

    args = build_parser().parse_args()
    server = ThreadingHTTPServer((args.host, args.port), AppHandler)
    print(f"Serving on http://{args.host}:{args.port}")
    print("UI: /web/index.html")
    print("Health: /api/health")
    print("Providers: /api/providers")
    print("Watchlist: /api/watchlist?user_id=default")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        ALERT_THREAD_STOP.set()
        server.server_close()


if __name__ == "__main__":
    main()
