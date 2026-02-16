if (typeof window !== "undefined" && window.__stockBoot) {
  window.__stockBoot.appLoaded = true;
  const diag = document.getElementById("bootDiagnostics");
  if (diag) {
    diag.textContent = "app 스크립트 로드됨, 초기화 중...";
    diag.dataset.level = "info";
  }
}

const SECTOR_KEYWORDS = {
  Technology: ["software", "cloud", "ai", "semiconductor", "chip", "cybersecurity", "saas"],
  Robotics: ["robot", "automation", "factory", "autonomous", "industrial arm"],
  Financials: [
    "bank",
    "insurance",
    "asset management",
    "payment",
    "fintech",
    "stablecoin",
    "exchange",
    "lending",
  ],
  Healthcare: ["biotech", "pharma", "medical", "drug", "diagnostic"],
  Energy: ["oil", "gas", "renewable", "battery", "solar", "utility"],
  Consumer: ["retail", "e-commerce", "consumer", "food", "beverage", "apparel"],
  Industrials: ["construction", "machinery", "logistics", "aerospace", "defense", "manufacturing"],
};

const THEME_MANIA_TERMS = new Set([
  "stablecoin",
  "robotics",
  "ai",
  "metaverse",
  "quantum",
  "meme",
  "token",
  "crypto",
  "blockchain",
]);

const SECTOR_TECH_KEYWORDS = {
  반도체: "반도체, HBM, AI 칩, 파운드리",
  AI: "ai, llm, inference, cloud, gpu",
  원자력: "nuclear, smr, reactor, power plant, uranium",
  휴머노이드: "humanoid robot, robot actuator, motion control, computer vision",
  Semiconductors: "semiconductor, hbm, ai chip, foundry",
  자동차: "전기차, 자율주행, 배터리, 모빌리티",
  로보틱스: "robotics, automation, computer vision, ai",
  Robotics: "robotics, automation, machine vision, ai",
  인터넷플랫폼: "플랫폼, AI 서비스, 광고, 클라우드",
  Technology: "ai, cloud, software, platform",
  Finance: "digital finance, payment, risk management, fintech",
  Financials: "digital finance, payment, risk management, fintech",
  바이오: "바이오, 신약개발, 임상, 항체",
  Healthcare: "biotech, drug discovery, clinical trial, antibody",
  "2차전지": "2차전지, 배터리 소재, 에너지 저장",
  Energy: "renewable, battery, grid, energy transition",
  증권: "brokerage, capital market, trading volume, investment banking, wealth management",
  IT서비스: "system integration, enterprise software, cloud service, fintech platform, payment infra",
};

const COMPANY_SECTOR_HINTS = [
  { terms: ["엔씨소프트", "카카오게임즈", "넷마블", "크래프톤", "펄어비스", "게임", "gaming", "videogame"], sector: "게임/콘텐츠" },
  { terms: ["카카오뱅크", "토스뱅크", "케이뱅크", "인터넷은행", "bank"], sector: "금융" },
  { terms: ["sfa반도체", "sfa 반도체", "한미반도체", "리노공업"], sector: "반도체" },
  { terms: ["두산에너빌리티", "한전기술", "한전kps", "원전", "원자력"], sector: "원자력" },
  { terms: ["레인보우로보틱스", "두산로보틱스", "휴머노이드", "robot"], sector: "휴머노이드" },
  { terms: ["naver", "google", "alphabet", "meta", "openai", "microsoft"], sector: "AI" },
  { terms: ["반도체", "semiconductor"], sector: "반도체" },
  { terms: ["삼성전자", "sk하이닉스", "하이닉스", "nvidia", "amd", "tsm"], sector: "반도체" },
  { terms: ["현대차", "기아", "tesla", "toyota", "현대모비스", "한온시스템", "만도", "hl만도"], sector: "자동차" },
  { terms: ["sk증권", "미래에셋증권", "키움증권", "삼성증권", "nh투자증권", "한국금융지주", "메리츠금융지주", "증권"], sector: "증권" },
  { terms: ["한화생명", "삼성생명", "신한지주", "kb금융", "하나금융"], sector: "금융" },
  { terms: ["소프트센", "삼성에스디에스", "현대오토에버", "카카오페이", "lg씨엔에스", "it서비스", "si"], sector: "IT서비스" },
  { terms: ["한화솔루션", "lg화학", "롯데케미칼", "금양"], sector: "화학" },
  { terms: ["한전산업", "한전kps", "한국전력"], sector: "에너지" },
  { terms: ["보스턴다이나믹스"], sector: "휴머노이드" },
  { terms: ["인터넷플랫폼", "technology"], sector: "인터넷플랫폼" },
];

const COMPANY_TECH_KEYWORDS = {
  "005930": "semiconductor, hbm, ai chip, foundry, memory",
  "000660": "hbm, dram, nand, semiconductor packaging",
  "036540": "semiconductor equipment, display equipment, chip packaging, automation",
  "005380": "electric vehicle, autonomous driving, software-defined vehicle, mobility platform",
  "000270": "electric vehicle, autonomous driving, battery management, mobility",
  "018880": "automotive thermal management, electric compressor, heat pump, hvac, mobility",
  "088350": "insurtech, actuarial analytics, digital underwriting, risk management",
  "009830": "solar pv, energy materials, hydrogen, battery materials, petrochemical",
  "130660": "power plant maintenance, grid monitoring, predictive maintenance, energy efficiency",
  "373220": "battery cell, battery pack, energy storage system, bms",
  "006400": "battery materials, cathode, all-solid-state battery, energy storage",
};

const KEYWORD_RELATED_SECTORS = [
  { terms: ["현대차", "기아", "hyundai", "kia"], sectors: ["자동차", "휴머노이드"] },
  { terms: ["전기차", "ev", "모빌리티"], sectors: ["자동차", "2차전지"] },
  { terms: ["자율주행", "autonomous"], sectors: ["자동차", "휴머노이드"] },
  { terms: ["배터리", "이차전지", "2차전지", "battery"], sectors: ["2차전지", "자동차"] },
  { terms: ["로봇", "robot", "robotics", "automation"], sectors: ["휴머노이드", "자동차"] },
  { terms: ["반도체", "hbm", "ai칩", "ai chip", "semiconductor"], sectors: ["반도체", "휴머노이드"] },
  { terms: ["원자력", "원전", "nuclear", "smr"], sectors: ["원자력", "에너지"] },
  { terms: ["휴머노이드", "humanoid"], sectors: ["휴머노이드", "AI"] },
  { terms: ["ai", "인공지능", "llm", "foundation model"], sectors: ["AI", "반도체"] },
  { terms: ["증권", "securities", "broker", "brokerage", "capital market"], sectors: ["증권", "금융"] },
  { terms: ["it서비스", "it service", "software", "si", "system integration"], sectors: ["IT서비스", "AI"] },
];

const els = {
  navIntelBtn: document.getElementById("navIntelBtn"),
  navAutoBtn: document.getElementById("navAutoBtn"),
  intelPage: document.getElementById("intelPage"),
  autoPage: document.getElementById("autoPage"),
  csvFile: document.getElementById("csvFile"),
  csvText: document.getElementById("csvText"),
  analyzeBtn: document.getElementById("analyzeBtn"),
  loadSampleBtn: document.getElementById("loadSampleBtn"),
  exportBtn: document.getElementById("exportBtn"),
  resultMeta: document.getElementById("resultMeta"),
  summaryCards: document.getElementById("summaryCards"),
  resultTableBody: document.querySelector("#resultTable tbody"),
  reasonList: document.getElementById("reasonList"),
  intelMeta: document.getElementById("intelMeta"),
  intelTicker: document.getElementById("intelTicker"),
  intelMarket: document.getElementById("intelMarket"),
  intelSummaryCard: document.getElementById("intelSummaryCard"),
  decisionPanelCard: document.getElementById("decisionPanelCard"),
  relativeComparisonCard: document.getElementById("relativeComparisonCard"),
  scenarioAnalyzerCard: document.getElementById("scenarioAnalyzerCard"),
  prefHorizon: document.getElementById("prefHorizon"),
  prefRisk: document.getElementById("prefRisk"),
  feedIntensity: document.getElementById("feedIntensity"),
  scenarioFx: document.getElementById("scenarioFx"),
  scenarioEv: document.getElementById("scenarioEv"),
  scenarioFxText: document.getElementById("scenarioFxText"),
  scenarioEvText: document.getElementById("scenarioEvText"),
  spotlightQuery: document.getElementById("spotlightQuery"),
  spotlightSearchBtn: document.getElementById("spotlightSearchBtn"),
  companyQuery: document.getElementById("companyQuery"),
  searchCompanyBtn: document.getElementById("searchCompanyBtn"),
  sectorSelect: document.getElementById("sectorSelect"),
  loadSectorBtn: document.getElementById("loadSectorBtn"),
  techQuery: document.getElementById("techQuery"),
  loadIntelBtn: document.getElementById("loadIntelBtn"),
  quoteCard: document.getElementById("quoteCard"),
  fundamentalCard: document.getElementById("fundamentalCard"),
  valuationExplainCard: document.getElementById("valuationExplainCard"),
  newsSourceFilter: document.getElementById("newsSourceFilter"),
  filingFormFilter: document.getElementById("filingFormFilter"),
  newsList: document.getElementById("newsList"),
  filingList: document.getElementById("filingList"),
  techList: document.getElementById("techList"),
  relatedStocksList: document.getElementById("relatedStocksList"),
  relatedSectorChips: document.getElementById("relatedSectorChips"),
  relatedPrevBtn: document.getElementById("relatedPrevBtn"),
  relatedNextBtn: document.getElementById("relatedNextBtn"),
  sectorCompareCard: document.getElementById("sectorCompareCard"),
  sectorCompareMeta: document.getElementById("sectorCompareMeta"),
  sectorCompareSelected: document.getElementById("sectorCompareSelected"),
  sectorCompareTabs: document.getElementById("sectorCompareTabs"),
  sectorCompareBody: document.getElementById("sectorCompareBody"),
  autoMeta: document.getElementById("autoMeta"),
  userId: document.getElementById("userId"),
  watchTicker: document.getElementById("watchTicker"),
  watchMarket: document.getElementById("watchMarket"),
  addWatchBtn: document.getElementById("addWatchBtn"),
  priceThreshold: document.getElementById("priceThreshold"),
  hypeThreshold: document.getElementById("hypeThreshold"),
  filingEnabled: document.getElementById("filingEnabled"),
  notifyEmail: document.getElementById("notifyEmail"),
  notifyWebhook: document.getElementById("notifyWebhook"),
  onesignalExternalId: document.getElementById("onesignalExternalId"),
  pushEnabled: document.getElementById("pushEnabled"),
  saveChannelsBtn: document.getElementById("saveChannelsBtn"),
  testNotifyBtn: document.getElementById("testNotifyBtn"),
  saveRulesBtn: document.getElementById("saveRulesBtn"),
  scanNowBtn: document.getElementById("scanNowBtn"),
  refreshRankingBtn: document.getElementById("refreshRankingBtn"),
  refreshAutoBtn: document.getElementById("refreshAutoBtn"),
  watchlistView: document.getElementById("watchlistView"),
  notificationView: document.getElementById("notificationView"),
  rankingView: document.getElementById("rankingView"),
  sectorView: document.getElementById("sectorView"),
  summaryCompanyName: document.getElementById("summaryCompanyName"),
  summaryTickerMarket: document.getElementById("summaryTickerMarket"),
  summaryCurrentPrice: document.getElementById("summaryCurrentPrice"),
  summaryChange: document.getElementById("summaryChange"),
  summarySignal: document.getElementById("summarySignal"),
  summaryAssumptionBadge: document.getElementById("summaryAssumptionBadge"),
  summaryUpdatedAt: document.getElementById("summaryUpdatedAt"),
  mobileViewSwitch: document.getElementById("mobileViewSwitch"),
  mobileViewCoreBtn: document.getElementById("mobileViewCoreBtn"),
  mobileViewDetailBtn: document.getElementById("mobileViewDetailBtn"),
  mobileViewFeedBtn: document.getElementById("mobileViewFeedBtn"),
  headerWatchToggleBtn: document.getElementById("headerWatchToggleBtn"),
  headerAlertSetupBtn: document.getElementById("headerAlertSetupBtn"),
  headerShareBtn: document.getElementById("headerShareBtn"),
  scenarioPresetConservativeBtn: document.getElementById("scenarioPresetConservativeBtn"),
  scenarioPresetBaseBtn: document.getElementById("scenarioPresetBaseBtn"),
  scenarioPresetAggressiveBtn: document.getElementById("scenarioPresetAggressiveBtn"),
  scenarioResetBtn: document.getElementById("scenarioResetBtn"),
  newsKeywordFilter: document.getElementById("newsKeywordFilter"),
  newsSentimentFilter: document.getElementById("newsSentimentFilter"),
  newsMoreBtn: document.getElementById("newsMoreBtn"),
  filingMoreBtn: document.getElementById("filingMoreBtn"),
  techMoreBtn: document.getElementById("techMoreBtn"),
  emailValidation: document.getElementById("emailValidation"),
  webhookValidation: document.getElementById("webhookValidation"),
  confirmModal: document.getElementById("confirmModal"),
  confirmMessage: document.getElementById("confirmMessage"),
  confirmCancelBtn: document.getElementById("confirmCancelBtn"),
  confirmOkBtn: document.getElementById("confirmOkBtn"),
  loadingOverlay: document.getElementById("loadingOverlay"),
  loadingOverlayText: document.getElementById("loadingOverlayText"),
};

let latestResults = [];
let sectorSeedCache = null;
let latestHistory3M = [];
let historyPeriod = "1mo";
let latestQuoteData = null;
let latestDecisionTicker = "";
let latestDecisionMarket = "US";
let loadingOverlayCount = 0;
let loadingOverlayTimer = null;
let latestNewsData = { ok: false, items: [] };
let latestFilingData = { ok: false, items: [] };
let latestTechData = { ok: false, items: [] };
let latestWatchlistItems = [];
let newsExpanded = false;
let filingExpanded = false;
let techExpanded = false;
let assumptionChanged = false;
let pendingConfirmAction = null;
let currentMobileView = "core";
let currentCompareTab = "core";
let compareSelection = [];
const sectorStocksCache = new Map();
const compareDataCache = new Map();
const peerQuoteCache = new Map();

const FEED_INTENSITY_CONFIG = {
  light: { newsDays: 5, newsLimit: 15, filingLimit: 10, techLimit: 8 },
  standard: { newsDays: 7, newsLimit: 30, filingLimit: 20, techLimit: 16 },
  deep: { newsDays: 14, newsLimit: 60, filingLimit: 40, techLimit: 32 },
};

function normalize(value) {
  return (value || "").trim().toLowerCase();
}

function parseFloatSafe(value, defaultValue = 0) {
  const text = String(value ?? "")
    .replaceAll(",", "")
    .trim();
  if (!text) return defaultValue;
  const n = Number.parseFloat(text);
  return Number.isFinite(n) ? n : defaultValue;
}

function getFeedIntensity() {
  const raw = String(els.feedIntensity?.value || "standard").trim().toLowerCase();
  if (raw === "light" || raw === "deep" || raw === "standard") return raw;
  return "standard";
}

function getFeedConfig() {
  return FEED_INTENSITY_CONFIG[getFeedIntensity()] || FEED_INTENSITY_CONFIG.standard;
}

function parseSpotlightInput(rawText) {
  const raw = String(rawText || "").trim();
  let market = "";
  let sector = "";
  let text = raw;
  const marketMatch = text.match(/(?:^|\s)m(?:arket)?\s*:\s*(US|KR|ALL)(?=\s|$)/i);
  if (marketMatch) {
    market = String(marketMatch[1] || "").toUpperCase();
    text = text.replace(marketMatch[0], " ").trim();
  }
  const sectorMatch = text.match(/(?:^|\s)s(?:ector)?\s*:\s*([^\s]+)/i);
  if (sectorMatch) {
    sector = String(sectorMatch[1] || "").trim();
    text = text.replace(sectorMatch[0], " ").trim();
  }
  text = text.replace(/\s+/g, " ").trim();
  return { market, sector, query: text };
}

function applySpotlightToInputs(rawText) {
  const parsed = parseSpotlightInput(rawText);
  if (parsed.market && els.intelMarket) {
    els.intelMarket.value = parsed.market;
  }
  if (parsed.sector && els.sectorSelect) {
    const options = Array.from(els.sectorSelect.options || []).map((o) => o.value);
    if (!options.includes(parsed.sector)) {
      const option = document.createElement("option");
      option.value = parsed.sector;
      option.textContent = parsed.sector;
      els.sectorSelect.appendChild(option);
    }
    els.sectorSelect.value = parsed.sector;
  }
  if (els.companyQuery && (parsed.query || rawText)) {
    els.companyQuery.value = parsed.query;
  }
  return parsed;
}

function parseCSV(text) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    const next = text[i + 1];

    if (inQuotes) {
      if (ch === '"' && next === '"') {
        field += '"';
        i += 1;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        field += ch;
      }
      continue;
    }

    if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
    } else if (ch === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
    } else if (ch === "\r") {
      continue;
    } else {
      field += ch;
    }
  }

  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }

  if (rows.length === 0) return [];

  const headers = rows[0].map((h) => normalize(h));
  const mapped = [];
  for (let i = 1; i < rows.length; i += 1) {
    const vals = rows[i];
    if (vals.every((v) => !String(v).trim())) continue;
    const rec = {};
    headers.forEach((h, idx) => {
      rec[h] = vals[idx] ?? "";
    });
    mapped.push(rec);
  }

  return mapped;
}

function classifySector(row) {
  const text = [row.name, row.business_description, row.themes].map(normalize).join(" ");
  let bestSector = "Unclassified";
  let bestScore = 0;

  Object.entries(SECTOR_KEYWORDS).forEach(([sector, terms]) => {
    let score = 0;
    terms.forEach((term) => {
      if (text.includes(term)) score += 1;
    });
    if (score > bestScore) {
      bestScore = score;
      bestSector = sector;
    }
  });

  return bestSector;
}

