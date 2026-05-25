---
type: source
category: article
date_added: 2026-04-19
source_url: (대화 직접 제공)
tags: [llm, knowledge-management, wiki, rag, second-brain]
---

# LLM Wiki — A Pattern for Building Personal Knowledge Bases Using LLMs

## 한 줄 요약
RAG가 매번 지식을 재발견하는 것과 달리, LLM이 직접 위키를 작성·유지함으로써 복리처럼 누적되는 지식 베이스를 만드는 패턴.

## 핵심 포인트

- **RAG의 한계**: 매 쿼리마다 처음부터 재발견. 누적 없음. NotebookLM, ChatGPT 파일 업로드가 이 방식.
- **LLM Wiki의 차이**: LLM이 소스를 읽고 위키를 직접 작성·갱신. 지식이 한 번 컴파일되면 계속 현재 상태 유지.
- **복리 구조**: 새 소스 추가 시 기존 페이지와 교차 참조, 모순 플래그, 합성 강화. 위키가 점점 풍부해짐.
- **역할 분담**: 인간은 소스 큐레이션 + 질문 + 방향 결정. LLM은 요약·교차 참조·파일링·유지 관리 전부.
- **유지 비용 제거**: 인간이 위키를 버리는 이유는 관리 부담. LLM은 지치지 않음.

## 3계층 아키텍처

| 계층 | 역할 | 수정자 |
|------|------|--------|
| Raw Sources | 불변 원본 (논문, 아티클, 노트) | 인간만 추가 |
| Wiki | LLM이 작성한 마크다운 위키 | LLM만 수정 |
| Schema | LLM 행동 지침 (CLAUDE.md) | 협의 후 수정 |

## 3가지 오퍼레이션

1. **Ingest**: 소스 → 논의 → 요약 페이지 → 기존 페이지 업데이트 → 인덱스 → 로그
2. **Query**: 인덱스 탐색 → 관련 페이지 읽기 → 합성 답변 → (좋은 답변은 페이지화)
3. **Lint**: 모순·오래된 클레임·고아 페이지·누락 교차 참조·데이터 갭 점검

## 적용 도메인
- 개인: 목표, 건강, 심리, 자기계발 저널
- 리서치: 수주~수개월 심층 주제 탐구
- 독서: 챕터별 파일링, 캐릭터·테마 페이지 (팬 위키처럼)
- 비즈니스: Slack·회의록·고객 콜로 유지되는 내부 위키

## 도구 옵션
- **Obsidian**: 그래프 뷰, Web Clipper, Marp(슬라이드), Dataview
- **qmd**: 로컬 BM25/벡터 하이브리드 검색 (MCP 서버 포함)
- **Git**: 버전 히스토리, 브랜치, 협업

## 위키에 통합된 내용
- [[concept-llm-wiki]] 생성: 핵심 개념 전체 통합
- [[overview]] 갱신: 위키 목적과 구조 반영

## 인용 가능 구절
> "The wiki is a persistent, compounding artifact. The cross-references are already there. The contradictions have already been flagged."

> "The human's job is to curate sources, direct the analysis, ask good questions, and think about what it all means. The LLM's job is everything else."

> "Bush's vision was closer to this than to what the web became: private, actively curated, with the connections between documents as valuable as the documents themselves."

## 관련 페이지
- [[concept-llm-wiki]] — 이 소스의 핵심 개념 페이지
- [[overview]] — 위키 전체 합성
- [[index]] — 위키 전체 카탈로그
- [[log]] — 위키 활동 로그
