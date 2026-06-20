---
title: Git으로 남기는 마크다운 이력
date: 2026-05-28
source: daily-plus/2026-05-28.md (Card 2)
priority: P1
category: knowledge
status: distilled
tags:
- git
- markdown
- versioning
- idempotency
- audit
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# Git으로 남기는 마크다운 이력

> ChatGPT Pulse 2026-05-28 Card 2 증류 (P1 · knowledge)

## 목적
오늘의 플러스 메모를 Git으로 자동 보관하면 이력 보존·되돌리기·중복 방지·감사 추적이 한 번에 된다. SHA 해시 기반 idempotency로 중복 커밋 방지. Obsidian 볼트를 Git 저장소로 관리하면 완전한 변경 이력과 협업이 가능해짐.

## 핵심 내용
- **git commit 자동화 스크립트**:
  ```bash
  #!/bin/bash
  FILE="$1"
  SHA=$(sha256sum "$FILE" | cut -d' ' -f1)
  LAST_SHA=$(git log --format="%s" -1 -- "$FILE" | grep -o 'sha:[a-f0-9]*' | cut -d: -f2)
  if [ "$SHA" = "$LAST_SHA" ]; then
    echo "No changes, skipping commit"
    exit 0
  fi
  git add "$FILE"
  git commit -m "auto: update $(basename $FILE) sha:$SHA"
  ```
- **SHA 기반 중복 방지**: 커밋 메시지에 파일 SHA 포함, 동일 내용 재커밋 방지
- **감사 로그 활용**: `git log --follow --format="%H %ai %s" FILE` 로 전체 변경 이력 조회
- **자동화 트리거**: 파일 저장 시 watchdog → git 커밋 또는 cron으로 주기적 커밋

## 구현 체크리스트
- [ ] 자동 커밋 스크립트 작성 및 실행 권한 부여
- [ ] SHA 중복 체크 로직 테스트
- [ ] watchdog 또는 cron 트리거 설정
- [ ] `.gitignore` 설정 (오디오, 임시 파일 제외)
- [ ] 감사 로그 조회 명령어 alias 등록

## 관련 컨텍스트
- 웹훅 옵시디언 안전 전달: `2026-05-28-dp-webhook-to-obsidian-safe.md`
- 로컬 에이전트 오프라인 우선 경로: `2026-05-28-dp-local-agent-offline-first.md`
- Obsidian Agent Brain System Git 운영: `G:\내 드라이브\obsidian-agent-brain-system`

## 관련 노트
- [[hubs/JH System]]