function scoreValue(row) {
  const pe = parseFloatSafe(row.pe_ratio, 999);
  const pb = parseFloatSafe(row.pb_ratio, 999);
  const ps = parseFloatSafe(row.ps_ratio, 999);
  const dte = parseFloatSafe(row.debt_to_equity, 999);
  const roe = parseFloatSafe(row.roe, -999);
  const rg = parseFloatSafe(row.revenue_growth, -999);
  const nig = parseFloatSafe(row.net_income_growth, -999);
  const fcf = parseFloatSafe(row.fcf_margin, -999);
  const cash = parseFloatSafe(row.cash_ratio, -999);
  const insider = parseFloatSafe(row.insider_buy_ratio, 0);

  let score = 50;
  const reasons = [];

  if (pe <= 12) {
    score += 12;
    reasons.push("low P/E");
  } else if (pe <= 20) {
    score += 5;
  } else if (pe >= 45) {
    score -= 12;
    reasons.push("very high P/E");
  }

  if (pb <= 1.5) {
    score += 10;
    reasons.push("low P/B");
  } else if (pb >= 5) {
    score -= 10;
    reasons.push("high P/B");
  }

  if (ps <= 2) {
    score += 8;
  } else if (ps >= 12) {
    score -= 10;
    reasons.push("high P/S");
  }

  if (dte <= 0.7) {
    score += 8;
  } else if (dte >= 2) {
    score -= 10;
    reasons.push("high leverage");
  }

  if (roe >= 15) {
    score += 8;
  } else if (roe < 0) {
    score -= 8;
  }

  if (rg >= 10) {
    score += 6;
  } else if (rg < 0) {
    score -= 8;
    reasons.push("shrinking revenue");
  }

  if (nig >= 10) {
    score += 6;
  } else if (nig < 0) {
    score -= 10;
    reasons.push("shrinking earnings");
  }

  if (fcf >= 10) {
    score += 8;
  } else if (fcf < 0) {
    score -= 8;
  }

  if (cash >= 1) {
    score += 4;
  } else if (cash < 0.5) {
    score -= 4;
  }

  if (insider >= 0.02) {
    score += 4;
    reasons.push("insider buying");
  }

  return { score: Math.max(0, Math.min(100, score)), reasons };
}

function scoreHype(row) {
  const themes = String(row.themes || "")
    .split(",")
    .map((x) => normalize(x))
    .filter(Boolean);
  const desc = normalize(row.business_description);

  const pe = parseFloatSafe(row.pe_ratio, 999);
  const ps = parseFloatSafe(row.ps_ratio, 999);
  const shortInterest = parseFloatSafe(row.short_interest, 0);
  const rg = parseFloatSafe(row.revenue_growth, 0);
  const marketCap = parseFloatSafe(row.market_cap, 0);

  let hype = 20;
  const reasons = [];

  let maniaHits = 0;
  themes.forEach((t) => {
    if (THEME_MANIA_TERMS.has(t)) maniaHits += 1;
  });
  THEME_MANIA_TERMS.forEach((t) => {
    if (desc.includes(t)) maniaHits += 1;
  });

  if (maniaHits >= 2) {
    hype += 20;
    reasons.push("theme concentration");
  } else if (maniaHits === 1) {
    hype += 10;
  }

  if (pe >= 60 || ps >= 15) {
    hype += 20;
    reasons.push("valuation disconnected");
  }

  if (shortInterest >= 15) hype += 10;
  if (shortInterest >= 25) {
    hype += 10;
    reasons.push("extreme short interest");
  }

  if (rg < 5 && (pe >= 40 || ps >= 10)) {
    hype += 15;
    reasons.push("weak growth vs high multiples");
  }

  if (marketCap < 2_000_000_000 && maniaHits > 0) {
    hype += 10;
    reasons.push("small-cap thematic risk");
  }

  return { score: Math.max(0, Math.min(100, hype)), reasons };
}

function mapLabelAndDecision(valueScore, hypeScore) {
  const net = valueScore - 0.9 * hypeScore;

  if (net >= 35 && valueScore >= 65) return { label: "undervalued", decision: "buy" };
  if (net >= 18) return { label: "fairly valued", decision: "watch" };
  if (net >= 5) return { label: "overvalued", decision: "reduce" };
  return { label: "overvalued", decision: "sell" };
}

function evaluateStock(row) {
  const ticker = String(row.ticker || "UNKNOWN").trim().toUpperCase();
  const name = String(row.name || "").trim();

  const sector = classifySector(row);
  const valueResult = scoreValue(row);
  const hypeResult = scoreHype(row);
  const decision = mapLabelAndDecision(valueResult.score, hypeResult.score);

  const reasons = [];
  if (valueResult.reasons.length > 0) {
    reasons.push(`value: ${valueResult.reasons.join(", ")}`);
  }
  if (hypeResult.reasons.length > 0) {
    reasons.push(`hype: ${hypeResult.reasons.join(", ")}`);
  }

  return {
    ticker,
    name,
    sector,
    value_score: Number(valueResult.score.toFixed(1)),
    hype_score: Number(hypeResult.score.toFixed(1)),
    valuation_label: decision.label,
    decision: decision.decision,
    reasons,
  };
}

function getDecisionRank(decision) {
  const rank = { buy: 0, watch: 1, reduce: 2, sell: 3 };
  return rank[decision] ?? 99;
}

function renderSummary(results) {
  if (!els.summaryCards) return;
  const counts = { buy: 0, watch: 0, reduce: 0, sell: 0 };
  const sectors = {};

  results.forEach((r) => {
    counts[r.decision] = (counts[r.decision] || 0) + 1;
    sectors[r.sector] = (sectors[r.sector] || 0) + 1;
  });

  const topSector = Object.entries(sectors).sort((a, b) => b[1] - a[1])[0] || ["-", 0];

  const cards = [
    { k: "총 종목", v: String(results.length) },
    { k: "BUY", v: String(counts.buy) },
    { k: "SELL", v: String(counts.sell) },
    { k: "최다 섹터", v: `${topSector[0]} (${topSector[1]})` },
  ];

  els.summaryCards.innerHTML = cards
    .map((c) => `<div class="card"><span class="k">${c.k}</span><span class="v">${c.v}</span></div>`)
    .join("");
}

function renderTable(results) {
  if (!els.resultTableBody) return;
  els.resultTableBody.innerHTML = results
    .map(
      (r) => `<tr>
        <td>${r.ticker}</td>
        <td>${r.sector}</td>
        <td>${r.value_score.toFixed(1)}</td>
        <td>${r.hype_score.toFixed(1)}</td>
        <td>${r.valuation_label}</td>
        <td><span class="badge ${r.decision}">${r.decision}</span></td>
      </tr>`
    )
    .join("");
}

function renderReasons(results) {
  if (!els.reasonList) return;
  els.reasonList.innerHTML = results
    .map((r) => {
      const reasonText = r.reasons.length ? r.reasons.join("; ") : "no strong flags";
      return `<li><strong>${r.ticker}</strong>: ${reasonText}</li>`;
    })
    .join("");
}

function runAnalysis(csvText) {
  if (!els.resultMeta || !els.exportBtn) return;
  const rows = parseCSV(csvText);
  if (!rows.length) {
    throw new Error("CSV 데이터가 비어 있거나 형식이 잘못되었습니다.");
  }

  const results = rows.map((row) => evaluateStock(row));
  results.sort((a, b) => {
    const byDecision = getDecisionRank(a.decision) - getDecisionRank(b.decision);
    if (byDecision !== 0) return byDecision;
    if (a.value_score !== b.value_score) return b.value_score - a.value_score;
    return a.hype_score - b.hype_score;
  });

  latestResults = results;
  localStorage.setItem("stock_csv_input", csvText);

  renderSummary(results);
  renderTable(results);
  renderReasons(results);

  if (!els.intelTicker.value && results.length > 0) {
    els.intelTicker.value = results[0].ticker;
    els.techQuery.value = results[0].sector;
  }

  els.resultMeta.textContent = `${results.length}개 종목 분석 완료`;
  els.exportBtn.disabled = false;
}

async function loadSample() {
  const res = await fetch("../data/sample_stocks.csv", { cache: "no-store" });
  if (!res.ok) {
    throw new Error("샘플 데이터를 불러오지 못했습니다.");
  }
  const txt = await res.text();
  if (els.csvText) els.csvText.value = txt;
}

async function handleFileSelect(ev) {
  const file = ev.target.files?.[0];
  if (!file) return;
  const txt = await file.text();
  if (els.csvText) els.csvText.value = txt;
}

function exportResults() {
  if (!latestResults.length) return;
  const blob = new Blob([JSON.stringify(latestResults, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  const today = new Date().toISOString().slice(0, 10);
  a.href = url;
  a.download = `stock_decisions_${today}.json`;
  a.click();
  URL.revokeObjectURL(url);
}

function escapeHtml(text) {
  return String(text ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function marketLabel(market) {
  const m = String(market || "US").toUpperCase();
  if (m === "KR") return "한국";
  if (m === "US") return "미국";
  if (m === "ALL") return "전체(미국+한국)";
  return m;
}

function rankLabelKo(label) {
  const key = String(label || "").trim();
  const map = {
    "Strong Undervalued Quality": "강한 저평가 우량주",
    "Buy Candidate": "매수 후보",
    "Fair / Watch": "적정가 관찰",
    "Weak / Overvalued": "고평가 주의",
    Error: "평가 오류",
  };
  return map[key] || key || "-";
}

function formatSignedNumber(value, digits = 2) {
  const n = Number.parseFloat(String(value ?? ""));
  if (!Number.isFinite(n)) return "-";
  const abs = Math.abs(n).toFixed(digits);
  if (n > 0) return `+${abs}`;
  if (n < 0) return `-${abs}`;
  return abs;
}

function displayValue(value, fallback = "-") {
  if (value === null || value === undefined) return fallback;
  const text = String(value).trim();
  return text ? text : fallback;
}

function formatPriceInt(value, fallback = "-") {
  const n = Number.parseFloat(String(value ?? "").replaceAll(",", ""));
  if (!Number.isFinite(n)) return fallback;
  return Math.round(n).toLocaleString("ko-KR");
}

function currencyUnitForMarket(market) {
  const m = String(market || latestDecisionMarket || "US").toUpperCase();
  return m === "KR" ? "원" : "달러";
}

function formatPriceWithUnit(value, market, fallback = "-") {
  const p = formatPriceInt(value, fallback);
  if (p === fallback) return fallback;
  return `${p} ${currencyUnitForMarket(market)}`;
}

function showLoadingOverlay(message = "조회 중...") {
  loadingOverlayCount += 1;
  if (loadingOverlayTimer) {
    clearTimeout(loadingOverlayTimer);
    loadingOverlayTimer = null;
  }
  if (els.loadingOverlayText) {
    els.loadingOverlayText.textContent = String(message || "조회 중...");
  }
  if (els.loadingOverlay) {
    els.loadingOverlay.classList.add("show");
    els.loadingOverlay.setAttribute("aria-hidden", "false");
  }
  // Failsafe: avoid permanent blocked UI when one async request hangs.
  loadingOverlayTimer = setTimeout(() => {
    loadingOverlayCount = 0;
    if (els.loadingOverlay) {
      els.loadingOverlay.classList.remove("show");
      els.loadingOverlay.setAttribute("aria-hidden", "true");
    }
    loadingOverlayTimer = null;
  }, 45000);
}

function hideLoadingOverlay() {
  loadingOverlayCount = Math.max(0, loadingOverlayCount - 1);
  if (loadingOverlayCount > 0) return;
  if (loadingOverlayTimer) {
    clearTimeout(loadingOverlayTimer);
    loadingOverlayTimer = null;
  }
  if (els.loadingOverlay) {
    els.loadingOverlay.classList.remove("show");
    els.loadingOverlay.setAttribute("aria-hidden", "true");
  }
}

function nowStamp() {
  const d = new Date();
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")} ${hh}:${mm}`;
}

function markAssumptionChangedUI(changed) {
  const on = !!changed;
  if (els.summaryAssumptionBadge) els.summaryAssumptionBadge.hidden = !on;
  if (els.decisionPanelCard) els.decisionPanelCard.classList.toggle("assumption-changed", on);
  if (els.scenarioAnalyzerCard) els.scenarioAnalyzerCard.classList.toggle("assumption-changed", on);
}

function summarizeSignalsForHeader(payload) {
  const signals = payload?.decision_panel?.signals || {};
  const pick = signals.mid || signals.short || signals.long || {};
  const label = String(pick.label || "중립");
  const score = Number(pick.score || 0).toFixed(1);
  return `핵심 신호: ${label} (${score})`;
}

function updateStockHeaderSummary({ ticker, market, name, quoteData, decisionData }) {
  const company = String(name || quoteData?.name || ticker || "종목 선택 대기");
  const mk = String(market || latestDecisionMarket || "US").toUpperCase();
  if (els.summaryCompanyName) els.summaryCompanyName.textContent = company;
  if (els.summaryTickerMarket) els.summaryTickerMarket.textContent = `${ticker || "-"} | ${marketLabel(mk)}`;
  const cur = quoteData?.ok ? formatPriceWithUnit(quoteData.current_price, mk) : "-";
  if (els.summaryCurrentPrice) els.summaryCurrentPrice.textContent = cur;
  const pct = quoteData?.ok ? formatSignedNumber(quoteData.percent_change, 0) : "-";
  if (els.summaryChange) {
    els.summaryChange.textContent = pct === "-" ? "-" : `전일 대비 ${pct}%`;
    els.summaryChange.className = pct.startsWith("+")
      ? "change-positive"
      : pct.startsWith("-")
        ? "change-negative"
        : "change-neutral";
  }
  if (els.summarySignal) {
    els.summarySignal.textContent = decisionData ? summarizeSignalsForHeader(decisionData) : "핵심 신호: 조회 전";
  }
  if (els.summaryUpdatedAt) {
    els.summaryUpdatedAt.textContent = `마지막 업데이트: ${nowStamp()}`;
  }
}

function classifySentimentFromText(text) {
  const t = String(text || "").toLowerCase();
  const posTerms = ["상승", "호재", "수주", "실적 개선", "성장", "upgrade", "beat", "surge", "gain"];
  const negTerms = ["하락", "악재", "적자", "규제", "소송", "downgrade", "miss", "drop", "fall"];
  if (posTerms.some((k) => t.includes(k))) return "positive";
  if (negTerms.some((k) => t.includes(k))) return "negative";
  return "neutral";
}

function extractTags(text) {
  const t = String(text || "").toLowerCase();
  const map = [
    { key: "실적", tag: "실적" },
    { key: "가이던스", tag: "가이던스" },
    { key: "규제", tag: "규제" },
    { key: "공시", tag: "공시" },
    { key: "소송", tag: "법무" },
    { key: "인수", tag: "M&A" },
    { key: "배당", tag: "배당" },
    { key: "파트너", tag: "파트너십" },
  ];
  return map.filter((m) => t.includes(m.key.toLowerCase())).map((m) => m.tag).slice(0, 3);
}

function renderFeedSkeleton(element, count = 5) {
  if (!element) return;
  const rows = Array.from({ length: count })
    .map(() => `<li><div class="feed-skeleton"></div></li>`)
    .join("");
  element.classList.add("is-loading");
  element.innerHTML = rows;
}

function clearFeedSkeleton(element) {
  if (!element) return;
  element.classList.remove("is-loading");
}

function showConfirmModal(message, onConfirm) {
  pendingConfirmAction = typeof onConfirm === "function" ? onConfirm : null;
  if (els.confirmMessage) els.confirmMessage.textContent = message || "정말 진행하시겠습니까?";
  if (els.confirmModal) {
    els.confirmModal.classList.add("show");
    els.confirmModal.setAttribute("aria-hidden", "false");
  }
}

function hideConfirmModal() {
  pendingConfirmAction = null;
  if (els.confirmModal) {
    els.confirmModal.classList.remove("show");
    els.confirmModal.setAttribute("aria-hidden", "true");
  }
}

function validateNotificationInputs() {
  const email = String(els.notifyEmail?.value || "").trim();
  const webhook = String(els.notifyWebhook?.value || "").trim();
  const emailOk = !email || /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  const webhookOk = !webhook || /^https?:\/\//i.test(webhook);
  if (els.emailValidation) {
    els.emailValidation.textContent = email ? (emailOk ? "유효한 이메일 형식" : "이메일 형식이 올바르지 않습니다.") : "";
    els.emailValidation.style.color = email && !emailOk ? "#b3261e" : "#5f6c78";
  }
  if (els.webhookValidation) {
    els.webhookValidation.textContent = webhook ? (webhookOk ? "유효한 URL 형식" : "http:// 또는 https:// URL을 입력하세요.") : "";
    els.webhookValidation.style.color = webhook && !webhookOk ? "#b3261e" : "#5f6c78";
  }
  return emailOk && webhookOk;
}

function watchlistContains(ticker, market) {
  const t = String(ticker || "").toUpperCase();
  const m = String(market || "US").toUpperCase();
  return (latestWatchlistItems || []).some((x) => {
    const xm = String(x.market || "US").toUpperCase();
    const xt = xm === "KR" ? normalizeKRTicker(x.ticker) : String(x.ticker || "").toUpperCase();
    const tt = m === "KR" ? normalizeKRTicker(t) : t;
    return xm === m && xt === tt;
  });
}

function syncHeaderWatchButtonState() {
  if (!els.headerWatchToggleBtn) return;
  const ticker = String(els.intelTicker?.value || "").trim().toUpperCase();
  const market = String(els.intelMarket?.value || "US").toUpperCase();
  if (!ticker) {
    els.headerWatchToggleBtn.textContent = "관심종목 추가/제거";
    els.headerWatchToggleBtn.disabled = true;
    return;
  }
  const exists = watchlistContains(ticker, market);
  els.headerWatchToggleBtn.disabled = false;
  els.headerWatchToggleBtn.textContent = exists ? "관심종목 제거" : "관심종목 추가";
}

function isMobileViewport() {
  return true;
}

function setMobileView(view) {
  currentMobileView = ["core", "detail", "feed"].includes(view) ? view : "core";
  const items = document.querySelectorAll("[data-mobile-view-item]");
  items.forEach((node) => {
    const group = node.getAttribute("data-mobile-view-item");
    node.classList.toggle("mobile-hidden", group !== currentMobileView);
  });
  if (els.mobileViewSwitch) els.mobileViewSwitch.style.display = "flex";
  const tabs = [
    ["core", els.mobileViewCoreBtn],
    ["detail", els.mobileViewDetailBtn],
    ["feed", els.mobileViewFeedBtn],
  ];
  tabs.forEach(([name, btn]) => {
    if (!btn) return;
    const active = name === currentMobileView;
    btn.classList.toggle("secondary", active);
    btn.classList.toggle("ghost", !active);
    btn.setAttribute("aria-selected", active ? "true" : "false");
  });
}

function activatePage(page) {
  const target = page === "auto" ? "auto" : "intel";
  if (els.intelPage) els.intelPage.classList.toggle("is-active", target === "intel");
  if (els.autoPage) els.autoPage.classList.toggle("is-active", target === "auto");
  if (els.navIntelBtn) els.navIntelBtn.classList.toggle("active", target === "intel");
  if (els.navAutoBtn) els.navAutoBtn.classList.toggle("active", target === "auto");
  const nextHash = target === "auto" ? "#auto" : "#intel";
  if (location.hash !== nextHash) history.replaceState(null, "", nextHash);
}

function initPageTabs() {
  const byHash = String(location.hash || "").toLowerCase();
  activatePage(byHash === "#auto" ? "auto" : "intel");
  if (els.navIntelBtn) {
    els.navIntelBtn.addEventListener("click", () => activatePage("intel"));
  }
  if (els.navAutoBtn) {
    els.navAutoBtn.addEventListener("click", () => activatePage("auto"));
  }
  window.addEventListener("hashchange", () => {
    const h = String(location.hash || "").toLowerCase();
    activatePage(h === "#auto" ? "auto" : "intel");
  });
}

async function fetchApi(path) {
  const res = await fetch(path, { cache: "no-store" });
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = body?.error ? String(body.error) : JSON.stringify(body);
    } catch (_err) {
      try {
        detail = await res.text();
      } catch (_err2) {
        detail = "";
      }
    }
    throw new Error(`API ${res.status}${detail ? `: ${detail}` : ""}`);
  }
  return res.json();
}

async function fetchApiPost(path, body) {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body || {}),
  });
  if (!res.ok) throw new Error(`API ${res.status}`);
  return res.json();
}

