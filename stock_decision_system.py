#!/usr/bin/env python3
"""Stock sector classifier and value-vs-overvaluation decision system.

Input CSV columns (case-insensitive):
- ticker (required)
- name
- business_description
- themes (comma-separated)
- price
- pe_ratio
- pb_ratio
- ps_ratio
- debt_to_equity
- roe
- revenue_growth
- net_income_growth
- fcf_margin
- cash_ratio
- insider_buy_ratio
- short_interest
- market_cap

Output:
- Sector classification
- Value score and hype score
- Label: undervalued / fairly valued / overvalued
- Decision: buy / watch / reduce / sell
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Tuple


SECTOR_KEYWORDS: Dict[str, Tuple[str, ...]] = {
    "Technology": (
        "software",
        "cloud",
        "ai",
        "semiconductor",
        "chip",
        "cybersecurity",
        "saas",
    ),
    "Robotics": (
        "robot",
        "automation",
        "factory",
        "autonomous",
        "industrial arm",
    ),
    "Financials": (
        "bank",
        "insurance",
        "asset management",
        "payment",
        "fintech",
        "stablecoin",
        "exchange",
        "lending",
    ),
    "Healthcare": (
        "biotech",
        "pharma",
        "medical",
        "drug",
        "diagnostic",
    ),
    "Energy": (
        "oil",
        "gas",
        "renewable",
        "battery",
        "solar",
        "utility",
    ),
    "Consumer": (
        "retail",
        "e-commerce",
        "consumer",
        "food",
        "beverage",
        "apparel",
    ),
    "Industrials": (
        "construction",
        "machinery",
        "logistics",
        "aerospace",
        "defense",
        "manufacturing",
    ),
}

THEME_MANIA_TERMS = {
    "stablecoin",
    "robotics",
    "ai",
    "metaverse",
    "quantum",
    "meme",
    "token",
    "crypto",
    "blockchain",
}


@dataclass
class StockResult:
    ticker: str
    name: str
    sector: str
    value_score: float
    hype_score: float
    valuation_label: str
    decision: str
    reasons: List[str]


def normalize(value: str) -> str:
    return (value or "").strip().lower()


def parse_float(row: Dict[str, str], key: str, default: float = 0.0) -> float:
    raw = row.get(key, "")
    if raw is None:
        return default
    text = str(raw).replace(",", "").strip()
    if text == "":
        return default
    try:
        return float(text)
    except ValueError:
        return default


def classify_sector(row: Dict[str, str]) -> str:
    text = " ".join(
        [
            normalize(row.get("name", "")),
            normalize(row.get("business_description", "")),
            normalize(row.get("themes", "")),
        ]
    )

    scores: Dict[str, int] = {k: 0 for k in SECTOR_KEYWORDS}
    for sector, terms in SECTOR_KEYWORDS.items():
        for term in terms:
            if term in text:
                scores[sector] += 1

    best_sector, best_score = "Unclassified", 0
    for sector, score in scores.items():
        if score > best_score:
            best_sector, best_score = sector, score

    return best_sector


def score_value(row: Dict[str, str]) -> Tuple[float, List[str]]:
    pe = parse_float(row, "pe_ratio", default=999)
    pb = parse_float(row, "pb_ratio", default=999)
    ps = parse_float(row, "ps_ratio", default=999)
    dte = parse_float(row, "debt_to_equity", default=999)
    roe = parse_float(row, "roe", default=-999)
    rg = parse_float(row, "revenue_growth", default=-999)
    nig = parse_float(row, "net_income_growth", default=-999)
    fcf = parse_float(row, "fcf_margin", default=-999)
    cash = parse_float(row, "cash_ratio", default=-999)
    insider = parse_float(row, "insider_buy_ratio", default=0)

    score = 50.0
    reasons: List[str] = []

    if pe <= 12:
        score += 12
        reasons.append("low P/E")
    elif pe <= 20:
        score += 5
    elif pe >= 45:
        score -= 12
        reasons.append("very high P/E")

    if pb <= 1.5:
        score += 10
        reasons.append("low P/B")
    elif pb >= 5:
        score -= 10
        reasons.append("high P/B")

    if ps <= 2:
        score += 8
    elif ps >= 12:
        score -= 10
        reasons.append("high P/S")

    if dte <= 0.7:
        score += 8
    elif dte >= 2.0:
        score -= 10
        reasons.append("high leverage")

    if roe >= 15:
        score += 8
    elif roe < 0:
        score -= 8

    if rg >= 10:
        score += 6
    elif rg < 0:
        score -= 8
        reasons.append("shrinking revenue")

    if nig >= 10:
        score += 6
    elif nig < 0:
        score -= 10
        reasons.append("shrinking earnings")

    if fcf >= 10:
        score += 8
    elif fcf < 0:
        score -= 8

    if cash >= 1.0:
        score += 4
    elif cash < 0.5:
        score -= 4

    if insider >= 0.02:
        score += 4
        reasons.append("insider buying")

    return max(0.0, min(100.0, score)), reasons


def score_hype(row: Dict[str, str]) -> Tuple[float, List[str]]:
    themes = [normalize(x) for x in row.get("themes", "").split(",") if x.strip()]
    desc = normalize(row.get("business_description", ""))

    pe = parse_float(row, "pe_ratio", default=999)
    ps = parse_float(row, "ps_ratio", default=999)
    short_interest = parse_float(row, "short_interest", default=0)
    rg = parse_float(row, "revenue_growth", default=0)
    market_cap = parse_float(row, "market_cap", default=0)

    hype = 20.0
    reasons: List[str] = []

    mania_hits = 0
    for t in themes:
        if t in THEME_MANIA_TERMS:
            mania_hits += 1
    for t in THEME_MANIA_TERMS:
        if t in desc:
            mania_hits += 1

    if mania_hits >= 2:
        hype += 20
        reasons.append("theme concentration")
    elif mania_hits == 1:
        hype += 10

    if pe >= 60 or ps >= 15:
        hype += 20
        reasons.append("valuation disconnected")

    if short_interest >= 15:
        hype += 10
    if short_interest >= 25:
        hype += 10
        reasons.append("extreme short interest")

    if rg < 5 and (pe >= 40 or ps >= 10):
        hype += 15
        reasons.append("weak growth vs high multiples")

    if market_cap < 2_000_000_000 and mania_hits > 0:
        hype += 10
        reasons.append("small-cap thematic risk")

    return max(0.0, min(100.0, hype)), reasons


def map_label_and_decision(value_score: float, hype_score: float) -> Tuple[str, str]:
    net = value_score - 0.9 * hype_score

    if net >= 35 and value_score >= 65:
        return "undervalued", "buy"
    if net >= 18:
        return "fairly valued", "watch"
    if net >= 5:
        return "overvalued", "reduce"
    return "overvalued", "sell"


def evaluate_stock(row: Dict[str, str]) -> StockResult:
    ticker = row.get("ticker", "UNKNOWN").strip().upper()
    name = row.get("name", "").strip()

    sector = classify_sector(row)
    value_score, value_reasons = score_value(row)
    hype_score, hype_reasons = score_hype(row)
    label, decision = map_label_and_decision(value_score, hype_score)

    reasons = []
    if value_reasons:
        reasons.append("value: " + ", ".join(value_reasons))
    if hype_reasons:
        reasons.append("hype: " + ", ".join(hype_reasons))

    return StockResult(
        ticker=ticker,
        name=name,
        sector=sector,
        value_score=round(value_score, 1),
        hype_score=round(hype_score, 1),
        valuation_label=label,
        decision=decision,
        reasons=reasons,
    )


def load_rows(csv_path: Path) -> List[Dict[str, str]]:
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows = []
        for r in reader:
            rows.append({k.strip().lower(): (v or "") for k, v in r.items()})
        return rows


def print_table(results: List[StockResult]) -> None:
    headers = [
        "Ticker",
        "Sector",
        "Value",
        "Hype",
        "Label",
        "Decision",
    ]
    rows = [
        [
            r.ticker,
            r.sector,
            f"{r.value_score:.1f}",
            f"{r.hype_score:.1f}",
            r.valuation_label,
            r.decision,
        ]
        for r in results
    ]

    widths = [len(h) for h in headers]
    for row in rows:
        for i, col in enumerate(row):
            widths[i] = max(widths[i], len(col))

    def fmt(row: List[str]) -> str:
        return " | ".join(col.ljust(widths[i]) for i, col in enumerate(row))

    print(fmt(headers))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(fmt(row))


def save_json(results: List[StockResult], path: Path) -> None:
    payload = [
        {
            "ticker": r.ticker,
            "name": r.name,
            "sector": r.sector,
            "value_score": r.value_score,
            "hype_score": r.hype_score,
            "valuation_label": r.valuation_label,
            "decision": r.decision,
            "reasons": r.reasons,
        }
        for r in results
    ]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Classify stock sectors and score undervalued vs overvalued stocks."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/sample_stocks.csv"),
        help="Input CSV file path",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=None,
        help="Optional JSON output path",
    )
    parser.add_argument(
        "--min-confidence-buy",
        type=float,
        default=65.0,
        help="Reserved threshold for integration. Current rules already apply robust default thresholds.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input file not found: {args.input}")

    rows = load_rows(args.input)
    results = [evaluate_stock(row) for row in rows]

    decision_rank = {"buy": 0, "watch": 1, "reduce": 2, "sell": 3}
    results.sort(key=lambda r: (decision_rank.get(r.decision, 99), -r.value_score, r.hype_score))

    print_table(results)
    print("\nDetailed reasons")
    for r in results:
        print(f"- {r.ticker}: {'; '.join(r.reasons) if r.reasons else 'no strong flags'}")

    if args.json_output:
        save_json(results, args.json_output)
        print(f"\nSaved JSON result: {args.json_output}")


if __name__ == "__main__":
    main()
