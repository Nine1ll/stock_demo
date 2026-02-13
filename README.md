# Stock Sector & Valuation Decision System

섹터 분류 + 가치/과열 점수 기반으로 주식의 `buy/watch/reduce/sell` 결정을 지원하고,
실시간 시세/재무/뉴스/공시/기술 정보까지 조회하는 웹 앱입니다.
시장 범위는 `US`, `KR` 두 시장으로 제한됩니다.

## 구성
- `stock_decision_system.py`: CLI 분석 엔진
- `web_server.py`: 웹 + API 통합 서버
- `data/sector_seed.json`: 시장/섹터별 종목 시드
- `web/index.html`: 웹 앱 화면
- `web/methodology.html`: 용어/산식/백테스트 지표 설명 페이지
- `web/app_main_v35.js`: 메인 UI 로직 (index.html에서 실제 로드)
- `web/decision_ui_v35.js`: Decision Panel 렌더러 (index.html에서 실제 로드)
- `web/app.js`, `web/decision_ui.js`: 호환용 동기화 사본
- `web/manifest.webmanifest`, `web/sw.js`: PWA 설치/오프라인 캐시

## 1) API 키 설정
`.env` 사용 권장:

```bash
cd <repo-root>
cp .env.example .env
```

`.env`에 값을 채우면 서버가 시작 시 자동으로 로드합니다.

또는 직접 `export`로 설정할 수 있습니다.

```bash
export FINNHUB_API_KEY="YOUR_FINNHUB_KEY"
export ALPHA_VANTAGE_API_KEY="YOUR_ALPHA_KEY"
export SEC_USER_AGENT="YourName your@email.com"
export ALERT_POLL_SECONDS="300"
# optional for e-mail alerts
export SMTP_HOST="smtp.example.com"
export SMTP_PORT="587"
export SMTP_USER="user"
export SMTP_PASS="pass"
export SMTP_FROM="alerts@example.com"
export SMTP_TLS="1"
# optional for OneSignal push
export ONESIGNAL_APP_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export ONESIGNAL_API_KEY="ONESIGNAL_REST_API_KEY"
export DART_API_KEY="YOUR_DART_API_KEY"
export OPENAI_API_KEY="YOUR_OPENAI_API_KEY"
export OPENAI_MODEL="gpt-4.1-mini"
```

- `FINNHUB_API_KEY`: 실시간 시세 + 뉴스
- `ALPHA_VANTAGE_API_KEY`: 재무 요약(OVERVIEW) + 뉴스 fallback
- `SEC_USER_AGENT`: SEC 공시 API 권장 헤더 (연락 가능한 정보 포함)
- `OPENAI_API_KEY`: 뉴스/공시/기술 통합 LLM 요약(없으면 규칙 기반 요약으로 자동 동작)

키가 없어도 일부 fallback 공급자(Yahoo/Google News/Crossref)는 동작합니다.

## 2) 웹 앱 실행 (모바일/PC 공용)
```bash
cd <repo-root>
python3 web_server.py --host 0.0.0.0 --port 8000
```

브라우저:
- PC: `http://localhost:8000/web/index.html`
- 같은 Wi-Fi 모바일: `http://<내-PC-IP>:8000/web/index.html`

## 상시 배포 (내 PC 꺼도 동작)
- Oracle Always Free VM 배포 가이드: `DEPLOY_ORACLE_FREE.md`
- 원클릭 설치 스크립트: `deploy/oracle/setup_oci_free.sh`
- HTTPS(도메인) 스크립트: `deploy/oracle/setup_caddy_https.sh`
- Render 배포 가이드: `DEPLOY_RENDER.md`
- Render Blueprint 파일: `render.yaml`

### 모바일 홈 화면 설치(PWA)
- Android Chrome: 메뉴 > `홈 화면에 추가`
- iPhone Safari: 공유 > `홈 화면에 추가`