async function loadProviderStatus() {
  try {
    const data = await fetchApi("/api/providers");
    if (!data.ok) return;
    const p = data.providers || {};
    const flags = [];
    if (p.finnhub?.configured) flags.push("Finnhub");
    if (p.alpha_vantage?.configured) flags.push("Alpha");
    if (p.dart?.configured) flags.push("DART");
    flags.push("Naver", "Yahoo", "SEC", "GoogleNews", "arXiv/Crossref");
    const mk = (data.allowed_markets || []).join("/");
    els.intelMeta.textContent = `연결(${mk}): ${flags.join(", ")}`;
  } catch (_err) {
    // no-op
  }
}

function renderQuoteCard(data) {
  if (!data.ok) {
    els.quoteCard.innerHTML = `<strong>실시간 시세</strong><div>${escapeHtml(data.error || "데이터 없음")}</div>`;
    return;
  }
  const market = String(data.market || latestDecisionMarket || "US").toUpperCase();
  const name = escapeHtml(data.name || data.ticker || "-");
  const change = formatSignedNumber(data.change, 0);
  const pct = formatSignedNumber(data.percent_change, 0);
  const pctText = pct === "-" ? "-" : `${pct}%`;
  const prevClose = formatPriceWithUnit(data.previous_close, market);
  els.quoteCard.innerHTML = `
    <div class="panel-head"><strong>실시간 시세</strong><span class="muted-sm">출처: ${escapeHtml(data.source)} · 단위: ${currencyUnitForMarket(market)}</span></div>
    <div>종목명: ${name}</div>
    <div>현재가: ${escapeHtml(formatPriceWithUnit(data.current_price, market))}</div>
    <div>등락(전일 종가 기준): ${change} (${pctText})</div>
    <div>전일 종가: ${escapeHtml(prevClose)}</div>
    <div>고가/저가: ${escapeHtml(formatPriceWithUnit(data.high, market))} / ${escapeHtml(formatPriceWithUnit(data.low, market))}</div>
    <div class="chart-head" style="margin-top:10px;">
      <strong>가격 추이</strong>
      <div class="chart-periods">
        <button class="chart-btn ${historyPeriod === "1mo" ? "active" : ""}" data-history-period="1mo">1개월</button>
        <button class="chart-btn ${historyPeriod === "3mo" ? "active" : ""}" data-history-period="3mo">3개월</button>
      </div>
    </div>
    <div id="priceHistoryChart" class="sparkline"></div>
    <div id="priceHistoryStats" class="chart-stats">1개월/3개월 최고·최저 계산 중...</div>
    <details style="margin-top:8px;">
      <summary class="muted-sm">이 차트의 해석 가이드</summary>
      <div class="muted-sm">빨간색은 기준선(조회 시작 시점) 상단, 파란색은 하단 구간입니다. 거래량 막대에 마우스를 올리면 날짜/종가/거래량을 확인할 수 있습니다.</div>
    </details>
  `;
}

function pickHistoryPoints(period) {
  if (!Array.isArray(latestHistory3M)) return [];
  if (period === "3mo") return latestHistory3M;
  const n = latestHistory3M.length;
  if (n <= 24) return latestHistory3M;
  return latestHistory3M.slice(Math.max(0, n - 24));
}

function historyMinMax(points) {
  const closes = (points || [])
    .map((p) => Number(p.close))
    .filter((v) => Number.isFinite(v));
  if (!closes.length) return { min: null, max: null };
  return { min: Math.min(...closes), max: Math.max(...closes) };
}

function renderHistoryStats() {
  const el = document.getElementById("priceHistoryStats");
  if (!el) return;
  const unit = currencyUnitForMarket(latestDecisionMarket);
  const p1 = pickHistoryPoints("1mo");
  const p3 = pickHistoryPoints("3mo");
  const s1 = historyMinMax(p1);
  const s3 = historyMinMax(p3);
  const one = s1.min == null ? "-" : `최고 ${formatPriceInt(s1.max)} ${unit} / 최저 ${formatPriceInt(s1.min)} ${unit}`;
  const three = s3.min == null ? "-" : `최고 ${formatPriceInt(s3.max)} ${unit} / 최저 ${formatPriceInt(s3.min)} ${unit}`;
  el.textContent = `1개월: ${one}   |   3개월: ${three}`;
}

function renderPriceHistoryChart(period = "1mo") {
  const holder = document.getElementById("priceHistoryChart");
  if (!holder) return;
  const points = pickHistoryPoints(period).filter((p) => Number.isFinite(Number(p.close)));
  if (!points.length) {
    holder.innerHTML = "<div style='padding:12px;color:#6c7986;'>가격 히스토리 데이터가 없습니다.</div>";
    return;
  }
  const closes = points.map((p) => Number(p.close));
  const volumes = points.map((p) => Number.parseFloat(String(p.volume ?? ""))).map((v) => (Number.isFinite(v) ? v : 0));
  const min = Math.min(...closes);
  const max = Math.max(...closes);
  const baseline = closes[0];
  const pad = Math.max((max - min) * 0.1, 1e-6);
  const lo = min - pad;
  const hi = max + pad;
  const volMax = Math.max(1, ...volumes);
  const w = 900;
  const h = 270;
  const left = 8;
  const right = 56;
  const plotTop = 12;
  const plotBottom = 170;
  const volTop = 182;
  const volBottom = 228;
  const axisY = 248;
  const plotW = w - left - right;
  const plotH = plotBottom - plotTop;
  const x = (idx) => left + (idx / Math.max(1, points.length - 1)) * plotW;
  const y = (v) => plotBottom - ((v - lo) / Math.max(1e-6, hi - lo)) * plotH;
  const yBase = y(baseline);

  let grid = "";
  const ticks = 4;
  for (let i = 0; i <= ticks; i += 1) {
    const gy = plotTop + (plotH * i) / ticks;
        const val = hi - ((hi - lo) * i) / ticks;
        grid += `<line x1="${left}" y1="${gy.toFixed(2)}" x2="${(w - right).toFixed(2)}" y2="${gy.toFixed(2)}" stroke="#e6edf6" stroke-width="1"/>`;
        grid += `<text x="${(w - right + 6).toFixed(2)}" y="${(gy + 4).toFixed(2)}" fill="#7a8794" font-size="11">${Math.round(val).toLocaleString("ko-KR")}</text>`;
  }
  grid += `<line x1="${left}" y1="${plotBottom}" x2="${(w - right).toFixed(2)}" y2="${plotBottom}" stroke="#cfd9e6" stroke-width="1"/>`;
  grid += `<line x1="${left}" y1="${volTop}" x2="${(w - right).toFixed(2)}" y2="${volTop}" stroke="#cfd9e6" stroke-width="1"/>`;
  grid += `<line x1="${left}" y1="${volBottom}" x2="${(w - right).toFixed(2)}" y2="${volBottom}" stroke="#cfd9e6" stroke-width="1"/>`;
  grid += `<line x1="${left}" y1="${yBase.toFixed(2)}" x2="${(w - right).toFixed(2)}" y2="${yBase.toFixed(2)}" stroke="#9ba8b6" stroke-width="1.2" stroke-dasharray="2 2"/>`;

  // Time axis ticks
  const xTickCount = Math.min(6, Math.max(3, Math.floor(points.length / 4)));
  for (let i = 0; i < xTickCount; i += 1) {
    const idx = Math.round((i / Math.max(1, xTickCount - 1)) * (points.length - 1));
    const tx = x(idx);
    const raw = String(points[idx]?.date || "");
    const label = raw.length >= 10 ? raw.slice(5) : raw;
    grid += `<line x1="${tx.toFixed(2)}" y1="${plotTop}" x2="${tx.toFixed(2)}" y2="${volBottom}" stroke="#eef2f7" stroke-width="1"/>`;
    grid += `<text x="${tx.toFixed(2)}" y="${axisY.toFixed(2)}" text-anchor="middle" fill="#7a8794" font-size="11">${escapeHtml(label)}</text>`;
  }

  let lineSegs = "";
  for (let i = 1; i < points.length; i += 1) {
    const c1 = closes[i - 1];
    const c2 = closes[i];
    const segColor = ((c1 + c2) / 2 >= baseline) ? "#ff4d4f" : "#2f7de1";
    lineSegs += `<line x1="${x(i - 1).toFixed(2)}" y1="${y(c1).toFixed(2)}" x2="${x(i).toFixed(2)}" y2="${y(c2).toFixed(2)}" stroke="${segColor}" stroke-width="2.3" stroke-linecap="round"/>`;
  }

  let belowAreas = "";
  let startIdx = -1;
  for (let i = 0; i <= points.length; i += 1) {
    const isBelow = i < points.length ? closes[i] < baseline : false;
    if (isBelow && startIdx < 0) startIdx = i;
    if (!isBelow && startIdx >= 0) {
      const endIdx = i - 1;
      const topPts = [];
      for (let k = startIdx; k <= endIdx; k += 1) {
        topPts.push(`${x(k).toFixed(2)},${y(closes[k]).toFixed(2)}`);
      }
      const poly = `${topPts.join(" ")} ${x(endIdx).toFixed(2)},${yBase.toFixed(2)} ${x(startIdx).toFixed(2)},${yBase.toFixed(2)}`;
      belowAreas += `<polygon points="${poly}" fill="#dfeafc" opacity="0.85"/>`;
      startIdx = -1;
    }
  }

  let volumeBars = "";
  let volumeHitZones = "";
  const bw = Math.max(1.5, (plotW / Math.max(1, points.length)) * 0.55);
  for (let i = 0; i < points.length; i += 1) {
    const vx = x(i) - bw / 2;
    const vh = ((volumes[i] || 0) / volMax) * (volBottom - volTop - 2);
    const vy = volBottom - vh;
    const vtxt = Number(volumes[i] || 0).toLocaleString("ko-KR");
    const ctxt = `${Math.round(Number(closes[i] || 0)).toLocaleString("ko-KR")} ${currencyUnitForMarket(latestDecisionMarket)}`;
    const dtxt = escapeHtml(String(points[i]?.date || "-"));
    volumeBars += `<rect x="${vx.toFixed(2)}" y="${vy.toFixed(2)}" width="${bw.toFixed(2)}" height="${Math.max(1, vh).toFixed(2)}" fill="#9f87dd" opacity="0.75"></rect>`;
    volumeHitZones += `<rect class="vol-hit" x="${(vx - 1).toFixed(2)}" y="${volTop.toFixed(2)}" width="${(bw + 2).toFixed(2)}" height="${(volBottom - volTop).toFixed(2)}" fill="transparent" data-tooltip="${dtxt}\n종가: ${ctxt}\n거래량: ${vtxt}"></rect>`;
  }

  holder.innerHTML = `
    <svg viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" width="100%" height="100%">
      <rect x="0" y="0" width="${w}" height="${h}" fill="#ffffff"></rect>
      ${grid}
      ${belowAreas}
      ${lineSegs}
      ${volumeBars}
      ${volumeHitZones}
      <text x="${left}" y="${(plotTop - 1).toFixed(2)}" fill="#8a97a5" font-size="11">가격(상단) / 거래량(하단, 마우스 오버)</text>
    </svg>
    <div class="chart-footer">
      <span>${escapeHtml(points[0].date || "-")}</span>
      <span>기준선 ${formatPriceInt(baseline)} ${currencyUnitForMarket(latestDecisionMarket)} | 최저 ${formatPriceInt(min)} ${currencyUnitForMarket(latestDecisionMarket)} / 최고 ${formatPriceInt(max)} ${currencyUnitForMarket(latestDecisionMarket)}</span>
      <span>${escapeHtml(points[points.length - 1].date || "-")}</span>
    </div>
  `;
  renderHistoryStats();

  const tipClass = "chart-tooltip";
  let tooltip = holder.querySelector(`.${tipClass}`);
  if (!tooltip) {
    tooltip = document.createElement("div");
    tooltip.className = tipClass;
    tooltip.style.display = "none";
    holder.appendChild(tooltip);
  }
  holder.querySelectorAll(".vol-hit").forEach((hit) => {
    hit.addEventListener("mousemove", (ev) => {
      const text = hit.getAttribute("data-tooltip") || "";
      tooltip.textContent = text;
      tooltip.style.display = "block";
      const rect = holder.getBoundingClientRect();
      const xPos = ev.clientX - rect.left;
      const yPos = ev.clientY - rect.top;
      tooltip.style.left = `${xPos}px`;
      tooltip.style.top = `${yPos}px`;
    });
    hit.addEventListener("mouseleave", () => {
      tooltip.style.display = "none";
    });
  });
}

function renderFundamentalCard(data) {
  if (!data.ok) {
    els.fundamentalCard.innerHTML = `<strong>재무 요약</strong><div>${escapeHtml(data.error || "데이터 없음")}</div>`;
    return;
  }
  const market = String(data.market || latestDecisionMarket || "US").toUpperCase();
  els.fundamentalCard.innerHTML = `
    <strong>재무 요약 (${escapeHtml(data.source)})</strong>
    <div>${escapeHtml(data.name || data.ticker)} | ${escapeHtml(data.sector || "섹터 정보 없음")} / ${escapeHtml(data.industry || "산업 정보 없음")}</div>
    <div>시가총액: ${escapeHtml(formatPriceWithUnit(data.market_cap, market))} | P/E: ${escapeHtml(displayValue(data.pe_ratio))} | P/B: ${escapeHtml(displayValue(data.pb_ratio))}</div>
    <div>ROE: ${escapeHtml(displayValue(data.roe))} | 영업마진(TTM): ${escapeHtml(displayValue(data.operating_margin_ttm))}</div>
    <details style="margin-top:8px;">
      <summary class="muted-sm">용어 쉽게 보기</summary>
      <ul class="reason-list">
        <li><strong>P/E</strong>: 회사 이익 대비 주가가 몇 배인지. 낮을수록 상대적으로 저렴할 가능성.</li>
        <li><strong>P/B</strong>: 회사 순자산 대비 주가가 몇 배인지. 1에 가까우면 자산가치 대비 부담이 낮을 수 있음.</li>
        <li><strong>ROE</strong>: 자기자본으로 얼마나 이익을 냈는지. 높을수록 수익성 효율이 좋은 편.</li>
      </ul>
    </details>
  `;
}

function renderValuationExplain(data) {
  if (!els.valuationExplainCard) return;
  if (!data?.ok) {
    els.valuationExplainCard.innerHTML = "<strong>밸류에이션 설명</strong><div>재무 데이터가 없어 설명을 생성할 수 없습니다.</div>";
    return;
  }
  const pe = Number.parseFloat(String(data.pe_ratio ?? "").replaceAll(",", ""));
  const pb = Number.parseFloat(String(data.pb_ratio ?? "").replaceAll(",", ""));
  const roe = Number.parseFloat(String(data.roe ?? "").replaceAll(",", ""));

  let peText = "P/E 정보 부족 (이익 대비 주가가 비싼지 판단 어려움)";
  if (Number.isFinite(pe)) {
    if (pe <= 12) peText = `P/E ${pe.toFixed(2)}: 회사가 벌어들이는 이익 대비 주가가 비교적 낮아 보입니다.`;
    else if (pe <= 20) peText = `P/E ${pe.toFixed(2)}: 시장에서 보통 수준으로 평가받는 구간입니다.`;
    else if (pe <= 35) peText = `P/E ${pe.toFixed(2)}: 성장 기대가 이미 주가에 반영된 상태일 수 있습니다.`;
    else peText = `P/E ${pe.toFixed(2)}: 기대가 과하게 반영됐을 수 있어 실적 확인이 특히 중요합니다.`;
  }

  let pbText = "P/B 정보 부족 (자산 대비 주가 부담 판단 어려움)";
  if (Number.isFinite(pb)) {
    if (pb <= 1.2) pbText = `P/B ${pb.toFixed(2)}: 회사 자산가치와 비교하면 주가 부담이 상대적으로 낮은 편입니다.`;
    else if (pb <= 2.5) pbText = `P/B ${pb.toFixed(2)}: 자산가치 대비 평균적인 평가 구간입니다.`;
    else pbText = `P/B ${pb.toFixed(2)}: 자산가치 대비 프리미엄이 붙어 있어 성장성 검증이 필요합니다.`;
  }

  let roeText = "ROE 정보 부족 (수익성 효율 판단 어려움)";
  if (Number.isFinite(roe)) {
    if (roe >= 15) roeText = `ROE ${roe.toFixed(2)}: 투자한 자본으로 이익을 잘 내는 편입니다.`;
    else if (roe >= 8) roeText = `ROE ${roe.toFixed(2)}: 수익성은 평균 수준으로 볼 수 있습니다.`;
    else roeText = `ROE ${roe.toFixed(2)}: 수익성 체력 점검이 필요한 구간입니다.`;
  }

  els.valuationExplainCard.innerHTML = `
    <strong>밸류에이션 설명</strong>
    <ul class="reason-list">
      <li>${escapeHtml(peText)}</li>
      <li>${escapeHtml(pbText)}</li>
      <li>${escapeHtml(roeText)}</li>
      <li>단일 지표만으로 매수/매도 판단하지 말고 뉴스/공시/기술 경쟁력과 함께 확인하세요.</li>
    </ul>
  `;
}

