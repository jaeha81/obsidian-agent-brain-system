---
type: knowledge-note
date: 2026-06-06
source: daily-plus
category: voice-pipeline
tags:
- '#area/ai_automation'
- '#status/active'
summary: 현장 음성 녹음 동의·PII 마스킹·보존 정책·감사 로그 규칙
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# On-Site Voice Privacy Rules

## 개요

현장(건설·인테리어 시공 등) 음성 녹음 수집 시 준수해야 할 프라이버시 규칙.
동의 스크립트 → 로컬 처리 → PII 마스킹 → 검토 → 감사 로그 순서로 실행한다.

---

## 1. 동의 스크립트 (녹음 시작 전 10초 재생)

```
[재생 텍스트 — 한국어]
"이 대화는 AI 분석을 위해 녹음됩니다.
 개인정보는 자동 마스킹 처리되며,
 원본 음성은 처리 후 즉시 삭제됩니다.
 계속하시려면 '네'라고 말씀해 주세요."
```

**동의 확인 로직**:

```python
def check_consent(audio_response: str) -> bool:
    affirmatives = ["네", "예", "응", "ok", "yes", "괜찮아요", "좋아요"]
    transcript = stt_short(audio_response)  # 5초 이내 응답
    return any(word in transcript.lower() for word in affirmatives)

# 동의 거부 또는 무응답(5초) → 녹음 즉시 중단
```

---

## 2. 로컬 순환 버퍼 (원본 음성)

```python
import collections
import threading

class VoiceCircularBuffer:
    """원본 음성을 로컬에서만 보관하는 순환 버퍼"""
    
    def __init__(self, max_seconds: int = 300):
        self.buffer = collections.deque(maxlen=max_seconds * 16000)  # 16kHz
        self.lock = threading.Lock()
    
    def write(self, chunk: bytes):
        with self.lock:
            self.buffer.extend(chunk)
    
    def flush_after_processing(self):
        """STT 처리 완료 후 원본 즉시 삭제"""
        with self.lock:
            self.buffer.clear()
        # 메모리 강제 해제
        import gc; gc.collect()
```

**원칙**:
- 버퍼는 로컬 RAM에만 존재 (디스크 기록 없음)
- STT 처리 완료 즉시 `flush_after_processing()` 호출
- 버퍼 최대 5분 분량 (처리 지연 대비)

---

## 3. 자동 PII 마스킹

```python
import re

PII_PATTERNS = [
    # 이름 → [NAME_N]
    (r"(?:저는|저|제\s*이름은|이름이)\s+([가-힣]{2,4})\s*(?:입니다|이에요|예요|야|이야)?",
     lambda m, n=[0]: f"[NAME_{(n.__setitem__(0, n[0]+1) or n[0])}]"),
    
    # 전화번호 → [PHONE]
    (r"01[0-9]-?\d{3,4}-?\d{4}", "[PHONE]"),
    
    # 주민등록번호 앞 6자리 → [RRNO]
    (r"\d{6}-[1-4]\d{6}", "[RRNO]"),
    
    # 이메일 → [EMAIL]
    (r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", "[EMAIL]"),
    
    # 주소 패턴 → [ADDRESS]
    (r"(?:서울|부산|대구|인천|광주|대전|울산|세종|경기|강원|충북|충남|전북|전남|경북|경남|제주)\s+\S+\s+\d+",
     "[ADDRESS]"),
]

def mask_pii(text: str) -> tuple[str, list[str]]:
    """PII 마스킹 후 (마스킹된 텍스트, 마스킹 항목 목록) 반환"""
    masked = text
    found = []
    for pattern, replacement in PII_PATTERNS:
        matches = re.findall(pattern, masked)
        if matches:
            found.extend(matches)
        masked = re.sub(pattern, replacement if isinstance(replacement, str) else "[MASKED]", masked)
    return masked, found
```

---

## 4. 30–120초 검토 창

```python
def review_window(masked_text: str, window_seconds: int = 60) -> str:
    """
    운영자가 마스킹 결과를 검토하는 시간 제공.
    window_seconds 초 내 응답 없으면 자동 승인.
    """
    print(f"[검토] 마스킹된 텍스트:\n{masked_text}")
    print(f"[안내] {window_seconds}초 내 수정하거나 Enter로 승인하세요.")
    
    import select, sys
    readable, _, _ = select.select([sys.stdin], [], [], window_seconds)
    
    if readable:
        correction = sys.stdin.readline().strip()
        return correction if correction else masked_text
    else:
        print("[자동 승인]")
        return masked_text
```

---

## 5. 감사 로그

```python
def write_audit_log(event: str, metadata: dict):
    """영구 보관 감사 로그 기록"""
    entry = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "event": event,  # "consent_given" | "recording_start" | "pii_masked" | "raw_deleted"
        "session_id": metadata.get("session_id"),
        "consent": metadata.get("consent", False),
        "pii_items_masked": metadata.get("pii_count", 0),
        "raw_voice_deleted": metadata.get("raw_deleted", False),
    }
    # 로그는 append-only (삭제 금지)
    with open("audit_voice.log", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
```

---

## 보존 정책 요약

| 데이터 유형 | 보존 기간 | 저장 위치 | 삭제 방법 |
|------------|-----------|-----------|-----------|
| 원본 음성 | **0분** (즉시 삭제) | RAM 버퍼만 | `flush_after_processing()` |
| 마스킹된 텍스트 | **30일** | 로컬 암호화 DB | 자동 만료 |
| 감사 로그 | **영구** | append-only 파일 | 삭제 금지 |

---

## 체크리스트

- [ ] 동의 스크립트 10초 재생 확인
- [ ] 동의 거부 시 녹음 중단 로직 테스트
- [ ] PII 마스킹 패턴 단위 테스트 (이름·전화·주소)
- [ ] 순환 버퍼 `flush_after_processing()` 호출 검증
- [ ] 감사 로그 append-only 권한 설정 (chmod 444)
- [ ] 30일 텍스트 만료 cron 등록
