"""Domain decision logic extracted from transport/server layer.

These functions are intentionally framework-agnostic so they can be tested
and reused without coupling to HTTP handlers or persistence concerns.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


def _to_float(value: Any, default: float = 0.0) -> float:
    if value is None:
        return default
    text = str(value).replace(",", "").replace("%", "").strip()
    if not text:
        return default
    try:
        return float(text)
    except Exception:
        return default


def _to_float_or_none(value: Any) -> Optional[float]:
    if value is None:
        return None
    text = str(value).replace(",", "").replace("%", "").strip()
    if not text:
        return None
    try:
        return float(text)
    except Exception:
        return None


def _normalize_search_key(text: str) -> str:
    return re.sub(r"[\s\W_]+", "", str(text or "").lower(), flags=re.UNICODE)


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def _mean_std(values: List[float]) -> Tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    return (mean, var ** 0.5)


def canonical_sector(sector: str, name: str = "", industry: str = "") -> str:
    raw_sector = str(sector or "").strip()
    raw_name = str(name or "").strip()
    raw_industry = str(industry or "").strip()
    text = _normalize_search_key(f"{raw_sector} {raw_name} {raw_industry}")

    def has_any(keywords: List[str]) -> bool:
        return any(_normalize_search_key(k) in text for k in keywords if k)

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


def signal_label(score: float) -> str:
    if score >= 62:
        return "상승 우세"
    if score <= 42:
        return "하락 우세"
    return "중립"


def compute_sector_heat_signal(
    quote: Dict[str, Any],
    news: Dict[str, Any],
    hype: float,
    quality: float,
    capital_power: float,
    valuation: float,
) -> Dict[str, Any]:
    pct = abs(_to_float(quote.get("percent_change"), 0.0))
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
    heat = _clamp(heat, 0.0, 100.0)

    resilience = (0.36 * quality) + (0.34 * capital_power) + (0.30 * valuation) - (max(0.0, hype - 60.0) * 0.45)
    resilience = _clamp(resilience, 0.0, 100.0)

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
    close = _to_float_or_none(points[idx].get("close"))
    prev_close = _to_float_or_none(points[idx - 1].get("close"))
    close_5 = _to_float_or_none(points[idx - 5].get("close"))
    future_close = _to_float_or_none(points[idx + hold_days].get("close"))
    if close in (None, 0) or prev_close in (None, 0) or close_5 in (None, 0) or future_close in (None, 0):
        return None

    window = points[idx - 20 : idx]
    closes = [_to_float_or_none(x.get("close")) for x in window]
    closes = [x for x in closes if x not in (None, 0)]
    if len(closes) < 10:
        return None
    ma20 = sum(closes) / len(closes)
    hi20 = max(closes)

    returns_20: List[float] = []
    for j in range(idx - 20, idx):
        c0 = _to_float_or_none(points[j - 1].get("close")) if j > 0 else None
        c1 = _to_float_or_none(points[j].get("close"))
        if c0 in (None, 0) or c1 in (None, 0):
            continue
        returns_20.append(((c1 - c0) / c0) * 100.0)
    _, std20 = _mean_std(returns_20)

    vols = [_to_float_or_none(x.get("volume")) for x in window]
    vols = [x for x in vols if x is not None and x > 0]
    cur_vol = _to_float_or_none(points[idx].get("volume"))
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
    heat = _clamp(heat, 0.0, 100.0)

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
    resilience = _clamp(resilience, 0.0, 100.0)

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
    return round(_clamp(impact, -30.0, 30.0), 2)


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

    pe = _to_float_or_none(fundamentals.get("pe_ratio"))
    pb = _to_float_or_none(fundamentals.get("pb_ratio"))
    roe = _to_float_or_none(fundamentals.get("roe"))
    opm = _to_float_or_none(fundamentals.get("operating_margin_ttm"))
    mcap = _to_float_or_none(fundamentals.get("market_cap"))
    avg = relative.get("sector_average", {}) or {}
    avg_pe = _to_float_or_none(avg.get("pe"))
    avg_pb = _to_float_or_none(avg.get("pb"))
    avg_roe = _to_float_or_none(avg.get("roe"))

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

    current = _to_float(quote.get("current_price"), 0.0)
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

