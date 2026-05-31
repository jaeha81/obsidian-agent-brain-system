---
type: concept
updated: 2026-04-26
sources: []
tags: [obsidian, plugins, setup, knowledge-management]
  - #status/archive
---

# Obsidian 플러그인 구성 — SECOND 볼트

SECOND 볼트(JH 지식 브레인)에 설치된 커뮤니티 플러그인 목록과 활용 방법.

## 설치된 플러그인 (2026-04-26 기준)

| 플러그인 | 역할 | 주요 사용처 |
|---------|------|------------|
| **terminal** | Obsidian 내 터미널 임베드 | Claude Code 직접 실행 |
| **obsidian-shellcommands** | 커스텀 셸 커맨드 등록 | Wiki 슬래시 명령어 5종 |
| **dataview** | 노트를 데이터베이스처럼 쿼리 | wiki/ 페이지 자동 집계 |
| **file-tree-alternative** | 파일 트리 대체 뷰 | 볼트 폴더 구조 탐색 |
| **folder-notes** | 폴더에 설명 노트 연결 | 각 폴더 용도 문서화 |

## Shell Commands — Wiki 전용 커맨드 5종

| 커맨드 alias | 실제 동작 |
|------------|----------|
| Wiki: 현재 노트 인제스트 | `claude --print "[파일] wiki에 ingest"` |
| Wiki: 선택 텍스트 질문 | `claude --print "[선택]에 대해 wiki 기반 답변"` |
| Wiki: 건강 검진 | `claude --print "wiki/ 전체 lint"` |
| Wiki: 통계 | `claude --print "wiki 통계 요약"` |
| Wiki: 개요 갱신 | `claude --print "overview.md 갱신"` |

추가 커맨드:
- `Claude Code 실행 (인터랙티브)` — 볼트 루트에서 `claude` 실행
- `Claude: 현재 노트 요약` — 현재 노트를 claude로 요약
- `Claude: 아이디어 확장` — 현재 노트 아이디어 3가지 확장
- `Claude: Wiki 인덱스 업데이트` — wiki/index.md 자동 갱신
- `Git: 노트 동기화` — add → commit → push 원스텝

## Dataview 활용 예시

```dataview
TABLE updated, tags FROM "wiki"
SORT updated DESC
```

위 쿼리를 임의 노트에 넣으면 wiki 페이지 전체를 날짜순으로 조회할 수 있다.

## 설치 이력

- 2026-04-25 (노트북): dataview, file-tree-alternative, folder-notes 추가 설치
- 2026-04-26 (집 PC): 경로 수정 및 집 PC 동기화 완료

## 관련 페이지
- [[entity-claude-ai-desktop-setup]] — Claude Code Obsidian 연동 가이드
- [[concept-llm-wiki]] — LLM Wiki 운영 패턴
- [[overview]] — 볼트 전체 개요
