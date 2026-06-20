---
title: 로컬 에이전트의 오프라인 우선 경로
date: 2026-05-28
source: daily-plus/2026-05-28.md (Card 3)
priority: P2
category: knowledge
status: distilled
tags:
- obsidian
- offline
- local-first
- queue
- atomic-write
- daily-plus
- knowledge
- source/today_plus
- type/reference
- area/obsidian_brain
graph_cluster: daily-practice
---

# 로컬 에이전트의 오프라인 우선 경로

> ChatGPT Pulse 2026-05-28 Card 3 증류 (P2 · knowledge)

## 목적
오프라인에서 캡처를 안전하게 모아두고 Obsidian이 켜지면 원자적으로 노트에 쓰는 로컬 에이전트 아이디어. 간단 설치, 보안, 중복방지, 확실한 쓰기 4원칙. 네트워크 의존성을 제거해 항상 신뢰할 수 있는 데이터 캡처 환경을 구축.

## 핵심 내용
- **오프라인 큐 설계**:
  - SQLite 로컬 큐 (`~/.agent/queue.db`)
  - 각 항목: id, content, sha256, created_at, status (pending/synced/failed)
  - Obsidian 연결 감지 시 자동 플러시
- **원자적 파일쓰기**: tmp 파일 생성 → 내용 쓰기 → mv 명령으로 원자 이동
- **플러그인 연동 방식**:
  - Obsidian Local REST API 플러그인 또는 파일시스템 직접 쓰기
  - 연결 상태 폴링: 5초 간격으로 vault 폴더 접근 가능 여부 체크
- **4원칙**:
  1. 간단 설치: 단일 Python 스크립트 + SQLite, 외부 의존성 최소화
  2. 보안: 로컬 전용, 네트워크 미노출
  3. 중복방지: SHA256 기반 중복 항목 거부
  4. 확실한 쓰기: 원자적 파일쓰기로 부분 쓰기 방지

## 구현 체크리스트
- [ ] SQLite 큐 스키마 설계 및 CRUD 함수 작성
- [ ] Obsidian 연결 상태 감지 로직 (파일시스템 폴링)
- [ ] 큐 플러시 → 원자적 파일쓰기 파이프라인 구현
- [ ] SHA256 중복 항목 거부 로직
- [ ] 에러 처리 및 failed 항목 재시도 메커니즘

## 관련 컨텍스트
- 웹훅 옵시디언 안전 전달: `2026-05-28-dp-webhook-to-obsidian-safe.md`
- 로컬 우선 음성 전사 플레이북: `2026-05-29-dp-local-first-voice-playbook.md`
- 원격 실패 시 로컬 전환: `2026-05-28-dp-remote-fail-local-fallback.md`

## 관련 노트
- [[hubs/JH System]]
