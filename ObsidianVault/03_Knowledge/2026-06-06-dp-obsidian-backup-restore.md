---
title: 옵시디언 백업과 복구 체크리스트
date: 2026-06-06
source: daily-plus/2026-06-06.md (Card 10)
priority: P3
category: knowledge
status: distilled
tags:
- obsidian
- backup
- restore
- aes256
- kms
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 옵시디언 백업과 복구 체크리스트

> ChatGPT Pulse 2026-06-06 Card 10 증류 (P3 · knowledge-candidate)

## 목적

클라이언트 측 AES-256-GCM 암호화, manifest 기반 변화 감지, KMS 봉투 패턴으로 DEK 래핑. 매일 증분/매주 전체 스냅샷, 매월 스모크 복구 검증.

## 암호화 설정

### AES-256-GCM 암호화

```python
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os, json

def encrypt_vault(vault_path: str, output_path: str, key: bytes):
    """볼트 전체를 AES-256-GCM으로 암호화"""
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)  # 96-bit nonce

    # 볼트 데이터 수집
    vault_data = collect_vault_files(vault_path)
    plaintext = json.dumps(vault_data).encode()

    # 암호화
    ciphertext = aesgcm.encrypt(nonce, plaintext, associated_data=None)

    with open(output_path, "wb") as f:
        f.write(nonce + ciphertext)  # nonce + ciphertext 저장

def decrypt_vault(encrypted_path: str, key: bytes) -> dict:
    """복호화"""
    with open(encrypted_path, "rb") as f:
        data = f.read()
    nonce, ciphertext = data[:12], data[12:]
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, associated_data=None)
    return json.loads(plaintext)
```

### KMS 봉투 패턴 (DEK 보호)

```python
# DEK(Data Encryption Key)를 KMS로 래핑하여 저장
# 자세한 구현은 → [[rbac-secrets-handoff]]
```

## 스냅샷 일정

| 유형 | 주기 | 보존 기간 | 저장 위치 |
|-----|-----|---------|---------|
| 증분 백업 | 매일 오전 3시 | 30일 | 로컬 + Google Drive |
| 전체 스냅샷 | 매주 일요일 | 90일 | Google Drive + S3 |
| 긴급 스냅샷 | 수동 | 30일 | 즉시 업로드 |

### manifest 기반 변화 감지

```python
import hashlib, json
from pathlib import Path

def build_manifest(vault_path: str) -> dict:
    """볼트 파일 해시 manifest 생성"""
    manifest = {}
    for file in Path(vault_path).rglob("*.md"):
        content = file.read_bytes()
        manifest[str(file.relative_to(vault_path))] = {
            "sha256": hashlib.sha256(content).hexdigest(),
            "size": len(content),
            "mtime": file.stat().st_mtime,
        }
    return manifest

def detect_changes(old_manifest: dict, new_manifest: dict) -> dict:
    """변경된 파일만 증분 백업 대상으로 추출"""
    changed = {}
    for path, info in new_manifest.items():
        if path not in old_manifest or old_manifest[path]["sha256"] != info["sha256"]:
            changed[path] = info
    return changed
```

## 복구 절차

### 일반 복구 (파일 단위)

1. 백업 위치에서 해당 날짜 스냅샷 확인
2. KMS로 DEK 언래핑 → AES-256-GCM 복호화
3. 대상 파일 복원
4. manifest로 무결성 검증

### 전체 볼트 복구

```bash
# 1. 최신 전체 스냅샷 다운로드
python scripts/vault_restore.py --type full --date 2026-06-01

# 2. 복호화 및 압축 해제
python scripts/vault_restore.py --decrypt --output ./vault_restored

# 3. 무결성 검증
python scripts/vault_verify.py --manifest manifest_2026-06-01.json --vault ./vault_restored
```

## 최소 권한 역할 분리

| 작업 | 역할 | 비고 |
|-----|-----|-----|
| 백업 실행 | Writer | 자동 스케줄러 |
| 암호화 키 접근 | Secret-operator | 사람만 |
| 복구 실행 | Deployer | 승인 필요 |
| 스모크 테스트 | Reader | 자동화 가능 |

## 매월 스모크 복구 검증 체크리스트

- [ ] 랜덤 선택 5개 파일 복구 테스트
- [ ] manifest 해시 일치 확인
- [ ] 복구 시간 측정 (목표: 전체 < 30분)
- [ ] DEK 언래핑 정상 작동 확인
- [ ] 복구 로그 감사 기록

## 관련 컨텍스트

- [[rbac-secrets-handoff]] — KMS 봉투 패턴 상세
- [[obsidian-ai-plugin-patterns]]
