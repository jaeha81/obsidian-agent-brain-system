---
type: knowledge-note
project: shorts-dashboard
date: 2026-06-19
source: Claude Code Remote Session
tags:
  - "#project/shorts-dashboard"
  - "#area/monetization"
  - "#area/ai_automation"
  - "#status/implemented"
---

# shorts-dashboard 파이프라인 진화 — 2026-06-19

Bucky Orchestration 귀속 선언 수신. 이 노트는 Claude Code 에이전트가 자율 구현 사이클 완료 후 Obsidian Brain System에 기록한 진화 로그다.

---

## 구현 완료 사항

### 1. 4씬 AI 시나리오 기반 영상 파이프라인 (commit: 0c47ff1)

**변경 전**: 단일 클립 텍스트 영상
**변경 후**: 4씬 구매 유도 영상

| 씬 | 시간 | 내용 |
|---|---|---|
| Hook | 0-7s | 제품명 대형 표시 + 그라디언트 배경 |
| 성능 | 7-18s | ①②③ 성능 포인트 + 제품 이미지 오버레이 |
| 가격 | 18-25s | 정가 취소선 + 빨간 할인가 |
| CTA | 25-30s | 골드 그라디언트 + 구매 버튼 + 쿠팡 URL |

**신규 파일**:
- `src/lib/agents/scenario-agent.ts` — Gemini 2.5 Flash → VideoScenario JSON 생성
- `src/lib/agents/image-agent.ts` — Stability AI SD3 → 제품 이미지 생성
- `src/lib/shotstack.ts` — `submitShotstackScenicRender()` 추가

**TTS 음성**: 한국어=Seoyeon, 일본어=Mizuki, 영어=Amy

---

### 2. 에이전트 두뇌 자가수리 (commit: 2c3aa60)

**변경 전**: "해결" 버튼 → DB resolved=1 마킹만
**변경 후**: "해결" 버튼 → 실제 수리 액션 실행

`resolveAndFix(id)` 액션 매핑:
| 문제 유형 | 실행 액션 |
|---|---|
| render_failure | 실패 잡 재큐잉 + processPendingJobs() |
| upload_failure | 게시물 재스케줄 (5분 후 재시도) |
| system_error | startWorkflow() 자동 재시작 |
| low_performance | /api/youtube/fix-kids-status |

---

### 3. 자율 자가수리 루프 (commit: e1fb69a)

**신규**: `POST /api/agent/autofix`

1. 두뇌 스캔 (Before)
2. Shotstack API 키 검증 (HTTP probe)
3. 활성 문제별 resolveAndFix() 실행
4. 재스캔 (After)
5. evolution_log INSERT (cycle, insights, performance_delta)

UI: "🔄 자동 수리" 버튼 + 실시간 로그 표시 + Shotstack 키 무효 경고 배너

---

### 4. 렌더 오류 진단 강화 (commit: 68ae7d1)

- brain scan: `MAX(error) AS last_error` → 실제 Shotstack 에러 노출
- isAuthError (401/403) vs isTtsError 스마트 분류
- `/api/diagnostics`: failed_renders 배열 추가 (최근 5건 + 에러 메시지)

---

## 현재 상태

### ✅ 완료
- [x] 4씬 영상 파이프라인
- [x] 에이전트 두뇌 자가수리
- [x] 자율 자가수리 루프 (/api/agent/autofix)
- [x] 렌더 오류 진단 강화

### ⚠️ 진행 중
- Shotstack 렌더 실패 근본 원인 미해결 (API 키 또는 TTS 문제)
  → 확인: https://shorts-dashboard-one.vercel.app/api/diagnostics

### 📋 대기 (사용자 승인 후 구현)
- 컴플라이언스 JH-SHORTS-COMPLIANCE-REQ-001:
  - PUB-02: privacyStatus public→private
  - PUB-03: paidProductPlacementDetails
  - CNT-01: 금지 카테고리 필터 + 체험형 표현 차단
  - COM-01: 공시 문구 첫 줄 배치

---

## Obsidian 통합 (이번 세션 신규)

이 대시보드는 이제 **Bucky Orchestration 귀속** 에이전트로 동작한다.

- `src/lib/obsidian-bridge.ts` — Obsidian 노트 포맷 빌더
- `GET /api/agent/obsidian` — 현재 시스템 상태 → Obsidian 노트 생성
- Claude Code 세션에서 Drive MCP로 Vault에 직접 기록 (현재 방식)

**Drive Folder IDs (Obsidian Vault)**:
- 03_Knowledge: `10gSXu5BPbDLjc9JmPupFDxt9oMQ9A7RV`
- 00_UPGRADE: `18XMMzJnZARI5oOYeUfo6JaqJqCx1FUQk`
- 06_Context_Packs: `1DeNNPTddz_wuIitNvpRztFwtAjuckKK2`

---

## Git 상태
- 브랜치: `claude/charming-faraday-76e8nw`
- 3 커밋 origin 대비 ahead
- 푸시 대기 중 (사용자 승인 필요)