function renderIntelSummary(data) {
  if (!els.intelSummaryCard) return;
  if (!data?.ok || !data?.summary) {
    const msg = escapeHtml(data?.error || "요약 데이터 없음");
    els.intelSummaryCard.innerHTML = `<strong>AI 인텔리전스 요약</strong><div>${msg}</div>`;
    return;
  }
  const s = data.summary || {};
  const overview = escapeHtml(s.overview || "-");
  const priceDriver = escapeHtml(s.price_driver || "상승/하락 원인 데이터가 부족합니다.");
  const stance = escapeHtml(s.stance || "관망");
  const confidence = escapeHtml(s.confidence || "medium");
  const llmUsed = !!s.llm_used;
  const points = (s.key_points || []).map((x) => `<li>${escapeHtml(x)}</li>`).join("") || "<li>핵심 포인트 없음</li>";
  const risks = (s.risks || []).map((x) => `<li>${escapeHtml(x)}</li>`).join("") || "<li>리스크 없음</li>";
  els.intelSummaryCard.innerHTML = `
    <div class="intel-summary-title">
      <strong>AI 인텔리전스 요약</strong>
      <span class="chip">${llmUsed ? "LLM 요약" : "규칙 기반 요약"}</span>
    </div>
    <div>${overview}</div>
    <div class="driver-box"><strong>상승/하락 원인</strong><div>${priceDriver}</div></div>
    <div style="margin-top:8px;">
      <span class="stance-pill">${stance}</span>
      <small style="margin-left:8px;color:#5f6c78;">신뢰도: ${confidence}</small>
    </div>
    <div class="intel-summary-grid" style="margin-top:10px;">
      <div><strong>핵심 포인트</strong><ul>${points}</ul></div>
      <div><strong>주요 리스크</strong><ul>${risks}</ul></div>
    </div>
  `;
}

function renderSimpleList(element, rows, emptyText) {
  if (!element) return;
  if (!rows || rows.length === 0) {
    element.innerHTML = `<li>${escapeHtml(emptyText)}</li>`;
    return;
  }
  element.innerHTML = rows.join("");
}

function renderNews(data) {
  latestNewsData = data || { ok: false, items: [] };
  clearFeedSkeleton(els.newsList);
  const sourceFilter = String(els.newsSourceFilter?.value || "").trim().toLowerCase();
  const keywordFilter = String(els.newsKeywordFilter?.value || "").trim().toLowerCase();
  const sentimentFilter = String(els.newsSentimentFilter?.value || "").trim().toLowerCase();
  if (!latestNewsData.ok) {
    renderSimpleList(els.newsList, [], latestNewsData.error || "뉴스 데이터 없음");
    if (els.newsMoreBtn) els.newsMoreBtn.hidden = true;
    return;
  }
  let filtered = (latestNewsData.items || []).filter((item) => {
    const source = String(item.source || "").toLowerCase();
    const head = String(item.headline || "").toLowerCase();
    if (sourceFilter && !source.includes(sourceFilter)) return false;
    if (keywordFilter && !head.includes(keywordFilter)) return false;
    const senti = classifySentimentFromText(head);
    if (sentimentFilter && senti !== sentimentFilter) return false;
    return true;
  });
  const limit = newsExpanded ? 999 : 5;
  const rows = filtered.slice(0, limit).map((item) => {
    const url = escapeHtml(item.url || "#");
    const headline = String(item.headline || "(제목 없음)");
    const title = escapeHtml(headline);
    const src = escapeHtml(item.source || "-");
    const dt = escapeHtml(String(item.datetime || item.time || "").slice(0, 16) || "-");
    const senti = classifySentimentFromText(headline);
    const tagClass = senti === "positive" ? "pos" : senti === "negative" ? "neg" : "";
    const cardClass = senti === "positive" ? "sentiment-positive" : senti === "negative" ? "sentiment-negative" : "sentiment-neutral";
    const tags = extractTags(headline).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("");
    const sentiLabel = senti === "positive" ? "긍정" : senti === "negative" ? "부정" : "중립";
    return `<li class="sentiment-card ${cardClass}">
      <a class="intel-link" href="${url}" target="_blank" rel="noopener noreferrer">${title}</a>
      <div class="muted-sm">${src} · ${dt} <span class="tag ${tagClass}">${sentiLabel}</span>${tags}</div>
    </li>`;
  });
  renderSimpleList(els.newsList, rows, "뉴스 없음");
  if (els.newsMoreBtn) {
    const hiddenCount = Math.max(0, filtered.length - (newsExpanded ? filtered.length : 5));
    els.newsMoreBtn.hidden = filtered.length <= 5;
    els.newsMoreBtn.textContent = newsExpanded ? "뉴스 접기" : `뉴스 더 보기 (${hiddenCount}개)`;
  }
}

function renderFilings(data) {
  latestFilingData = data || { ok: false, items: [] };
  clearFeedSkeleton(els.filingList);
  const formFilter = String(els.filingFormFilter?.value || "").trim().toLowerCase();
  if (!latestFilingData.ok) {
    const msg = String(latestFilingData.error || "공시 데이터 없음");
    if (msg.includes("DART_API_KEY")) {
      renderSimpleList(els.filingList, [], "KR 공시는 DART_API_KEY 설정이 필요합니다. (.env 참고)");
      if (els.filingMoreBtn) els.filingMoreBtn.hidden = true;
      return;
    }
    renderSimpleList(els.filingList, [], msg);
    if (els.filingMoreBtn) els.filingMoreBtn.hidden = true;
    return;
  }
  const filtered = (latestFilingData.items || []).filter((item) => {
    if (!formFilter) return true;
    return String(item.form || "").toLowerCase().includes(formFilter);
  });
  const limit = filingExpanded ? 999 : 5;
  const rows = filtered.slice(0, limit).map((item) => {
    const form = escapeHtml(item.form || "-");
    const dt = escapeHtml(item.filing_date || "-");
    const tone = classifySentimentFromText(String(item.form || ""));
    const toneLabel = tone === "positive" ? "긍정" : tone === "negative" ? "부정" : "중립";
    const toneClass = tone === "positive" ? "pos" : tone === "negative" ? "neg" : "";
    if (item.url) {
      const url = escapeHtml(item.url);
      return `<li><a class="intel-link" href="${url}" target="_blank" rel="noopener noreferrer">${form}</a><div class="muted-sm">${dt} <span class="tag ${toneClass}">${toneLabel}</span></div></li>`;
    }
    return `<li>${form}<div class="muted-sm">${dt} <span class="tag ${toneClass}">${toneLabel}</span></div></li>`;
  });
  renderSimpleList(els.filingList, rows, "공시 없음");
  if (els.filingMoreBtn) {
    const hiddenCount = Math.max(0, filtered.length - (filingExpanded ? filtered.length : 5));
    els.filingMoreBtn.hidden = filtered.length <= 5;
    els.filingMoreBtn.textContent = filingExpanded ? "공시 접기" : `공시 더 보기 (${hiddenCount}개)`;
  }
}

function renderTechnology(data) {
  latestTechData = data || { ok: false, items: [] };
  clearFeedSkeleton(els.techList);
  if (!latestTechData.ok) {
    renderSimpleList(els.techList, [], String(latestTechData.error || "기술 데이터 없음"));
    if (els.techMoreBtn) els.techMoreBtn.hidden = true;
    return;
  }
  const items = latestTechData.items || [];
  const limit = techExpanded ? 999 : 5;
  const rows = items.slice(0, limit).map((item) => {
    const title = escapeHtml(item.title || "(제목 없음)");
    const url = escapeHtml(item.url || "#");
    const published = escapeHtml(item.published || "-").slice(0, 10);
    const tags = extractTags(String(item.title || "")).map((t) => `<span class="tag">${escapeHtml(t)}</span>`).join("");
    return `<li><a class="intel-link" href="${url}" target="_blank" rel="noopener noreferrer">${title}</a><div class="muted-sm">${published} ${tags}</div></li>`;
  });
  renderSimpleList(els.techList, rows, "기술 자료 없음");
  if (els.techMoreBtn) {
    const hiddenCount = Math.max(0, items.length - (techExpanded ? items.length : 5));
    els.techMoreBtn.hidden = items.length <= 5;
    els.techMoreBtn.textContent = techExpanded ? "기술 자료 접기" : `기술 자료 더 보기 (${hiddenCount}개)`;
  }
}

function renderRelatedStocks(items, emptyText = "관련 종목 없음") {
  const rows = (items || []).map((it) => {
    const ticker = escapeHtml(it.ticker || "-");
    const name = escapeHtml(it.name || "");
    const market = String(it.market || "US").toUpperCase();
    const sector = escapeHtml(it.sector || "");
    const rank = it.rank != null ? Number(it.rank).toFixed(1) : "";
    const price = Number(it.price);
    const changePct = Number(it.change_percent);
    const hasPrice = Number.isFinite(price);
    const hasChange = Number.isFinite(changePct);
    const priceText = hasPrice ? formatNumber(price, market === "KR" ? 0 : 2) : "-";
    const changeText = hasChange ? `${changePct >= 0 ? "+" : ""}${changePct.toFixed(2)}%` : "-";
    const toneClass = hasChange ? (changePct >= 0 ? "bullish" : "bearish") : "neutral";
    const meta = [marketLabel(market), sector ? `섹터 ${sector}` : "", rank ? `랭크 ${rank}` : ""].filter(Boolean).join(" | ");
    return `
      <article class="stock-card">
        <div><strong>${name || ticker}</strong></div>
        <div class="meta">${ticker} | ${meta}</div>
        <div class="muted-sm">현재가 ${priceText} | 등락률 <span class="tag ${toneClass}">${changeText}</span></div>
        <div class="stock-card-actions">
          <button class="btn secondary" data-pick-ticker="${ticker}" data-pick-market="${escapeHtml(market)}" data-pick-name="${name}" data-pick-sector="${sector}">선택</button>
          <button class="btn ghost" data-compare-ticker="${ticker}" data-compare-market="${escapeHtml(market)}" data-compare-name="${name}" data-compare-sector="${sector}">비교추가</button>
        </div>
      </article>
    `;
  });
  if (!els.relatedStocksList) return;
  if (!rows.length) {
    els.relatedStocksList.innerHTML = `<div class="stock-card">${escapeHtml(emptyText)}</div>`;
    return;
  }
  els.relatedStocksList.innerHTML = rows.join("");
}

function renderRelatedSectorChips(sectors) {
  if (!els.relatedSectorChips) return;
  const list = (sectors || []).filter(Boolean);
  if (!list.length) {
    els.relatedSectorChips.innerHTML = '<span class="chip soft">연관 섹터 없음</span>';
    return;
  }
  els.relatedSectorChips.innerHTML = list
    .map((s) => `<span class="chip soft">${escapeHtml(s)}</span>`)
    .join("");
}

async function enrichRelatedStocksWithQuotes(items) {
  const list = Array.isArray(items) ? items : [];
  if (!list.length) return list;
  const tasks = [];
  for (const item of list.slice(0, 20)) {
    const ticker = String(item.ticker || "").trim().toUpperCase();
    const market = String(item.market || "US").trim().toUpperCase();
    if (!ticker) continue;
    const key = `${market}:${ticker}`;
    if (peerQuoteCache.has(key)) continue;
    tasks.push(
      fetchApi(`/api/quote?ticker=${encodeURIComponent(ticker)}&market=${encodeURIComponent(market)}`)
        .then((res) => {
          if (!res || res.ok === false) return;
          const price = toNumberOrNull(res.price);
          const changePercent = toNumberOrNull(res.change_percent);
          peerQuoteCache.set(key, { price, change_percent: changePercent });
        })
        .catch(() => {
          // no-op
        })
    );
  }
  if (tasks.length) await Promise.allSettled(tasks);
  for (const item of list) {
    const ticker = String(item.ticker || "").trim().toUpperCase();
    const market = String(item.market || "US").trim().toUpperCase();
    const key = `${market}:${ticker}`;
    const cached = peerQuoteCache.get(key);
    if (!cached) continue;
    if (item.price == null && cached.price != null) item.price = cached.price;
    if (item.change_percent == null && cached.change_percent != null) item.change_percent = cached.change_percent;
  }
  return list;
}

function toNumberOrNull(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : null;
}

function compareItemKey(item) {
  return `${String(item.market || "US").toUpperCase()}:${String(item.ticker || "").toUpperCase()}`;
}

function upsertCompareItem(item) {
  const next = {
    ticker: String(item.ticker || "").toUpperCase(),
    market: String(item.market || "US").toUpperCase(),
    name: String(item.name || item.ticker || "").trim(),
    sector: String(item.sector || "").trim(),
  };
  if (!next.ticker) return false;
  const key = compareItemKey(next);
  const idx = compareSelection.findIndex((x) => compareItemKey(x) === key);
  if (idx >= 0) {
    compareSelection[idx] = next;
    return true;
  }
  if (compareSelection.length >= 4) return false;
  compareSelection.push(next);
  return true;
}

function removeCompareItem(key) {
  compareSelection = compareSelection.filter((x) => compareItemKey(x) !== key);
}

function renderCompareSelection() {
  if (!els.sectorCompareSelected) return;
  if (!compareSelection.length) {
    els.sectorCompareSelected.innerHTML = '<span class="chip soft">선택된 비교 종목 없음</span>';
    return;
  }
  els.sectorCompareSelected.innerHTML = compareSelection
    .map((it) => {
      const key = compareItemKey(it);
      const text = `${it.name || it.ticker} (${it.ticker}, ${it.market})`;
      return `<button class="chip soft compare-chip" type="button" data-compare-remove="${escapeHtml(key)}">${escapeHtml(text)} ×</button>`;
    })
    .join("");
}

function renderCompareTable(headers, rows) {
  const thead = `<tr>${headers.map((h) => `<th>${escapeHtml(h)}</th>`).join("")}</tr>`;
  const tbody = rows
    .map((row) => `<tr>${row.map((col) => `<td>${escapeHtml(String(col ?? "-"))}</td>`).join("")}</tr>`)
    .join("");
  return `<table class="compare-table"><thead>${thead}</thead><tbody>${tbody}</tbody></table>`;
}

function clipText(text, maxLen = 38) {
  const t = String(text || "").trim();
  if (!t) return "-";
  return t.length > maxLen ? `${t.slice(0, maxLen - 1)}…` : t;
}

async function fetchCompareTabData(item, tab) {
  const intensity = getFeedIntensity();
  const key = `${compareItemKey(item)}:${tab}:${intensity}`;
  const now = Date.now();
  const hit = compareDataCache.get(key);
  if (hit && hit.expireAt > now) return hit.value;

  const ticker = encodeURIComponent(item.ticker);
  const market = encodeURIComponent(item.market);
  let data = {};
  if (tab === "core") {
    const [quote, decision, backtest] = await Promise.all([
      fetchApi(`/api/quote?ticker=${ticker}&market=${market}`),
      fetchApi(`/api/decision-intel?ticker=${ticker}&market=${market}&horizon=mid&risk=neutral&fx_change_pct=0&ev_growth_pct=5`),
      fetchApi(`/api/backtest-sector-signal?ticker=${ticker}&market=${market}&period=3mo&hold_days=5`),
    ]);
    data = { quote, decision, backtest };
  } else if (tab === "detail") {
    const [fund, decision, backtest] = await Promise.all([
      fetchApi(`/api/fundamentals?ticker=${ticker}&market=${market}`),
      fetchApi(`/api/decision-intel?ticker=${ticker}&market=${market}&horizon=mid&risk=neutral&fx_change_pct=0&ev_growth_pct=5`),
      fetchApi(`/api/backtest-sector-signal?ticker=${ticker}&market=${market}&period=3mo&hold_days=5`),
    ]);
    data = { fund, decision, backtest };
  } else {
    const feed = getFeedConfig();
    const [news, filings, tech] = await Promise.all([
      fetchApi(`/api/news?ticker=${ticker}&market=${market}&days=${feed.newsDays}&limit=${feed.newsLimit}`),
      fetchApi(`/api/filings?ticker=${ticker}&market=${market}&limit=${feed.filingLimit}`),
      fetchApi(`/api/technology?query=${encodeURIComponent(item.name || item.ticker)}&limit=${feed.techLimit}`),
    ]);
    data = { news, filings, tech };
  }
  compareDataCache.set(key, { expireAt: now + 90_000, value: data });
  return data;
}

