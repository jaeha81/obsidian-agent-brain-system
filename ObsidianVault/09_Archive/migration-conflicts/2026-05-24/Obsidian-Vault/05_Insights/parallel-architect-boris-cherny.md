---
type: knowledge
source: web
project: JH-Meta
system: JH-Obsidian-Second
status: done
priority: P2
owner: claude
date: 2026-04-24
tags: [parallel-workflow, claude-code, boris-cherny, agent-ops, productivity]
  - #status/archive
  - #status/completed
summary: "Claude Code 제작자 Boris Cherny의 고속 병렬 AI 워크플로 — worktree 환경 분리, 자가 검증 루프, 계획 모드 우선의 3대 원칙"
next_action: "분류 후 `05_Insights/parallel-workflow-boris-cherny.md` 또는 `03_Strategy/` 로 이동"
---

# The Parallel Architect — Boris Cherny의 고속 AI 워크플로

> 로컬 PC에서 pull 받은 뒤 `OBSIDIAN-SECOND/00_Inbox/` 로 이동 → 분류 후 `05_Insights/` 또는 `03_Strategy/` 로 승격.

## 한 줄 결론

**AI 생산성은 복잡한 아키텍처가 아니라 "분리된 병렬 작업 공간 + 탄탄한 사전 계획 + 자동화된 검증 + 지속 피드백"의 조합에서 나온다.**

## 메타 정보

- 출처: NotebookLM 요약 — "The Parallel Architect: Boris Cherny's High-Velocity AI Workflow"
- 주체: Boris Cherny (Claude Code 제작자)
- 측정 지표: 매주 PR 50~100개 처리, 동시 Claude 인스턴스 최대 15개 (터미널 5 + 브라우저 10)

## 핵심 원리 1 — 병렬 실행의 인프라

| 요소 | 방식 | 효과 |
|------|------|------|
| 환경 분리 | 같은 리포를 각각 **별도 git checkout (worktree)** 에서 운영 | 코드 충돌 제거, 독립 진행 |
| 탭 번호화 | 터미널 탭에 1~5 번호 부여 | 라우팅 인지 부하 감소 |
| 알림 시스템 | Claude가 사용자 입력 필요 시 **시스템 알림** | 폴링·감시 불필요 |
| 라운드로빈 운영 | 작업 끝난 탭부터 즉시 새 작업 투입 | 유휴 시간 0에 수렴 |

> 핵심 통찰: **에이전트 수보다 "간섭 없는 환경 구성"이 더 중요하다.** 세션 15개를 돌려도 혼란이 없는 이유는 "복잡한 오케스트레이션"이 아니라 **단순한 격리**다.

## 핵심 원리 2 — 품질 3원칙

### (1) 공용 CLAUDE.md — ~2,500 토큰 살아있는 규율집

- 코드베이스 전체에 적용되는 단일 컨벤션 파일
- Claude가 실수할 때마다 **즉시 새 규칙 추가**
- AI를 "현장에서 배우는 주니어 개발자"로 대한다 → 실수는 학습 자산

### (2) 자가 검증 수단 의무

- Claude가 **자기 결과를 직접 검증**할 수 있는 도구를 반드시 준비
- 예: 브라우저 조작 도구, 휴대폰 시뮬레이터, 실제 서버 띄우기, E2E 자동화
- 측정: 피드백 루프만 갖춰도 **품질 2~3배 상승**

### (3) 계획 모드 우선 (Plan First)

- "일단 코드 만들고 나중에 수정" ❌
- **계획 모드에서 세션 시작 → 아키텍처 확정까지 AI와 대화** → 그 다음 구현
- 추천 조합: **Opus + thinking 활성화**
- 이유: 사람의 오류 수정 시간이 AI 코딩의 진짜 병목

## JH 통합 시스템에 대한 시사점

| JH 요소 | 연결 지점 |
|---------|----------|
| JH Harness (§11 역할 분리) | Planner/Builder/Reviewer 세션을 worktree로 물리 분리하면 §13-1 ("같은 위치 무분별 저장") 위반 원천 차단 |
| §7 Claude 세션 역할 분리 (A~E) | 기존 "논리적 역할 분리"에 **"물리적 환경 분리(worktree)"** 계층 추가 → 혼선 방지 강화 |
| §12 산출물 환원 | 자가 검증 루프 = "실행 결과물" 환원 품질의 상한선을 결정 |
| 개발 워크플로우 2단계(plan) | Boris 원칙과 일치. 단, "2단계 완료 전 4단계 진입 금지"를 규범화할 여지 |
| AI 응답 원칙 "단순성 우선" | Boris의 "단순한 격리" 철학과 정합 |

## 반론·한계

- 15 인스턴스 병렬은 **구독 한도 / 비용** 제약이 있음 — 개인 환경에선 3~5개가 현실적
- worktree 전환 비용: 리포 규모 크면 디스크·CI 부담 존재
- "공용 CLAUDE.md 2,500 토큰" 원칙 — JH의 현재 CLAUDE.md는 ~26KB (~6,500+ 토큰)로 2.6배 초과. 단순 준수 대신 **§규율·절차 분리 원칙 (적응형)**으로 해결 → 2026-04-24 CLAUDE.md §8 규칙 신설 반영.

## 반영 기록

- 2026-04-24 1차 반영 (CLAUDE.md §7 worktree / 자가 검증 / Plan First / guides/multi-agent.md)
- 2026-04-24 2차 보강 — 미반영 2건 처리:
  - 실수→규칙 승격 의무 → CLAUDE.md §7 (글로벌 안전 규칙)
  - CLAUDE.md 레이어 원칙 (2,500 토큰 원칙의 JH식 적응) → CLAUDE.md §8 (글로벌 안전 규칙)
- 팩트 체크: 원본 14개 중 13개 규범 반영, 1개(주당 PR 처리량)는 지표로 knowledge 전용 유지

## 재사용 프롬프트 후보

```
새 기능 작업 시작 전 체크:
1. 이 작업은 어느 worktree에서 수행되는가? (다른 기능과 격리되었는가)
2. 완료 후 Claude가 스스로 검증할 수단이 있는가? (없으면 먼저 구축)
3. 계획이 확정되었는가? 아직이면 plan 모드로 회귀
```

## 연결 노트

- (로컬 이동 후) [[parallel-architect-boris-cherny]]
- 관련: `03_Strategy/claude-multi-session.md` (있다면 연결)
- 관련: `05_Insights/ai-productivity-bottleneck.md` (있다면 연결)
