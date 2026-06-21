---
type: system-doc
category: plugin-management
updated: 2026-05-26
tags: [plugin, obsidian, bucky-system]
---

# Bucky Plugin Stack — 공식 플러그인 운영 원칙

## 핵심 원칙

1. **플러그인으로 해결 가능한 문제는 직접 개발하지 않는다**
2. 직접 개발 허용 조건: Community Plugin 불가 · 성능 문제 · 보안 문제 · 워크플로우 충돌
3. 신규 기능 추가 시 **"기존 Plugin 활용 가능 여부"를 먼저 검사한다**

---

## 현재 Plugin Stack (23개)

### Core Automation (자동화 핵심)

| 플러그인 | ID | 용도 | 대체하는 커스텀 코드 |
|---------|-----|------|------------------|
| **QuickAdd** | `quickadd` | 자연어 기반 자동 액션, 매크로, 스크립트 트리거 | 단순 Vault 입력 자동화 |
| **Templater** | `templater-obsidian` | 자동 문서 구조화, 프로젝트 생성 자동화 | daily_report_generator.py (부분) |
| **Dataview** | `dataview` | Vault 데이터 쿼리·시각화, 프로젝트 상태 추적 | task_tracker.py (부분) |
| **Tasks** | `obsidian-tasks-plugin` | 작업 추적·관리, 마감일·우선순위 | task_tracker.py (대체 가능) |
| **Shell Commands** | `obsidian-shellcommands` | Vault에서 직접 쉘 스크립트 실행 | 수동 스크립트 실행 |

### UI & Interaction (인터페이스)

| 플러그인 | ID | 용도 |
|---------|-----|------|
| **Meta Bind** | `obsidian-meta-bind-plugin` | 대시보드형 인터페이스, 입력 UI, 버튼·슬라이더 |
| **Buttons** | `obsidian-buttons` | 클릭형 액션 자동화, QuickAdd 트리거 |
| **Kanban** | `obsidian-kanban` | 작업 흐름 시각화, 프로젝트 보드 |

### Search & Discovery (검색·발견)

| 플러그인 | ID | 용도 | 대체하는 커스텀 코드 |
|---------|-----|------|------------------|
| **Omnisearch** | `omnisearch` | 전역 검색, 세컨드브레인 탐색 | vault_rag.py (부분) |
| **Smart Connections** | `smart-connections` | AI 기반 노트 연결, 시맨틱 검색 | vault_rag.py (대체 검토) |

### Integration (연동)

| 플러그인 | ID | 용도 |
|---------|-----|------|
| **Local REST API** | `obsidian-local-rest-api` | Python 스크립트 ↔ Vault 직접 통신 |
| **Git** | `obsidian-git` | Vault 버전 관리 자동화 |
| **Claudian** | `claudian` | Claude AI 인라인 통합 |
| **Remotely Save** | `remotely-save` | Google Drive 클라우드 동기화 |

### Visualization (시각화)

| 플러그인 | ID | 용도 |
|---------|-----|------|
| **Excalidraw** | `obsidian-excalidraw-plugin` | 다이어그램, 비주얼 노트 |
| **Infranodus** | `infranodus-graph-view` | 3D 그래프, AI 토픽 모델링 |
| **Calendar** | `calendar` | 달력 기반 일정·Daily Notes |
| **Table Editor** | `table-editor-obsidian` | 마크다운 테이블 편집 |

---

## 커스텀 코드 필수 영역 (Plugin 대체 불가)

| 영역 | 스크립트 | 이유 |
|------|---------|------|
| Discord 실시간 처리 | `discord_bot.py` | discord.py API 필수, 외부 서비스 |
| 비동기 병렬 실행 | `bucky_multi_dispatcher.py` | asyncio.gather() — JS 플러그인 제약 |
| Claude API 호출 | `bucky_orchestrator.py` | ANTHROPIC_API_KEY 관리 + 스트리밍 |
| 패턴 감지/스킬 제안 | `pattern_extractor.py` | 통계 분석 + AI 학습 |
| 음성 처리 (STT) | `whisper_transcribe.py` | OpenAI Whisper API 필수 |
| Vercel 배포 | `bucky_vercel_deploy.py` | 외부 서비스 API |

---

## Plugin 추가 검토 대상 (미설치)

| 플러그인 | 용도 | 필요 조건 |
|---------|------|---------|
| RSS Feed Reader | 뉴스 자동 수집 (bucky_briefing.py 대체) | 안정성 검증 필요 |
| Advanced URI | 외부 앱 → Vault 트리거 | Discord webhook 연동 시 |
| Periodic Notes | Daily/Weekly/Monthly 노트 자동화 | Templater와 중복 검토 |

---

## 자동화 흐름 (Plugin 중심)

```
Discord 명령 → bucky_multi_dispatcher.py (병렬 분배)
  → Local REST API → QuickAdd 매크로 → Vault 저장
  → Templater 템플릿 적용 → Dataview 쿼리 갱신
  → Shell Commands 실행 → 결과 Discord 전송
```

---

## Deprecated 감시 목록

플러그인 업데이트 중단 시 자동 알림 대상:

- `claudian` — 최근 커밋 활동 확인 필요
- `jh-local-graph-view` — 커스텀 플러그인, 유지 필요
- `infranodus-graph-view` — 유료 서비스 연동, 구독 상태 확인

[[bucky-system-hub]]
