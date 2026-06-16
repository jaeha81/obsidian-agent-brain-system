# JH 통합 구축 시스템 — 시스템 브리핑

> 최종 업데이트: 2026-04-29 20:16 KST  
> 대상: Claude · Codex · 대표  
> 상세 명세서: `~/.claude/plans/virtual-mixing-oasis.md`

---

## 시스템 구조

```
대표 (방향·지시·승인)
  ├── Claude (운영 총괄) ──→ GitHub / Obsidian / Google Drive 라우팅
  ├── Codex  (독립 검수) ──→ Claude 구현물 검수 후 대표 직보
  └── Obsidian (지식 허브) ──→ 개발 기록 · 문맥 · 설계 결정

로컬 PC (실행환경)
  ├── 집 PC: D:\ai프로젝트\
  ├── 사무실 PC: C:\ai프로젝트\ (whoami=설계4)
  └── 노트북: C:\ai프로젝트\ (whoami=info)
```

---

## 저장소 역할 분리 (핵심 원칙)

| 저장소 | 담당 | 금지 |
|--------|------|------|
| **GitHub** | 코드 · 버전관리 · 단일 진실 원천 | node_modules, .env 커밋 |
| **Google Drive** | 데이터 · 문서 · 자료 · 대용량 파일 | 코드 저장, Git처럼 사용 |
| **Obsidian Vault** | 개발 기록 · 설계 결정 · 지식 연결 | 코드 직접 저장 |
| **로컬 PC** | 실행환경 · node_modules 유지 | 코드 로컬만 보관 |
| **G:\JH-SHARED** | Claude ↔ Codex 공유 시스템 정보 | 코드 · 데이터 저장 |

---

## 에이전트 시스템 구조

### JH 브레인 시스템 (`D:\ai프로젝트\jh-brain-system\`)
| 에이전트 | 역할 |
|---------|------|
| 므네메 | 오케스트레이터 |
| 헤르메스 | 비서 · 대표 디지털 분신 |
| 스카우트 | 리서치 |
| 므네모시네 | Obsidian RAG |

### JH 하네스 (`D:\ai프로젝트\jh-harness\`)
| 에이전트 | 역할 |
|---------|------|
| 아고니스 | 오케스트레이터 · 의도 분류 |
| 아르키 | 리서치 · 기획 |
| 재하 | 구현 위임 |
| 카이 | 계획 검증 |
| 에어라 | 검증 · 오류 학습 |
| 기르 | GitHub 전담 |

- **통신 채널**: `synapse.md` — 브레인 ↔ 하네스 단방향 통신
- **경로**: `D:\ai프로젝트\jh-brain-system\synapse.md`

---

## 멀티 PC 동기화 원칙

```
작업 종료 시: git push → ~/.claude push.sh
작업 시작 시: git pull → ~/.claude pull.sh
기준 정보:   GitHub(코드) + Obsidian(지식) + G:\(자료) + ~/.claude(지침)
```

---

## Claude ↔ Codex 협력 원칙

| 항목 | 규칙 |
|------|------|
| 구현 | Claude가 담당 |
| 검수 | Codex가 독립적으로 담당 |
| 보고 | Codex → 대표 직보 (Claude 경유 금지) |
| 수정 | 대표 지시 후 Claude가 실행 |
| 자동 처리 | Claude가 Codex 결과 자동 처리 금지 |

---

## 핵심 경로 참조

| 자원 | 경로 |
|------|------|
| Claude 지침 | `~/.claude/CLAUDE.md` |
| 시스템 가이드 | `~/.claude/guides/jh-system.md` |
| 동기화 지침 | `G:\내 드라이브\Claude\동기화-지침.md` |
| 이 파일 | `G:\내 드라이브\JH-SHARED\jh-system.md` |
| Obsidian Vault | `C:\Users\user1\Documents\Obsidian Vault\` |
| synapse.md | `D:\ai프로젝트\jh-brain-system\synapse.md` |
| GitHub | https://github.com/jaeha81 |
