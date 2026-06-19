---
type: knowledge-note
date: 2026-06-10
source: daily-plus
category: obsidian-queue
tags:
- '#area/ai_automation'
- '#status/active'
summary: Daily Plus Curator Copy Template — 오늘의_플러스 카드 복사 템플릿, 견적 PDF 자동화, I-Manager
  curl 트리거
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# Daily Plus Curator Copy Template

오늘의_플러스 Discord 카드 복사용 템플릿. 현장 사진 3장 + 도면 → 간단 견적 PDF 자동 생성 예시 포함.
시스템/보안 알림 섹션, curl 명령어로 I-Manager 트리거하는 To-Do 포함.

---

## 오늘의_플러스 카드 템플릿

```markdown
## 오늘의_플러스 | {{date}}

### 현장 정보
- 현장명: {{site_name}}
- 위치: {{location}}
- 담당자: {{manager}}

### 첨부 (사진 3장 + 도면)
- 사진 1: {{photo_1_url}}
- 사진 2: {{photo_2_url}}
- 사진 3: {{photo_3_url}}
- 도면: {{floor_plan_url}}

### AI 견적 요청
→ 위 도면 기준 간단 견적 PDF 자동 생성
→ 예상 공종: {{estimated_work_types}}
→ 면적: {{area_sqm}}㎡

### To-Do (복사 후 즉시 실행)
\```bash
curl -X POST http://localhost:8080/api/i-manager/trigger \
  -H "Content-Type: application/json" \
  -d '{"site": "{{site_name}}", "action": "generate_estimate", "floor_plan": "{{floor_plan_url}}"}'
\```
```

---

## 견적 PDF 자동 생성 파이프라인

### 입력 → 처리 → 출력

```
현장 사진 3장 + 도면 이미지
    ↓
[AI Vision] 공종 자동 인식
    ↓
[jh-estimate skill] 물량 산출
    ↓
[PDF 생성] 견적서 템플릿 적용
    ↓
Discord DM 또는 이메일 발송
```

### 견적서 PDF 필수 항목

| 항목 | 설명 |
|---|---|
| 현장명 | 자동 입력 |
| 공종 분류 | AI 자동 인식 (철거/도장/전기 등) |
| 물량 | ㎡ 또는 개소 기준 |
| 단가 | 기준 단가표 적용 |
| 합계 | VAT 포함/별도 선택 |
| 유효기간 | 발행일로부터 7일 |

---

## 시스템/보안 알림 섹션

### 오프라인 STT 우선순위 설정

```python
# config/stt_priority.py
STT_PRIORITY = [
    {"provider": "whisper-local", "model": "medium", "offline": True},   # 1순위
    {"provider": "whisper-local", "model": "small", "offline": True},    # 2순위 (fallback)
    {"provider": "openai-whisper", "model": "whisper-1", "offline": False},  # 3순위 (온라인만)
]

# 민감 필드 자동 마스킹 대상
SENSITIVE_FIELDS = [
    "계약금액", "낙찰금액", "투찰가", "주민등록번호",
    "계좌번호", "사업자번호", "연락처"
]
```

### 민감 필드 자동 마스킹

```python
import re

def mask_sensitive(text: str) -> str:
    patterns = {
        "주민번호": r"\d{6}-\d{7}",
        "계좌번호": r"\d{3,4}-\d{3,4}-\d{4,6}",
        "전화번호": r"0\d{1,2}-\d{3,4}-\d{4}",
    }
    for label, pattern in patterns.items():
        text = re.sub(pattern, f"[{label} 마스킹]", text)
    return text
```

### 보안 알림 트리거 조건

| 조건 | 알림 대상 | 채널 |
|---|---|---|
| 민감 필드 3개 이상 감지 | 담당자 | Discord DM |
| 외부 API 호출 실패 | 시스템 관리자 | #agent-alerts |
| STT 모델 폴백 발생 | 운영자 | #agent-logs |
| 파일 저장 실패 | 운영자 | #agent-logs |

---

## I-Manager 트리거 엔드포인트

```bash
# 견적 생성 트리거
curl -X POST http://localhost:8080/api/i-manager/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "action": "generate_estimate",
    "site": "현장명",
    "floor_plan": "https://...",
    "photos": ["url1", "url2", "url3"]
  }'

# 상태 확인
curl http://localhost:8080/api/i-manager/status/{job_id}
```

## 다음 액션

- [ ] 카드 템플릿을 Discord 봇 `/daily-plus` 명령어에 연결
- [ ] 민감 필드 마스킹 함수 `scripts/stt_utils.py`에 추가
- [ ] I-Manager API 엔드포인트 구현 확인

## 관련 노트
- [[hubs/JH System]]
