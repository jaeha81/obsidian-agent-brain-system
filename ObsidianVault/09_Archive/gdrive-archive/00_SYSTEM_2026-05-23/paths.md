# JH 시스템 — 핵심 경로 참조표

> 최종 업데이트: 2026-05-01 KST

---

## PC별 기본 경로

| PC | 감지 기준 | 프로젝트 루트 |
|----|----------|-------------|
| 집 PC (user1) | D:\ai프로젝트\ 존재 | `D:\ai프로젝트\` |
| 사무실 PC (설계4) | whoami=설계4 | `C:\ai프로젝트\` |
| 노트북 (info) | whoami=info | `C:\ai프로젝트\` |

---

## 핵심 시스템 경로

| 시스템 | 경로 |
|--------|------|
| 브레인시스템 | `D:\ai프로젝트\jh-brain-system\` |
| 하네스 | `D:\ai프로젝트\jh-harness\` |
| Claude 대시보드 | `D:\ai프로젝트\JH-CLAUDE-DASHBORD\` |
| Agent Dashboard | `D:\ai프로젝트\JH-Agent-Dashboard\` |
| synapse.md | `D:\ai프로젝트\jh-brain-system\synapse.md` |

---

## 지식/자료 경로

| 자원 | 경로 |
|------|------|
| Google Drive | `G:\내 드라이브\` |
| Claude ↔ Codex 공유 | `G:\내 드라이브\JH-SHARED\` |
| 동기화 지침 | `G:\내 드라이브\Claude\동기화-지침.md` |

---

## PC별 Obsidian 경로 (중요: 하드코딩 금지)

| PC | 사용자 | Obsidian Vault | OBSIDIAN-SECOND |
|----|--------|---------------|----------------|
| 집 PC | user1 | `C:\Users\user1\Documents\Obsidian Vault\` | `C:\Users\user1\Documents\OBSIDIAN-SECOND\` |
| 노트북 | info | `C:\Users\info\Documents\Obsidian Vault\` | `C:\Users\info\Documents\OBSIDIAN-SECOND\` |
| 사무실 PC | 설계4 | `C:\Users\설계4\Documents\Obsidian Vault\` | `C:\Users\설계4\Documents\OBSIDIAN-SECOND\` |

**공통 경로 (Google Drive):**
- Obsidian Vault 원본: `G:\내 드라이브\Obsidian Vault\`
- OBSIDIAN-SECOND 원본: `G:\내 드라이브\OBSIDIAN-SECOND\`

**운영 기준:**
- 집 PC `user1`의 Documents 경로를 기준 경로로 본다.
- 노트북/사무실 PC에 로컬 Documents 미러가 없으면 Google Drive 원본 경로를 사용한다.
- `C:\ai-main\jh-obsidian`, `C:\ai프로젝트\JA-OBSIDIAN-SECOND` 같은 임시/구버전 경로는 기준 경로로 사용하지 않는다.
- 2026-05-15 사무실 PC: `C:\Users\설계4\Documents\Obsidian Vault`, `C:\Users\설계4\Documents\OBSIDIAN-SECOND`는 Google Drive 원본을 바라보는 junction으로 동기화했다.

> ⚠️ jh-brain-system/data/config.json의 vaultPath는 **각 PC에서 실행 시 해당 PC 경로**로 설정해야 한다.  
> 노트북 설정 방법: `G:\내 드라이브\JH-SHARED\노트북-옵시디언-설정가이드.md` 참조

---

## Claude 지침 경로

| 파일 | 경로 |
|------|------|
| 전역 지침 | `C:\Users\user1\.claude\CLAUDE.md` |
| 시스템 가이드 | `C:\Users\user1\.claude\guides\jh-system.md` |
| 전체 명세서 | `C:\Users\user1\.claude\plans\virtual-mixing-oasis.md` |
| GitHub 동기화 | https://github.com/jaeha81/claude-projects-jh |

---

## Codex 지침 경로

| 파일 | 경로 |
|------|------|
| 전역 지침 | `C:\Users\user1\.codex\AGENTS.md` |
| 공유 시스템 정보 | `G:\내 드라이브\JH-SHARED\jh-system.md` |
