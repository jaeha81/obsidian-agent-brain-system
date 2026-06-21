---
type: decision-matrix
category: plugin-management
updated: 2026-05-26
---

# 신규 기능 추가 시 Plugin 우선 결정 매트릭스

## 체크리스트 (순서대로)

신규 기능 요청이 들어오면 아래 순서로 검사한다.

```
[ ] 1. Community Plugin으로 가능한가?
      YES → Plugin 설정으로 해결
      NO  → 2번으로

[ ] 2. Plugin + Shell Commands 조합으로 가능한가?
      YES → 조합으로 해결
      NO  → 3번으로

[ ] 3. 아래 4가지 중 하나인가?
      a) Community Plugin으로 불가능
      b) 성능 문제 (플러그인이 너무 느림)
      c) 보안 문제 (외부 서비스 필수)
      d) 워크플로우 충돌
      YES → 직접 개발 허용
      NO  → 요구사항 재검토
```

---

## 기능별 Plugin 대응표

| 기능 요청 | Plugin 우선 | 커스텀 필요 |
|---------|------------|-----------|
| 노트 자동 생성 | Templater, QuickAdd | ❌ |
| 데이터 집계·시각화 | Dataview | ❌ |
| 작업 추적·마감 관리 | Tasks | ❌ |
| 대시보드 UI | Meta Bind, Buttons | ❌ |
| 검색 | Omnisearch | ❌ |
| 칸반 보드 | Kanban | ❌ |
| 쉘 스크립트 실행 | Shell Commands | ❌ |
| 외부 API 연동 (Discord 등) | — | ✅ 필수 |
| Claude API 직접 호출 | — | ✅ 필수 |
| 비동기 병렬 처리 | — | ✅ 필수 |
| 음성 인식 | — | ✅ 필수 |
| AI 패턴 학습 | — | ✅ 필수 |

[[bucky-system-hub]]
