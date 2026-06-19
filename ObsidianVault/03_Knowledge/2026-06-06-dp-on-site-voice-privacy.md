---
title: 현장 음성 프라이버시 규칙
date: 2026-06-06
source: daily-plus/2026-06-06.md (Card 12)
priority: P3
category: knowledge
status: distilled
tags:
- voice
- privacy
- pii-masking
- consent
- audit-log
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 현장 음성 프라이버시 규칙

> ChatGPT Pulse 2026-06-06 Card 12 증류 (P3 · knowledge-candidate)

## 목적

녹음 시 10초 동의 스크립트 재생, 로컬 순환 버퍼에 원본 저장 후 처리 후 삭제, PII 자동 마스킹(이름→[NAME_1]). 30-120초 검토 창, 감사 로그 영구 보관.

## 동의 스크립트 (10초)

녹음 시작 전 자동 재생:

```
"이 대화는 견적 자동화를 위해 녹음됩니다.
 개인정보는 자동으로 마스킹 처리됩니다.
 계속하시려면 확인을 눌러주세요."
```

**구현**:
```python
import pygame

def play_consent_audio():
    """동의 스크립트 재생 (10초)"""
    pygame.mixer.init()
    pygame.mixer.music.load("assets/consent_ko.mp3")
    pygame.mixer.music.play()
    pygame.time.wait(10000)  # 10초 대기

def get_consent() -> bool:
    """사용자 동의 확인"""
    play_consent_audio()
    response = input("동의하시면 Enter, 취소하시면 N을 누르세요: ")
    return response.strip().upper() != "N"
```

## 로컬 순환 버퍼

원본 음성을 로컬에만 임시 저장:

```python
import collections, threading, time

class CircularAudioBuffer:
    """최근 N초 분량만 유지하는 순환 버퍼"""

    def __init__(self, max_seconds: int = 300):
        self.max_seconds = max_seconds
        self.buffer = collections.deque()
        self._lock = threading.Lock()

    def add_chunk(self, audio_chunk: bytes, timestamp: float):
        with self._lock:
            self.buffer.append((timestamp, audio_chunk))
            # 오래된 청크 제거
            cutoff = time.time() - self.max_seconds
            while self.buffer and self.buffer[0][0] < cutoff:
                self.buffer.popleft()

    def get_recent(self, seconds: int) -> bytes:
        """최근 N초 데이터 반환"""
        cutoff = time.time() - seconds
        with self._lock:
            chunks = [chunk for ts, chunk in self.buffer if ts >= cutoff]
        return b"".join(chunks)

    def flush(self):
        """원본 데이터 즉시 삭제"""
        with self._lock:
            self.buffer.clear()
```

## PII 마스킹 규칙

STT 전사 후 자동 마스킹:

```python
import re

class PIIMasker:
    """개인정보 자동 마스킹"""

    # 마스킹 패턴
    PATTERNS = [
        # 전화번호 (010-XXXX-XXXX, 02-XXX-XXXX)
        (r'\b(01[0-9]|02|0[3-9][0-9]?)-\d{3,4}-\d{4}\b', '[PHONE]'),
        # 이름 (2~4글자 한국어, 성씨 앞)
        (r'\b[가-힣]{1}[가-힣]{1,3}씨\b', '[NAME]'),
        (r'\b[가-힣]{1}[가-힣]{1,3} 부장\b', '[NAME] 부장'),
        # 이메일
        (r'\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b', '[EMAIL]'),
        # 주민등록번호
        (r'\b\d{6}-[1-4]\d{6}\b', '[SSN]'),
        # 주소 (상세 주소)
        (r'\b[가-힣]+구\s[가-힣]+동\s\d+번지?\b', '[ADDRESS]'),
    ]

    def mask(self, text: str) -> tuple[str, list]:
        """PII 마스킹 후 (마스킹된 텍스트, 마스킹 항목 목록) 반환"""
        masked = text
        found = []
        counter = {}

        for pattern, replacement in self.PATTERNS:
            matches = re.findall(pattern, masked)
            for match in matches:
                label = replacement.strip("[]")
                counter[label] = counter.get(label, 0) + 1
                found.append({"type": label, "original": match})
                masked = masked.replace(match, f"[{label}_{counter[label]}]", 1)

        return masked, found
```

## 보존 기간 정책

| 데이터 유형 | 보존 기간 | 저장 위치 | 삭제 방법 |
|-----------|---------|---------|---------|
| 원본 음성 (로컬 버퍼) | 처리 후 즉시 삭제 | 로컬 메모리 | buffer.flush() |
| STT 전사 원본 | 검토 창(30~120초) 이후 삭제 | 로컬 임시 파일 | os.unlink() |
| 마스킹된 전사 | 프로젝트 기간 | 암호화 저장소 | 프로젝트 종료 후 삭제 |
| 감사 로그 | 영구 보관 | 별도 감사 DB | 삭제 불가 |

## 30~120초 검토 창

STT 전사 후 업로드 전 검토 기회:

```python
def review_transcript(transcript: str, window_seconds: int = 60) -> str:
    """검토 창: 사용자가 수정 또는 취소 가능"""
    print(f"\n=== 전사 결과 검토 ({window_seconds}초 이내) ===")
    print(transcript)
    print(f"\n[Enter: 승인] [e: 편집] [n: 취소] ({window_seconds}초 후 자동 취소)")

    import select, sys
    ready, _, _ = select.select([sys.stdin], [], [], window_seconds)
    if ready:
        choice = sys.stdin.readline().strip().lower()
        if choice == "e":
            return input("수정된 내용: ")
        elif choice == "n":
            return None  # 취소
    else:
        return None  # 시간 초과 → 자동 취소

    return transcript  # 승인
```

## 감사 로그 형식

```json
{
  "log_id": "VOICE-2026-06-06-001",
  "timestamp": "2026-06-06T10:30:00+09:00",
  "event": "voice_recording",
  "consent_given": true,
  "consent_timestamp": "2026-06-06T10:29:50+09:00",
  "duration_seconds": 45,
  "pii_items_masked": [
    {"type": "NAME", "count": 2},
    {"type": "PHONE", "count": 1}
  ],
  "original_deleted": true,
  "transcript_approved": true,
  "project_id": "PROJ-견적-001",
  "operator": "field_agent_01"
}
```

## 관련 컨텍스트

- [[rbac-secrets-handoff]] — 감사 로그 접근 권한
- [[planswift-qc-pilot]] — 음성 리뷰 자동 전사 활용
