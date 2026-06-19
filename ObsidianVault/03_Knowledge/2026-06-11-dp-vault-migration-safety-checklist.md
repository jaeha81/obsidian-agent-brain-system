---
title: Vault Migration Safety Checklist
date: 2026-06-11
source: daily-plus/2026-06-10.md (Card 8)
priority: P1
category: verification
owner: codex
status: auto-implemented
tags:
- - daily-plus
- auto-implemented
- vault
- migration
- safety
- checklist
graph_cluster: daily-practice
---

# Vault Migration Safety Checklist

> ChatGPT Pulse 2026-06-10 Card 8 자동 증류 (P1 · verification)

## 목적

Obsidian Vault는 마크다운 파일 폴더이며, 커뮤니티는 백업과 동기화를 분리할 것을 강조합니다

## 핵심 내용

Obsidian Vault는 마크다운 파일 폴더이며, 커뮤니티는 백업과 동기화를 분리할 것을 강조합니다. Git이나 오프라인 아카이브로 완전한 히스토리(플러그인 설정 포함)를 캡처하는 것이 안전합니다. rsync나 
Syncthing 같은 자동화 도구가 유용하며, 플러그인 상태는 명시적으로 관리해야 합니다.

## 적용 방법

Turn checks into a repeatable verification checklist before implementation.

## 관련 영역

- 대상: `00_UPGRADE/review-automation-protocol.md`
- 담당: codex

## 관련 노트
- [[hubs/JH System]]
