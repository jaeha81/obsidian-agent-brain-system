---
title: RBAC와 시크릿 핸드오프 플레이북
date: 2026-06-06
source: daily-plus/2026-06-06.md (Card 3)
priority: P1
category: knowledge
status: distilled
tags:
- rbac
- secrets
- kms
- agent
- security
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# RBAC와 시크릿 핸드오프 플레이북

> ChatGPT Pulse 2026-06-06 Card 3 증류 (P1 · knowledge-candidate)

## 목적

옵시디언 볼트에 5가지 역할(Observer/Reader/Writer/Deployer/Secret-operator) 정의로 에이전트 접근 제한. KMS 봉투 패턴으로 비밀 래핑, TTL 1-15분 서비스 토큰.

## 역할 정의 테이블

| 역할 | 읽기 | 쓰기 | 배포 | 시크릿 접근 | 용도 |
|-----|-----|-----|-----|-----------|-----|
| Observer | 공개만 | X | X | X | 모니터링, 읽기 전용 대시보드 |
| Reader | 전체 | X | X | X | 문서 검색, RAG 조회 |
| Writer | 전체 | 지정 폴더 | X | X | 노트 작성 에이전트 |
| Deployer | 전체 | 전체 | O | X | CI/CD, 빌드 파이프라인 |
| Secret-operator | 전체 | 전체 | O | O | 운영자 전용, 사람만 해당 |

```yaml
# RBAC 정의 (YAML 프론트매터 또는 별도 roles.yaml)
roles:
  observer:
    read: ["public/**"]
    write: []
    deploy: false
    secrets: false

  reader:
    read: ["**"]
    write: []
    deploy: false
    secrets: false

  writer:
    read: ["**"]
    write: ["03_Knowledge/**", "04_DAILY_REPORTS/**"]
    deploy: false
    secrets: false

  deployer:
    read: ["**"]
    write: ["**"]
    deploy: true
    secrets: false

  secret_operator:
    read: ["**"]
    write: ["**"]
    deploy: true
    secrets: true
    require_mfa: true
```

## KMS 봉투 패턴

Data Encryption Key(DEK)를 Key Encryption Key(KEK)로 래핑하는 봉투 암호화:

```python
from cryptography.fernet import Fernet
import boto3  # 또는 Google KMS, Azure Key Vault

# 1. DEK 생성 (데이터 암호화용 임시 키)
dek = Fernet.generate_key()
cipher = Fernet(dek)

# 2. DEK를 KMS KEK로 래핑 (봉투 암호화)
kms = boto3.client("kms")
wrapped_dek = kms.encrypt(
    KeyId="arn:aws:kms:...",
    Plaintext=dek
)["CiphertextBlob"]

# 3. 데이터 암호화
encrypted_secret = cipher.encrypt(b"MY_API_KEY=sk-abc123")

# 저장: encrypted_secret + wrapped_dek (원본 DEK 폐기)
vault.store({"wrapped_dek": wrapped_dek, "ciphertext": encrypted_secret})

# 4. 복호화 시: KMS로 DEK 언래핑 → 데이터 복호화
def decrypt_secret(wrapped_dek: bytes, ciphertext: bytes) -> bytes:
    dek = kms.decrypt(CiphertextBlob=wrapped_dek)["Plaintext"]
    return Fernet(dek).decrypt(ciphertext)
```

## TTL 서비스 토큰

에이전트용 단기 액세스 토큰:

```python
import jwt, time

def issue_agent_token(agent_id: str, role: str, ttl_minutes: int = 5) -> str:
    payload = {
        "sub": agent_id,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + (ttl_minutes * 60),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

# 역할별 TTL 권장값
TTL_MAP = {
    "observer": 60,      # 60분
    "reader": 60,        # 60분
    "writer": 15,        # 15분
    "deployer": 5,       # 5분
    "secret_operator": 1, # 1분 (사람 전용)
}
```

## YAML 프론트매터 감사

옵시디언 노트의 YAML 프론트매터로 접근 권한 추적:

```yaml
---
access_level: writer    # 최소 필요 역할
sensitive: false        # true 시 Reader 이상만 접근
last_modified_by: bucky # 마지막 수정 에이전트
audit_log: true         # 변경 이력 기록 여부
---
```

## 보안 체크리스트

- [ ] 역할별 최소 권한 원칙 적용
- [ ] Secret-operator 역할은 사람만 (에이전트 금지)
- [ ] DEK 생성 후 즉시 래핑, 원본 메모리에서 삭제
- [ ] 서비스 토큰 TTL 준수 (역할별 최대값 초과 금지)
- [ ] 모든 시크릿 접근에 감사 로그 기록
- [ ] `.env` 파일 git 커밋 금지 (gitignore 확인)

## 관련 컨텍스트

- [[hmac-idempotency-human-checklist]], [[obsidian-backup-restore]]
- [[approval-gate]] — Secret-operator 작업은 approval_required=true
