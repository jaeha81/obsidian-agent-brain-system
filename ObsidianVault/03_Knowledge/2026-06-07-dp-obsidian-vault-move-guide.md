---
title: Obsidian 볼트 이동 실전 가이드
date: 2026-06-07
source: daily-plus/2026-06-07.md (Card 10)
priority: P1
category: knowledge
status: distilled
tags:
- obsidian
- vault-migration
- data-integrity
- verification
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# Obsidian 볼트 이동 실전 가이드

> ChatGPT Pulse 2026-06-07 Card 10 증류 (P1 · knowledge-candidate)

## 목적

Obsidian 볼트를 한 드라이브에서 다른 드라이브로 이동하면서 데이터 무결성을 검증하는 절차를 제공한다.

## 이동 전 백업 절차

1. Obsidian 완전 종료 (트레이 아이콘 포함)
2. `.obsidian/` 폴더 포함 전체 볼트 복사본 생성
3. 복사 전 파일 수 기록:
   ```powershell
   (Get-ChildItem "D:\OldVault" -Recurse).Count
   ```
4. Git 사용 시: `git add -A && git commit -m "pre-migration snapshot"`

## 무결성 검증 방법

### 파일 수 비교
```powershell
# 이전 위치
(Get-ChildItem "D:\OldVault" -Recurse).Count

# 새 위치 이동 후
(Get-ChildItem "G:\NewVault" -Recurse).Count
```
두 값이 일치해야 함.

### 체크섬 비교 (선택)
```powershell
Get-FileHash "D:\OldVault\important-note.md" -Algorithm SHA256
Get-FileHash "G:\NewVault\important-note.md" -Algorithm SHA256
```

### 링크 무결성 확인
Obsidian 실행 후 → 그래프 뷰 열기 → 고아 노드(링크 없는 파일) 수 이전과 비교

## 플러그인 재설정

이동 후 플러그인이 초기화될 수 있음:

1. `.obsidian/plugins/` 폴더가 새 위치에 복사됐는지 확인
2. Obsidian → 설정 → 커뮤니티 플러그인 → 각 플러그인 활성화 상태 확인
3. 플러그인별 설정 파일 (`data.json`) 존재 여부 확인

## 데이터 유실 사례 대응

| 유실 원인 | 증상 | 복구 방법 |
|-----------|------|-----------|
| 동기화 중 이동 | 일부 파일 최신 버전 아님 | 동기화 완료 후 재이동 |
| 숨김 파일 미복사 | 플러그인 설정 초기화 | `.obsidian/` 폴더 수동 복사 |
| 경로 길이 초과 | 파일 복사 실패 | 파일명 단축 후 재시도 |

## 실패 시 복구

백업 위치에서 원본 복원:
```powershell
robocopy "D:\Backup\OldVault" "D:\OldVault" /E /COPYALL
```

## 관련 컨텍스트

- [[vault-migration-safety]]
- [[agent-manifest-recovery]]
- [[one-click-deploy-package]]
