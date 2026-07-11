# ADR-0003: 이벤트 = 단일 append-only jsonl 관측 로그 (이벤트 버스·파일 큐 아님)

- 상태: 승인됨 (플랜 확정, 2026-07-11) — 구현은 Stage 15
- 관련: [ADR-0001](ADR-0001-queue-canonical-oracle.md) (10_AgentBus 파일 큐 금지) · `docs/bucky/target_architecture.md` P-3

## 맥락

실측(07-11) 결과 이벤트 기록이 3개 jsonl로 분산되어 있고 통합 봉투(envelope)가 없다. 스펙 §26은 `event_bus: unknown`으로 두었고, 스펙 P0-2·P0-8은 이벤트 기록과 model_decision 감사를 요구한다. 한편 10_AgentBus 파일 큐 신설은 영구 금지(ADR-0001)이며, G:드라이브 동기화 위 파일 기반 pub/sub은 경합·유실 위험이 크다.

## 결정

1. 이벤트는 **`05_Logs/bucky-events.jsonl` 단일 append-only 로그** 하나로 기록한다 (`scripts/core/event_log.py`, Stage 15).
2. envelope 스키마: `event_id / ts / kind / task_id / conversation_id / agent / model / payload`.
3. **이벤트 버스가 아니다** — 구독·라우팅·재전송 없음. 소비는 읽기 전용 집계(대시보드·감사)뿐.
4. 기존 3개 jsonl은 불변 유지 (이관·삭제 없음). 10_AgentBus 무접촉.
5. 기록 실패는 try/except 격리로 **실행 비차단** (G:드라이브 append 경합 대비 — 관측이 실행을 죽이지 않는다).

## 결과

- (+) model_decision·정책 shadow 판정·예산 경고가 한 파일에서 시간순 감사 가능.
- (+) 불변 이벤트 원장 갭(G3·G8) 동시 해소.
- (−) 유실 허용 설계다 — 기록 실패 시 이벤트가 빠질 수 있다 (정본성은 큐·볼트가 담당하므로 허용).
- 제약: 이 로그를 큐·트리거로 쓰는 코드는 금지. 그 요구가 생기면 oracle 큐로 간다.
