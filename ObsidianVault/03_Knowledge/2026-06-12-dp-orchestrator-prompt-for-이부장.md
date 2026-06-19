---
title: Orchestrator Prompt for 이부장
date: 2026-06-12
source: daily-plus/2026-06-10.md (Card 9)
priority: P3
category: agent-prompting
owner: bucky
status: user-approved
approved_at: 2026-06-12
tags:
- daily-plus
- agent-prompting
- orchestrator
- 이부장
- routing
graph_cluster: daily-practice
---

# Orchestrator Prompt for 이부장

> ChatGPT Pulse 2026-06-10 Card 9 사용자 승인 후 구현 (P3 · agent-prompting)

## 목적

「You are 이부장, a cautious orchestration agent」 프롬프트로 금융 조치에 확인 요구, 결정 로깅, 단일 줄 근거 제공을 강제합니다.

## 핵심 내용

「You are 이부장, a cautious orchestration agent」 프롬프트로 금융 조치에 확인 요구, 결정 로깅, 단일 줄 근거 제공을 강제합니다. 도메인별 라우팅(Code→Codex, 장문→Claude Code, 설계→3D agent, 문서→Bucky), 금융 가드레일(투찰/계약 승인 필수), /Logs 폴더 구조 및 append-only 로깅을 포함합니다.

## 적용 방법

Stage prompt changes as role-specific snippets and keep approval notes.

## 관련 영역

- 대상: `03_Projects/agents / Bucky planner-executor prompts`
- 담당: bucky
