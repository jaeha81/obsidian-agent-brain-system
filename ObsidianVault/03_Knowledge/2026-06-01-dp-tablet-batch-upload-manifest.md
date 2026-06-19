---
title: 태블릿 배치 업로드 매니페스트
date: 2026-06-01
source: daily-plus/2026-06-01.md (Card 9)
priority: P1
category: knowledge
status: distilled
tags:
- tablet
- upload
- manifest
- bucky
- integrity
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 태블릿 배치 업로드 매니페스트

> Daily Plus Pulse 2026-06-01 Card 9 증류 (P1 · knowledge-candidate)

## 목적

태블릿에서 녹음/파일 배치 업로드 시 쓸 수 있는 버키 인제스트 매니페스트. 청크 정보, 무결성 해시, 암호화 힌트, 지연시간·WER 등 메타 포함.

## 매니페스트 JSON 필드 정의

```json
{
  "manifest_version": "1.0",
  "manifest_id": "mfst_<uuid>",
  "created_at": "2026-06-01T10:00:00Z",
  "device": {
    "id": "galaxy-tab-ultra-001",
    "model": "Samsung Galaxy Tab S Ultra",
    "os": "Android 14",
    "app_version": "1.2.3"
  },
  "session": {
    "id": "sess_<uuid>",
    "field_site": "현장명 또는 주소",
    "operator": "사용자ID 또는 이름",
    "started_at": "2026-06-01T09:00:00Z",
    "ended_at": "2026-06-01T09:45:00Z"
  },
  "files": [
    {
      "file_id": "file_001",
      "filename": "recording_001.wav",
      "mime_type": "audio/wav",
      "size_bytes": 5242880,
      "duration_sec": 45.3,
      "sample_rate": 16000,
      "channels": 1,
      "integrity": {
        "algorithm": "sha256",
        "hash": "a3f9b2c1..."
      },
      "encryption": {
        "algorithm": "AES-256-GCM",
        "key_hint": "env:UPLOAD_KEY_2026",
        "iv": "base64_iv_string"
      },
      "chunks": [
        {
          "chunk_id": 1,
          "offset_bytes": 0,
          "size_bytes": 1048576,
          "hash": "chunk_hash_1"
        }
      ],
      "metadata": {
        "stt_engine": "google-stt-v2",
        "wer_estimate": 0.08,
        "latency_ms": 1200,
        "noise_level_db": 62,
        "language": "ko-KR",
        "tags": ["목공", "점검", "완료보고"]
      }
    }
  ],
  "batch_integrity": {
    "total_files": 1,
    "total_bytes": 5242880,
    "manifest_hash": "sha256:<hash_of_entire_manifest>"
  }
}
```

## 무결성 해시 계산

```python
import hashlib, json

def compute_file_hash(filepath: str) -> str:
    """파일 SHA-256 해시 계산"""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()

def compute_manifest_hash(manifest: dict) -> str:
    """매니페스트 전체 JSON의 SHA-256"""
    # manifest_hash 필드 제외하고 계산
    m = {k: v for k, v in manifest.items() if k != 'batch_integrity'}
    serialized = json.dumps(m, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(serialized).hexdigest()

def verify_upload(manifest: dict, downloaded_files: dict) -> bool:
    """업로드 후 무결성 검증"""
    for file_meta in manifest['files']:
        fid = file_meta['file_id']
        expected_hash = file_meta['integrity']['hash']
        actual_hash = compute_file_hash(downloaded_files[fid])
        if expected_hash != actual_hash:
            return False
    return True
```

## 암호화 방식

```
파일 암호화: AES-256-GCM
  - 키: 환경변수 UPLOAD_KEY_<YYYY> (월별 교체)
  - IV: 파일별 랜덤 생성 (12 bytes)
  - 키 관리: 서버 사이드 KMS, 클라이언트에 평문 키 미노출

전송: HTTPS TLS 1.3 필수
인증: Bearer Token (60분 만료)
재업로드: 멱등성 키 (manifest_id) 기반 중복 방지
```

## 버키 인제스트 연동

```json
{
  "trigger": "tablet_batch_upload",
  "manifest_id": "mfst_xxx",
  "file_count": 3,
  "total_mb": 15.2,
  "field_site": "현장명",
  "action": "ingest_and_transcribe",
  "notify_channel": "#jh-현장업로드"
}
```

Bucky 수신 → STT 파이프라인 → Obsidian 기록 → 태블릿 확인 알림

## 구현 우선순위

- [ ] 매니페스트 JSON 스키마 검증기 (jsonschema)
- [ ] `compute_file_hash()` 태블릿 앱 통합
- [ ] AES-256-GCM 암호화 유틸 구현
- [ ] Bucky 인제스트 엔드포인트 연결
- [ ] 업로드 후 무결성 자동 검증

## 관련 컨텍스트

- Galaxy Tab STT 워크플로우 업로드 단계
- [[탭-울트라-현장-STT-점검]], [[현장-음성-프라이버시-체크리스트]]
