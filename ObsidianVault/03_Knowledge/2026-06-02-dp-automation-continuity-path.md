---
type: knowledge-note
date: 2026-06-02
source: daily-plus
category: obsidian-queue
tags:
- '#area/ai_automation'
- '#status/active'
summary: 자동화 연속성 경로 — BuckyDailyPlus는 반드시 Agent Brain System 경로에서만 동작, 레거시 경로 금지,
  수집 실패 후 안전 복구 캡처
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# Automation Continuity Path

## 핵심 규칙

BuckyDailyPlus는 **반드시** `obsidian-agent-brain-system` 경로에서만 동작한다.
레거시 시스템 경로(`G:\내 드라이브\Obsidian Vault\` 등)를 실행 백엔드로 사용하지 않는다.

## 경로 경계 규칙

### 허용 경로
```
G:\내 드라이브\obsidian-agent-brain-system\
  ObsidianVault/
  scripts/
  data/
```

### 금지 경로 (archive-only)
```
G:\내 드라이브\Obsidian Vault\          # 구 볼트 — 읽기도 주의
G:\내 드라이브\AI개발계획\              # 레거시 계획 폴더
```

## 수집 실패 후 안전 복구 캡처

수집이 실패한 경우 복구 캡처 절차:

### 1. 실패 상태 기록

```python
RECOVERY_LOG_PATH = "G:/내 드라이브/obsidian-agent-brain-system/data/recovery_log.json"

def log_collection_failure(date_str, reason):
    entry = {
        "date": date_str,
        "reason": reason,
        "status": "recovery_needed",
        "recovery_attempted": False,
        "logged_at": datetime.now().isoformat()
    }
    append_to_json(RECOVERY_LOG_PATH, entry)
```

### 2. 복구 캡처 실행 조건

복구 캡처는 **현재 상태**를 기반으로만 실행:
- 실패 당일 데이터가 없는 경우
- Pulse 소스가 다시 접근 가능한 경우
- 이미 비교 보고서가 존재하지 않는 경우

### 3. 복구 캡처 실행 패턴

```python
def recovery_capture(date_str):
    if comparison_report_exists(date_str):
        log("Skipping recovery — comparison report already exists")
        return

    current_pulse = collect_pulse_safe()
    if current_pulse[1]:  # error
        log(f"Recovery failed: {current_pulse[1]['message']}")
        return

    save_as_recovery_snapshot(current_pulse[0], date_str)
    log(f"Recovery snapshot saved for {date_str}")
```

## 연속성 보장 체크리스트

- [ ] 스크립트 실행 경로가 `obsidian-agent-brain-system` 하위인지 확인
- [ ] 레거시 경로 하드코딩 없음
- [ ] 실패 시 복구 로그 생성됨
- [ ] 복구 캡처가 기존 보고서를 덮어쓰지 않음

## 관련 노트

- [[2026-06-02-dp-daily-plus-source-guard]]
- [[2026-06-02-dp-bucky-morning-report-failsafe]]
