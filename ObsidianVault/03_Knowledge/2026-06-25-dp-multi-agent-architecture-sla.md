---
title: 멀티에이전트 표준 아키텍처와 SLA 플랜
date: 2026-06-25
source: daily-plus/2026-06-25.md (Card 2)
priority: P1
category: knowledge
status: distilled
tags:
- multi-agent
- architecture
- sla
- idempotency
- audit-trail
- control-plane
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: agent-ops
---

# 멀티에이전트 표준 아키텍처와 SLA 플랜

> ChatGPT Pulse 2026-06-25 Card 2 증류 (P1 · command-payload)
> Bucky 환경 즉시 적용 후보. 핵심 구조 변경 시 Bucky 패킷 검토 필요.

## 전체 흐름 (Thin-Agent / Fat-Control-Plane)

```
Control Plane (정책/라우팅)
  → Scheduler/Queue (내구성 큐·DLQ·재시도)
    → Worker Agents (무상태·플러그인 스킬)
      → State & Idempotency (Postgres + Redis)
      → Audit Trail (불변 S3/Object Lock)
  → Human Approval (서명 웹훅)
  → Observability (Prometheus + Grafana)
```

## 컴포넌트별 핵심 규칙

### Control Plane (두뇌)
- 작업 분해·라우팅·정책 집행 담당
- 실패 처리/재시도 관리는 Control Plane 책임 (Worker 아님)

### Scheduler/Queue
- at-least-once 전달 전제
- 가시성 타임아웃 ≥ 최대 처리시간
- DLQ + 리드라이브 설정 필수

### Worker Agents
- 무상태 유지 (스킬만 탑재 → LLM 교체 용이)
- 독립 실행 가능 단위로 설계

### State & Idempotency
- **Postgres**: 영속 상태 / 워크플로 이력
- **Redis**: idem 키 · 락 · 짧은 TTL
  - idem 키 스코프: 엔드포인트 + 페이로드
  - TTL ≥ 최대 재시도창 × 2
  - 원자적 "insert-or-ignore" 사용 (409 충돌 일관화)

### Audit Trail
- S3 Object Lock (불변 append-only)
- 저장 항목: 타임스탬프 · 주체 · 요약 해시 (SHA/HMAC)
- Per-Job Audit Object: 실행 전/후 입력·출력 요약 + 모델 버전 + 프롬프트 해시

### Human-in-the-Loop
- 승인 웹훅 + 서명 토큰
- HMAC으로 승인 본문과 실행 입력 연결

### Observability
- Prometheus 지표 + Grafana 대시보드
- 주요 지표: 요청율·오류율·지연·재시도량·idem 충돌율·에이전트별 성공률/SLO

## 하드와이어링 필수 항목

| 항목 | 규칙 |
|------|------|
| Idempotency | 키 스코프(엔드포인트+페이로드), TTL = 재시도창×2, 저장 응답 재사용 또는 409 |
| Optimistic Retry | 지수 백오프 + 지터, 부분 성공 레코드 재전달 방지 |
| Audit Object | 불변 저장소에 single 객체로 일괄 기록 |
| Sandbox | dev/test/prod 분리, 승인 없는 prod 변경 금지 |

## SLA 플랜 (판매용 템플릿)

| 티어 | 가용성 | 지원 | 추가 옵션 |
|------|--------|------|-----------|
| Bronze | 99.5% | 업무시간 이메일 | 모델 크레딧 관리 +10~25% |
| Silver | 99.9% | 8×5 전화 + 24h 응답 | 기본 런북, 관리형 백업 |
| Gold | 99.95% | 24/7 온콜 | 전용 인스턴스(+50%), 월간 아키 리뷰 |

## JH 환경 즉시 적용 체크리스트

- [ ] API 게이트웨이 + idem 키 필수화 (레이트리밋 포함)
- [ ] 큐 가시성 타임아웃 ≥ 최대 처리시간, DLQ 리드라이브 설정
- [ ] Postgres(상태) / Redis(idem·락) / S3 Object Lock(감사) 기동
- [ ] Grafana 대시보드: 요청율·오류율·지연·재시도량·idem 충돌율·에이전트별 SLO

## 연결 노트
- [[bucky-evolution-roadmap]]
- [[bucky-evolution-pipeline]]
- [[hubs/AgentBus]]
