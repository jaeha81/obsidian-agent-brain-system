---
title: 옵시디언 큐 짧은 후보
date: 2026-05-27
source: daily-plus/2026-05-27.md (Card 7)
priority: P3
category: knowledge
status: distilled
tags:
- obsidian
- queue
- workflow
- plugin
- agentbus
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 옵시디언 큐 짧은 후보

> ChatGPT Pulse 2026-05-27 Card 7 증류 (P3 · knowledge)

## 목적
Obsidian 큐/재생 스타일 처리를 강화하는 세 가지 소규모 프로젝트. 큐 기반 처리, 점진적 작성, 로컬 우선 큐 처리 실험용 도구들. 워크플로우 자동화의 점진적 진화를 위한 아이디어 저장소.

## 핵심 내용
- **큐 기반 노트 처리 패턴**:
  - 아이디어 → 인박스 큐 → 처리 → 분류 자동화
  - FIFO 또는 우선순위 기반 처리 순서
  - 처리 완료 노트에 `status: processed` 태그 자동 부여
- **점진적 작성 도구**:
  - 단편 아이디어를 큐에 쌓고 나중에 Merge
  - 관련 노트 자동 링크 제안
  - Draft → Review → Final 상태 전환 자동화
- **로컬 우선 큐 처리 실험**:
  - Python watchdog으로 vault 폴더 감시
  - 새 파일 생성 시 큐에 자동 등록
  - AgentBus 연결로 처리 결과 피드백
- **AgentBus 연결 가능성**: 큐 처리 결과를 AgentBus 이벤트로 발행, 다른 에이전트가 구독 가능

## 구현 체크리스트
- [ ] Obsidian 인박스 큐 폴더 구조 설계 (`00_Inbox/queue/`)
- [ ] Python watchdog 기반 폴더 감시 스크립트 프로토타입
- [ ] 처리 상태 태그 자동 갱신 로직
- [ ] AgentBus 이벤트 스키마 정의

## 관련 컨텍스트
- 로컬 에이전트 오프라인 우선 경로: `2026-05-28-dp-local-agent-offline-first.md`
- Skills Obsidian 이관: `2026-05-28-dp-skills-to-obsidian-migration.md`
- 이 항목은 P3(낮은 우선순위)이므로 P0~P1 완료 후 검토

## 관련 노트
- [[hubs/JH System]]