## 3) API 엔드포인트
- `GET /api/health`
- `GET /api/providers` (현재 공급자 설정/상태)
- `GET /api/quote?ticker=AAPL&market=US`
- `GET /api/fundamentals?ticker=AAPL&market=US`
- `GET /api/news?ticker=AAPL&market=US&days=7`
- `GET /api/filings?ticker=AAPL&market=US&limit=10`
- `GET /api/technology?query=robotics&limit=8`
- `GET /api/intel-summary?ticker=AAPL&market=US&query=robotics` (뉴스/공시/기술 통합 요약)
- `GET /api/backtest-sector-signal?ticker=AAPL&market=US&period=3mo&hold_days=5` (가격/거래량 기반 신호 리플레이 백테스트)
- `GET /api/watchlist?user_id=default`
- `GET /api/company-lookup?query=apple&market=US&limit=20` (회사명/종목코드 검색)
- `GET /api/sector-list?user_id=default&market=US` (시장별 섹터 목록)
- `GET /api/sector-stocks?user_id=default&market=US&sector=Technology&limit=40` (섹터 관련 종목)
- `GET /api/related-stocks?ticker=005930&market=KR&limit=30` (KR 동일업종/유사종목 자동수집)
- `POST /api/watchlist` body: `{ "user_id":"default", "ticker":"AAPL", "market":"US" }`
- `DELETE /api/watchlist?user_id=default&ticker=AAPL&market=US`
- `GET /api/alerts?user_id=default`
- `POST /api/alerts/defaults` body: `{ "user_id":"default","ticker":"AAPL","market":"US","price_change_pct":5,"hype_score_jump":15,"new_filing_enabled":true }`
- `GET /api/channels?user_id=default`
- `POST /api/channels` body: `{ "user_id":"default","email":"a@b.com","webhook_url":"https://..." }`
- `GET /api/notifications?user_id=default&limit=20`
- `GET /api/ranking?user_id=default&limit=50` (저평가 우량주 랭킹)
- `GET /api/sectors?user_id=default&limit=80` (섹터별 그룹 뷰)
- `GET /api/scan?user_id=default` or `POST /api/scan` (즉시 스캔)
- `POST /api/test-notification` body: `{ "user_id":"default","ticker":"AAPL","market":"US" }`

### 자동 fallback
- 시세: `Finnhub -> Yahoo`
- 재무: `Alpha Vantage -> Yahoo`
- 뉴스: `Finnhub -> Alpha Vantage -> Google News RSS`
- 기술: `arXiv -> Crossref`
- KR 시세/재무: `Naver Finance -> Yahoo`
- KR 뉴스: `Naver Finance News -> Google News RSS`
- KR 공시: `DART API` (DART 키 없으면 공시 조회 제한)
- US 공시: `SEC`

또한 API 결과는 용도별 TTL 캐시를 사용해 호출 제한/지연을 완화합니다.

### 자동 수집/알림 저장소
- DB: `data/stock_app.db` (SQLite)
- 관심종목 추가 시 기본 규칙 자동 생성:
  - `price_change_pct` 5%
  - `hype_score_jump` +15
  - `new_filing` 활성

### 이메일/푸시 테스트
1. 웹의 `자동 수집/알림` 패널에서 채널 저장
2. `테스트 알림 발송` 클릭
3. `/api/notifications?user_id=...` 또는 UI `최근 알림`에서 전달 결과 확인

OneSignal은 `onesignal_external_id`를 앱 사용자 External ID와 동일하게 맞춰야 푸시가 전달됩니다.

## UI 변경
- CSV 입력 영역은 제거되었습니다.
- 현재는 `티커 + 시장(US/KR) + 관심종목 + 자동 알림` 중심으로 사용합니다.
- 회사명으로 검색 후 `선택` 버튼으로 종목코드 자동 채우기가 가능합니다.
- 시장별 섹터를 선택해 관련 종목 목록을 불러올 수 있습니다.
- 섹터 시드 데이터가 확장되어(US/KR) 섹터별 조회 종목 수가 크게 늘었습니다.
- KR 전용 필터:
  - 뉴스 소스 필터(예: 연합뉴스, 매일경제)
  - 공시명/폼 필터(예: 사업보고서, 반기보고서, 10-K)

## 판단 로직 요약
- 랭킹 점수(0~100): `Quality`, `Tech Moat`, `Market Impact`, `Valuation`, `Hype`를 결합
- `Quality`: ROE/마진/밸류에이션 건전성/변동성
- `Tech Moat`: 기술자료(논문/학술), 뉴스 확산, 공시 신호
- `Market Impact`: 시총/뉴스 강도/가격 모멘텀
- `Sector Heat Signal`: `heat_score(섹터 과열/수급)` vs `resilience_score(체력)`를 분리해
  - `테마동반급등(체력취약)` vs `섹터상승+체력동반(추세지속후보)`를 구분
- 최종 라벨: `Strong Undervalued Quality`, `Buy Candidate`, `Fair / Watch`, `Weak / Overvalued`
- 백테스트(MVP): 과거 일봉을 리플레이하여
  - `테마동반급등(체력취약)` / `섹터상승+체력동반(추세지속후보)` / `저평가 체력 우위` 신호별
  - N일(기본 5일) 선행 수익률 평균과 승률(hit rate)을 집계

## 운영 점검 (MVP 스모크 테스트)
- 빠른 점검 절차는 `SMOKE_TEST.md` 참고
- 최소 확인 항목:
  - `/api/decision-intel`에 `decision_panel.sector_heat`가 존재하는지
  - `/api/ranking`에 `sector_heat_score`, `resilience_score`, `sector_heat_label`이 존재하는지
  - 랭킹 문구에 `자본력`과 `시장영향`이 분리되어 표시되는지

## 주의
- 본 도구는 의사결정 보조용이며 투자 자문이 아닙니다.
- 외부 API 속도/요금제/호출 제한에 따라 일부 데이터가 지연 또는 누락될 수 있습니다.
