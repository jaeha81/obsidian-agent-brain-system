---
title: Google AdSense Operating System
created: 2026-06-16
updated: 2026-06-16
owner: Bucky
project: Google-AdSense-Operating-System
repo: https://github.com/jaeha81/Google-AdSense-Operating-System.git
local_path: D:\ai프로젝트\Google-AdSense-Operating-System\
status: active
subscription: claude-code-max + codex-pro
tags:
  - #area/business_model
  - #project/adsense-os
  - #status/active
category: monetization
summary: "AI 에이전트 탑재 구글 애드센스 수익화 운영 대시보드. 다중 블로그 포트폴리오 관리, 키워드/콘텐츠/SEO/수익 자동화."
---

# Google AdSense Operating System

## 프로젝트 개요

92년생 블로거 75억 적립 전략(채널: 돈터치) 벤치마킹.  
"디지털 건물주" 전략을 AI 에이전트로 자동화한 풀스택 수익화 운영 대시보드.

---

## 구독 구성 (Subscription)

| 에이전트 | 구독 | 역할 |
|---------|------|------|
| Claude Code | **Max 플랜** | 구현 / 운영자 / 메인 개발 |
| Codex | **Pro 플랜** | 독립 검수 / 코드 리뷰 |
| Bucky | Orchestrator | 패킷 관리 / 라우팅 / 권한 판단 |

> Claude Code Max: 고용량 컨텍스트, 대형 코드베이스 작업 최적화  
> Codex Pro: 독립 검수, Claude 판단 비종속 검토

---

## 권한 매핑 (Agent Authority)

### Claude Code (구현 권한)

```
허용:
  - D:\ai프로젝트\Google-AdSense-Operating-System\ 전체 읽기/쓰기
  - backend/ — FastAPI 코드, 에이전트 코드, DB 모델, 라우터
  - frontend/src/ — Next.js 페이지, 컴포넌트, lib
  - .gitignore, README.md, .claude/launch.json
  - git commit (사용자 명시 승인 후)
  - git push (사용자 명시 승인 후)

금지:
  - 프로덕션 DB 직접 수정 (backend/adsense_os.db)
  - ANTHROPIC_API_KEY, 기타 시크릿 파일 커밋
  - .env 파일 커밋 (`.env.example`만 허용)
  - 사용자 승인 없이 GitHub 외부 배포
  - 다른 레포/프로젝트 패킷 재사용
```

### Codex (검수 권한)

```
허용:
  - 전체 파일 읽기 (독립 확인용)
  - 검수 결과 사용자 직보 (Claude 경유 금지)
  - uncommitted 변경분 / 최근 커밋 기본 확인

금지:
  - Claude Code 구현 중인 파일 무단 수정
  - commit / push (사용자 명시 요청 시에만)
  - Claude의 결론 자동 신뢰
```

### Bucky (오케스트레이터 권한)

```
허용:
  - 프로젝트 패킷 발행 및 갱신 (이 파일)
  - Context Pack 선택 및 라우팅
  - Claude Code / Codex 작업 범위 지정
  - 이 문서 내 scope/constraints 수정

금지:
  - 코드 직접 수정
  - 사용자 승인 없이 범위 확장
```

---

## 현재 베이스라인 (as of 2026-06-16)

```
상태: v1.0 완성 · GitHub push 완료
커밋: 43ad2d4 — feat: Google AdSense OS v1.0

구조:
  backend/
    main.py              — FastAPI 앱, /api/stats
    database.py          — SQLite 연결
    models.py            — Site/Keyword/Content/Revenue/AgentLog
    routers/             — sites / keywords / content / revenue / agents
    agents/              — keyword / content / seo / revenue 에이전트 4종
  frontend/
    src/app/             — 6개 페이지 (/ sites keywords content revenue agents)
    src/components/      — Sidebar
    src/lib/api.ts       — API 클라이언트

DB: SQLite (backend/adsense_os.db) — 운영 시 자동 생성
AI: claude-sonnet-4-6 (Anthropic SDK)
```

