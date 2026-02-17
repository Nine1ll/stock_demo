# PDCA Log

이 디렉터리는 작업 단위를 `Plan / Do / Check / Act` 문서로 기록하는 저장소다.

## Rules
- 작업 1건당 폴더 1개를 생성한다.
- 각 폴더에는 `PLAN.md`, `DO.md`, `CHECK.md`, `ACT.md`를 둔다.
- `CHECK.md`에는 실제 실행한 검증 명령과 결과를 기록한다.
- 배포/운영 영향이 있으면 `ACT.md`에 반영 절차를 기록한다.

## Index
- `2026-02-17-domain-store-refactor/`: 도메인 로직 분리 + SQLite 저장소 어댑터 분리
- `2026-02-17-agent-project-review/`: 에이전트 합동 프로젝트 점검 + 프론트 동기화 회귀 방지
