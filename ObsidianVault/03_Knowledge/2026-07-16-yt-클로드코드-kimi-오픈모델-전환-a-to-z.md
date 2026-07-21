---
title: "클로드코드 → Kimi(오픈모델) 갈아타기 A to Z"
source: "https://youtu.be/w7CLlkBtFbU?si=jNeFt_UQV090HDsM"
source_type: youtube
video_id: w7CLlkBtFbU
channel: "김플립 - LLM 코딩"
date: 2026-07-16
captured_at: 2026-07-16
one_line: "Claude Code 그대로 모델만 Kimi 2.7로 바꾸는 법 + Kimi Code CLI 대응표"
tags:
  - knowledge
  - youtube
  - discord-video
  - auto-capture
  - ai-api-routing
  - model-routing
status: knowledge
has_transcript: false
graph_cluster: youtube-learning
deep_analyzed: false
---
# 클로드코드 → Kimi(오픈모델) 갈아타기 A to Z

## 요약

핵심 메시지: "Kimi로 갈아타라"가 아니라 **"언제든 갈아탈 수 있는 상태를 만들어두자"**. 배경은 2026-06-13 미 상무부의 Anthropic 최상위 모델 수출통제 차단 시나리오 — 구독형 AI는 "포토샵 매달 대여"(공급사가 끊으면 끝)인 반면 오픈웨이트 모델은 "포토샵 구매 설치"(회수 불가)라는 비유. Kimi 2.7 선택 이유: 가성비 1위, 빠른 업데이트, 서드파티 지원 빠름, MCP Mark Verified 벤치마크 81.1%로 Claude Opus 4.8보다 높은 수치 언급.

### 방법 1 — Claude Code 그대로, 모델만 Kimi로 교체
- 프록시(OpenRouter 등) 불필요 — moonshot.ai가 Anthropic 호환 엔드포인트 직접 제공.
- 프로젝트 `.claude/settings.local.json`(gitignore 대상, 공유 `settings.json`에는 키 절대 넣지 말 것)에 env 블록:
  - `ANTHROPIC_BASE_URL="https://api.moonshot.ai/anthropic"`
  - `ANTHROPIC_AUTH_TOKEN="<키>"`, `ANTHROPIC_API_KEY=""` (반드시 빈칸 — 안 하면 충돌)
  - FABLE/OPUS/SONNET/HAIKU/SMALL_FAST/SUBAGENT 모델명을 전부 `kimi-k2.7-code`로
  - `ENABLE_TOOL_SEARCH=false`(공식 권장), `CLAUDE_CODE_AUTO_COMPACT_WINDOW=262144`(256K, Kimi 컨텍스트 기준)
  - 전역 적용 시 `~/.claude/settings.json`
- 완료 후 `/status`로 모델명이 `kimi-k2.7-code`로 뜨면 성공.

### 실전 비교 (정렬 알고리즘 시각화 원샷 프롬프트, 6개 알고리즘+애니메이션+상태관리)
- Kimi 2.7과 Opus 4.8 둘 다 에러 없이 1회 성공, 알고리즘 정확도 동일, 애니메이션 정상.
- 차이는 "디자인 감각" 정도(Opus가 근소 우위). 결론: 기능은 대등, 마감만 Claude가 근소 우위 — 한쪽이 막혀도 큰 손해 아님.

### 방법 2 — Kimi Code CLI 통째로 사용 (Claude Code ↔ Kimi Code 대응표)
| 기능 | Claude Code | Kimi Code |
|---|---|---|
| YOLO모드 | `--dangerously-skip-permissions`(별칭 `ccd`) | `--yolo` / `/yolo` |
| 사고량 조절 | `/effort` | 동일 |
| 스킬 호출 | `/스킬명` | `/스킬명:...` 또는 자연어 요청 |
| 규칙파일 | `CLAUDE.md` | `AGENTS.md`(`/init`으로 자동생성) |
| 브라우저 제어 | Chrome 확장/DevTools | Playwright MCP 설치 |
| 플랜모드 | Shift+Tab | `/plan`, Shift+Tab |

대화 스타일 차이: Claude Code는 PLAN.md 중심(포괄적 요청→리서치·토론→단계별 계획→구현). Kimi Code는 Codex 유사 스타일(긴 대화로 맥락 잡고 compact로 압축 — 256K라 자주 압축됨 → 순차 진행+TDD/Playwright 검증 권장).

### 마무리
"이건 영업이 아니라 반대" — Claude·Codex 양대 진영 외에도 오픈소스 LLM 대안이 있다는 걸 늘 인지하자는 메시지. 카파시 발언 인용: "이제 암기·습득보다 이해가 중요."

## 실무 메모 (JH 적용 관점)
- 지금 시스템은 Fable/Opus/Sonnet/Haiku 구독 기반 라우팅([[project_model_routing]] 참고) — 이 영상은 "구독 차단 시 비상구"로서 Kimi/moonshot.ai 엔드포인트 전환 옵션을 제공. 즉시 전환 필요는 없음, 비상 대안으로 기록.
- 전환 시 주의: `.claude/settings.local.json`은 절대 git에 커밋 금지(레포가 public — [[reference_repo_is_public]] 참고), `ANTHROPIC_API_KEY=""` 빈칸 필수.

[[bucky-system-hub]]
