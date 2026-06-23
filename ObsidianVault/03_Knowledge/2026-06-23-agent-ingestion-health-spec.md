---
title: 에이전트 수집 파이프라인 헬스 텔레메트리 스펙
tags:
  - ops
  - monitoring
  - telemetry
  - agent-health
  - obsidian
  - ingestion
source: pulse-evolution/2026-06-23
distilled_at: 2026-06-23
status: active
category: agent-ops
---

# 에이전트 수집 파이프라인 헬스 텔레메트리 스펙

에이전트별 수집 성공/실패, 드리프트, 읽기전용 위반, 오래된 파일까지 한 번에 보여주는 건강도 텔레메트리.

## 목적과 범위

- 목적: 데이터 수집 파이프라인(에이전트별)의 건강 상태를 실시간으로 가시화하고, "진짜 문제"일 때만 알림.
- 대상: 에이전트(ingestion runners), 인박스/아웃박스(S3·로컬), Git 리포지토리, Vault/Queue 상태.

## 핵심 지표 (에이전트별)

- ingestion_success_count, ingestion_failure_count
- fail_rate = failures / (successes + failures) — 0 나누기 방지
- last_processed_id vs vault_run_id drift (불일치 정도, 오프셋 차이)
- frontmatter_mismatches: sha256(프론트매터) ≠ 바디 해시
- read_only_flag 위반 (읽기전용 문서가 수정됨)
- 파일 나이 히스토그램: inbox_age_hist [0-1h, 1-6h, 6-24h, 24-72h, >72h]
- git_head(SHA), last_commit_ts(UTC)

## 중대한 변화 (Material Change) 규칙

다음 중 하나라도 참이면 중대한 상태 = true:
- fail_rate > 5%
- inbox_max_age > 24h 또는 outbox_max_age > 24h
- read_only_flag 위반 1건 이상

알림은 상태가 바뀔 때만 발송 (정상→중대, 중대→정상). 동일 상태 지속 시 억제.

## 알림 페이로드 (필수 필드)

```json
{
  "run_id": "2026-06-21T11:30:00Z#abc123",
  "agent": "bucky-ingestor",
  "failing_file_count": 7,
  "total_files": 112,
  "pct_fail": 6.25,
  "top_5_failure_reasons": [
    {"reason":"YAML frontmatter parse error","count":3},
    {"reason":"S3 403 Forbidden","count":2},
    {"reason":"Checksum mismatch","count":1}
  ],
  "max_stale_age_hours": {"inbox": 28.4, "outbox": 3.1},
  "drift_summary": {"last_processed_id": 158923, "vault_run_id": 158911, "delta": 12},
  "evidence_links": {"git_blobs": [...], "s3_keys": [...]}
}
```

## 데이터 모델

agent_health_runs: run_id(pk), agent, ts, success, failure, fail_rate, inbox_max_age_h, outbox_max_age_h, drift_delta, git_head, last_commit_ts, read_only_violations, mismatch_count, top_failure_reasons(jsonb), material(bool)

material_state_edges: edge_id, agent, ts, prev_material, next_material, run_id

audit_objects: audit_sha256(pk), run_id, hmac_header, payload(jsonb), created_ts, storage_uri

## 핵심 SQL 스니펫

실패율:
```sql
SELECT agent,
       SUM(failure)::float/(SUM(success)+SUM(failure)) AS fail_rate
FROM ingest_logs
WHERE ts >= now() - interval '5 minutes'
GROUP BY agent;
```

드리프트:
```sql
SELECT a.agent, (MAX(a.last_processed_id)-MAX(v.vault_run_id)) AS delta
FROM agent_offsets a JOIN vault_offsets v USING(agent)
GROUP BY a.agent;
```

머티리얼 판정:
```sql
material = (fail_rate > 0.05)
        OR (inbox_max_age_h > 24 OR outbox_max_age_h > 24)
        OR (read_only_violations > 0)
```

## 심각도 분류

- P1: read_only_flag 위반 또는 outbox_max_age > 24h
- P2: 실패율 > 5%
- P3: 그 외 (대시보드에만 표시)

## 스케줄 & 보관

- 주기: 5분마다 평가 (크론/워크플로우 스케줄러)
- 보관: 텔레메트리 90일 유지
- 감사: 각 알림에 대해 불변 감사 객체 (audit_sha256 + HMAC 헤더) → 버전닝 켠 S3에 저장

## 구현 체크리스트

- [ ] 수집 커넥터: 로그/큐/파일시스템/Git 리더
- [ ] 지표 계산 함수 모듈: 실패율·히스토그램·드리프트·프론트매터 검사
- [ ] 상태 머신: 에이전트별 (prev_material → next_material) 전이 감지
- [ ] 알림 어댑터: Slack/Email/Webhook
- [ ] 감사 레코더: SHA256 + HMAC 생성, 저장
- [ ] 대시보드: 표 + 히스토그램 + 타임라인 + 증거 링크

## 연결 노트

[[webhook-replay-ops-checklist]]
[[recovery-oneshot-playbook]]
[[hubs/AgentBus]]
