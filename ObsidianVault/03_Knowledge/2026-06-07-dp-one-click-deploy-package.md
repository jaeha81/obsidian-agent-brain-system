---
title: 원클릭 설치 배포 패키지
date: 2026-06-07
source: daily-plus/2026-06-07.md (Card 7)
priority: P1
category: knowledge
status: distilled
tags:
- deployment
- obsidian
- template
- github
- install
- daily-plus
- knowledge
- source/today_plus
- type/reference
- source/web
- area/obsidian_brain
graph_cluster: daily-practice
---

# 원클릭 설치 배포 패키지

> ChatGPT Pulse 2026-06-07 Card 7 증류 (P1 · knowledge-candidate)

## 목적

Obsidian 기반 프로젝트를 비개발자도 배포·설치할 수 있는 3가지 방식을 제공한다.

## 3가지 배포 옵션 비교

| 옵션 | 방식 | 대상 | 난이도 |
|------|------|------|--------|
| A. 템플릿 ZIP | 압축 파일 다운로드 + 압축 해제 | 완전 비개발자 | 최저 |
| B. GitHub + 설치 스크립트 | git clone + install.bat/sh 실행 | 기초 CLI 가능자 | 낮음 |
| C. Obsidian 커뮤니티 플러그인 | BRAT 플러그인으로 설치 | Obsidian 중급 사용자 | 낮음 |

## 옵션 A — 템플릿 ZIP

```
배포 파일 구조:
obsidian-starter-kit.zip
├── ObsidianVault/
│   ├── 00_System/
│   ├── 01_Inbox/
│   └── .obsidian/
│       └── plugins/
└── README.txt
```

설치: ZIP 다운로드 → 압축 해제 → Obsidian에서 볼트 열기

## 옵션 B — GitHub + 설치 스크립트

```batch
@echo off
:: install.bat (Windows)
git clone https://github.com/jh/obsidian-kit.git
cd obsidian-kit
copy .env.example .env
echo 설치 완료. README.txt를 참고하세요.
pause
```

```bash
#!/bin/bash
# install.sh (Mac/Linux)
git clone https://github.com/jh/obsidian-kit.git
cd obsidian-kit && cp .env.example .env
echo "설치 완료"
```

## 사용자 가이드 체크리스트

- [ ] README.txt 또는 설치 안내서 동봉
- [ ] .env.example 파일 포함 (실제 키값 없이)
- [ ] Obsidian 버전 요구사항 명시 (1.4.x 이상 권장)
- [ ] 필수 플러그인 목록과 설치 방법 안내
- [ ] 문제 발생 시 연락처/문서 링크 제공

## 배포 자동화

GitHub Actions를 통해 ZIP 자동 생성:

```yaml
- name: Create Release ZIP
  run: zip -r obsidian-starter-kit.zip ObsidianVault/ README.txt
- name: Upload Release
  uses: actions/upload-release-asset@v1
```

## 관련 컨텍스트

- [[deploy-verify-error-recovery]]
- [[vault-migration-safety]]
- [[agent-manifest-recovery]]
