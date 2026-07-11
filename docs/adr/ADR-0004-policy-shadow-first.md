# ADR-0004: 정책 집행은 shadow 우선 — enforce는 관측 후 별도 결정

- 상태: 승인됨 (플랜 확정, 2026-07-11) — 구현은 Stage 18(엔진)·19(배선)
- 관련: `docs/bucky/target_architecture.md` §3 · 플랜 오픈 퀘스천 1

## 맥락

리스크 규칙(T0~T3)은 현재 산문 문서(`ObsidianVault/00_System/ROUTING_RULES.md`, `ObsidianVault/03_Projects/agents/bucky.md`)에만 존재하고, 승인은 3중 경로(`pending_approval/` 파일큐 + `approve_task.py` CLI + Discord `!approve`)로 이미 운영 중이다. 코드화된 정책을 처음부터 차단(enforce) 모드로 배선하면 오판정 한 건이 운영 중인 자동화(스케줄 7종·Discord 봇)를 세울 수 있다.

## 결정

1. Stage 18: `config/policy_rules.yaml`(산문 규칙의 T0~T3 데이터화) + `scripts/core/policy_engine.py` — `evaluate(task_spec) -> {tier, decision, reason}` **순수 함수, 미배선**. `routing_policy.yaml`과 중복 키 금지.
2. Stage 19: worker가 디스패치 전 정책 상담 — 기본값 `features.policy_enforcement: shadow`. **shadow = 판정을 이벤트로만 방출, 차단 없음. 기존 동작 바이트 동일 회귀 필수.**
3. enforce 전환은 이번 플랜 범위가 아니다 — "shadow 운영 + 오판정 관측 + 사용자 승인" 3조건 후 별도 결정.
4. enforce 시에도 승인 메커니즘은 신설하지 않는다 — `require_approval` 판정은 기존 pending_approval 3중 경로를 그대로 사용한다 (승인 경로 이중화 갭 G7의 통합 접점).

## 결과

- (+) 정책 코드화의 이득(감사 가능·테스트 가능)을 운영 리스크 없이 먼저 얻는다.
- (+) shadow 이벤트 로그가 enforce 전환 결정의 근거 데이터가 된다.
- (−) shadow 기간에는 규칙 위반이 관측만 되고 막히지 않는다 — 기존 산문 규칙·수동 승인이 그동안의 방어선.
- 제약: shadow 판정과 실제 승인 경로의 불일치(이중 승인 경로 동기화 결함)는 이벤트 로그로 관측해 enforce 전 해소한다 (플랜 리스크 1).
