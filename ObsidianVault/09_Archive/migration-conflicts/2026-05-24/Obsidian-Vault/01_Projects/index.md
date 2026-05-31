---
type: reference
system: JH-Obsidian-Vault
date: 2026-04-29
status: active
tags:
  - #status/archive
  - #status/active
---

# JH 프로젝트 전체 현황 인덱스

> 최종 업데이트: 2026-04-29 20:16 KST  
> 기준 경로: D:\ai프로젝트\  
> 상태 범례: 🔄 활성 / ✅ 완료 / 📦 아카이브 / ⏸ 보류

---

## 핵심 인프라 (항상 활성)

| 프로젝트 | 상태 | GitHub | 역할 |
|---------|------|--------|------|
| jh-brain-system | 🔄 | jaeha81/jh-brain-system | 브레인 에이전트 시스템 (므네메·헤르메스·스카우트·므네모시네) |
| jh-harness | 🔄 | jaeha81/jh-harness | 하네스 실행 플랫폼 (아고니스 외 8 에이전트) |
| JH-CLAUDE-DASHBORD | 🔄 | jaeha81/JH-CLAUDE-DASHBORD | Claude 멀티패널 세션 관리 |
| JH-Agent-Dashboard | 🔄 | jaeha81/JH-Agent-Dashboard | 에이전트 현황 모니터링 |
| jh_windows | 🔄 | jaeha81/jh_windows | GitHub 기반 브리핑 대시보드 |
| ~/.claude | 🔄 | jaeha81/claude-projects-jh | Claude 지침·스킬·훅 중앙 저장소 |

---

## 활성 개발 프로젝트

| 프로젝트 | 상태 | 분류 | 메모 |
|---------|------|------|------|
| JH BuildFlow | 🔄 | 빌드 자동화 | synapse.md 언급, 경로 정정 완료 (2026-04-26) |
| precon-ai | 🔄 | AI 도구 | — |
| arkistore | 🔄 | 플랫폼 | — |
| VISIONAI_SYSTEM | 🔄 | AI 시스템 | — |
| jh-free-ott-hub | 🔄 | 콘텐츠 | — |
| JH-multi-excel-estimate | 🔄 | 견적 도구 | — |
| jh-handoff | 🔄 | 핸드오프 | — |
| jh-keanu | 🔄 | 특화 서브워크스페이스 | — |
| jh-estimate-system | 🔄 | 견적 시스템 | — |

---

## 점검 필요 (보류/상태 불명)

| 프로젝트 | 마지막 확인 | 판단 필요 사항 |
|---------|------------|--------------|
| AonID_System | — | 활성/보류 확인 필요 |
| jh-Development-Status-Analysis | — | 상태 확인 필요 |
| jh-obsidian | — | 중복 여부 확인 |
| jh-brain-system (D: 루트) | — | jh-brain-system 레포와 동일 여부 확인 |

---

## 아카이브 대상 (6개월 이상 비활성 추정)

> 아래 항목은 다음 월간 점검 시 GitHub archive + 로컬 삭제 검토 대상

- bitmex-ai-bot (비트코인 자동매매, 운영 여부 불명)
- desktop-tutorial (튜토리얼 프로젝트)
- upload-auto-netlify (용도 불명)
- github-sisyphus-dashboard (대체 대시보드 존재 시 중복)

---

## 월간 점검 체크리스트

매월 1회 아래 항목을 점검한다:

- [ ] 각 활성 프로젝트 마지막 git commit 날짜 확인
- [ ] 6개월 이상 비활성 → archive 대상으로 이동
- [ ] 완료 프로젝트 로컬 폴더 삭제 확인 (GitHub push 먼저)
- [ ] 이 index.md 상태 업데이트
- [ ] Obsidian INDEX.md 날짜 갱신

---

## 조회 가이드

| 질문 | 찾아볼 위치 |
|------|-----------|
| 특정 프로젝트 설계 기록 | `01_Projects/[프로젝트명]/` 또는 `02_Architecture/` |
| 운영 에러 이력 | `04_Issues/` |
| 오늘 한 일 | `05_Logs/daily/YYYY-MM-DD.md` |
| 전체 시스템 구조 | `~/.claude/guides/jh-system.md` |
| 프로젝트 코드 | GitHub: github.com/jaeha81/[프로젝트명] |
