---
title: 배포 검증과 오류 복구 절차
date: 2026-06-07
source: daily-plus/2026-06-07.md (Card 4)
priority: P1
category: knowledge
status: distilled
tags:
  - deployment
  - verification
  - rollback
  - apps-script
  - checklist
  - daily-plus
  - knowledge
---

# 배포 검증과 오류 복구 절차

> ChatGPT Pulse 2026-06-07 Card 4 증류 (P1 · knowledge-candidate)

## 목적

배포 직후 비개발자도 실행할 수 있는 검증 체크리스트와 오류 복구 절차를 제공한다. Apps Script + Google 스프레드시트 + Zapier/n8n 기준.

## 초기 테스트 8단계

1. **웹앱 URL 확인**: 배포 URL에 브라우저로 접근 → 403 없이 응답 오는지 확인
2. **샘플 POST 전송**: curl 또는 Postman으로 샘플 JSON 전송
   ```bash
   curl -X POST "YOUR_WEBAPP_URL" \
     -H "Content-Type: application/json" \
     -d '{"현장":"테스트","공사번호":"T-001","공종":"테스트"}'
   ```
3. **시트 적재 확인**: '정규화_견적' 시트에 데이터 추가 여부 확인
4. **오류 로그 빈 상태 확인**: '오류_로그' 시트가 비어 있는지 확인
5. **오류 시나리오 테스트**: 빈 JSON `{}` 전송 → 오류 로그 기록 확인
6. **관리자 알림 확인**: 오류 발생 시 이메일/Slack 수신 확인
7. **Zapier/n8n 연결 테스트**: 실제 트리거 발동 후 시트 반영 확인
8. **데이터 정합성 확인**: 수량 × 단가 = 금액 자동 계산 결과 검증

## 오류 로그 포맷

| 컬럼 | 설명 |
|------|------|
| 타임스탬프 | ISO 8601 형식 |
| 원본_데이터 | 수신된 JSON 문자열 |
| 오류_메시지 | 예외 메시지 |
| 처리_상태 | pending / resolved |

## 롤백 절차

1. Apps Script 편집기 → 배포 관리 → 이전 버전 선택
2. 또는 Google Sheets → 파일 → 버전 기록 → 이전 시점으로 복원
3. Zapier/n8n에서 해당 Zap/워크플로우 일시 정지

## 알림 설정

```javascript
function notifyAdmin(err) {
  const adminEmail = 'admin@example.com';
  MailApp.sendEmail({
    to: adminEmail,
    subject: '[오류] Apps Script 웹앱 오류 발생',
    body: `오류 시각: ${new Date()}\n오류 내용: ${err.message}`
  });
}
```

## 관련 컨텍스트

- [[apps-script-sync-recipe]]
- [[one-click-deploy-package]]
- 배포 후 첫 72시간은 오류 로그 상시 모니터링 권장