async function renderSectorComparePanel(tab = currentCompareTab) {
  currentCompareTab = tab;
  if (!els.sectorCompareBody || !els.sectorCompareMeta) return;
  renderCompareSelection();
  if (compareSelection.length < 2) {
    els.sectorCompareMeta.textContent = "비교하려는 종목을 2개 이상 선택하세요. (최대 4개)";
    els.sectorCompareBody.innerHTML = '<div class="muted-sm">관련 종목 카드에서 `비교추가`를 눌러 목록을 구성하세요.</div>';
    return;
  }

  els.sectorCompareMeta.textContent = `${compareSelection.length}개 종목 비교 중...`;
  els.sectorCompareBody.innerHTML = '<div class="muted-sm">비교 데이터를 불러오는 중...</div>';
  try {
    const dataset = await Promise.all(compareSelection.map((it) => fetchCompareTabData(it, tab)));
    const nameOf = (it) => `${it.name || it.ticker} (${it.ticker})`;
    let table = "";
    if (tab === "core") {
      const headers = ["종목", "현재가", "등락률", "종합점수", "시그널", "섹터열기/체력", "5일 백테스트 평균", "승률"];
      const rows = compareSelection.map((it, idx) => {
        const q = dataset[idx].quote || {};
        const d = dataset[idx].decision || {};
        const snap = (d.decision_panel || {}).snapshot || {};
        const heat = (d.decision_panel || {}).sector_heat || {};
        const bt = dataset[idx].backtest || {};
        const stat = ((bt.stats_by_label || {})[String(heat.label || "").trim()] || {});
        return [
          nameOf(it),
          displayValue(q.current_price, "-"),
          formatSignedNumber(q.percent_change, 2),
          displayValue(toNumberOrNull(snap.composite)?.toFixed(1), "-"),
          summarizeSignalsForHeader(d),
          `${displayValue(heat.heat_score, "-")} / ${displayValue(heat.resilience_score, "-")} ${heat.label ? `(${heat.label})` : ""}`,
          stat.avg_forward_return_pct == null ? "-" : `${Number(stat.avg_forward_return_pct).toFixed(2)}%`,
          stat.hit_rate_pct == null ? "-" : `${Number(stat.hit_rate_pct).toFixed(1)}%`,
        ];
      });
      table = renderCompareTable(headers, rows);
    } else if (tab === "detail") {
      const headers = ["종목", "PER", "PBR", "ROE", "영업마진", "품질", "밸류", "기술력", "자본력", "리스크", "5일 알파"];
      const rows = compareSelection.map((it, idx) => {
        const f = dataset[idx].fund || {};
        const decisionPanel = (dataset[idx].decision || {}).decision_panel || {};
        const snap = decisionPanel.snapshot || {};
        const risk = decisionPanel.risk || {};
        const bt = dataset[idx].backtest || {};
        const heat = decisionPanel.sector_heat || {};
        const stat = ((bt.stats_by_label || {})[String(heat.label || "").trim()] || {});
        return [
          nameOf(it),
          displayValue(f.pe_ratio, "-"),
          displayValue(f.pb_ratio, "-"),
          displayValue(f.roe, "-"),
          displayValue(f.operating_margin_ttm, "-"),
          displayValue(toNumberOrNull(snap.quality)?.toFixed(1), "-"),
          displayValue(toNumberOrNull(snap.valuation)?.toFixed(1), "-"),
          displayValue(toNumberOrNull(snap.tech_strength)?.toFixed(1), "-"),
          displayValue(toNumberOrNull(snap.capital_power)?.toFixed(1), "-"),
          displayValue(toNumberOrNull(risk.total)?.toFixed(1), "-"),
          stat.alpha_vs_baseline_pct == null ? "-" : `${Number(stat.alpha_vs_baseline_pct).toFixed(2)}%`,
        ];
      });
      table = renderCompareTable(headers, rows);
    } else {
      const feedCfg = getFeedConfig();
      const headers = [`종목`, `뉴스(${feedCfg.newsDays}일)`, "최근 헤드라인", `공시(${feedCfg.filingLimit}건)`, "최근 공시", `기술자료(${feedCfg.techLimit})`, "피드 강도"];
      const rows = compareSelection.map((it, idx) => {
        const n = dataset[idx].news || {};
        const f = dataset[idx].filings || {};
        const t = dataset[idx].tech || {};
        const newsRatio = Math.min(1, Number(n.count || 0) / Math.max(1, feedCfg.newsLimit));
        const filingRatio = Math.min(1, Number(f.count || 0) / Math.max(1, feedCfg.filingLimit));
        const techRatio = Math.min(1, Number(t.count || 0) / Math.max(1, feedCfg.techLimit));
        const feed = ((newsRatio * 1.2) + (filingRatio * 0.9) + (techRatio * 1.1)) * 100;
        const topNews = clipText((n.items || [])[0]?.headline || (n.items || [])[0]?.title || "-", 34);
        const topFiling = clipText((f.items || [])[0]?.form || (f.items || [])[0]?.title || "-", 26);
        return [
          nameOf(it),
          String(n.count || 0),
          topNews,
          String(f.count || 0),
          topFiling,
          String(t.count || 0),
          `${feed.toFixed(1)} / 100`,
        ];
      });
      table = renderCompareTable(headers, rows);
    }
    els.sectorCompareBody.innerHTML = table;
    const tabName = tab === "core" ? "핵심" : tab === "detail" ? "근거" : "피드";
    els.sectorCompareMeta.textContent = `${tabName} 비교 완료 · ${compareSelection.length}개 종목`;
  } catch (err) {
    els.sectorCompareMeta.textContent = "비교 데이터 로드 실패";
    els.sectorCompareBody.innerHTML = `<div class="muted-sm">오류: ${escapeHtml(err?.message || "알 수 없는 오류")}</div>`;
  }
}

async function fetchSectorStocksCached(userId, market, sector, limit = 30, includeRanked = false) {
  const key = `${userId}:${market}:${sector}:${limit}:${includeRanked ? 1 : 0}`;
  const now = Date.now();
  const hit = sectorStocksCache.get(key);
  if (hit && hit.expireAt > now) return hit.value;
  let value = null;
  try {
    const path =
      `/api/sector-stocks?user_id=${encodeURIComponent(userId)}` +
      `&market=${encodeURIComponent(market)}` +
      `&sector=${encodeURIComponent(sector)}` +
      `&limit=${encodeURIComponent(limit)}` +
      `&include_ranked=${includeRanked ? "1" : "0"}`;
    value = await fetchApi(path);
  } catch (_err) {
    value = { ok: true, items: await getSectorStocksLocal(market, sector, limit), source: "local_fallback" };
  }
  sectorStocksCache.set(key, { expireAt: now + 120_000, value });
  return value;
}

function normalizeSearchText(text) {
  return String(text || "")
    .toLowerCase()
    .replaceAll(/\s+/g, "")
    .trim();
}

function hasHangulText(text) {
  return /[ㄱ-ㅎㅏ-ㅣ가-힣]/.test(String(text || ""));
}

function normalizeLooseText(text) {
  return String(text || "")
    .toLowerCase()
    .replaceAll(/\s+/g, "")
    .replaceAll(/[().,_-]/g, "")
    .trim();
}

function inferSectorByName(name) {
  const key = normalizeLooseText(name);
  for (const rule of COMPANY_SECTOR_HINTS) {
    if (rule.terms.some((t) => key.includes(normalizeLooseText(t)))) {
      return rule.sector;
    }
  }
  return "";
}

function findSectorByName(name) {
  return inferSectorByName(name);
}

function inferTechKeywords(sector, companyName, ticker = "") {
  const t = String(ticker || "").replaceAll(/[^0-9A-Za-z]/g, "").toUpperCase();
  if (t && COMPANY_TECH_KEYWORDS[t]) return COMPANY_TECH_KEYWORDS[t];
  const bySector = SECTOR_TECH_KEYWORDS[String(sector || "").trim()];
  if (bySector) return bySector;
  const inferred = inferSectorByName(companyName);
  if (inferred && SECTOR_TECH_KEYWORDS[inferred]) return SECTOR_TECH_KEYWORDS[inferred];
  if (String(companyName || "").trim()) return "technology, patent, product roadmap, manufacturing";
  return "semiconductor, battery, electric vehicle, ai, robotics";
}

function inferRelatedSectorsFromKeywords(keywordText, primarySector = "") {
  const t = normalizeLooseText(keywordText);
  const set = new Set();
  const first = String(primarySector || "").trim();
  if (first && !["기타", "UNCLASSIFIED", "미분류"].includes(first)) set.add(first);
  for (const rule of KEYWORD_RELATED_SECTORS) {
    if (rule.terms.some((k) => t.includes(normalizeLooseText(k)))) {
      rule.sectors.forEach((s) => set.add(s));
    }
  }
  return Array.from(set);
}

function extractFamilyToken(name, ticker = "") {
  const raw = String(name || "").trim();
  if (raw) {
    const first = raw.split(/\s+/)[0].trim();
    if (first && !/^[0-9]+$/.test(first)) return first;
  }
  const t = String(ticker || "").trim().toUpperCase();
  if (t) return t;
  return "";
}

function extractInstrumentTraits(name) {
  const txt = normalizeLooseText(name);
  const traits = [];
  const keys = [
    "인버스",
    "inverse",
    "레버리지",
    "leveraged",
    "선물",
    "futures",
    "2x",
    "3x",
    "etf",
    "etn",
  ];
  for (const k of keys) {
    if (txt.includes(normalizeLooseText(k))) traits.push(k.toLowerCase());
  }
  return traits;
}

async function fetchFamilyRelatedStocks(name, ticker, market, limit = 30) {
  const family = extractFamilyToken(name, ticker);
  if (!family) return [];
  let items = [];
  try {
    const res = await fetchApi(
      `/api/company-lookup?query=${encodeURIComponent(family)}&market=${encodeURIComponent(market)}&limit=${encodeURIComponent(Math.max(limit * 2, 40))}`
    );
    items = res.items || [];
  } catch (_err) {
    items = await lookupCompanyLocal(family, market, Math.max(limit * 2, 40));
  }

  const targetTraits = extractInstrumentTraits(name);
  const targetTicker = String(ticker || "").toUpperCase();
  const scored = [];
  for (const it of items) {
    const itMarket = String(it.market || "").toUpperCase();
    if (itMarket !== String(market || "US").toUpperCase()) continue;
    const itTicker = String(it.ticker || "").toUpperCase();
    if (!itTicker || itTicker === targetTicker) continue;
    const itName = String(it.name || "");
    const key = normalizeLooseText(itName);
    const fam = normalizeLooseText(family);
    if (!key.includes(fam)) continue;
    const traits = extractInstrumentTraits(itName);
    const overlap = targetTraits.filter((x) => traits.includes(x)).length;
    const score = overlap * 4 + (itName.startsWith(family) ? 2 : 0) + (traits.length ? 1 : 0);
    scored.push({
      ticker: itTicker,
      name: itName || itTicker,
      sector: String(it.sector || "").trim() || "종목군",
      market: itMarket,
      source: "family_lookup",
      rank: score,
    });
  }
  scored.sort((a, b) => Number(b.rank || 0) - Number(a.rank || 0));
  return scored.slice(0, Math.max(1, Math.min(limit, 50)));
}

function pickBestSectorFromItems(items, fallbackName = "") {
  const sectors = (items || [])
    .map((x) => String(x?.sector || "").trim())
    .filter(Boolean);
  if (sectors.length) return sectors[0];
  const inferred = inferSectorByName(fallbackName);
  if (inferred) return inferred;
  return "";
}

function sortCompanyItems(items, preferredMarket = "ALL") {
  const pref = String(preferredMarket || "ALL").toUpperCase();
  const rank = (m) => {
    const market = String(m || "").toUpperCase();
    if (pref === "KR") return market === "KR" ? 0 : 1;
    if (pref === "US") return market === "US" ? 0 : 1;
    return market === "KR" ? 0 : market === "US" ? 1 : 2;
  };
  return [...(items || [])].sort((a, b) => {
    const ra = rank(a.market);
    const rb = rank(b.market);
    if (ra !== rb) return ra - rb;
    const saScore = Number(a.score || 0);
    const sbScore = Number(b.score || 0);
    if (Math.abs(sbScore - saScore) > 0.001) return sbScore - saScore;
    const sa = String(a.sector || "");
    const sb = String(b.sector || "");
    if (sa && !sb) return -1;
    if (!sa && sb) return 1;
    return String(a.name || "").localeCompare(String(b.name || ""), "ko");
  });
}

async function getLocalCompanyNameByTicker(ticker, market) {
  const t = String(ticker || "").trim().toUpperCase();
  const m = String(market || "US").trim().toUpperCase();
  if (!t) return "";
  const data = await getSectorSeed();
  for (const item of data) {
    const itemMarket = String(item.market || "").toUpperCase();
    if (itemMarket !== m) continue;
    const itemTicker = itemMarket === "KR" ? normalizeKRTicker(item.ticker) : String(item.ticker || "").toUpperCase();
    const targetTicker = itemMarket === "KR" ? normalizeKRTicker(t) : t;
    if (itemTicker === targetTicker) return String(item.name || "");
  }
  return "";
}

function buildLocalSummaryPayload(ticker, market, quoteData, fundData, newsData, filingData, techData) {
  const points = [];
  const risks = [];
  if (quoteData?.ok) {
    points.push(
      `현재가 ${formatPriceWithUnit(quoteData.current_price, market)}, 등락률 ${formatSignedNumber(quoteData.percent_change, 0)}%`,
    );
  } else {
    risks.push("실시간 시세 확보 실패");
  }
  if (fundData?.ok) {
    points.push(`밸류에이션 P/E ${displayValue(fundData.pe_ratio)}, P/B ${displayValue(fundData.pb_ratio)}, ROE ${displayValue(fundData.roe)}`);
  } else {
    risks.push("재무 요약 확보 실패");
  }
  if (newsData?.ok && (newsData.items || []).length) {
    points.push(`뉴스 ${newsData.items.length}건 반영`);
  } else {
    risks.push("뉴스 확보 실패");
  }
  if (filingData?.ok && (filingData.items || []).length) {
    points.push(`최근 공시 ${(filingData.items[0] || {}).form || "-"} 반영`);
  } else {
    risks.push("공시 확보 실패");
  }
  if (techData?.ok && (techData.items || []).length) {
    points.push(`관련 기술 자료 ${techData.items.length}건 반영`);
  } else {
    risks.push("기술 자료 확보 실패");
  }
  let driver = "상승/하락 원인 데이터가 부족합니다.";
  if (quoteData?.ok) {
    const pct = Number.parseFloat(String(quoteData.percent_change ?? ""));
    if (Number.isFinite(pct)) {
      if (pct >= 1.5) driver = `전일 종가 대비 +${pct.toFixed(0)}% 상승(단기 매수 우위)`;
      else if (pct <= -1.5) driver = `전일 종가 대비 ${pct.toFixed(0)}% 하락(단기 매도 우위)`;
      else driver = `전일 종가 대비 ${pct.toFixed(0)}%로 방향성 약함`;
    }
  }
  if (newsData?.ok && (newsData.items || []).length) {
    const h = String((newsData.items[0] || {}).headline || "").trim();
    if (h) driver = `${driver} | 뉴스 이슈: ${h}`;
  }

  return {
    ok: true,
    summary: {
      overview: `${ticker} (${market}) 통합 요약`,
      key_points: points.slice(0, 6),
      risks: risks.slice(0, 5),
      price_driver: driver,
      stance: "관망",
      confidence: "medium",
      llm_used: false,
    },
  };
}

async function enrichWatchlistCompanyNames(items) {
  const out = [];
  for (const item of items || []) {
    const cloned = { ...(item || {}) };
    const ticker = String(cloned.ticker || "").toUpperCase();
    const market = String(cloned.market || "US").toUpperCase();
    const name = String(cloned.company_name || "").trim();
    if (!name || name.replaceAll(" ", "") === ticker.replaceAll(" ", "")) {
      const localName = await getLocalCompanyNameByTicker(ticker, market);
      if (localName) cloned.company_name = localName;
    }
    out.push(cloned);
  }
  return out;
}

async function enrichRankingCompanyNames(items) {
  const out = [];
  for (const item of items || []) {
    const cloned = { ...(item || {}) };
    const ticker = String(cloned.ticker || "").toUpperCase();
    const market = String(cloned.market || "US").toUpperCase();
    const name = String(cloned.company_name || "").trim();
    if (!name || name.replaceAll(" ", "") === ticker.replaceAll(" ", "")) {
      const localName = await getLocalCompanyNameByTicker(ticker, market);
      if (localName) cloned.company_name = localName;
    }
    out.push(cloned);
  }
  return out;
}

async function lookupCompanyFromWatchlist(query, market = "ALL") {
  const q = normalizeLooseText(query);
  if (!q) return [];
  try {
    const userId = getUserId();
    const res = await fetchApi(`/api/watchlist?user_id=${encodeURIComponent(userId)}`);
    const items = await enrichWatchlistCompanyNames(res.items || []);
    const out = [];
    for (const item of items) {
      const itemMarket = String(item.market || "US").toUpperCase();
      if (market !== "ALL" && itemMarket !== market) continue;
      const ticker = itemMarket === "KR" ? normalizeKRTicker(item.ticker) : String(item.ticker || "").toUpperCase();
      const name = String(item.company_name || "");
      const sector = findSectorByName(name) || "";
      const text = normalizeLooseText(`${ticker} ${name} ${sector}`);
      if (!text.includes(q)) continue;
      out.push({ ticker, name, sector, market: itemMarket, source: "watchlist_fallback" });
    }
    return out;
  } catch (_err) {
    return [];
  }
}

function normalizeKRTicker(ticker) {
  const digits = String(ticker || "").replaceAll(/[^0-9]/g, "");
  if (!digits) return "";
  return digits.padStart(6, "0").slice(-6);
}

async function getSectorSeed() {
  if (Array.isArray(sectorSeedCache)) return sectorSeedCache;
  try {
    const api = await fetchApi("/api/sector-seed?market=ALL&limit=8000");
    const items = Array.isArray(api?.items) ? api.items : [];
    if (items.length) {
      sectorSeedCache = items;
      return sectorSeedCache;
    }
  } catch (_err) {
    // static fallback below
  }
  try {
    const res = await fetch("/data/sector_seed.json", { cache: "no-store" });
    if (!res.ok) throw new Error(`seed ${res.status}`);
    const data = await res.json();
    sectorSeedCache = Array.isArray(data) ? data : [];
    return sectorSeedCache;
  } catch (_err) {
    sectorSeedCache = [];
    return sectorSeedCache;
  }
}