---

## Bucky 패킷 포맷 (작업 요청 시 사용)

```yaml
project: Google-AdSense-Operating-System
local_path: D:\ai프로젝트\Google-AdSense-Operating-System\
repo: https://github.com/jaeha81/Google-AdSense-Operating-System.git

goal: <구체적 달성 목표>
baseline: v1.0 완성 (2026-06-16) — 6페이지 대시보드 + 에이전트 4종
target_state: <측정 가능한 완료 상태>

scope:
  - allowed: backend/ frontend/src/ README.md .gitignore
  - forbidden: .env 커밋, 프로덕션 DB 직접 수정, 타 레포 패킷 재사용

role:
  claude_code: 구현 / 파일 수정 / 서버 실행 테스트
  codex: 독립 검수 / 사용자 직보
  bucky: 패킷 관리 / 범위 조율

constraints:
  - git commit/push: 사용자 명시 승인 필요
  - 시크릿: ANTHROPIC_API_KEY .env에만 보관, 커밋 금지
  - 외부 배포: 사용자 승인 후

references:
  - G:\내 드라이브\obsidian-agent-brain-system\ObsidianVault\03_Projects\agents\Google-AdSense-OS.md (이 파일)
  - D:\ai프로젝트\Google-AdSense-Operating-System\README.md
  - D:\ai프로젝트\Google-AdSense-Operating-System\backend\main.py

verification:
  backend: cd backend && python -m uvicorn main:app --port 8000 → http://localhost:8000/docs
  frontend: cd frontend && npm run dev → http://localhost:3000
  api: curl http://localhost:8000/api/stats → JSON 응답 확인

done_when: 기능 동작 + 빌드 성공 + (필요시) GitHub push 완료
record_path: G:\내 드라이브\obsidian-agent-brain-system\ObsidianVault\00_System\HANDOFF_LOG.md
next_action: <다음 첫 단계>
```

---

## 다음 개발 우선순위 (Bucky 관리)

| 우선순위 | 기능 | 설명 |
|---------|------|------|
| P0 | ANTHROPIC_API_KEY 설정 가이드 | 사용자가 .env 직접 설정 필요 |
| P1 | 실제 데이터 입력 골든패스 테스트 | 사이트→키워드→콘텐츠 흐름 검증 |
| P2 | AdSense API 연동 | 수동 입력 → 자동 수익 동기화 |
| P3 | Vercel 배포 | 프론트엔드 공개 배포 |
| P4 | 자동 발행 연동 | 티스토리/블로그스팟 API 연결 |
| P5 | 수익 예측 고도화 | 시계열 분석 추가 |

---

## 시크릿 관리 정책

```
ANTHROPIC_API_KEY:
  위치: backend/.env (gitignore 처리됨)
  형식: ANTHROPIC_API_KEY=sk-ant-...
  커밋 금지: 절대 .env 파일을 git에 추가하지 않는다
  참조 파일: backend/.env.example (키 형식만 표시)

추가 예정 시크릿:
  TISTORY_API_KEY     — 티스토리 자동 발행 (P4)
  BLOGSPOT_API_KEY    — 블로그스팟 자동 발행 (P4)
  ADSENSE_CLIENT_ID   — AdSense API 연동 (P2)
```

---

## 컨텍스트 팩 발동 조건

이 패킷은 다음 요청 시 Bucky가 자동 선택한다:

- `Google-AdSense-OS`, `애드센스`, `AdSense OS`, `디지털건물주` 키워드 포함
- `D:\ai프로젝트\Google-AdSense-Operating-System` 경로 언급
- 키워드 에이전트, 콘텐츠 에이전트, 수익 대시보드 관련 요청

```powershell
# Fast selector 발동 예시
powershell -ExecutionPolicy Bypass -File scripts/context_pack_selector_fast.ps1 -Project "Google-AdSense-Operating-System" "키워드 에이전트 개선"
```
