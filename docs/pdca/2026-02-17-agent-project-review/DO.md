# DO

## Do Agent Execution
1. 프론트 파일 정합성 복구
- `web/app_main_v35.js` -> `web/app.js` 동기화
- `web/decision_ui_v35.js` -> `web/decision_ui.js` 동기화

2. 회귀 방지 테스트 추가
- `tests/test_web_asset_sync.py` 추가
  - `web/app.js` == `web/app_main_v35.js`
  - `web/decision_ui.js` == `web/decision_ui_v35.js`

3. 문서화
- 현재 사이클 PDCA 문서(`PLAN/DO/CHECK/ACT`) 작성

## Design Agent Recommendations (Backlog)
1. 현재 UI는 정보량이 매우 많아 모바일 첫 화면 인지부하가 큼.
2. "핵심/근거/피드" 탭의 시각적 위계(타이포/간격/강조색)를 더 강하게 분리 필요.
3. 다음 사이클에서 컴포넌트 토큰화(카드/칩/버튼 변형)로 스타일 중복 축소 권장.