async function lookupCompanyLocal(query, market, limit = 20) {
  const q = normalizeSearchText(query);
  if (!q) return [];
  const data = await getSectorSeed();
  const out = [];
  for (const item of data) {
    const itemMarket = String(item.market || "").toUpperCase();
    if (market !== "ALL" && itemMarket !== market) continue;
    const tickerRaw = String(item.ticker || "");
    const ticker = itemMarket === "KR" ? normalizeKRTicker(tickerRaw) : tickerRaw.toUpperCase();
    const name = String(item.name || "");
    const sector = String(item.sector || "");
    const target = normalizeSearchText(`${tickerRaw} ${ticker} ${name} ${sector}`);
    if (!target.includes(q)) continue;
    out.push({ ticker, name, sector, market: itemMarket, source: "local_seed_fallback" });
    if (out.length >= Math.max(1, Math.min(limit, 100))) break;
  }
  return out;
}

async function getSectorListLocal(market) {
  const data = await getSectorSeed();
  const sectors = new Set();
  data.forEach((item) => {
    const itemMarket = String(item.market || "").toUpperCase();
    if (market !== "ALL" && itemMarket !== market) return;
    const sector = String(item.sector || "").trim();
    if (sector) sectors.add(sector);
  });
  return Array.from(sectors).sort();
}

async function getSectorStocksLocal(market, sector, limit = 40) {
  const data = await getSectorSeed();
  const key = normalizeSearchText(sector);
  const out = [];
  for (const item of data) {
    const itemMarket = String(item.market || "").toUpperCase();
    if (market !== "ALL" && itemMarket !== market) continue;
    if (normalizeSearchText(item.sector || "") !== key) continue;
    out.push({
      ticker: itemMarket === "KR" ? normalizeKRTicker(item.ticker) : String(item.ticker || "").toUpperCase(),
      name: String(item.name || ""),
      sector: String(item.sector || ""),
      market: itemMarket,
      source: "local_seed_fallback",
      rank: 0,
    });
    if (out.length >= Math.max(1, Math.min(limit, 200))) break;
  }
  return out;
}

function isLikelyTicker(input, market) {
  const raw = String(input || "").trim();
  if (!raw) return false;
  if (market === "KR") return /^[0-9]{4,6}$/.test(raw);
  // US ticker heuristic:
  // - Typical symbols are <= 5 chars (e.g., AAPL, GOOGL, TSLA)
  // - Allow class suffix style (e.g., BRK.B, BRK-B)
  return /^[A-Za-z]{1,5}([.\-][A-Za-z0-9]{1,4})?$/.test(raw);
}

async function resolveTickerInput(rawInput, market) {
  const raw = String(rawInput || "").trim();
  if (!raw) return { ticker: "", name: "" };
  if (market === "ALL") {
    try {
      const allRes = await fetchApi(
        `/api/company-lookup?query=${encodeURIComponent(raw)}&market=ALL&limit=5`
      );
      const first = (allRes.items || [])[0];
      if (first?.ticker) {
        const firstMarket = String(first.market || "US").toUpperCase();
        return {
          ticker: firstMarket === "KR" ? normalizeKRTicker(first.ticker) : String(first.ticker).toUpperCase(),
          name: String(first.name || ""),
          market: firstMarket,
        };
      }
    } catch (_err) {
      // local fallback below
    }
    const local = await lookupCompanyLocal(raw, "ALL", 1);
    const firstLocal = local[0];
    if (firstLocal?.ticker) {
      const firstMarket = String(firstLocal.market || "US").toUpperCase();
      return { ticker: firstLocal.ticker, name: String(firstLocal.name || ""), market: firstMarket };
    }
    // Heuristic fallback when all lookup failed.
    if (/^[0-9]{4,6}$/.test(raw)) {
      return { ticker: normalizeKRTicker(raw), name: "", market: "KR" };
    }
    return { ticker: raw.toUpperCase(), name: "", market: "US" };
  }
  if (isLikelyTicker(raw, market)) {
    return { ticker: market === "KR" ? normalizeKRTicker(raw) : raw.toUpperCase(), name: "", market };
  }
  // For name-like US text (e.g., GOOGLE), try lookup first instead of forcing ticker.
  const looksNameLikeUs = market === "US" && /^[A-Za-z][A-Za-z\s]{4,}$/.test(raw);
  if (looksNameLikeUs) {
    try {
      const res = await fetchApi(
        `/api/company-lookup?query=${encodeURIComponent(raw)}&market=US&limit=1`
      );
      const first = (res.items || [])[0];
      if (first?.ticker) {
        return {
          ticker: String(first.ticker).toUpperCase(),
          name: String(first.name || ""),
          market: "US",
        };
      }
    } catch (_err) {
      // fallback below
    }
  }
  try {
    const res = await fetchApi(
      `/api/company-lookup?query=${encodeURIComponent(raw)}&market=${encodeURIComponent(market)}&limit=1`
    );
    const first = (res.items || [])[0];
    if (first?.ticker) {
      return {
        ticker: market === "KR" ? normalizeKRTicker(first.ticker) : String(first.ticker).toUpperCase(),
        name: String(first.name || ""),
        market,
      };
    }
  } catch (_err) {
    // fallback below
  }
  const local = await lookupCompanyLocal(raw, market, 1);
  const firstLocal = local[0];
  if (firstLocal?.ticker) {
    return { ticker: firstLocal.ticker, name: String(firstLocal.name || ""), market };
  }
  return { ticker: market === "KR" ? normalizeKRTicker(raw) : raw.toUpperCase(), name: "", market };
}

async function loadSectorOptions() {
  const userId = getUserId();
  const market = String(els.intelMarket.value || "US").toUpperCase();
  let sectors = [];
  try {
    const res = await fetchApi(`/api/sector-list?user_id=${encodeURIComponent(userId)}&market=${encodeURIComponent(market)}`);
    sectors = res.sectors || [];
  } catch (_err) {
    sectors = await getSectorListLocal(market);
  }
  const options = [`<option value="">섹터 선택</option>`].concat(sectors.map((s) => `<option value="${escapeHtml(s)}">${escapeHtml(s)}</option>`));
  els.sectorSelect.innerHTML = options.join("");
}

async function searchCompanyByName() {
  showLoadingOverlay("회사명을 검색하고 데이터를 조회하는 중...");
  try {
  const spotlightRaw = String(els.spotlightQuery?.value || "").trim();
  const parsed = applySpotlightToInputs(spotlightRaw);
  const q = String(els.companyQuery.value || "").trim();
  const market = String(els.intelMarket.value || parsed.market || "US").toUpperCase();
  const queryHasHangul = hasHangulText(q);
  if (!q) throw new Error("회사 이름을 입력하세요.");
  let items = [];
  let usedFallback = false;
  let lookupOrder = [market, "ALL"];
  if (queryHasHangul) {
    if (market === "US") lookupOrder = ["US", "ALL", "KR"];
    else if (market === "KR") lookupOrder = ["KR", "ALL", "US"];
    else lookupOrder = ["KR", "US", "ALL"];
  }
  for (const lookupMarket of lookupOrder) {
    if (items.length) break;
    try {
      const res = await fetchApi(
        `/api/company-lookup?query=${encodeURIComponent(q)}&market=${encodeURIComponent(lookupMarket)}&limit=20`
      );
      items = res.items || [];
    } catch (_err) {
      items = await lookupCompanyLocal(q, lookupMarket, 20);
      usedFallback = true;
    }
  }
  if (!items.length) {
    items = await lookupCompanyLocal(q, "ALL", 40);
    usedFallback = true;
  }
  if (!items.length) {
    const watchlistItems = await lookupCompanyFromWatchlist(q, market);
    if (watchlistItems.length) items = watchlistItems;
  }
  if (queryHasHangul && market !== "US") {
    const krItems = items.filter((x) => String(x.market || "").toUpperCase() === "KR");
    if (krItems.length) items = krItems;
  }
  const preferredMarket = queryHasHangul && market !== "US" ? "KR" : market;
  items = sortCompanyItems(items, preferredMarket);
  renderRelatedStocks(items, "검색 결과 없음");
  const first = items[0];
  const bestSector = String(pickBestSectorFromItems(items, first?.name || q) || "").trim();
  if (bestSector) {
    const options = Array.from(els.sectorSelect.options || []).map((o) => o.value);
    if (!options.includes(bestSector)) {
      const option = document.createElement("option");
      option.value = bestSector;
      option.textContent = bestSector;
      els.sectorSelect.appendChild(option);
    }
    els.sectorSelect.value = bestSector;
  }
  if (usedFallback) {
    els.intelMeta.textContent = "회사명 검색: 로컬 데이터로 조회";
  }
  if (first?.ticker) {
    const pickedMarket = String(first.market || market).toUpperCase();
    const pickedTicker = pickedMarket === "KR" ? normalizeKRTicker(first.ticker) : String(first.ticker).toUpperCase();
    els.intelTicker.value = pickedTicker;
    if (pickedMarket === "US" || pickedMarket === "KR") {
      els.intelMarket.value = pickedMarket;
    }
    els.techQuery.value = inferTechKeywords(bestSector, first?.name || q, first?.ticker || "");
    if (bestSector) {
      await loadStocksBySector(bestSector, { showOverlay: false, includeRanked: false }).catch(() => {
        // no-op
      });
    } else {
      await loadStocksBySector("", { showOverlay: false, includeRanked: false }).catch(() => {
        // no-op
      });
    }
    await loadIntelligence({ showOverlay: false });
  } else {
    els.intelMeta.textContent = "검색 결과가 없습니다. 회사명을 더 정확히 입력해 주세요.";
  }
  } finally {
    hideLoadingOverlay();
  }
}

async function submitSpotlightQuery() {
  const raw = String(els.spotlightQuery?.value || "").trim();
  const parsed = applySpotlightToInputs(raw);
  const queryText = String(parsed.query || "").trim();
  if (!queryText) throw new Error("검색어를 입력하세요.");
  if (els.intelMeta) {
    els.intelMeta.textContent = "통합 검색 실행 중...";
    els.intelMeta.style.background = "#eef2ff";
    els.intelMeta.style.color = "#334155";
  }
  const market = String(els.intelMarket?.value || "US").toUpperCase();
  if (isLikelyTicker(queryText, market)) {
    els.intelTicker.value = market === "KR" ? normalizeKRTicker(queryText) : queryText.toUpperCase();
    await loadIntelligence();
    return;
  }
  await searchCompanyByName();
}

async function loadStocksBySector(forcedSector = "", options = {}) {
  const showOverlay = options.showOverlay !== false;
  const includeRanked = options.includeRanked === true;
  if (showOverlay) showLoadingOverlay("섹터 관련 종목을 불러오는 중...");
  try {
  const userId = getUserId();
  const market = String(els.intelMarket.value || "US").toUpperCase();
  const baseTickerRaw = String(els.intelTicker.value || "").trim().toUpperCase();
  const baseTicker = market === "KR" ? normalizeKRTicker(baseTickerRaw) : baseTickerRaw;
  const baseName = String(els.companyQuery.value || "").trim();
  const sector = String(forcedSector || els.sectorSelect.value || "").trim();
  const keywordText = `${String(els.techQuery.value || "")} ${baseName}`.trim();
  let relatedSectors = inferRelatedSectorsFromKeywords(keywordText, sector);
  if (!relatedSectors.length) {
    const inferredByName = inferSectorByName(baseName);
    if (inferredByName) relatedSectors = [inferredByName];
  }
  relatedSectors = relatedSectors.filter((s) => !["기타", "UNCLASSIFIED", "미분류"].includes(String(s || "").trim()));

  let allItems = [];
  let usedFallback = false;
  if (relatedSectors.length) {
    renderRelatedSectorChips(relatedSectors);
    if (els.intelMeta) {
      els.intelMeta.textContent = `연관 섹터 비교: ${relatedSectors.join(" · ")}`;
    }
    const sectorResults = await Promise.all(
      relatedSectors.map((s) => fetchSectorStocksCached(userId, market, s, 30, includeRanked))
    );
    allItems = sectorResults.flatMap((res) => res.items || []);
    usedFallback = sectorResults.some((res) => String(res.source || "").includes("fallback"));
  } else {
    renderRelatedSectorChips([]);
  }

  let providerTicker = baseTicker;
  if (!providerTicker && baseName) {
    const resolved = await resolveTickerInput(baseName, market);
    const resolvedTicker = String(resolved.ticker || "").trim().toUpperCase();
    providerTicker = market === "KR" ? normalizeKRTicker(resolvedTicker) : resolvedTicker;
  }

  if (allItems.length < 5) {
    if (providerTicker) {
      try {
        const rel = await fetchApi(
          `/api/related-stocks?ticker=${encodeURIComponent(providerTicker)}&market=${encodeURIComponent(market)}&limit=30`
        );
        const relItems = (rel.items || []).map((x) => ({
          ticker: String(x.ticker || "").toUpperCase(),
          name: String(x.name || x.ticker || ""),
          sector: String(x.sector || "").trim() || "동일업종",
          market: String(x.market || market).toUpperCase(),
          source: "related_provider",
          rank: Number(x.rank || 0),
        }));
        if (relItems.length) {
          allItems.push(...relItems);
          if (els.intelMeta) {
            els.intelMeta.textContent = "동일업종/유사종목 자동수집 반영";
          }
        }
      } catch (_err) {
        // no-op
      }
    }
  }

  if (allItems.length < 5) {
    let resolvedBaseName = baseName;
    if (!resolvedBaseName && baseTicker) {
      resolvedBaseName = await getLocalCompanyNameByTicker(baseTicker, market);
    }
    const familyItems = await fetchFamilyRelatedStocks(resolvedBaseName, baseTicker, market, 30);
    if (familyItems.length) {
      allItems.push(...familyItems);
      if (els.intelMeta) {
        const family = extractFamilyToken(resolvedBaseName, baseTicker);
        els.intelMeta.textContent = `종목군(브랜드) 기반 확장: ${family}`;
      }
    }
  }

  const merged = [];
  const seen = new Set();
  for (const it of allItems) {
    const key = `${String(it.market || "")}:${String(it.ticker || "").toUpperCase()}`;
    if (seen.has(key)) continue;
    seen.add(key);
    merged.push(it);
  }
  merged.sort((a, b) => {
    const sa = String(a.sector || "");
    const sb = String(b.sector || "");
    const ia = relatedSectors.indexOf(sa);
    const ib = relatedSectors.indexOf(sb);
    if (ia !== ib) return (ia < 0 ? 99 : ia) - (ib < 0 ? 99 : ib);
    return String(a.name || a.ticker || "").localeCompare(String(b.name || b.ticker || ""), "ko");
  });
  if (!relatedSectors.length) {
    const inferMap = new Map();
    for (const item of merged) {
      const s = String(item.sector || "").trim();
      if (!s || ["기타", "미분류", "UNCLASSIFIED", "동일업종"].includes(s)) continue;
      inferMap.set(s, (inferMap.get(s) || 0) + 1);
    }
    const inferredSectors = Array.from(inferMap.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, 4)
      .map((x) => x[0]);
    renderRelatedSectorChips(inferredSectors);
    if (inferredSectors.length && els.intelMeta) {
      els.intelMeta.textContent = `연관 섹터(관련종목 기반): ${inferredSectors.join(" · ")}`;
    }
  }
  await enrichRelatedStocksWithQuotes(merged);
  renderRelatedStocks(merged, "섹터 종목 없음");
  if (usedFallback) {
    els.intelMeta.textContent = "섹터 종목: 로컬 데이터로 조회";
  }
  } finally {
    if (showOverlay) hideLoadingOverlay();
  }
}

function getUserId() {
  const current = els.userId ? String(els.userId.value || "").trim() : "";
  const userId = current || "default";
  if (els.userId) els.userId.value = userId;
  localStorage.setItem("stock_user_id", userId);
  return userId;
}

function renderWatchlist(items) {
  const rows = (items || []).map((item) => {
    const tickerRaw = String(item.ticker || "-");
    const ticker = escapeHtml(tickerRaw);
    const companyNameRaw = String(item.company_name || item.ticker || "-");
    const companyName = escapeHtml(companyNameRaw);
    const market = String(item.market || "US").toUpperCase();
    const same = companyNameRaw.replaceAll(" ", "") === tickerRaw.replaceAll(" ", "");
    const title = same ? `<strong>${ticker}</strong>` : `<strong>${companyName}</strong> <small>(${ticker})</small>`;
    return `<li>${title} <small>[${marketLabel(market)}]</small> <button class="btn ghost" aria-label="관심종목 삭제" data-remove-ticker="${ticker}" data-remove-market="${escapeHtml(market)}">🗑 삭제</button></li>`;
  });
  renderSimpleList(els.watchlistView, rows, "관심종목 없음");
}

function renderNotifications(items) {
  const rows = (items || []).map((n) => {
    const ticker = escapeHtml(n.ticker || "-");
    const kind = escapeHtml(n.kind || "-");
    const msg = escapeHtml(n.message || "");
    const dt = escapeHtml(String(n.created_at || "").slice(0, 19));
    return `<li><strong>${ticker}</strong> [${kind}] ${msg} <small>${dt}</small></li>`;
  });
  renderSimpleList(els.notificationView, rows, "알림 없음");
}

function renderRanking(items) {
  const rows = (items || []).map((r, idx) => {
    const ticker = escapeHtml(r.ticker || "-");
    const market = String(r.market || "US").toUpperCase();
    const companyName = escapeHtml(r.company_name || r.fundamentals?.name || r.ticker || "-");
    const rank = Number(r.undervalued_rank || 0).toFixed(1);
    const label = escapeHtml(rankLabelKo(r.label || "-"));
    const q = Number(r.quality_score || 0).toFixed(1);
    const m = Number(r.tech_moat_score || 0).toFixed(1);
    const i = Number(r.capital_power_score ?? 0).toFixed(1);
    const mi = Number(r.market_impact_score ?? 0).toFixed(1);
    const v = Number(r.valuation_score || 0).toFixed(1);
    const heat = Number(r.sector_heat_score ?? 0).toFixed(1);
    const resilience = Number(r.resilience_score ?? 0).toFixed(1);
    const heatLabel = escapeHtml(r.sector_heat_label || "중립");
    const sector = escapeHtml(r.sector || "-");
    const secRank = Number(r.sector_rank || 0);
    const secSize = Number(r.sector_size || 0);
    const secPct = Number(r.sector_percentile || 0).toFixed(1);
    const secText = secRank > 0 && secSize > 0 ? `${sector} #${secRank}/${secSize} (상위 ${secPct}%)` : sector;
    return `<li><strong>#${idx + 1} ${companyName}</strong> <small>(${ticker}) [${marketLabel(market)}] 종합점수 ${rank}점 (${label}) | ${secText} | 밸류 ${v} / 기술력 ${m} / 자본력 ${i} / 시장영향 ${mi} / 품질 ${q} | 섹터열기 ${heat} · 체력 ${resilience} (${heatLabel})</small></li>`;
  });
  renderSimpleList(els.rankingView, rows, "랭킹 데이터 없음");
}

