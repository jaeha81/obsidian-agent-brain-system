---
type: knowledge-hub
created: 2026-05-27
updated: 2026-06-08
tags:
  - knowledge-hub
  - "#area/ai_automation"
  - "#area/research"
summary: "JH 에이전트 시스템의 메시지 버스 — Bucky/Codex/Claude Code 간 라우팅 허브"
category: research
status: active
---

# AgentBus — 에이전트 메시지 버스

JH 에코시스템에서 에이전트 간 메시지·태스크·핸드오프를 중개하는 운영 레이어.

## 에이전트 연결

- [[Bucky]] — 오케스트레이터, 태스크 발행
- [[Codex]] — 독립 검수 에이전트
- [[Claude Code]] — 구현 실행 에이전트

## Vault 운영 폴더

- [[10_AgentBus/index|AgentBus 허브]] — 전체 구조 및 운영 방식
- [[10_AgentBus/completed/index|완료 태스크]] — 처리 완료 기록
- [[10_AgentBus/inbox/index|inbox]] — 수신 메시지 큐
- [[10_AgentBus/handoffs/index|handoffs]] — Claude ↔ Codex 핸드오프

## 관련 지식

- [[bucky-evolution-pipeline]] — 버스로 유입되는 메시지 처리 파이프라인
- [[bucky-evolution-roadmap]] — 버스 기반 자가 진화 로드맵
- [[webhook-vault-write-pattern]] — 버스 메시지 → Vault 기록 패턴
- [[ROUTING_RULES]] — 메시지 라우팅 규칙
- [[vault-galaxy-graph-bridge]] — 전체 지식 허브 MOC
- [[typeless-voice-stt-analysis]] — 음성 STT 입력 → AgentBus 유입 경로
- [[knowledge-auto-capture]] — 자동 지식 캡처 → AgentBus를 통한 Vault 저장
- [[pattern-extractor]] — 반복 패턴 → AgentBus 태스크 자동 생성
