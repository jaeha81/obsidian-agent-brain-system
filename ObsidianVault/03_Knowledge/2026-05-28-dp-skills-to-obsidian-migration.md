---
title: Skills를 옵시디언으로 옮기는 법
date: 2026-05-28
source: daily-plus/2026-05-28.md (Card 10)
priority: P2
category: knowledge
status: distilled
tags:
  - skills
  - obsidian
  - migration
  - agent
  - knowledge-base
  - daily-plus
  - knowledge
---

# Skills를 옵시디언으로 옮기는 법

> ChatGPT Pulse 2026-05-28 Card 10 증류 (P2 · knowledge)

## 목적
GitHub 스킬 레포를 Obsidian 볼트로 이관해 에이전트가 스킬 노트를 읽고 즉시 실행할 수 있게 만드는 마이그레이션 가이드. 폴더=카테고리, 파일=스킬 구조. 스킬을 코드 저장소가 아닌 지식 그래프의 일부로 관리해 연결성과 발견 가능성을 높임.

## 핵심 내용
- **폴더 구조 설계**:
  ```
  ObsidianVault/
  └── 05_Skills/
      ├── deployment/
      │   ├── jh-deploy.md
      │   └── jh-vercel.md
      ├── analysis/
      │   ├── jh-research.md
      │   └── jh-explore.md
      └── agent/
          ├── bucky-commands.md
          └── codex-patterns.md
  ```
- **YAML 프런트매터 스킬 포맷**:
  ```yaml
  ---
  title: 스킬 이름
  skill_id: jh-deploy
  version: 1.2.0
  category: deployment
  triggers:
    - "배포"
    - "deploy"
    - "vercel"
  dependencies:
    - vercel-cli
    - github-actions
  agent_readable: true
  ---
  ```
- **에이전트 참조 방식**: 스킬 노트의 `skill_id` 필드로 직접 조회, 트리거 키워드로 자동 매칭
- **마이그레이션 순서**: GitHub README → Obsidian 노트 변환 → YAML 메타 추가 → 링크 연결 → 테스트

## 구현 체크리스트
- [ ] `05_Skills/` 폴더 구조 생성
- [ ] 기존 `.claude/skills/` 디렉토리 스킬 목록 추출
- [ ] 각 스킬 YAML 프런트매터 추가
- [ ] 에이전트 스킬 조회 스크립트 작성
- [ ] 스킬 노트 ↔ 관련 프로젝트 노트 링크 연결

## 관련 컨텍스트
- 옵시디언 큐 아이디어: `2026-05-27-dp-obsidian-queue-ideas.md`
- 현재 스킬 위치: `G:\내 드라이브\obsidian-agent-brain-system\.claude\skills\`
- Vault Structure: Vault Memory `project_vault_structure.md`
