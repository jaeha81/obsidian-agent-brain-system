---
type: knowledge-note
date: 2026-06-02
source: daily-plus
category: verification
tags:
- '#area/ai_automation'
- '#status/active'
summary: 공개 대시보드 무결성 체크리스트 — 비교 보고서는 기존 Pulse Evolution 비교가 없는 날짜에만 생성, 404 상태는 보고서
  생성 불가, 복구 캡처는 현재 상태 기반
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# Public Dashboard Integrity Checklist

## 핵심 원칙

비교 보고서(Comparison Report)는 다음 조건을 모두 만족할 때만 생성 가능:
1. 해당 날짜에 기존 Pulse Evolution 비교 보고서가 **없어야** 한다
2. Pulse 소스가 **404가 아닌** 정상 상태여야 한다
3. 수집된 데이터가 **비어 있지 않아야** 한다
4. 복구 캡처는 **현재 상태 데이터**만 사용해야 한다

## 사전 생성 검증 게이트

```python
def can_create_comparison_report(date_str, pulse_result):
    # Gate 1: 기존 보고서 중복 방지
    if comparison_report_exists(date_str):
        return False, "report_already_exists"

    # Gate 2: 404 상태 차단
    if pulse_result.get("status_code") == 404:
        return False, "source_404"

    # Gate 3: 빈 데이터 차단
    if len(pulse_result.get("items", [])) == 0:
        return False, "empty_data"

    # Gate 4: 복구 캡처 출처 검증
    if pulse_result.get("source") == "legacy_path":
        return False, "invalid_source_path"

    return True, "ok"
```

## 무결성 체크리스트

### 생성 전 체크

- [ ] 해당 날짜 `comparison_{date}.json` 파일 부재 확인
- [ ] Pulse HTTP 상태 코드 != 404
- [ ] `items` 배열 길이 > 0
- [ ] 데이터 타임스탬프가 당일 범위 내

### 생성 후 체크

- [ ] 보고서 파일이 올바른 경로에 저장됨
- [ ] 이전 보고서가 덮어써지지 않음
- [ ] 보고서에 `generated_at` 타임스탬프 포함
- [ ] Bucky 채널에 생성 완료 알림 전송됨

### 복구 캡처 체크

- [ ] 복구 캡처는 실패 당일 기준으로만 실행
- [ ] 실패 이후 Pulse가 정상 상태로 돌아온 경우에만 실행
- [ ] 복구 캡처 결과물에 `recovery: true` 플래그 포함
- [ ] 복구 보고서와 정상 보고서 구분 저장

## 금지 사항

| 금지 | 이유 |
|------|------|
| 404 상태에서 보고서 생성 | 소스 장애 상태를 정상 데이터로 오인 |
| 기존 보고서 덮어쓰기 | 검증된 과거 데이터 손상 |
| 레거시 경로 데이터 사용 | 운영 권한 외 경로 |
| 빈 배열로 비교 실행 | "모든 항목 삭제됨" 오판 생성 |

## 관련 노트

- [[2026-06-02-dp-daily-plus-source-guard]]
- [[2026-06-02-dp-bucky-morning-report-failsafe]]
- [[2026-06-02-dp-automation-continuity-path]]
