---
type: knowledge-note
date: 2026-06-06
source: daily-plus
category: agent-prompting
tags:
  - "#area/ai_automation"
  - "#status/active"
summary: 이부장 에이전트용 세 가지 핸드오프 명령 — 온보딩·데일리하이라이트·매니페스트 적용
status: staged
approval_required: true
owner: bucky
applied_at: 2026-06-11
---

# I-Bujang Three Handoff Prompts

## 개요

이부장(I-Bujang) 에이전트가 반복 작업을 안전하게 인계받기 위한 세 가지 표준 핸드오프 명령어 패턴.
각 명령은 YAML frontmatter 산출물을 생성하며, `idempotency_key`로 중복 실행을 방지한다.

---

## 1. 사용자 온보딩 핸드오프

```yaml
# 명령 트리거: "이부장, 신규 사용자 온보딩 시작해"
handoff:
  command: ibujang_onboard_user
  idempotency_key: "onboard-{user_id}-{date}"
  output_schema:
    voice_url: "gs://bucket/voice/{idempotency_key}.m4a"
    stt_transcript: "[STT 전사 텍스트]"
    confidence: 0.92          # 0.0–1.0
    snippet_map:
      - label: "이름 확인"
        start: "00:08"
        end: "00:23"
      - label: "역할 설정"
        start: "00:45"
        end: "01:10"
  duplicate_policy: skip_if_key_exists
```

**실행 흐름**:
1. 사용자 ID + 날짜 기반 `idempotency_key` 생성
2. 음성 URL 유효성 확인 → STT 전사 실행
3. confidence < 0.80이면 수동 검토 큐 등록
4. 완료 시 온보딩 노트 Vault에 저장

---

## 2. 오늘의 플러스 (Daily Highlight) 핸드오프

```yaml
# 명령 트리거: "이부장, 오늘 플러스 요약 만들어"
handoff:
  command: ibujang_daily_highlight
  idempotency_key: "daily-plus-{YYYY-MM-DD}"
  output_schema:
    voice_url: "gs://bucket/voice/daily-{date}.m4a"
    stt_transcript: "[오늘의 핵심 인사이트 전사]"
    confidence: 0.95
    snippet_map:
      - label: "핵심 성과"
        start: "00:05"
        end: "00:30"
      - label: "다음 우선순위"
        start: "00:55"
        end: "01:20"
    highlight_tags:
      - "#daily-plus"
      - "#status/active"
  duplicate_policy: skip_if_key_exists
```

**실행 흐름**:
1. 당일 Vault 노트에서 `#daily-plus` 태그 수집
2. 음성 요약 생성 → mm:ss 클립 맵 첨부
3. HANDOFF_LOG에 날짜별 항목 추가

---

## 3. 매니페스트 적용 핸드오프

```yaml
# 명령 트리거: "이부장, 매니페스트 v{n} 적용해"
handoff:
  command: ibujang_apply_manifest
  idempotency_key: "manifest-v{version}-{date}"
  output_schema:
    voice_url: "gs://bucket/voice/manifest-{version}.m4a"
    stt_transcript: "[매니페스트 변경사항 전사]"
    confidence: 0.88
    snippet_map:
      - label: "변경 항목"
        start: "00:10"
        end: "00:40"
      - label: "롤백 조건"
        start: "01:00"
        end: "01:25"
    manifest_version: "{version}"
    rollback_key: "manifest-v{version-1}-{date}"
  duplicate_policy: skip_if_key_exists
  approval_required: true
```

**실행 흐름**:
1. 버전 넘버 + 날짜로 키 생성
2. 이전 매니페스트 백업 (`rollback_key`)
3. Bucky 승인 확인 후 적용
4. 적용 증거 Vault 기록

---

## 공통 원칙

| 항목 | 규칙 |
|------|------|
| idempotency_key | 동일 키 재실행 시 skip |
| confidence 임계값 | < 0.80 → 수동 검토 큐 |
| snippet 형식 | mm:ss (예: "01:23") |
| 승인 필요 명령 | approval_required: true 표기 |
| 실패 처리 | HANDOFF_LOG에 failed 항목 기록 |
