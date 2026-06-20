---
title: 현장 음성 프라이버시 체크리스트
date: 2026-06-01
source: daily-plus/2026-06-01.md (Card 10)
priority: P1
category: knowledge
status: distilled
tags:
- voice
- privacy
- pii
- field
- compliance
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# 현장 음성 프라이버시 체크리스트

> Daily Plus Pulse 2026-06-01 Card 10 증류 (P1 · knowledge-candidate)

## 목적

현장(공사/설치/점검)에서 오디오 수집·분석 시 적용하는 프라이버시·보안 체크리스트. 개인정보보호법 준수, PII 마스킹, 명시적 옵트인 필수.

## 수집 전 동의 절차

```
[현장 진입 시]
1. 녹음 시작 전 현장 내 모든 관계자에게 고지
2. 구두 또는 서면 동의 획득
3. 동의 거부 시 녹음 즉시 중단

[동의서 포함 항목]
  - 수집 목적: 공사 진행 기록 및 품질 관리
  - 수집 항목: 음성 (STT 변환 포함)
  - 보존 기간: 프로젝트 완료 후 90일
  - 제3자 제공: 없음 (STT 엔진 처리 제외)
  - 철회 방법: 담당자 연락 또는 앱 내 삭제 요청

[디지털 동의 (앱 내)]
  "현장 음성 수집에 동의합니다. [동의] [거부]"
  → 동의 기록: consent_id, timestamp, 서명
```

## PII 마스킹 방법

```python
import re

# STT 변환 텍스트에서 PII 자동 마스킹
PII_PATTERNS = {
    'phone': r'0[1-9][0-9]-?\d{3,4}-?\d{4}',           # 전화번호
    'rrn': r'\d{6}-[1-4]\d{6}',                          # 주민등록번호
    'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
    'account': r'\d{10,14}',                              # 계좌번호
    'name_pattern': r'(?:저는|제 이름은|성함은)\s+(\S+)',  # 이름 언급
}

def mask_pii(text: str) -> tuple[str, list]:
    """PII 마스킹 후 (마스킹된 텍스트, 탐지된 PII 목록) 반환"""
    detections = []
    masked = text
    for pii_type, pattern in PII_PATTERNS.items():
        matches = re.findall(pattern, masked)
        if matches:
            detections.append({'type': pii_type, 'count': len(matches)})
            masked = re.sub(pattern, f'[{pii_type.upper()}_MASKED]', masked)
    return masked, detections

# 오디오 레벨 PII (화자 식별 방지)
def strip_speaker_metadata(audio_path: str) -> str:
    """오디오 메타데이터에서 화자 식별 정보 제거"""
    # ffmpeg 기반 메타데이터 스트립
    import subprocess
    output = audio_path.replace('.wav', '_stripped.wav')
    subprocess.run(['ffmpeg', '-i', audio_path, '-map_metadata', '-1', output])
    return output
```

## 저장 기간 정책

| 데이터 유형 | 보존 기간 | 삭제 방법 |
|-----------|--------|---------|
| 원본 오디오 | 프로젝트 완료 후 30일 | 안전 삭제 (덮어쓰기) |
| STT 변환 텍스트 | 프로젝트 완료 후 90일 | DB 레코드 삭제 |
| PII 마스킹 텍스트 | 1년 | 아카이브 후 삭제 |
| 동의 기록 | 5년 (법적 의무) | 별도 보관 |
| 감사 로그 | 3년 | 압축 보관 |

자동 삭제 스케줄러:
```python
# 매일 자정 실행
def cleanup_expired_data():
    threshold = datetime.now() - timedelta(days=30)
    AudioRecord.objects.filter(
        project_completed_at__lt=threshold
    ).delete()  # cascade로 파일도 삭제
```

## 감사 로그 요건

```json
{
  "audit_id": "prv_<uuid>",
  "ts": "2026-06-01T10:00:00Z",
  "action": "audio_collect | stt_process | pii_mask | data_delete",
  "actor": "operator:user_id | system:bucky",
  "resource": "audio_file_id or stt_record_id",
  "field_site": "현장명",
  "consent_id": "cst_xxx",
  "pii_detected": false,
  "pii_types": [],
  "result": "success",
  "retention_expires_at": "2026-09-01T00:00:00Z"
}
```

감사 로그는 수정/삭제 불가 (append-only 스토리지).

## 최종 체크리스트

```
수집 전
  [ ] 현장 관계자 전원 고지 완료
  [ ] 명시적 동의 획득 (동의서 또는 앱 내 기록)
  [ ] 녹음 표시등/알림음 활성화 확인

수집 중
  [ ] 수집 범위 최소화 (필요 구역만)
  [ ] 불필요한 개인 대화 녹음 즉시 중단
  [ ] 암호화 전송 확인 (HTTPS)

수집 후
  [ ] STT 변환 전 PII 스캔
  [ ] 마스킹 처리 후 Bucky 전달
  [ ] 원본 오디오 보존 기간 라벨링
  [ ] 감사 로그 기록

정기 점검 (월 1회)
  [ ] 보존 기간 초과 파일 삭제 확인
  [ ] 동의 철회 요청 처리 확인
  [ ] PII 마스킹 정확도 샘플 테스트
```

## 구현 우선순위

- [ ] 앱 내 동의 화면 및 기록 저장
- [ ] `mask_pii()` 함수 STT 파이프라인 삽입
- [ ] 자동 삭제 스케줄러 배포
- [ ] 감사 로그 append-only 스토리지 구성
- [ ] 월별 PII 마스킹 정확도 리포트

## 관련 컨텍스트

- 개인정보보호법 (대한민국) 준수 기반
- [[태블릿-배치-업로드-매니페스트]], [[탭-울트라-현장-STT-점검]]
