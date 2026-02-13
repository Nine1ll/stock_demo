# MVP Smoke Test

목표: 섹터 과열 동반 상승 구간에서 `체력 취약 종목`과 `체력 동반 종목`이 구분되는지 확인한다.

## 1) 서버 실행
```bash
cd /Users/nine1ll/주식
python3 web_server.py --host 0.0.0.0 --port 8000
```

## 2) 필수 API 점검
다른 터미널에서 아래 순서로 호출:

```bash
curl -s "http://127.0.0.1:8000/api/health"
curl -s "http://127.0.0.1:8000/api/providers"
curl -s "http://127.0.0.1:8000/api/company-lookup?query=현대차&market=KR&limit=5"
curl -s "http://127.0.0.1:8000/api/decision-intel?ticker=005380&market=KR&horizon=mid&risk=neutral&fx_change_pct=0&ev_growth_pct=8"
curl -s "http://127.0.0.1:8000/api/backtest-sector-signal?ticker=005380&market=KR&period=3mo&hold_days=5"
```

확인 기준:
- `/api/health`: `ok=true`
- `/api/providers`: `providers` 객체 존재
- `/api/decision-intel`:
  - `decision_panel.snapshot.market_impact` 존재
  - `decision_panel.sector_heat.heat_score` 존재
  - `decision_panel.sector_heat.resilience_score` 존재
  - `decision_panel.sector_heat.label` 존재
- `/api/backtest-sector-signal`:
  - `latest_signal.label` 존재
  - `stats_by_label` 존재
  - `baseline_forward_return_pct` 존재

## 3) 랭킹/옥석 구분 점검
1. 웹에서 `자동 수집/알림` 탭
2. 같은 섹터 종목 3개 이상 관심종목 추가 (예: 자동차 섹터)
3. `우량주 랭킹 갱신` 클릭
4. 목록 문구 확인:
   - `자본력`, `시장영향`이 각각 별도 점수로 노출되는지
   - `섹터열기`, `체력`, `(...) 라벨`이 함께 보이는지

## 4) 알림 기본 동작 점검
```bash
curl -s -X POST "http://127.0.0.1:8000/api/test-notification" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"default","ticker":"005380","market":"KR"}'

curl -s "http://127.0.0.1:8000/api/notifications?user_id=default&limit=5"
```

확인 기준:
- 최근 알림 목록에 `manual_test`가 생성됨

## 5) 회귀 테스트
```bash
cd /Users/nine1ll/주식
python3 -m unittest discover -s tests -v
python3 -m py_compile web_server.py stock_decision_system.py
```

확인 기준:
- 테스트 모두 통과
- 컴파일 에러 없음
