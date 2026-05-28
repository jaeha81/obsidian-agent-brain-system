---
updated: 2026-05-29
session: 집 PC — Codex 검수 이슈 수정 + GitHub Pages 복구
---

# 세션 상태

## 마지막 세션 요약 (2026-05-29 집 PC)

### 완료 작업

1. **GitHub Pages P1 수정** ✅
   - `docs/.nojekyll` 추가 — Jekyll이 Mustache/JS 템플릿 리터럴을 Liquid로 파싱해 `Liquid::SyntaxError` 발생하던 문제 해결
   - Pages 빌드 `success` 확인 완료

2. **wishket 대시보드 파이프라인 P2 수정** ✅
   - `dashboard-update.yml`에 `generate_wishket_dashboard.py` 스텝 추가
   - diff/commit 범위 `wishket.html` 포함
   - `docs/wishket.html` 2026-05-28 데이터 5개 공고로 갱신

3. **레포 동기화 prune 로직 P2 수정** ✅
   - `update_dashboard.py`에 `prune_deleted_repos()` 추가
   - GitHub에 없는 레포(`claude-projects-jh` 등) 다음 자동 실행 시 자동 제거

### 커밋
- `16796fb` fix: GitHub Pages 빌드 실패 수정 + 대시보드 파이프라인 개선
- `8d02dd6` chore: Daily Plus 대시보드 스크립트 + 세션 산출물 커밋

### 다음 세션 P1
- `claude-projects-jh` prune 실제 반영 확인 (다음 dashboard-update 자동 실행 후)

---

## 이전 세션 요약 (2026-05-28 사무실 PC)

### 완료 작업

1. **ROI 측정 시스템 구축** ✅
   - `scripts/subscription_roi.py` — Codex + Claude Code 7/30일 분석
   - 측정 결과: Claude 198세션 / Codex 90세션 (7일), 비대칭 2.2배 정상

2. **모델 라우팅 시스템 도입** ✅
   - `scripts/model_router.py` — task_type → haiku/sonnet/opus 매핑
   - 폴백 체인: sonnet→haiku→opus
   - 한도 초과 자동 감지(`LIMIT_PATTERNS`) + 폴백 시도

3. **bucky_client 통합** ✅
   - `run_bucky(task_type=...)`, `run_bucky_with_tools(task_type=...)`
   - `BuckyLimitError` 신설
   - 우선순위 재설계: override > BUCKY_FORCE_MODEL > task_type > BUCKY_CHAT_MODEL env > sonnet

4. **6개 호출 위치 마이그레이션** ✅
   - bucky_memory.py:118 → `extract` (Haiku)
   - goal_tracker.py:120 → `reasoning` (Opus)
   - discord_bot.py:1065/2052 → `chat`/`code`
   - bucky_voice.py:147 → `chat`
   - agent_dispatcher.py:257/264/405 → `chat`/`implementation`/`chat`

5. **Codex 공유** ✅
   - 핸드오프: `G:/내 드라이브/JH-SHARED/02_HANDOFF/codex-model-routing-2026-05-28.md`
   - AgentBus 알림: `agent-room-messages.jsonl` P2 등록

6. **정책 문서 + 메모리** ✅
   - `ObsidianVault/05_Frameworks/guides/model-routing.md`
   - `~/.claude/projects/.../memory/project_model_routing.md`
   - MEMORY.md 인덱스 갱신

### 미결 항목 (다음 세션 P0)

- **`bucky_memory.py:170-186` 들여쓰기 버그 수정** ⏳
  - 기존 버그(내 마이그레이션과 무관): `try:` 8sp vs `except:` 4sp
  - 사용자 승인 후 들여쓰기만 정렬 (로직 무변경)
- **`.env` 정리** ⏳
  - `BUCKY_CHAT_MODEL=haiku` 줄 제거 또는 `BUCKY_FORCE_MODEL=haiku`로 이동
- **Codex 검수 회신 대기** ⏳
  - 검수 요청: 라우팅 테이블 합리성, 폴백 무한루프 위험, LIMIT_PATTERNS 오탐
- **1주일 후 ROI 재측정** ⏳
  - `python scripts/subscription_roi.py --days 7 --save`로 마이그레이션 효과 확인

### 알려진 한계

- `subscription_roi.py`의 Codex 토큰 0으로 표시 — JSONL usage 필드 위치 미상 (Codex 회신 대기)

### 다음 세션 첫 번째 할 일

1. Codex 검수 결과 확인 (`G:/내 드라이브/JH-SHARED/02_HANDOFF/` 또는 AgentBus)
2. `bucky_memory.py` 들여쓰기 수정 승인 → 적용
3. `.env`에서 `BUCKY_CHAT_MODEL=haiku` 정리

### 환경

- PC: 사무실 PC (DESKTOP-6F8H500, 설계4)
- Vault: `G:/내 드라이브/obsidian-agent-brain-system/`
- Sonnet 일일 한도 초과 발생 → 11pm KST 리셋 / Haiku·Opus는 정상
