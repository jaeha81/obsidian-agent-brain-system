---
title: 언제까지 AI에게 매번 같은 설명을 다시 해야할까? | 현업이 알려주는 LLM Wiki (Feat. RAG와의 차이)
source: https://youtu.be/4XBofMHVyyc?si=-AmPa26WHsb3SrWN
source_type: youtube
channel: ''
publish_date: ''
date: 2026-05-26
captured_at: 2026-05-26 07:50:30
tags:
- youtube
- knowledge
- auto-capture
- LLM
- RAG
- AI-memory
- prompt-engineering
- type/reference
- source/youtube
- source/api
status: knowledge
has_transcript: false
summary: 현업이 알려주는 LLM Wiki (Feat. RAG와의 차이)
category: research
next_action: review
graph_cluster: youtube-learning
---

# 언제까지 AI에게 매번 같은 설명을 다시 해야할까?

> 현업이 알려주는 LLM Wiki (Feat. RAG와의 차이)

![thumbnail](https://img.youtube.com/vi/4XBofMHVyyc/mqdefault.jpg)

## 핵심 주제

LLM에게 매번 동일한 컨텍스트를 반복 입력하는 비효율 문제와 해결책.
**RAG** vs **LLM Wiki(메모리/컨텍스트 관리)** 의 차이와 실무 적용법.

## 요약

- AI와 반복 대화 시 매번 같은 배경 설명을 해야 하는 문제 → 현업에서 실제 겪는 고충
- **RAG**: 외부 문서를 검색해 프롬프트에 삽입하는 방식 (검색 기반)
- **LLM Wiki / 메모리 관리**: AI가 맥락을 장기 보존하는 방식 (세션 지속 또는 영구 저장)
- 두 방식의 차이점, 장단점, 어떤 상황에 무엇을 쓸지 실무 관점에서 설명

## 우리 시스템 적용 포인트

> 이 노트는 Bucky가 자동 캡처 + 요약했습니다.

- [ ] RAG vs CLAUDE.md(LLM Wiki) 구조 비교 → 현재 브레인시스템에 어떻게 적용 중인지 점검
- [ ] `session-state.md` + `MEMORY.md` = LLM Wiki 역할 → 개선 포인트 있는지 검토
- [ ] 반복 입력 컨텍스트 → hooks/CLAUDE.md로 자동화된 것들 목록화

## 원본 링크

- [YouTube 영상 보기](https://youtu.be/4XBofMHVyyc?si=-AmPa26WHsb3SrWN)

## 관련 허브

- [[vault-galaxy-graph-bridge]] — 전체 지식 허브 MOC
- [[jh-system]] — JH 통합 구축 시스템
- [[bucky-evolution-pipeline]] — LLM Wiki 패턴 관련
