---
title: 옵시디언 모바일 호환 점검
date: 2026-06-01
source: daily-plus/2026-06-01.md (Card 12)
priority: P3
category: knowledge
status: distilled
tags:
- obsidian
- mobile
- ios
- android
- plugin-compatibility
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 옵시디언 모바일 호환 점검

> Daily Plus Pulse 2026-06-01 Card 12 증류 (P3 · knowledge-candidate)

## 목적

Obsidian 모바일 앱 OS 조건 변화 후 모바일 워크플로우 동작 확인. 플러그인·위젯·인터페이스 변화 대응 체크리스트.

## 최소 OS 요건

| 플랫폼 | 최소 버전 | 권장 버전 |
|--------|--------|--------|
| Android | 8.0 (API 26) | 13 이상 |
| iOS | 16.0 | 17 이상 |
| iPadOS | 16.0 | 17 이상 |

Obsidian 앱 최소 버전: 1.5.x 이상 (2024년 기준)

## 플러그인 호환성 확인 방법

```
1. Obsidian 설정 → 커뮤니티 플러그인 → 각 플러그인 클릭
   → "모바일 지원" 항목 확인

2. 플러그인별 모바일 지원 상태표:
```

| 플러그인 | Android | iOS | 비고 |
|---------|---------|-----|------|
| Dataview | 지원 | 지원 | 쿼리 성능 다소 낮음 |
| Templater | 지원 | 지원 | 시스템 명령 불가 |
| Tasks | 지원 | 지원 | 완전 지원 |
| Kanban | 지원 | 지원 | 드래그 제한 |
| Graph Analysis | 지원 | 지원 | 대형 그래프 느림 |
| Shell Commands | 미지원 | 미지원 | 모바일 비활성화 필요 |
| Local REST API | 미지원 | 미지원 | 데스크탑 전용 |
| Custom JS | 부분 | 부분 | Node.js API 불가 |

```
3. 플러그인 모바일 비활성화 방법:
   설정 → 커뮤니티 플러그인 → 해당 플러그인 → "모바일에서 비활성화"
```

## 실패 시 대응

| 증상 | 원인 | 대응 |
|------|-----|------|
| 플러그인 로드 실패 | Node.js API 사용 | 플러그인 모바일 비활성화 |
| 동기화 충돌 | iCloud/Syncthing 경쟁 | 단일 동기화 도구만 사용 |
| 그래프 뷰 느림 | 노트 2000개 이상 | 그래프 필터로 범위 축소 |
| 렌더링 깨짐 | CSS snippet 미지원 | 모바일용 별도 snippet |
| 검색 느림 | 인덱스 손상 | 볼트 재인덱싱 (설정→파일) |

## 동기화 설정 재확인

```
Obsidian Sync (공식)
  - 설정 → Sync → 동기화 상태 확인
  - "지금 동기화" 수동 실행
  - 충돌 파일: 설정 → Sync → 충돌 해결

iCloud (iOS/iPadOS)
  - iOS 설정 → iCloud → Obsidian → iCloud Drive ON
  - 파일 앱에서 "다운로드" 수동 실행 가능

Syncthing (Android)
  - 폴더 권한 확인 (Android 13+ 추가 권한 필요)
  - 배터리 최적화 제외 설정 필수

Google Drive / OneDrive (비공식)
  - 실시간 동기화 지원 안 됨, 주기적 백업 용도만
```

## 체크리스트

```
설치/업데이트 후 점검
  [ ] Obsidian 앱 버전 최신 확인
  [ ] 핵심 플러그인 로드 오류 없음
  [ ] 볼트 열기 정상 (파일 목록 표시)
  [ ] 노트 편집 및 저장 정상

플러그인 점검
  [ ] 모바일 미지원 플러그인 비활성화 확인
  [ ] Dataview 쿼리 결과 표시 정상
  [ ] Templater 템플릿 실행 정상
  [ ] Tasks 체크박스 토글 정상

동기화 점검
  [ ] 최근 편집 파일 반영 여부 확인
  [ ] 충돌 파일 없음
  [ ] 오프라인 편집 후 동기화 정상

성능 점검
  [ ] 앱 시작 시간 < 5초
  [ ] 검색 응답 < 3초 (1000개 노트 기준)
  [ ] 그래프 뷰 로드 < 10초
```

## 구현 우선순위

- [ ] Galaxy Tab Ultra에서 Obsidian 앱 버전 확인
- [ ] 미지원 플러그인 비활성화 목록 작성
- [ ] 동기화 도구 단일화 (충돌 방지)
- [ ] 모바일용 CSS snippet 별도 작성
- [ ] 월 1회 호환성 점검 Bucky 알림 등록

## 관련 컨텍스트

- 현장 태블릿 Obsidian 활용 워크플로우
- [[태블릿-배치-업로드-매니페스트]], [[탭-울트라-현장-STT-점검]]
