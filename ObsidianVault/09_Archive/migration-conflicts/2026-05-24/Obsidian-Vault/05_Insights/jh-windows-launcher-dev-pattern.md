---
type: knowledge
source: claude
system: JH-Obsidian-Second
status: done
date: 2026-04-21
tags: [jh-windows, launcher, electron, vbs, windows-encoding, insight]
summary: "JH Windows 런처 개발 시 반복 등장한 Windows 실행 환경 문제와 해결 패턴"
next_action: "새 Windows 실행 스크립트 작성 시 참고"
---

# JH Windows 런처 개발 패턴 — 2026-04-21

> 출처: 2026-04-21 세션 로그 → [[07_Archive/sessions/2026-04-21-session-log]]

## 핵심 인사이트

2026-04-21 4시간 세션에서 jh_windows 런처에 **10개의 커밋**이 발생했다.
대부분이 fix였고, 반복되는 Windows 실행 환경 문제 3가지가 원인이었다.

---

## 반복 문제 패턴

### 1. 프로세스 감지 방식 문제
- **문제**: `netstat`으로 포트 체크 → 환경에 따라 실패
- **해결**: PowerShell TCP 소켓 체크로 교체 (630cd9c)
- **교훈**: Windows에서 포트 감지는 netstat보다 `Test-NetConnection` 또는 TCP 소켓 직접 확인이 신뢰성 높음

### 2. VBS 숨김 실행 + 브라우저 오픈 충돌
- **문제**: VBS로 숨김 실행 시 `Start-Process` 브라우저 오픈 실패
- **해결**: 브라우저 오픈 방식 교체 (8407c36)
- **교훈**: VBS `WScript.Shell.Run` 환경에서는 일부 PowerShell 명령이 제한됨

### 3. 한글 경로 + 인코딩 문제
- **문제**: PowerShell 스크립트를 바탕화면 아이콘으로 실행 시 한글 경로 깨짐
- **해결 1**: run.vbs 래퍼로 우회 (5d5ed81)
- **해결 2**: launch-app.ps1에 UTF-8 BOM 추가 (0596bc5)
- **교훈**: Windows cold-start PowerShell은 기본 인코딩이 CP949. BOM 있는 UTF-8 또는 `-Encoding UTF8` 명시 필수

### 4. 포트 충돌
- **문제**: 포트 3000이 다른 앱과 충돌
- **해결**: 3001로 변경 (039c723)
- **교훈**: JH 생태계에서 3000은 예약 없이 사용하지 말 것

### 5. NODE_ENV=production 충돌
- **문제**: 런처에서 production 환경변수가 Next.js 동작 방해
- **해결**: 환경변수 분리 + 런처 안정화 (249008e)

---

## 아키텍처 결론

```
바탕화면 아이콘
  → run.vbs (UTF-8 BOM, 숨김 실행 래퍼)
    → launch-app.ps1 (UTF-8 BOM, TCP 소켓 포트 체크)
      → Next.js 서버 or Electron 앱
```

- VBS 래퍼: PowerShell 창 숨김 + 경로 인코딩 안전
- TCP 소켓 체크: netstat 대체, 신뢰성 높음
- UTF-8 BOM: 한글 경로 cold-start 안전

## 관련 아카이브
- [[07_Archive/sessions/2026-04-21-session-log]]
