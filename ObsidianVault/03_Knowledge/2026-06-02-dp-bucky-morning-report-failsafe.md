---
type: knowledge-note
date: 2026-06-02
source: daily-plus
category: knowledge-candidate
tags:
- '#area/ai_automation'
- '#status/active'
summary: Bucky 09시 보고 fail-safe — 빈 에러 캡처 강화, 실패를 needs-attention 보고로 처리, 기존 비교 보고서
  보호
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# Bucky Morning Report Fail-Safe

## 목적

`daily_plus_morning_report.py`에서 Pulse 수집 실패 시 기존 비교 보고서를 덮어쓰지 않고, 실패를 "주의 필요" 보고로 처리하는 fail-safe 패턴.

## 현재 문제점

- 빈 에러 캡처: 예외 발생 시 스택 트레이스 없이 빈 결과 반환
- 실패 상태와 정상 상태를 동일하게 처리
- Pulse 실패 시 기존 비교 보고서가 빈 데이터로 덮어써짐

## Fail-Safe 강화 패턴

### 1. 빈 에러 캡처 강화

```python
def collect_pulse_safe():
    try:
        result = collect_pulse()
        if not result or len(result.get("items", [])) == 0:
            raise ValueError("Empty collection result")
        return result, None
    except Exception as e:
        error_info = {
            "type": type(e).__name__,
            "message": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat()
        }
        return None, error_info
```

### 2. 실패를 needs-attention 보고로 전환

```python
def generate_morning_report(pulse_result, error_info):
    if error_info:
        return {
            "status": "needs_attention",
            "reason": error_info["message"],
            "action_required": "Manual pulse check needed",
            "previous_data_preserved": True
        }
    # 정상 보고 생성
    return generate_normal_report(pulse_result)
```

### 3. 기존 비교 보고서 보호

```python
def save_report_safely(report, date_str):
    existing_path = f"reports/comparison_{date_str}.json"
    if os.path.exists(existing_path) and report["status"] == "needs_attention":
        # 실패 시 기존 보고서 보존, 실패 로그만 추가
        log_failure(report, date_str)
        return  # 덮어쓰지 않음
    save_report(report, existing_path)
```

## 09시 보고 흐름

```
수집 시도
  ↓ 성공 → 정상 비교 보고서 생성 → Discord 전송
  ↓ 실패 → needs-attention 보고 생성
           → "수집 실패: {reason}" 메시지 Discord 전송
           → 기존 보고서 유지
           → 실패 로그 기록
```

## 적용 파일

- `scripts/daily_plus_morning_report.py`

## 관련 노트

- [[2026-06-02-dp-daily-plus-source-guard]]
- [[2026-06-02-dp-public-dashboard-integrity]]
