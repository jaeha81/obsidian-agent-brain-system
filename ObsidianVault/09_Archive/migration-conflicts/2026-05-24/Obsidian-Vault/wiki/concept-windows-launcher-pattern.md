---
type: concept
updated: 2026-04-25
sources: [source-jh-windows-launcher-insight]
tags: [windows, launcher, powershell, vbs, encoding, electron]
  - #status/archive
---

# Windows 런처 개발 패턴

Windows에서 PowerShell/Electron 앱을 바탕화면 아이콘으로 실행할 때 반복 등장하는 5가지 문제와 검증된 해결 패턴.

## 핵심 아키텍처

```
바탕화면 아이콘
  → run.vbs (UTF-8 BOM, 숨김 실행 래퍼)
    → launch-app.ps1 (UTF-8 BOM, TCP 소켓 포트 체크)
      → Next.js 서버 or Electron 앱
```

## 5가지 문제와 해결 패턴

### 1. 포트 감지 — netstat 대신 TCP 소켓

- **문제**: `netstat`으로 포트 체크 시 환경에 따라 실패
- **해결**: PowerShell TCP 소켓 직접 확인
- **적용**: Windows에서 포트 감지는 `Test-NetConnection` 또는 TCP 소켓이 신뢰성 높음

### 2. VBS 숨김 실행 + 브라우저 오픈 충돌

- **문제**: VBS `WScript.Shell.Run` 환경에서 `Start-Process` 브라우저 오픈 실패
- **해결**: 브라우저 오픈 방식 교체 (ShellExecute 또는 별도 프로세스)
- **적용**: VBS 환경에서는 일부 PowerShell 명령이 제한됨을 가정하고 설계

### 3. 한글 경로 + 인코딩 (가장 중요)

- **문제**: 바탕화면 아이콘 cold-start 시 한글 경로 깨짐
- **해결 1**: `run.vbs` 래퍼로 우회
- **해결 2**: `launch-app.ps1`에 **UTF-8 BOM** 추가
- **원리**: Windows cold-start PowerShell 기본 인코딩은 CP949. BOM 있는 UTF-8 또는 `-Encoding UTF8` 명시 필수

### 4. 포트 충돌 — JH 생태계 예약 포트

- **문제**: 포트 3000이 다른 앱과 충돌
- **규칙**: JH 생태계에서 **3000은 예약 없이 사용 금지** → 3001+ 사용

### 5. NODE_ENV 환경변수 충돌

- **문제**: `NODE_ENV=production`이 Next.js 동작 방해
- **해결**: 런처 환경변수와 앱 환경변수 분리

## 체크리스트 (신규 Windows 런처 작성 시)

- [ ] VBS 래퍼 작성 (UTF-8 BOM, 숨김 실행)
- [ ] PowerShell 스크립트 UTF-8 BOM 저장
- [ ] 포트 감지 방식: TCP 소켓 사용
- [ ] 포트 번호: 3001 이상
- [ ] 환경변수 분리 확인

## 관련 페이지

- [[entity-claude-ai-desktop-setup]] — Claude.ai 데스크탑 연동 설정
- [[concept-llm-wiki]] — 위키 운영 구조

## 출처

- [[source-jh-windows-launcher-insight]] (2026-04-25)
