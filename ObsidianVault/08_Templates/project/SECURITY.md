---
tags:
  - orphan
---

# SECURITY — {{PROJECT_NAME}}

## 비밀 키 관리
- 저장 위치: `.env` (코드에 절대 포함 금지)
- 환경별 분리: `.env.local` / `.env.production`

## 인증/인가
<!-- 인증 방식, 권한 레벨 -->

## 입력 검증
<!-- XSS, SQL Injection, Command Injection 방어 -->

## 알려진 취약점
<!-- 발견된 보안 이슈 및 조치 현황 -->

## 보안 체크리스트
- [ ] API 키 코드 노출 없음
- [ ] 입력값 서버측 검증
- [ ] HTTPS 강제
- [ ] 민감 로그 마스킹
