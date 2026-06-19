---
title: Codex Goal / Pet / Remote Control 적용 노트
source: https://youtu.be/qMU5CB9M7hI?si=j13Q5cnPP4PTT66b
source_type: youtube
channel: 배움의 달인 (AI·자동화)
date: 2026-05-26
captured_at: 2026-05-26 23:20:00+09:00
tags:
- youtube
- codex
- goal-mode
- bucky
- remote-control
- ai-agent
- null
status: knowledge
has_transcript: true
transcript_file: qMU5CB9M7hI.ko-orig.vtt
summary: 영상은 Codex 앱을 오래 실행되는 목표형 에이전트로 쓰는 세 가지 사용 패턴을 설명한다.
category: research
next_action: review
graph_cluster: youtube-learning
---

# Codex Goal / Pet / Remote Control 적용 노트

## 영상 핵심

영상은 Codex 앱을 오래 실행되는 목표형 에이전트로 쓰는 세 가지 사용 패턴을 설명한다.

1. Goal: 한 번 답하고 끝나는 프롬프트가 아니라, 목표를 주고 계획, 행동, 테스트, 반복을 끝까지 수행하게 한다.
2. Pet: 앱 안에서 사용자가 계속 상태를 보고 싶게 만드는 가시적 존재감과 정체성 장치다.
3. Remote Control: 스마트폰이나 다른 기기에서 이어서 답장하고 후속 작업을 넣어, 로컬 PC 작업을 계속 진행한다.

## Bucky 적용 해석

### 1. Bucky Goal Mode

Bucky의 작업 등록은 단순 요청 저장이 아니라 목표 카드로 변환되어야 한다.

- 목표: 사용자가 최종적으로 얻으려는 상태
- 완료 기준: PASS/FAIL을 판정할 수 있는 검증 조건
- 반복 루프: 계획 -> 실행 -> 검증 -> 보완
- 중단 조건: 권한 필요, 위험 작업, 무한 반복 가능성, 외부 결제/API 실행
- 보고 형식: 현재 상태, 남은 작업, 사용자에게 필요한 선택

### 2. Bucky Pet Presence

Pet 기능은 귀여운 장식 자체보다 "작업 중인 에이전트가 살아 있는 상태로 보이는 것"이 핵심이다. Bucky에는 다음처럼 적용한다.

- Discord/Obsidian 상태 메시지에 현재 모드 표시: idle, goal-running, waiting-approval, blocked, done
- 긴 작업은 "무응답"이 아니라 짧은 heartbeat를 남긴다.
- Bucky의 정체성은 "사용자의 작업 관리자 + 기록 관리자"로 유지한다.

### 3. Bucky Remote Continuation

원격제어 패턴은 JH 시스템의 Discord/Obsidian/AgentBus와 잘 맞는다.

- 사용자는 모바일 Discord에서 후속 지시를 남긴다.
- Bucky는 기존 task_id 또는 goal_id에 후속 지시를 append한다.
- 실행 에이전트는 새 작업을 만들기보다 기존 목표의 다음 루프로 이어간다.
- 위험 작업은 즉시 실행하지 않고 approval 카드로 분리한다.

## 바로 적용할 운영 규칙

- Bucky가 "업그레이드", "끝까지", "내일까지", "계속 진행" 같은 요청을 받으면 Goal Mode 후보로 분류한다.
- Goal Mode 카드에는 반드시 완료 기준과 중단 조건이 있어야 한다.
- 사용자가 모바일에서 짧게 답장해도 기존 목표 문맥에 붙일 수 있도록 source, channel, task_id를 유지한다.
- Pet Presence는 상태 노트와 Discord 응답 문구부터 적용하고, UI 캐릭터/이미지는 나중 단계로 둔다.

## 관련 파일

- [[bucky-evolution-roadmap]]
- [[Bucky Goal Prompt Template]]
- [[bucky-codex-goal-pet-remote-2026-05-26]]