async function refreshRanking() {
  const userId = getUserId();
  const res = await fetchApi(`/api/ranking?user_id=${encodeURIComponent(userId)}&limit=50`);
  const enriched = await enrichRankingCompanyNames(res.items || []);
  renderRanking(enriched);
}

function renderSectors(sectors) {
  const rows = (sectors || []).map((s) => {
    const name = escapeHtml(s.sector || "UNCLASSIFIED");
    const count = Number(s.count || 0);
    const avg = Number(s.avg_rank || 0).toFixed(1);
    const tickers = (s.items || [])
      .slice(0, 6)
      .map((it) => `${escapeHtml(it.ticker || "-")}(${escapeHtml(it.market || "US")})`)
      .join(", ");
    return `<li><strong>${name}</strong> | ${count}종목 | 평균랭크 ${avg} <small>${tickers}</small></li>`;
  });
  renderSimpleList(els.sectorView, rows, "섹터 데이터 없음");
}

async function refreshSectors() {
  const userId = getUserId();
  const res = await fetchApi(`/api/sectors?user_id=${encodeURIComponent(userId)}&limit=80`);
  renderSectors(res.sectors || []);
}

async function refreshAutoPanel() {
  const userId = getUserId();
  const [watchlistRes, channelsRes, notifRes] = await Promise.all([
    fetchApi(`/api/watchlist?user_id=${encodeURIComponent(userId)}`),
    fetchApi(`/api/channels?user_id=${encodeURIComponent(userId)}`),
    fetchApi(`/api/notifications?user_id=${encodeURIComponent(userId)}&limit=20`),
  ]);
  const watchlistItems = await enrichWatchlistCompanyNames(watchlistRes.items || []);
  latestWatchlistItems = watchlistItems;
  renderWatchlist(watchlistItems);
  renderNotifications(notifRes.items || []);

  const channels = channelsRes.channels || {};
  els.notifyEmail.value = channels.email || "";
  els.notifyWebhook.value = channels.webhook_url || "";
  els.onesignalExternalId.value = channels.onesignal_external_id || "";
  els.pushEnabled.checked = Number(channels.push_enabled || 0) === 1;
  els.autoMeta.textContent = `${userId} | 관심 ${String((watchlistRes.items || []).length)}종목`;
  syncHeaderWatchButtonState();
  await refreshRanking();
  await refreshSectors();
}

async function addWatchItem() {
  const userId = getUserId();
  const ticker = String(els.watchTicker.value || "").trim().toUpperCase();
  const market = String(els.watchMarket.value || "US").toUpperCase();
  if (!ticker) throw new Error("관심 티커를 입력하세요.");
  await fetchApiPost("/api/watchlist", { user_id: userId, ticker, market });
  els.watchTicker.value = "";
  await refreshAutoPanel();
}

async function saveAlertRules() {
  const userId = getUserId();
  const ticker = String(els.watchTicker.value || els.intelTicker.value || "").trim().toUpperCase();
  const market = String(els.watchMarket.value || els.intelMarket.value || "US").toUpperCase();
  if (!ticker) throw new Error("알림 규칙 적용할 티커를 입력하세요.");
  const price = Number.parseFloat(String(els.priceThreshold.value || "5"));
  const hype = Number.parseFloat(String(els.hypeThreshold.value || "15"));
  await fetchApiPost("/api/alerts/defaults", {
    user_id: userId,
    ticker,
    market,
    price_change_pct: Number.isFinite(price) ? price : 5,
    hype_score_jump: Number.isFinite(hype) ? hype : 15,
    new_filing_enabled: !!els.filingEnabled.checked,
  });
  els.autoMeta.textContent = `${ticker} 규칙 저장 완료`;
}

async function saveChannels() {
  const userId = getUserId();
  await fetchApiPost("/api/channels", {
    user_id: userId,
    email: String(els.notifyEmail.value || "").trim(),
    webhook_url: String(els.notifyWebhook.value || "").trim(),
    onesignal_external_id: String(els.onesignalExternalId.value || "").trim(),
    push_enabled: !!els.pushEnabled.checked,
  });
  els.autoMeta.textContent = `${userId} 채널 저장 완료`;
}

async function sendTestNotification() {
  const userId = getUserId();
  const ticker = String(els.watchTicker.value || els.intelTicker.value || "TEST").trim().toUpperCase();
  const market = String(els.watchMarket.value || els.intelMarket.value || "US").toUpperCase();
  const result = await fetchApiPost("/api/test-notification", { user_id: userId, ticker, market });
  const r = result.result || {};
  els.autoMeta.textContent = `테스트 발송: email=${r.email_sent ? "Y" : "N"}, webhook=${r.webhook_sent ? "Y" : "N"}, push=${r.push_sent ? "Y" : "N"}`;
  await refreshAutoPanel();
}

async function runScanNow() {
  const userId = getUserId();
  const result = await fetchApiPost("/api/scan", { user_id: userId });
  const triggered = (result.triggered || []).length;
  els.autoMeta.textContent = `즉시 스캔 완료: ${triggered}건 트리거`;
  await refreshAutoPanel();
}

async function removeWatchTicker(ticker, market) {
  const userId = getUserId();
  const path = `/api/watchlist?user_id=${encodeURIComponent(userId)}&ticker=${encodeURIComponent(ticker)}&market=${encodeURIComponent(market || "US")}`;
  const res = await fetch(path, { method: "DELETE" });
  if (!res.ok) throw new Error(`API ${res.status}`);
  await refreshAutoPanel();
}

async function loadDecisionIntelPanel(ticker, market) {
  if (!ticker) return;
  const horizon = String(els.prefHorizon?.value || "mid");
  const risk = String(els.prefRisk?.value || "neutral");
  const fx = Number.parseFloat(String(els.scenarioFx?.value || "0"));
  const ev = Number.parseFloat(String(els.scenarioEv?.value || "5"));
  if (els.scenarioFxText) els.scenarioFxText.textContent = `${Number.isFinite(fx) ? fx.toFixed(1) : "0.0"}%`;
  if (els.scenarioEvText) els.scenarioEvText.textContent = `${Number.isFinite(ev) ? ev.toFixed(0) : "5"}%`;

  const res = await fetchApi(
    `/api/decision-intel?ticker=${encodeURIComponent(ticker)}&market=${encodeURIComponent(market)}&horizon=${encodeURIComponent(horizon)}&risk=${encodeURIComponent(risk)}&fx_change_pct=${encodeURIComponent(Number.isFinite(fx) ? fx : 0)}&ev_growth_pct=${encodeURIComponent(Number.isFinite(ev) ? ev : 5)}`
  );
  if (window.DecisionUI) {
    window.DecisionUI.renderDecisionPanel(els.decisionPanelCard, res, {
      assumptionChanged,
      horizon,
      risk,
      fx: Number.isFinite(fx) ? fx : 0,
      ev: Number.isFinite(ev) ? ev : 5,
    });
    window.DecisionUI.renderRelativeComparison(els.relativeComparisonCard, res, { assumptionChanged });
    window.DecisionUI.renderScenario(els.scenarioAnalyzerCard, res, {
      assumptionChanged,
      fx: Number.isFinite(fx) ? fx : 0,
      ev: Number.isFinite(ev) ? ev : 5,
    });
  }
  return res;
}

async function loadIntelligence(options = {}) {
  const showOverlay = options.showOverlay !== false;
  if (showOverlay) showLoadingOverlay("종목 인텔리전스를 조회하는 중...");
  try {
  const rawInput = String(els.intelTicker.value || "").trim();
  let market = String(els.intelMarket.value || "US").trim().toUpperCase();
  const techQuery = String(els.techQuery.value || "").trim();
  if (!rawInput) {
    throw new Error("티커를 입력하세요.");
  }
  const resolved = await resolveTickerInput(rawInput, market);
  market = String(resolved.market || market).toUpperCase();
  if (market === "ALL") {
    throw new Error("시장 자동 판별에 실패했습니다. KR 또는 US를 선택해 주세요.");
  }
  const ticker = resolved.ticker;
  if (!ticker) throw new Error("종목코드를 찾지 못했습니다. 회사명 검색으로 먼저 선택해 주세요.");
  if (ticker !== rawInput) {
    els.intelTicker.value = ticker;
  }
  els.intelMarket.value = market;
  if (els.spotlightQuery) {
    const q = String(els.companyQuery?.value || resolved.name || ticker).trim();
    els.spotlightQuery.value = `${q || ticker} m:${market}`;
  }
  const displayName = (resolved.name || (await getLocalCompanyNameByTicker(ticker, market)) || rawInput).trim();

  els.intelMeta.textContent = `${ticker} (${market}) 조회 중...`;
  els.intelMeta.style.background = "#eef3ff";
  els.intelMeta.style.color = "#2f4d7a";

  const encodedTicker = encodeURIComponent(ticker);
  const encodedMarket = encodeURIComponent(market);
  const encodedQuery = encodeURIComponent(techQuery || resolved.name || rawInput);
  const feedCfg = getFeedConfig();
  newsExpanded = false;
  filingExpanded = false;
  techExpanded = false;
  renderFeedSkeleton(els.newsList, 5);
  renderFeedSkeleton(els.filingList, 4);
  renderFeedSkeleton(els.techList, 4);

  const [quoteRes, fundamentalsRes, newsRes, filingsRes, technologyRes, historyRes] = await Promise.allSettled([
    fetchApi(`/api/quote?ticker=${encodedTicker}&market=${encodedMarket}`),
    fetchApi(`/api/fundamentals?ticker=${encodedTicker}&market=${encodedMarket}`),
    fetchApi(`/api/news?ticker=${encodedTicker}&market=${encodedMarket}&days=${feedCfg.newsDays}&limit=${feedCfg.newsLimit}`),
    fetchApi(`/api/filings?ticker=${encodedTicker}&market=${encodedMarket}&limit=${feedCfg.filingLimit}`),
    fetchApi(`/api/technology?query=${encodedQuery}&limit=${feedCfg.techLimit}`),
    fetchApi(`/api/price-history?ticker=${encodedTicker}&market=${encodedMarket}&period=3mo`),
  ]);
  const quoteData =
    quoteRes.status === "fulfilled" ? quoteRes.value : { ok: false, error: quoteRes.reason?.message };
  const fundData =
    fundamentalsRes.status === "fulfilled"
      ? fundamentalsRes.value
      : { ok: false, error: fundamentalsRes.reason?.message };
  const newsData =
    newsRes.status === "fulfilled" ? newsRes.value : { ok: false, error: newsRes.reason?.message };
  const filingData =
    filingsRes.status === "fulfilled"
      ? filingsRes.value
      : { ok: false, error: filingsRes.reason?.message };
  const techData =
    technologyRes.status === "fulfilled"
      ? technologyRes.value
      : { ok: false, error: technologyRes.reason?.message };
  const historyData =
    historyRes.status === "fulfilled"
      ? historyRes.value
      : { ok: false, error: historyRes.reason?.message };

  if (quoteData?.ok && (!quoteData.name || String(quoteData.name).trim() === ticker)) {
    quoteData.name = displayName;
  }
  if (fundData?.ok && (!fundData.name || String(fundData.name).trim() === ticker)) {
    fundData.name = displayName;
  }

  let summaryData = null;
  try {
    summaryData = await fetchApi(`/api/intel-summary?ticker=${encodedTicker}&market=${encodedMarket}&query=${encodedQuery}`);
  } catch (_err) {
    summaryData = buildLocalSummaryPayload(ticker, market, quoteData, fundData, newsData, filingData, techData);
  }

  renderIntelSummary(summaryData);
  latestQuoteData = quoteData;
  renderQuoteCard(quoteData);
  latestHistory3M = historyData?.ok ? historyData.points || [] : [];
  renderPriceHistoryChart(historyPeriod);
  renderFundamentalCard(fundData);
  renderValuationExplain(fundData);
  renderNews(newsData);
  renderFilings(filingData);
  renderTechnology(techData);
  latestDecisionTicker = ticker;
  latestDecisionMarket = market;
  const decisionData = await loadDecisionIntelPanel(ticker, market).catch(() => {
    // no-op
    return null;
  });
  updateStockHeaderSummary({
    ticker,
    market,
    name: displayName,
    quoteData,
    decisionData,
  });
  markAssumptionChangedUI(assumptionChanged);
  syncHeaderWatchButtonState();

  els.intelMeta.textContent = `${ticker} (${market}) 조회 완료`;
  } finally {
    if (showOverlay) hideLoadingOverlay();
  }
}

function showError(message) {
  if (!els.resultMeta) return;
  els.resultMeta.textContent = message;
  els.resultMeta.style.background = "#ffe9e9";
  els.resultMeta.style.color = "#8c1d18";
}

function resetMeta() {
  if (!els.resultMeta) return;
  els.resultMeta.style.background = "#eef3ff";
  els.resultMeta.style.color = "#2f4d7a";
}

