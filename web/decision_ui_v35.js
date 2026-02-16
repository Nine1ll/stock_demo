(function () {
  function esc(text) {
    return String(text ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#39;");
  }

  function signalClass(label) {
    const v = String(label || "").toLowerCase();
    if (v.includes("bull") || v.includes("상승")) return "sig-bull";
    if (v.includes("bear") || v.includes("하락")) return "sig-bear";
    return "sig-neutral";
  }

  function confidenceLabel(score) {
    const s = Number(score || 0);
    const d = Math.abs(s - 50);
    if (d >= 18) return "높음";
    if (d >= 9) return "보통";
    return "낮음";
  }

  function fmt(v) {
    return Number.isFinite(Number(v)) ? Number(v).toFixed(2) : "N/A";
  }

  function safeNum(v, fallback = 0) {
    const n = Number(v);
    return Number.isFinite(n) ? n : fallback;
  }

  function clamp(n, min, max) {
    return Math.max(min, Math.min(max, n));
  }

  function uniqText(items) {
    const out = [];
    const seen = new Set();
    for (const item of items || []) {
      const t = String(item || "").trim();
      if (!t) continue;
      const key = t.toLowerCase().replace(/[^\w\u3131-\uD79D]+/g, "");
      if (!key || seen.has(key)) continue;
      seen.add(key);
      out.push(t);
    }
    return out;
  }

  function labelByScore(score) {
    if (score >= 60) return "상승 우세";
    if (score >= 45) return "중립";
    return "하락 우세";
  }

  function verdictFromActionStance(stance) {
    const s = String(stance || "").trim();
    if (s.includes("매수") || s.toLowerCase().includes("buy")) {
      return { key: "buy", text: "매수", tone: "Buy" };
    }
    if (s.includes("비중축소") || s.includes("매도") || s.toLowerCase().includes("sell")) {
      return { key: "sell", text: "비중축소", tone: "Reduce" };
    }
    return { key: "neutral", text: "관망", tone: "Neutral" };
  }

  function horizonModel(horizon, snap, risk, opts = {}) {
    const v = safeNum(snap.valuation, 50);
    const q = safeNum(snap.quality, 50);
    const t = safeNum(snap.tech_strength, 50);
    const c = safeNum(snap.capital_power, 50);
    const h = safeNum(snap.hype, 50);
    const rv = safeNum(risk.volatility, 5);
    const rf = safeNum(risk.fx_sensitivity, 5);
    const rc = safeNum(risk.competition, 5);

    const fxAdj = clamp(Number(opts.fx || 0), -10, 10);
    const evAdj = clamp(Number(opts.ev || 5), -20, 30);
    const riskPref = String(opts.risk || "neutral");
    const riskBias = riskPref === "aggressive" ? 1.8 : riskPref === "conservative" ? -1.8 : 0;
    if (horizon === "short") {
      return clamp(0.26 * v + 0.18 * q + 0.12 * t + 0.08 * c + 0.18 * (100 - h) + 0.18 * (100 - rv * 10) - fxAdj * 0.35 + evAdj * 0.22 + riskBias, 0, 100);
    }
    if (horizon === "mid") {
      return clamp(0.3 * v + 0.24 * q + 0.16 * t + 0.12 * c + 0.1 * (100 - rc * 10) + 0.08 * (100 - h) - fxAdj * 0.25 + evAdj * 0.18 + riskBias * 0.7, 0, 100);
    }
    return clamp(0.24 * v + 0.2 * q + 0.24 * t + 0.2 * c + 0.08 * (100 - rf * 10) + 0.04 * (100 - h) - fxAdj * 0.12 + evAdj * 0.1 + riskBias * 0.4, 0, 100);
  }

  function horizonReasons(horizon, snap, risk) {
    const v = safeNum(snap.valuation, 50).toFixed(1);
    const q = safeNum(snap.quality, 50).toFixed(1);
    const t = safeNum(snap.tech_strength, 50).toFixed(1);
    const c = safeNum(snap.capital_power, 50).toFixed(1);
    const h = safeNum(snap.hype, 50).toFixed(1);
    const rv = safeNum(risk.volatility, 5).toFixed(1);
    const rf = safeNum(risk.fx_sensitivity, 5).toFixed(1);
    const rc = safeNum(risk.competition, 5).toFixed(1);
    if (horizon === "short") {
      return [
        `변동성(${rv}/10) 대비 밸류 점수(${v})의 단기 안전마진 확인`,
        `과열 점수(${h})와 단기 모멘텀 균형 점검`,
        `품질(${q}) 기반 실적 쇼크 방어력 반영`,
      ];
    }
    if (horizon === "mid") {
      return [
        `밸류(${v})와 품질(${q})의 중기 리레이팅 가능성`,
        `경쟁강도(${rc}/10) 대비 업종 내 점유율 방어력 확인`,
        `기술력(${t})이 수익성 개선으로 이어지는지 점검`,
      ];
    }
    return [
      `기술력(${t}) + 자본력(${c})의 장기 복합 경쟁력`,
      `환율민감도(${rf}/10)와 글로벌 이익 체력 반영`,
      `품질(${q}) 기반 장기 현금흐름 안정성 점검`,
    ];
  }

  function buildTrapRisks(inputRisks, snap, risk) {
    const out = uniqText(inputRisks || []);
    const opMargin = safeNum(snap.quality, 50);
    const growth = safeNum(snap.tech_strength, 50);
    const comp = safeNum(risk.competition, 5);
    const fx = safeNum(risk.fx_sensitivity, 5);
    const fallback = [
      `분기 점검: 수익성 지표(${opMargin.toFixed(1)})가 2개 분기 연속 하락하면 가치함정 가능성 확대`,
      `실적/수주 점검: 성장 체력(${growth.toFixed(1)})이 업종 평균 대비 둔화되면 리레이팅 지연`,
      `공시 점검: 대규모 자금조달·증자 공시 발생 시 주주가치 희석 리스크 재평가`,
      `경쟁 점검: 경쟁강도(${comp.toFixed(1)}/10) 상승 구간에서 가격 인하 압력 주의`,
      `거시 점검: 환율민감도(${fx.toFixed(1)}/10) 상승 시 이익 변동폭 확대 가능`,
    ];
    return uniqText(out.concat(fallback)).slice(0, 3);
  }

  function assumptionChip(opts) {
    if (!opts?.assumptionChanged) return "";
    return '<span class="chip soft">가정 변경 반영됨</span>';
  }

  function renderDecisionPanel(el, payload, opts = {}) {
    if (!el) return;
    if (!payload?.ok) {
      el.innerHTML = `<strong>Decision Panel</strong><div>${esc(payload?.error || "데이터 없음")}</div>`;
      return;
    }
    const p = payload.decision_panel || {};
    const risk = p.risk || {};
    const signals = p.signals || {};
    const snap = p.snapshot || {};
    const sectorHeat = p.sector_heat || {};
    const todayMoveReason = String(p.today_move_reason || "").trim();
    const todayChangePct = safeNum(p.today_change_pct, 0);
    const todayMoveTitle = todayChangePct >= 0.8 ? "오늘 왜 올랐을까" : todayChangePct <= -0.8 ? "오늘 왜 떨어졌을까" : "오늘 왜 움직였을까";
    const order = [
      { key: "short", title: "단기" },
      { key: "mid", title: "중기" },
      { key: "long", title: "장기" },
    ];

    const rawScores = order.map((r) => safeNum(signals[r.key]?.score, 0));
    const allSameSignal = rawScores.length === 3 && rawScores.every((v) => Math.abs(v - rawScores[0]) < 0.01);
    const rows = order
      .map((r) => {
        const s = signals[r.key] || {};
        const modelScore = horizonModel(r.key, snap, risk, opts);
        const blended = allSameSignal
          ? modelScore
          : clamp(safeNum(s.score, 50) * 0.72 + modelScore * 0.28, 0, 100);
        const score = Math.round(blended * 10) / 10;
        const label = allSameSignal ? labelByScore(score) : (s.label || labelByScore(score));
        const reasonPool = uniqText([todayMoveReason, ...(s.reasons || []), ...horizonReasons(r.key, snap, risk)]);
        const topReasons = reasonPool.slice(0, 3);
        const topHtml = topReasons.map((x) => `<li>${esc(x)}</li>`).join("") || "<li>근거 없음</li>";
        const allHtml = reasonPool.map((x) => `<li>${esc(x)}</li>`).join("") || "<li>근거 없음</li>";
        const conf = confidenceLabel(score);
        return `<div class="decision-signal-card">
          <div class="decision-title"><strong>${r.title} 시그널</strong> <span class="sig-pill ${signalClass(label)}">${esc(label)}</span></div>
          <div class="muted-sm">신뢰도: ${conf} · 점수: ${score.toFixed(1)}</div>
          <ul class="reason-list">${topHtml}</ul>
          <details>
            <summary class="muted-sm">자세히 보기</summary>
            <ul class="reason-list">${allHtml}</ul>
          </details>
        </div>`;
      })
      .join("");
    const scoreSpread = Math.max(...rawScores) - Math.min(...rawScores);
    const useSingleSignal = allSameSignal || scoreSpread < 1.2;

    const unifiedScore = useSingleSignal
      ? Math.round(((horizonModel("short", snap, risk, opts) + horizonModel("mid", snap, risk, opts) + horizonModel("long", snap, risk, opts)) / 3) * 10) / 10
      : null;
    const unifiedLabel = unifiedScore == null ? "" : labelByScore(unifiedScore);
    const unifiedReasons = useSingleSignal
      ? uniqText([
          todayMoveReason,
          ...horizonReasons("short", snap, risk),
          ...horizonReasons("mid", snap, risk),
          ...horizonReasons("long", snap, risk),
        ]).slice(0, 4)
      : [];
    const unifiedHtml = unifiedReasons.map((x) => `<li>${esc(x)}</li>`).join("");

    const reasons = uniqText(p.undervalued_reasons || []).slice(0, 3).map((x) => `<li>${esc(x)}</li>`).join("") || "<li>근거 없음</li>";
    const traps = buildTrapRisks(p.value_trap_risks || [], snap, risk).map((x) => `<li>${esc(x)}</li>`).join("");
    const action = p.action || {};
    const buyBelowRaw = Number(action.buy_below);
    const takeProfitRaw = Number(action.take_profit);
    const buyBelow = Number.isFinite(buyBelowRaw) ? Math.round(buyBelowRaw) : null;
    const takeProfit = Number.isFinite(takeProfitRaw) ? Math.round(takeProfitRaw) : null;
    const stopLoss = buyBelow ? Math.round(buyBelow * 0.92) : null;
    const riskTotal = safeNum(risk.total, 0);
    const positionHint = riskTotal >= 7
      ? "리스크 높음: 1회 진입 비중 20% 이내 권장"
      : riskTotal >= 4.5
      ? "중립 리스크: 2~3회 분할 진입 권장"
      : "리스크 낮음: 계획 비중 내 단계적 확대 가능";
    const conditionText = action.condition || "업종 대비 할인율과 실적 유지 확인 후 단계적 대응";
    const executionChips = [
      buyBelow ? `1차 분할매수 ${buyBelow.toLocaleString("ko-KR")} 원` : null,
      stopLoss ? `방어가격 ${stopLoss.toLocaleString("ko-KR")} 원` : null,
      takeProfit ? `1차 이익실현 ${takeProfit.toLocaleString("ko-KR")} 원` : null,
      "기준: 현재가 대비 조건부 실행",
    ].filter(Boolean);
    const chipHtml = executionChips.map((x) => `<span class="tag action-chip">${esc(x)}</span>`).join("");
    const heatScore = safeNum(sectorHeat.heat_score, 0).toFixed(1);
    const resilienceScore = safeNum(sectorHeat.resilience_score, 0).toFixed(1);
    const overheatScore = clamp(safeNum(snap.hype, 0), 0, 100);
    const verdict = verdictFromActionStance(action.stance || "");
    const needleDeg = ((overheatScore / 100) * 180 - 90).toFixed(1);
    const heatText = sectorHeat.label
      ? ` | 섹터열기 ${heatScore} · 체력 ${resilienceScore} (${esc(sectorHeat.label)})`
      : "";
    const heatNote = sectorHeat.note
      ? `<div class="muted-sm" style="margin-top:4px;">${esc(sectorHeat.note)}</div>`
      : "";

    el.innerHTML = `
      <div class="panel-head"><h3>Decision Panel</h3><div>${assumptionChip(opts)}<span class="chip">개인화 반영</span></div></div>
      <section class="verdict-hero">
        <div class="verdict-meta">
          <strong>Final Verdict</strong>
          <span class="muted-sm">행동 제안 기준</span>
        </div>
        <div class="muted-sm" style="margin-bottom:8px;">최종 판단은 종합점수·리스크·밸류 기준으로 계산되며, 과열 점수는 보조지표로 제공됩니다.</div>
        <div class="verdict-center" style="margin:2px 0 8px;">
          <span class="verdict-label ${verdict.key}">${verdict.text} (${verdict.tone})</span>
        </div>
        <div class="verdict-gauge-wrap">
          <div class="verdict-gauge" role="img" aria-label="Overheat score ${overheatScore.toFixed(1)}"></div>
          <div class="verdict-needle" style="transform: translateX(-50%) rotate(${needleDeg}deg)"></div>
        </div>
        <div class="verdict-center">
          <div class="verdict-score">${overheatScore.toFixed(1)}</div>
          <span class="muted-sm">Overheat Gauge</span>
        </div>
      </section>
      <div class="risk-breakdown" style="margin-bottom:8px;">
        종합 ${safeNum(snap.composite, 0).toFixed(1)}점 | 밸류 ${safeNum(snap.valuation, 0).toFixed(1)} · 기술력 ${safeNum(snap.tech_strength, 0).toFixed(1)} · 자본력 ${safeNum(snap.capital_power, 0).toFixed(1)} · 시장영향 ${safeNum(snap.market_impact, 0).toFixed(1)} · 품질 ${safeNum(snap.quality, 0).toFixed(1)} · 과열 ${safeNum(snap.hype, 0).toFixed(1)}${heatText}
      </div>
      ${heatNote}
      <div class="risk-box">
        <strong>리스크 점수: ${safeNum(risk.total, 0).toFixed(1)} / 10</strong>
        <div class="risk-breakdown">변동성 ${safeNum(risk.volatility, 0).toFixed(1)} · 환율민감 ${safeNum(risk.fx_sensitivity, 0).toFixed(1)} · 경쟁강도 ${safeNum(risk.competition, 0).toFixed(1)}</div>
      </div>
      <div class="driver-box">
        <strong>행동 제안: ${esc(action.stance || "관망")}</strong>
        <div>${esc(conditionText)}</div>
        <div class="action-detail">${esc(positionHint)}</div>
        <div class="action-chip-row">${chipHtml}</div>
      </div>
      <div class="driver-box">
        <strong>${esc(todayMoveTitle)}</strong>
        <div>${esc(todayMoveReason || "가격 변동 원인 데이터가 부족합니다.")}</div>
        <div class="muted-sm">당일 등락률 + 최신 뉴스/공시를 근거로 자동 요약</div>
      </div>
      ${
        useSingleSignal
          ? `<div class="decision-grid single-signal">
               <div class="decision-signal-card">
                 <div class="decision-title"><strong>통합 시그널</strong> <span class="sig-pill ${signalClass(unifiedLabel)}">${esc(unifiedLabel)}</span></div>
                 <div class="muted-sm">신뢰도: ${confidenceLabel(unifiedScore)} · 점수: ${safeNum(unifiedScore, 0).toFixed(1)} · 단/중/장 공통 시그널</div>
                 <ul class="reason-list">${unifiedHtml || "<li>근거 없음</li>"}</ul>
               </div>
             </div>`
          : `<div class="decision-grid">${rows}</div>`
      }
      <div class="intel-summary-grid" style="margin-top:10px;">
        <div>
          <strong>저평가 근거 3가지</strong>
          <ul class="reason-list">${reasons}</ul>
        </div>
        <div>
          <strong>가치함정 리스크 3가지</strong>
          <ul class="reason-list">${traps}</ul>
        </div>
      </div>
    `;
  }

  function renderRelativeComparison(el, payload, opts = {}) {
    if (!el) return;
    if (!payload?.ok) {
      el.innerHTML = `<strong>Relative Comparison</strong><div>${esc(payload?.error || "데이터 없음")}</div>`;
      return;
    }
    const rel = payload.relative_comparison || {};
    const target = rel.target || {};
    const avg = rel.sector_average || {};
    const peer = rel.peer || {};

    const metrics = [
      { key: "pe", name: "PER" },
      { key: "pb", name: "PBR" },
      { key: "roe", name: "ROE" },
    ];

    const tr = metrics
      .map((m) => {
        const tv = target[m.key];
        const av = avg[m.key];
        const pv = peer[m.key];
        const na = '<span title="데이터 없음">N/A</span>';
        return `<tr><td>${m.name}</td><td>${fmt(tv) === "N/A" ? na : fmt(tv)}</td><td>${fmt(av) === "N/A" ? na : fmt(av)}</td><td>${fmt(pv) === "N/A" ? na : fmt(pv)}</td></tr>`;
      })
      .join("");

    const bars = metrics
      .map((m) => {
        const base = Math.max(0.0001, safeNum(avg[m.key], 0));
        const ratio = (v) => {
          const n = safeNum(v, 0);
          if (base <= 0 || n <= 0) return "4%";
          return `${Math.max(4, Math.min(100, (n / base) * 100)).toFixed(1)}%`;
        };
        return `<div class="cmp-bar-group"><div class="cmp-name">${m.name}</div>
          <div class="cmp-row"><span>대상</span><i style="width:${ratio(target[m.key])}"></i></div>
          <div class="cmp-row"><span>업종평균</span><i style="width:100%"></i></div>
          <div class="cmp-row"><span>경쟁사</span><i style="width:${ratio(peer[m.key])}"></i></div>
        </div>`;
      })
      .join("");

    el.innerHTML = `
      <div class="panel-head"><h3>Relative Comparison</h3><div>${assumptionChip(opts)}<span class="chip">동종/업종 대비</span></div></div>
      <div class="muted">${esc(rel.title || "대상 vs 업종 평균 vs 주요 경쟁사")}</div>
      <div class="table-wrap"><table>
        <thead><tr><th>지표</th><th>대상</th><th>업종 평균</th><th>주요 경쟁사</th></tr></thead>
        <tbody>${tr}</tbody>
      </table></div>
      <div class="cmp-bars">${bars}</div>
      <details style="margin-top:8px;"><summary class="muted-sm">정규화 기준 설명</summary><div class="muted-sm">막대는 업종 평균을 1.0(=100%)으로 정규화해 비교합니다. N/A는 데이터 부재를 의미합니다.</div></details>
    `;
  }

  function renderScenario(el, payload, opts = {}) {
    if (!el) return;
    if (!payload?.ok) {
      el.innerHTML = `<strong>Scenario Analyzer</strong><div>${esc(payload?.error || "데이터 없음")}</div>`;
      return;
    }
    const sc = payload.scenario || {};
    const impact = safeNum(sc.expected_impact_pct, 0);
    const target = sc.target_price_range || {};
    const low = safeNum(target.low, 0);
    const high = safeNum(target.high, 0);
    const base = (low + high) / 2;
    const delta = impact;
    el.innerHTML = `
      <div class="panel-head"><h3>Scenario Analyzer</h3><div>${assumptionChip(opts)}<span class="chip">실시간 계산</span></div></div>
      <div><strong>예상 영향:</strong> ${impact >= 0 ? "+" : ""}${impact.toFixed(2)}% <span class="muted-sm">(기준 대비 Δ ${delta >= 0 ? "+" : ""}${delta.toFixed(2)}%)</span></div>
      <div><strong>목표가격 범위:</strong> ${Math.round(low).toLocaleString("ko-KR")} ~ ${Math.round(high).toLocaleString("ko-KR")} <span class="muted-sm">(중심값 ${Math.round(base).toLocaleString("ko-KR")})</span></div>
      <p class="muted" style="margin-top:8px;">${esc(sc.model_note || "단순화된 민감도 모델")}</p>
      <details><summary class="muted-sm">계산 방식 설명</summary><div class="muted-sm">환율/EV 성장률 민감도를 선형으로 적용한 단순 모델입니다. 절대 목표가가 아니라 시나리오 비교용입니다.</div></details>
    `;
  }

  window.DecisionUI = {
    renderDecisionPanel,
    renderRelativeComparison,
    renderScenario,
  };
})();
