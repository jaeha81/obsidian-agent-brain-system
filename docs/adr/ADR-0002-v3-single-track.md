# ADR-0002: 세컨드 브레인 스펙은 별도 트랙이 아니라 V3 단일 트랙의 Stage 13~21로 흡수

- 상태: 승인됨 (플랜 확정, 2026-07-11)
- 관련: `C:\Users\user1\.claude\plans\foamy-churning-swing.md` (포지셔닝 결정) · `docs/BUCKY_OS_V3_MIGRATION_PLAN.md`

## 맥락

세컨드 브레인 진화 스펙 v0.1(`ObsidianVault/00_UPGRADE/BUCKY_SECOND_BRAIN_EVOLUTION_SPEC_v0.1_KR.md`)의 상당 부분이 진행 중인 Bucky OS V3 마이그레이션(Stage 0~8 완료)과 겹친다. 별도 트랙으로 세우면: V3 플랜은 커밋 해시·게이트 이력이 붙은 운영 기록이므로 트랙 이원화 = 정본 충돌(사용자 충돌금지 원칙 위배), 스펙 P0-7(비용)·P0-10(대시보드)은 V3 Stage 10 예약 범위와 중복, P0-4(메모리 출처)는 Stage 12의 선행 축소판이다.

## 결정

1. **단일 트랙 유지** — 스펙 구현은 V3 MIGRATION_PLAN의 Stage 13~21로 확장한다. 신규 트랙·신규 플랜 문서를 만들지 않는다.
2. 스펙 §0이 강제하는 `docs/bucky/*` 5종 + `docs/adr/`는 "산출 문서 계층"으로 신설하고 V3 Stage 번호와 상호 참조한다.
3. `docs/bucky/implementation_backlog.md`가 "스펙 P0/P1 → Stage 번호" 매핑 테이블 역할을 맡는다.

## 결과

- (+) 게이트(G3~G6)·커밋 단위·승인 절차가 V3와 동일 규율로 이어진다.
- (+) 스펙의 중복 요구(비용·대시보드·출처)가 기존 Stage 예약 범위에 자연 흡수된다.
- (−) 스펙 문서의 장 번호와 Stage 번호가 1:1이 아니다 — 매핑은 backlog 문서가 유일한 접점.
- 제약: 스펙발 신규 요구가 생기면 트랙을 늘리지 말고 Stage 추가 + backlog 갱신으로 처리한다.
