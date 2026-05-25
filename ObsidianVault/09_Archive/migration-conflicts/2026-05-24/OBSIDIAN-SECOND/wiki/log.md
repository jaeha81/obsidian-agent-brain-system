# Wiki Activity Log

> 형식: `## [YYYY-MM-DD] [타입] | [제목]`
> 파싱: `grep "^## \[" log.md | tail -10`

---

## [2026-04-19] setup | 위키 시스템 초기화

- 액션: LLM Wiki 세컨드 브레인 시스템 구축
- 생성: CLAUDE.md (스키마), wiki/index.md, wiki/log.md
- 폴더: wiki/, raw/articles/, raw/papers/, raw/notes/, raw/assets/, tools/
- 비고: Vannevar Bush의 Memex 개념에서 영감, LLM이 유지 비용 제거

## [2026-04-25] setup | Obsidian 위키 셋업 완료

- 액션: CLAUDE.md 위키지침에 따른 Obsidian 볼트 전체 설정
- 설정: slash-command 플러그인 활성화, showFrontmatter 활성화
- 설정: .obsidian/templates.json → _templates/ 폴더 연결
- 추가: obsidian-shellcommands 위키 전용 커맨드 5개 (ingest/query/lint/status/overview)
- 생성: _templates/ 폴더에 6개 템플릿 (wiki-concept, wiki-entity, wiki-source, wiki-synthesis, inbox-capture, knowledge-note)
- 생성: wiki/concept-windows-launcher-pattern.md (05_Insights 인사이트 승격)
- 생성: wiki/source-jh-windows-launcher-insight.md
- 업데이트: wiki/index.md (소스 2개, 페이지 6개), wiki/overview.md

## [2026-04-25] classify | 00_Inbox 세션 캡처 31개 처리

- 액션: 00_Inbox/session-2026-04-21-*.md 31개 분류 처리
- 통합: 07_Archive/sessions/2026-04-21-session-log.md (운영 기록)
- 생성: 05_Insights/jh-windows-launcher-dev-pattern.md (재사용 인사이트)
- 핵심 발견:
  - jh_windows 런처 개발 반복 패턴: VBS래퍼+UTF-8 BOM+TCP소켓체크 3종 세트
  - Windows cold-start에서 한글 경로 깨짐 → BOM 필수
  - netstat 대신 PowerShell TCP 소켓 체크가 신뢰성 높음
- 00_Inbox: 세션 파일 전체 삭제, .gitkeep만 유지

## [2026-04-26] fix | 집 PC Claude Code 연동 + lint 수정

- 액션: 집 PC 동기화 — shellcommands 경로 수정, .claude/CLAUDE.md 생성, broken link 수정
- 수정: entity-claude-ai-desktop-setup.md `[[wiki/_schema]]` → `[[concept-llm-wiki]]`, `[[Claude Code 사용 가이드]]` → `[[concept-obsidian-plugins]]`
- 수정: entity + overview 내 경로 5곳 `JA-OBSIDIAN-SECOND` → `C:\Users\user1\Documents\OBSIDIAN-SECOND`
- 테스트: claude -p `/status`, `/lint` 정상 동작 확인

## [2026-04-26] classify | 00_Inbox 세션 캡처 16개 처리

- 액션: 00_Inbox/session-2026-04-25-*.md (11개) + session-2026-04-26-*.md (5개) 분류
- 통합: 07_Archive/sessions/2026-04-25-session-log.md, 2026-04-26-session-log.md
- 핵심 마일스톤:
  - jh-mobile-second-brain: MVP 완성 (오디오 업로드 API + 자동 동기화)
  - jh-harness: tmux 패턴 A 실전 적용
  - CLAUDE.md 글로벌 지침 확산 3개 레포 (BuildFlow, android-studio, outsource-system)
  - JH-IDEAGO: Render 배포 설정 추가
- 00_Inbox: 세션 파일 16개 삭제

## [2026-04-27] ingest | ChatGPT 메모리 → 01_Knowledge 구조화

- 소스: raw/gpt/메모리.txt (ChatGPT 메모리 덤프 309줄)
- 생성: 01_Knowledge/gpt-memory-profile.md (사용자 프로필·AI 협업 철학·재무 목표)
- 생성: 01_Knowledge/gpt-memory-projects.md (진행 중 프로젝트 9개 표 정리)
- 생성: 01_Knowledge/gpt-memory-tech-stack.md (기술 스택·Make.com 자동화·NeuronGPT 구조)
- 업데이트: wiki/index.md (지식노트 섹션 추가), wiki/overview.md

## [2026-04-26] update | wiki/concept-obsidian-plugins.md 신규 생성

- 생성: wiki/concept-obsidian-plugins.md (플러그인 5종 + Shell Commands 10종 문서화)
- 업데이트: wiki/index.md (페이지 6 → 8개), wiki/overview.md

## 관련 페이지
- [[index]] — 위키 카탈로그
- [[overview]] — 위키 전체 합성
- [[concept-llm-wiki]] — LLM Wiki 핵심 개념
- [[source-llm-wiki-pattern]] — 수집된 소스

## [2026-04-19] ingest | LLM Wiki Pattern — 아이디어 문서

- 소스: (대화에서 직접 제공된 원문 텍스트)
- 저장: raw/articles/2026-04-19-llm-wiki-pattern.md
- 생성: wiki/source-llm-wiki-pattern.md
- 생성: wiki/concept-llm-wiki.md
- 업데이트: wiki/index.md, wiki/overview.md
- 핵심 발견:
  - RAG vs Wiki: RAG는 매번 재발견, Wiki는 복리 누적
  - 3계층 구조: raw sources → wiki → schema
  - 오퍼레이션: Ingest / Query / Lint
  - 유지 비용 제거가 핵심 — 인간은 관리에 지쳐 위키를 포기한다
