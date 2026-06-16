# JH 일일보고 체계

## 디렉토리 구조

```
daily-reports/
  YYYY-MM-DD/
    claude.md                        ← Claude 작업 내역 (Claude만 작성)
    codex-review-YYYYMMDD-daily.md   ← Codex 독립 검수 결과 (Codex만 작성)
    index.md                         ← 링크 + 최종 상태 요약 (Claude 생성)

../03_LOGS/
  daily-report-events.jsonl          ← append-only 감사 로그 (양쪽 공통)
```

## 에이전트 권한

| 에이전트 | 쓰기 가능 파일 | 금지 |
|----------|--------------|------|
| Claude | `claude.md`, `index.md` | Codex 파일 수정 |
| Codex | `codex-review-*.md` | Claude 파일 수정 |
| 공통 | `daily-report-events.jsonl` (append-only) | 기존 줄 수정 |

## 파일별 내용

**claude.md**
- 오늘 한 일 (시스템별 작업 내역 + 커밋 목록)
- 발견된 이슈 (미해결 항목 이월 포함)
- Codex 검수 요청 항목
- 내일 이어서 할 것

**codex-review-YYYYMMDD-daily.md**
- 독립 검수 결과 (P1/P2/P3)
- AI-Slop 감지 여부
- 반복 패턴 경보

**index.md**
- 두 파일 링크
- 날짜 최종 상태 한 줄 요약

## 세션 종료 시 Claude 체크리스트

1. `daily-reports/YYYY-MM-DD/claude.md` 생성 또는 업데이트
2. `daily-reports/YYYY-MM-DD/index.md` 생성 또는 업데이트
3. `03_LOGS/daily-report-events.jsonl` append
4. git 커밋 → push
