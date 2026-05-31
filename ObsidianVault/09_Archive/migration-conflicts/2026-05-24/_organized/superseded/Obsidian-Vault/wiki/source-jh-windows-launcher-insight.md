---
type: source
category: note
date_added: 2026-04-25
source_url:
tags: [windows, launcher, powershell, jh-windows, insight]
  - #status/archive
---

# JH Windows 런처 개발 패턴 인사이트 — 2026-04-21 세션

## 한 줄 요약

2026-04-21 세션 10개 커밋 분석에서 추출한 Windows 런처 반복 문제 5가지와 검증된 해결 패턴.

## 핵심 포인트

- Windows cold-start PowerShell은 기본 인코딩이 CP949 → UTF-8 BOM 필수
- 포트 감지는 netstat 대신 TCP 소켓 직접 확인이 신뢰성 높음
- VBS 래퍼 환경에서 일부 PowerShell 명령 제한됨
- JH 생태계에서 포트 3000은 사용 금지 (충돌 이력)
- 런처 환경변수와 앱 환경변수 분리 필수

## 위키에 통합된 내용

- [[concept-windows-launcher-pattern]] 생성: 5가지 패턴과 체크리스트

## 인용 가능 구절

> "VBS `WScript.Shell.Run` 환경에서는 일부 PowerShell 명령이 제한됨"

## 관련 페이지

- [[concept-windows-launcher-pattern]]
- [[05_Insights/jh-windows-launcher-dev-pattern]]
