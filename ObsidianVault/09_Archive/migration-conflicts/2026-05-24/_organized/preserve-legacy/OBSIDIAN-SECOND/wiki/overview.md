---
type: synthesis
updated: 2026-04-27
sources: [source-llm-wiki-pattern, source-jh-windows-launcher-insight]
tags: [meta, overview]
  - #status/archive
---

# Overview — 나의 세컨드 브레인

이 위키는 JH의 LLM 위키 에이전트가 운영하는 세컨드 브레인이다.

## 현재 상태

- **시작일**: 2026-04-19
- **소스**: 2개
- **페이지**: 8개 (개념 3, 엔티티 1, 소스 2, 개요 1, 아카이브 3)
- **지식노트**: 3개 (01_Knowledge/ — GPT 메모리 구조화)
- **주요 도메인**: 지식 관리, LLM 활용, Windows 개발 패턴, Obsidian 셋업, 사용자 프로필·프로젝트

## 핵심 아이디어

이 위키의 존재 이유는 **복리 지식 누적**이다.

매 대화에서 처음부터 재발견하는 RAG 방식과 달리, 이 위키는 지식이 한 번 처리되면 영구적으로 구조화·교차 참조된 상태로 남는다. 새 소스가 추가될수록, 새 질문을 할수록 위키는 더 풍부해진다.

인간(JH)의 역할: 소스 큐레이션, 질문, 방향 결정
LLM의 역할: 요약, 교차 참조, 파일링, 유지 관리 전부

## 현재 지식 클러스터

### 지식 관리

- [[concept-llm-wiki]]: LLM 위키 패턴의 핵심 구조와 원리
- [[entity-claude-ai-desktop-setup]]: Claude.ai Desktop Projects 연동 설정

### Windows 개발 패턴

- [[concept-windows-launcher-pattern]]: Windows 런처 cold-start 문제 5가지와 검증된 해결 패턴

### 사용자 지식 (GPT 메모리 구조화)

- [[../01_Knowledge/gpt-memory-profile]]: 사용자 프로필·AI 협업 철학·재무 목표
- [[../01_Knowledge/gpt-memory-projects]]: 진행 중 프로젝트 9개
- [[../01_Knowledge/gpt-memory-tech-stack]]: 기술 스택·Make.com·NeuronGPT 에이전트 구조

### Obsidian + Claude Code 셋업

- [[concept-obsidian-plugins]]: SECOND 볼트 플러그인 5종 + Shell Commands 10종 구성
- [[entity-claude-ai-desktop-setup]]: Claude.ai Desktop Projects 연동 방법

## Obsidian 셸 커맨드 (2026-04-26 집 PC 동기화 완료)

| 커맨드 | 기능 |
|--------|------|
| Wiki: 현재 노트 인제스트 | 현재 노트를 claude --print로 wiki에 ingest |
| Wiki: 선택 텍스트 질문 | 선택 텍스트로 wiki 기반 질의 |
| Wiki: 건강 검진 | wiki/ 전체 lint |
| Wiki: 통계 | 현재 wiki 통계 요약 |
| Wiki: 개요 갱신 | overview.md 갱신 |

## 위키 사용 방법

| 목적 | 방법 |
|------|------|
| 새 소스 추가 | Obsidian: "Wiki: 현재 노트 인제스트" 커맨드 |
| 위키에 질문 | Obsidian: "Wiki: 선택 텍스트 질문" 커맨드 |
| 건강 검진 | Obsidian: "Wiki: 건강 검진" 커맨드 |
| 집중 wiki 작업 | 터미널: `cd C:\Users\user1\Documents\OBSIDIAN-SECOND && claude` |

---

*이 페이지는 위키 전체를 반영하며, 새 소스가 추가될 때마다 갱신된다.*

## 관련 페이지
- [[index]] — 위키 전체 카탈로그
- [[concept-llm-wiki]] — 핵심 개념 페이지
- [[source-llm-wiki-pattern]] — 원본 소스
- [[log]] — 위키 활동 로그
- [[entity-claude-ai-desktop-setup]] — Claude.ai 설정 가이드
