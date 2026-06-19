---
title: 시트 동기화용 Apps Script 레시피
date: 2026-06-07
source: daily-plus/2026-06-07.md (Card 3)
priority: P1
category: knowledge
status: distilled
tags:
- google-apps-script
- webhook
- sheet
- normalization
- zapier
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 시트 동기화용 Apps Script 레시피

> ChatGPT Pulse 2026-06-07 Card 3 증류 (P1 · knowledge-candidate)

## 목적

Google Apps Script를 웹앱으로 배포해 Zapier/n8n에서 JSON POST를 받으면 표준 스키마로 시트에 적재하고, 오류 로깅과 관리자 알림까지 자동 처리한다.

## Apps Script 코드 구조

```javascript
// doPost(e) — 웹앱 엔트리포인트
function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents);
    const sheet = SpreadsheetApp.getActiveSpreadsheet()
                    .getSheetByName('정규화_견적');
    appendRow(sheet, data);
    return ContentService.createTextOutput(
      JSON.stringify({ status: 'ok' })
    ).setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    logError(err, e.postData.contents);
    notifyAdmin(err);
    return ContentService.createTextOutput(
      JSON.stringify({ status: 'error', message: err.message })
    ).setMimeType(ContentService.MimeType.JSON);
  }
}
```

## 웹앱 배포 방법

1. Apps Script 편집기 → 배포 → 새 배포
2. 유형: 웹앱 선택
3. 실행 계정: 내 계정
4. 액세스 권한: 모든 사용자 (또는 조직 내)
5. 배포 → URL 복사 → Zapier/n8n webhook URL로 등록

## 입력 스키마 (JSON)

```json
{
  "현장": "강남구 역삼동 OO빌딩",
  "공사번호": "2026-001",
  "공종": "목공",
  "품목코드": "WD-001",
  "품명": "합판 12T",
  "규격": "1220x2440",
  "단위": "장",
  "수량": 20,
  "단가": 15000,
  "금액": 300000,
  "비고": ""
}
```

## 오류 처리

- **logError()**: '오류_로그' 시트에 타임스탬프 + 원본 데이터 + 오류 메시지 기록
- **notifyAdmin()**: `MailApp.sendEmail()` 또는 Slack webhook으로 즉시 알림
- 파싱 실패 시 HTTP 200 + `{ status: 'error' }` 반환 (Zapier 재시도 방지)

## 구현 체크리스트

- [ ] doPost 웹앱 배포 완료
- [ ] appendRow 필드 매핑 검증
- [ ] 오류 로그 시트 생성
- [ ] 관리자 이메일/Slack 알림 설정
- [ ] Zapier/n8n 연결 테스트

## 관련 컨텍스트

- [[estimator-csv-standardization-kit]]
- [[deploy-verify-error-recovery]]
- Zapier Google Sheets 연동 또는 n8n HTTP Request 노드 활용