function bindEvents() {
  if (els.csvFile) {
    els.csvFile.addEventListener("change", (ev) => {
      handleFileSelect(ev).catch((err) => showError(err.message));
    });
  }
  if (els.loadSampleBtn) {
    els.loadSampleBtn.addEventListener("click", () => {
      loadSample().then(resetMeta).catch((err) => showError(err.message));
    });
  }
  if (els.analyzeBtn && els.csvText) {
    els.analyzeBtn.addEventListener("click", () => {
      resetMeta();
      try {
        runAnalysis(els.csvText.value);
      } catch (err) {
        showError(err.message);
      }
    });
  }
  if (els.exportBtn) {
    els.exportBtn.addEventListener("click", exportResults);
  }

  if (els.headerAlertSetupBtn) {
    els.headerAlertSetupBtn.addEventListener("click", () => {
      activatePage("auto");
      setTimeout(() => {
        els.watchTicker?.focus();
      }, 0);
    });
  }
  if (els.headerShareBtn) {
    els.headerShareBtn.addEventListener("click", async () => {
      const ticker = String(els.intelTicker?.value || "").trim().toUpperCase();
      const market = String(els.intelMarket?.value || "US").toUpperCase();
      const name = String(els.summaryCompanyName?.textContent || "").trim();
      const text = `[Stock Insight] ${name} (${ticker}, ${market}) | ${String(els.summarySignal?.textContent || "").trim()}`;
      try {
        await navigator.clipboard.writeText(text);
        if (els.intelMeta) els.intelMeta.textContent = "리포트 요약이 클립보드에 복사되었습니다.";
      } catch (_err) {
        if (els.intelMeta) els.intelMeta.textContent = "클립보드 복사 권한이 필요합니다.";
      }
    });
  }
  if (els.headerWatchToggleBtn) {
    els.headerWatchToggleBtn.addEventListener("click", () => {
      const ticker = String(els.intelTicker?.value || "").trim().toUpperCase();
      const market = String(els.intelMarket?.value || "US").toUpperCase();
      if (!ticker) return;
      if (watchlistContains(ticker, market)) {
        removeWatchTicker(ticker, market).catch((err) => {
          els.autoMeta.textContent = `오류: ${err.message}`;
        });
      } else {
        els.watchTicker.value = ticker;
        els.watchMarket.value = market;
        addWatchItem().catch((err) => {
          els.autoMeta.textContent = `오류: ${err.message}`;
        });
      }
    });
  }
  if (els.mobileViewCoreBtn) {
    els.mobileViewCoreBtn.addEventListener("click", () => setMobileView("core"));
  }
  if (els.mobileViewDetailBtn) {
    els.mobileViewDetailBtn.addEventListener("click", () => setMobileView("detail"));
  }
  if (els.mobileViewFeedBtn) {
    els.mobileViewFeedBtn.addEventListener("click", () => setMobileView("feed"));
  }
  window.addEventListener("resize", () => setMobileView(currentMobileView));

  if (els.loadIntelBtn) {
    els.loadIntelBtn.dataset.boundPrimary = "1";
    els.loadIntelBtn.addEventListener("click", () => {
      loadIntelligence().catch((err) => {
        if (els.intelMeta) {
          els.intelMeta.textContent = `오류: ${err.message}`;
          els.intelMeta.style.background = "#ffe9e9";
          els.intelMeta.style.color = "#8c1d18";
        }
      });
    });
  }

  if (els.searchCompanyBtn) {
    els.searchCompanyBtn.dataset.boundPrimary = "1";
    els.searchCompanyBtn.addEventListener("click", () => {
      searchCompanyByName().catch((err) => {
        els.intelMeta.textContent = `오류: ${err.message}`;
      });
    });
  }
  if (els.spotlightSearchBtn) {
    els.spotlightSearchBtn.addEventListener("click", () => {
      submitSpotlightQuery().catch((err) => {
        if (els.intelMeta) {
          els.intelMeta.textContent = `오류: ${err.message}`;
          els.intelMeta.style.background = "#fee2e2";
          els.intelMeta.style.color = "#b91c1c";
        }
      });
    });
  }
  if (els.spotlightQuery) {
    els.spotlightQuery.addEventListener("keydown", (ev) => {
      if (ev.key !== "Enter") return;
      ev.preventDefault();
      submitSpotlightQuery().catch((err) => {
        if (els.intelMeta) {
          els.intelMeta.textContent = `오류: ${err.message}`;
          els.intelMeta.style.background = "#fee2e2";
          els.intelMeta.style.color = "#b91c1c";
        }
      });
    });
  }
  if (els.loadSectorBtn) {
    els.loadSectorBtn.addEventListener("click", () => {
      loadStocksBySector().catch((err) => {
        els.intelMeta.textContent = `오류: ${err.message}`;
      });
    });
  }
  if (els.intelMarket) {
    els.intelMarket.addEventListener("change", () => {
      loadSectorOptions().catch(() => {
        // no-op
      });
    });
  }
  if (els.relatedStocksList) {
    els.relatedStocksList.addEventListener("click", async (ev) => {
      const target = ev.target;
      if (!(target instanceof HTMLElement)) return;
      const compareTicker = target.getAttribute("data-compare-ticker");
      if (compareTicker) {
        const ok = upsertCompareItem({
          ticker: compareTicker,
          market: target.getAttribute("data-compare-market") || "US",
          name: target.getAttribute("data-compare-name") || compareTicker,
          sector: target.getAttribute("data-compare-sector") || "",
        });
        if (!ok) {
          if (els.sectorCompareMeta) {
            els.sectorCompareMeta.textContent = "비교는 최대 4개 종목까지 가능합니다.";
          }
          return;
        }
        await renderSectorComparePanel(currentCompareTab);
        return;
      }
      const ticker = target.getAttribute("data-pick-ticker");
      const market = target.getAttribute("data-pick-market");
      const name = target.getAttribute("data-pick-name");
      const sector = target.getAttribute("data-pick-sector");
      if (!ticker) return;
      showLoadingOverlay("선택 종목을 기준으로 비교/인텔리전스를 갱신하는 중...");
      try {
        els.intelTicker.value = ticker;
        if (market) els.intelMarket.value = market;
        els.watchTicker.value = ticker;
        if (market) els.watchMarket.value = market;
        if (name) els.companyQuery.value = name;
        if (name && els.spotlightQuery) els.spotlightQuery.value = `${name}${market ? ` m:${market}` : ""}`;
        if (sector) {
          const options = Array.from(els.sectorSelect.options || []).map((o) => o.value);
          if (!options.includes(sector)) {
            const option = document.createElement("option");
            option.value = sector;
            option.textContent = sector;
            els.sectorSelect.appendChild(option);
          }
          els.sectorSelect.value = sector;
        }
        const autoSector = sector || inferSectorByName(name || ticker);
        if (autoSector && !els.sectorSelect.value) {
          const options = Array.from(els.sectorSelect.options || []).map((o) => o.value);
          if (!options.includes(autoSector)) {
            const option = document.createElement("option");
            option.value = autoSector;
            option.textContent = autoSector;
            els.sectorSelect.appendChild(option);
          }
          els.sectorSelect.value = autoSector;
        }
        els.techQuery.value = inferTechKeywords(els.sectorSelect.value || autoSector, name || ticker, ticker);
        if (els.sectorSelect.value) {
          await loadStocksBySector("", { showOverlay: false, includeRanked: false }).catch(() => {
            // no-op
          });
        }
        await loadIntelligence({ showOverlay: false }).catch(() => {
          // no-op
        });
        syncHeaderWatchButtonState();
      } finally {
        hideLoadingOverlay();
      }
    });
  }
  if (els.sectorCompareSelected) {
    els.sectorCompareSelected.addEventListener("click", (ev) => {
      const target = ev.target;
      if (!(target instanceof HTMLElement)) return;
      const key = target.getAttribute("data-compare-remove");
      if (!key) return;
      removeCompareItem(key);
      renderSectorComparePanel(currentCompareTab).catch(() => {
        // no-op
      });
    });
  }
  if (els.sectorCompareTabs) {
    els.sectorCompareTabs.addEventListener("click", (ev) => {
      const target = ev.target;
      if (!(target instanceof HTMLElement)) return;
      const tab = String(target.getAttribute("data-compare-tab") || "").trim();
      if (!tab) return;
      currentCompareTab = tab;
      const btns = Array.from(els.sectorCompareTabs.querySelectorAll("[data-compare-tab]"));
      btns.forEach((btn) => {
        const same = btn.getAttribute("data-compare-tab") === tab;
        btn.classList.toggle("active", same);
        btn.classList.toggle("secondary", same);
        btn.classList.toggle("ghost", !same);
      });
      renderSectorComparePanel(tab).catch(() => {
        // no-op
      });
    });
  }
  if (els.relatedPrevBtn) {
    els.relatedPrevBtn.addEventListener("click", () => {
      els.relatedStocksList?.scrollBy({ left: -320, behavior: "smooth" });
    });
  }
  if (els.relatedNextBtn) {
    els.relatedNextBtn.addEventListener("click", () => {
      els.relatedStocksList?.scrollBy({ left: 320, behavior: "smooth" });
    });
  }
  if (els.quoteCard) {
    els.quoteCard.addEventListener("click", (ev) => {
      const target = ev.target;
      if (!(target instanceof HTMLElement)) return;
      const p = target.getAttribute("data-history-period");
      if (!p) return;
      historyPeriod = p === "3mo" ? "3mo" : "1mo";
      if (latestQuoteData?.ok) renderQuoteCard(latestQuoteData);
      renderPriceHistoryChart(historyPeriod);
    });
  }
  const reloadDecision = () => {
    if (!latestDecisionTicker) return;
    loadDecisionIntelPanel(latestDecisionTicker, latestDecisionMarket).catch(() => {
      // no-op
    });
  };
  if (els.prefHorizon) els.prefHorizon.addEventListener("change", reloadDecision);
  if (els.prefRisk) els.prefRisk.addEventListener("change", reloadDecision);
  if (els.feedIntensity) {
    els.feedIntensity.addEventListener("change", () => {
      compareDataCache.clear();
      if (!latestDecisionTicker) return;
      loadIntelligence({ showOverlay: false }).catch(() => {
        // no-op
      });
    });
  }
  if (els.scenarioFx) {
    els.scenarioFx.addEventListener("input", () => {
      if (els.scenarioFxText) els.scenarioFxText.textContent = `${Number.parseFloat(String(els.scenarioFx.value || "0")).toFixed(1)}%`;
      assumptionChanged = true;
      markAssumptionChangedUI(true);
      reloadDecision();
    });
  }
  if (els.scenarioEv) {
    els.scenarioEv.addEventListener("input", () => {
      if (els.scenarioEvText) els.scenarioEvText.textContent = `${Number.parseFloat(String(els.scenarioEv.value || "0")).toFixed(0)}%`;
      assumptionChanged = true;
      markAssumptionChangedUI(true);
      reloadDecision();
    });
  }

  if (els.scenarioPresetConservativeBtn) {
    els.scenarioPresetConservativeBtn.addEventListener("click", () => {
      els.prefRisk.value = "conservative";
      els.prefHorizon.value = "long";
      els.scenarioFx.value = "2";
      els.scenarioEv.value = "0";
      if (els.scenarioFxText) els.scenarioFxText.textContent = "2.0%";
      if (els.scenarioEvText) els.scenarioEvText.textContent = "0%";
      assumptionChanged = true;
      markAssumptionChangedUI(true);
      reloadDecision();
    });
  }
  if (els.scenarioPresetBaseBtn) {
    els.scenarioPresetBaseBtn.addEventListener("click", () => {
      els.prefRisk.value = "neutral";
      els.prefHorizon.value = "mid";
      els.scenarioFx.value = "0";
      els.scenarioEv.value = "5";
      if (els.scenarioFxText) els.scenarioFxText.textContent = "0.0%";
      if (els.scenarioEvText) els.scenarioEvText.textContent = "5%";
      assumptionChanged = false;
      markAssumptionChangedUI(false);
      reloadDecision();
    });
  }
  if (els.scenarioPresetAggressiveBtn) {
    els.scenarioPresetAggressiveBtn.addEventListener("click", () => {
      els.prefRisk.value = "aggressive";
      els.prefHorizon.value = "short";
      els.scenarioFx.value = "-2";
      els.scenarioEv.value = "15";
      if (els.scenarioFxText) els.scenarioFxText.textContent = "-2.0%";
      if (els.scenarioEvText) els.scenarioEvText.textContent = "15%";
      assumptionChanged = true;
      markAssumptionChangedUI(true);
      reloadDecision();
    });
  }
  if (els.scenarioResetBtn) {
    els.scenarioResetBtn.addEventListener("click", () => {
      els.prefHorizon.value = "mid";
      els.prefRisk.value = "neutral";
      els.scenarioFx.value = "0";
      els.scenarioEv.value = "5";
      if (els.scenarioFxText) els.scenarioFxText.textContent = "0.0%";
      if (els.scenarioEvText) els.scenarioEvText.textContent = "5%";
      assumptionChanged = false;
      markAssumptionChangedUI(false);
      reloadDecision();
    });
  }

  if (els.newsSourceFilter) {
    els.newsSourceFilter.addEventListener("input", () => {
      if (latestNewsData?.ok) return renderNews(latestNewsData);
      const ticker = String(els.intelTicker.value || "").trim().toUpperCase();
      if (!ticker) return;
      loadIntelligence({ showOverlay: false }).catch(() => {
        // no-op
      });
    });
  }
  if (els.filingFormFilter) {
    els.filingFormFilter.addEventListener("input", () => {
      if (latestFilingData?.ok) return renderFilings(latestFilingData);
      const ticker = String(els.intelTicker.value || "").trim().toUpperCase();
      if (!ticker) return;
      loadIntelligence({ showOverlay: false }).catch(() => {
        // no-op
      });
    });
  }
  if (els.newsKeywordFilter) {
    els.newsKeywordFilter.addEventListener("input", () => renderNews(latestNewsData));
  }
  if (els.newsSentimentFilter) {
    els.newsSentimentFilter.addEventListener("change", () => renderNews(latestNewsData));
  }
  if (els.newsMoreBtn) {
    els.newsMoreBtn.addEventListener("click", () => {
      newsExpanded = !newsExpanded;
      renderNews(latestNewsData);
    });
  }
  if (els.filingMoreBtn) {
    els.filingMoreBtn.addEventListener("click", () => {
      filingExpanded = !filingExpanded;
      renderFilings(latestFilingData);
    });
  }
  if (els.techMoreBtn) {
    els.techMoreBtn.addEventListener("click", () => {
      techExpanded = !techExpanded;
      renderTechnology(latestTechData);
    });
  }

  if (els.notifyEmail) els.notifyEmail.addEventListener("input", validateNotificationInputs);
  if (els.notifyWebhook) els.notifyWebhook.addEventListener("input", validateNotificationInputs);

  if (els.addWatchBtn) {
    els.addWatchBtn.addEventListener("click", () => {
      addWatchItem().catch((err) => {
        if (els.autoMeta) els.autoMeta.textContent = `오류: ${err.message}`;
      });
    });
  }

  if (els.saveRulesBtn) {
    els.saveRulesBtn.addEventListener("click", () => {
      saveAlertRules().catch((err) => {
        if (els.autoMeta) els.autoMeta.textContent = `오류: ${err.message}`;
      });
    });
  }

  if (els.saveChannelsBtn) {
    els.saveChannelsBtn.addEventListener("click", () => {
      if (!validateNotificationInputs()) {
        if (els.autoMeta) els.autoMeta.textContent = "입력 형식을 확인해 주세요. (이메일/웹훅)";
        return;
      }
      saveChannels().catch((err) => {
        if (els.autoMeta) els.autoMeta.textContent = `오류: ${err.message}`;
      });
    });
  }

  if (els.testNotifyBtn) {
    els.testNotifyBtn.addEventListener("click", () => {
      sendTestNotification().catch((err) => {
        if (els.autoMeta) els.autoMeta.textContent = `오류: ${err.message}`;
      });
    });
  }

  if (els.scanNowBtn) {
    els.scanNowBtn.addEventListener("click", () => {
      runScanNow().catch((err) => {
        if (els.autoMeta) els.autoMeta.textContent = `오류: ${err.message}`;
      });
    });
  }

  if (els.refreshRankingBtn) {
    els.refreshRankingBtn.addEventListener("click", () => {
      refreshRanking().catch((err) => {
        els.autoMeta.textContent = `오류: ${err.message}`;
      });
    });
  }
  if (els.refreshAutoBtn) {
    els.refreshAutoBtn.addEventListener("click", () => {
      refreshAutoPanel().catch((err) => {
        els.autoMeta.textContent = `오류: ${err.message}`;
      });
    });
  }

  if (els.watchlistView) {
    els.watchlistView.addEventListener("click", (ev) => {
      const target = ev.target;
      if (!(target instanceof HTMLElement)) return;
      const ticker = target.getAttribute("data-remove-ticker");
      const market = target.getAttribute("data-remove-market");
      if (!ticker) return;
      showConfirmModal(`${ticker} 종목을 관심종목에서 삭제할까요?`, () => {
        removeWatchTicker(ticker, market).catch((err) => {
          if (els.autoMeta) els.autoMeta.textContent = `오류: ${err.message}`;
        });
      });
    });
  }

  if (els.confirmCancelBtn) {
    els.confirmCancelBtn.addEventListener("click", hideConfirmModal);
  }
  if (els.confirmOkBtn) {
    els.confirmOkBtn.addEventListener("click", () => {
      const fn = pendingConfirmAction;
      hideConfirmModal();
      if (typeof fn === "function") fn();
    });
  }
  if (els.confirmModal) {
    els.confirmModal.addEventListener("click", (ev) => {
      if (ev.target === els.confirmModal) hideConfirmModal();
    });
  }
}

function bindCriticalFallbacks() {
  if (els.searchCompanyBtn && !els.searchCompanyBtn.dataset.boundPrimary && !els.searchCompanyBtn.dataset.boundFallback) {
    els.searchCompanyBtn.dataset.boundFallback = "1";
    els.searchCompanyBtn.addEventListener("click", () => {
      searchCompanyByName().catch((err) => {
        if (els.intelMeta) {
          els.intelMeta.textContent = `오류: ${err.message}`;
          els.intelMeta.style.background = "#ffe9e9";
          els.intelMeta.style.color = "#8c1d18";
        }
      });
    });
  }
  if (els.loadIntelBtn && !els.loadIntelBtn.dataset.boundPrimary && !els.loadIntelBtn.dataset.boundFallback) {
    els.loadIntelBtn.dataset.boundFallback = "1";
    els.loadIntelBtn.addEventListener("click", () => {
      loadIntelligence().catch((err) => {
        if (els.intelMeta) {
          els.intelMeta.textContent = `오류: ${err.message}`;
          els.intelMeta.style.background = "#ffe9e9";
          els.intelMeta.style.color = "#8c1d18";
        }
      });
    });
  }
}

function restoreSavedInput() {
  if (!els.csvText) return;
  const saved = localStorage.getItem("stock_csv_input");
  if (saved) {
    els.csvText.value = saved;
  }
}

function setupPWA() {
  if ("serviceWorker" in navigator) {
    if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
      navigator.serviceWorker.getRegistrations().then((regs) => {
        regs.forEach((r) => r.unregister());
      });
      if ("caches" in window) {
        caches.keys().then((keys) => Promise.all(keys.map((k) => caches.delete(k))));
      }
      return;
    }
    navigator.serviceWorker
      .register("./sw.js?v=35")
      .then((reg) => reg.update())
      .catch(() => {
        // no-op
      });
  }
}

function init() {
  initPageTabs();
  try {
    bindEvents();
  } catch (err) {
    const bootError = `이벤트 초기화 오류: ${err?.message || err}`;
    if (els.intelMeta) {
      els.intelMeta.textContent = bootError;
      els.intelMeta.style.background = "#ffe9e9";
      els.intelMeta.style.color = "#8c1d18";
    }
    if (!els.intelMeta && document?.body) {
      const banner = document.createElement("div");
      banner.className = "boot-error-banner";
      banner.textContent = bootError;
      document.body.prepend(banner);
    }
  }
  bindCriticalFallbacks();
  restoreSavedInput();
  setupPWA();
  if (els.intelSummaryCard) {
    els.intelSummaryCard.innerHTML = "<strong>AI 인텔리전스 요약</strong><div>종목을 조회하면 뉴스/공시/기술 요약이 표시됩니다.</div>";
  }
  if (els.valuationExplainCard) {
    els.valuationExplainCard.innerHTML = "<strong>밸류에이션 설명</strong><div>재무 지표를 조회하면 P/E, P/B, ROE 기반 설명이 표시됩니다.</div>";
  }
  if (els.decisionPanelCard) {
    els.decisionPanelCard.innerHTML = "<strong>Decision Panel</strong><div>종목 조회 후 단기/중기/장기 시그널이 표시됩니다.</div>";
  }
  if (els.relativeComparisonCard) {
    els.relativeComparisonCard.innerHTML = "<strong>Relative Comparison</strong><div>동종/업종 대비 지표가 표시됩니다.</div>";
  }
  if (els.scenarioAnalyzerCard) {
    els.scenarioAnalyzerCard.innerHTML = "<strong>Scenario Analyzer</strong><div>환율/EV 성장률 시나리오에 따른 영향이 표시됩니다.</div>";
  }
  renderRelatedSectorChips([]);
  renderSectorComparePanel("core").catch(() => {
    // no-op
  });
  updateStockHeaderSummary({
    ticker: "",
    market: "US",
    name: "종목 선택 대기",
    quoteData: null,
    decisionData: null,
  });
  markAssumptionChangedUI(false);
  setMobileView("core");
  if (els.userId) {
    els.userId.value = localStorage.getItem("stock_user_id") || "default";
  }
  validateNotificationInputs();
  syncHeaderWatchButtonState();
  loadProviderStatus();
  if (els.intelMarket && els.sectorSelect) {
    loadSectorOptions().catch(() => {
      // no-op
    });
  }
  if (els.spotlightQuery && !els.spotlightQuery.value) {
    els.spotlightQuery.value = "AAPL m:US";
  }
  if (els.userId || els.watchlistView || els.autoMeta) {
    refreshAutoPanel().catch(() => {
      // no-op
    });
  }
  if (typeof window !== "undefined" && window.__stockBoot) {
    window.__stockBoot.appInitDone = true;
    const diag = document.getElementById("bootDiagnostics");
    if (diag) {
      diag.textContent = "JS 정상 동작";
      diag.dataset.level = "info";
      setTimeout(() => {
        diag.style.display = "none";
      }, 1800);
    }
  }
}

init();
