---
title: 에이전트 매니페스트 회복과 키 교체
date: 2026-06-07
source: daily-plus/2026-06-07.md (Card 11)
priority: P1
category: knowledge
status: distilled
tags:
- manifest
- recovery
- key-rotation
- idempotency
- integrity
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 에이전트 매니페스트 회복과 키 교체

> ChatGPT Pulse 2026-06-07 Card 11 증류 (P1 · knowledge-candidate)

## 목적

에이전트 매니페스트를 안전하게 이동하고, 중복 적용을 막고, 복구까지 점검하는 체크리스트를 제공한다.

## 이동 전 체크리스트

- [ ] 현재 매니페스트 버전 기록 (`manifest.json` → `version` 필드)
- [ ] sha256 해시 생성 및 저장
- [ ] idempotency_key 확인 (중복 적용 방지용 UUID)
- [ ] 에이전트 일시 정지 또는 드레인 모드 진입
- [ ] 의존 서비스 연결 상태 확인

## sha256 무결성 확인

```bash
# 이동 전
sha256sum manifest.json > manifest.sha256

# 이동 후 검증
sha256sum -c manifest.sha256
```

Windows PowerShell:
```powershell
Get-FileHash manifest.json -Algorithm SHA256 | Select-Object Hash
```

## idempotency_key 처리

매니페스트 적용 시 동일한 `idempotency_key`로 두 번 실행되어도 한 번만 처리:

```json
{
  "version": "1.2.0",
  "idempotency_key": "550e8400-e29b-41d4-a716-446655440000",
  "applied_at": null,
  "checksum": "sha256:abc123..."
}
```

- `applied_at`이 null이면 미적용 상태
- 적용 완료 후 타임스탬프 기록
- 동일 key 재실행 시 `already_applied` 반환

## 키 교체 절차

1. 새 idempotency_key 생성: `python -c "import uuid; print(uuid.uuid4())"`
2. 구 키 보관 (감사 로그용)
3. 매니페스트 버전 bump (`1.2.0` → `1.2.1`)
4. sha256 재계산
5. 에이전트 재시작 후 적용 확인

## 플러그인 깨짐 방지

- 매니페스트 이동 시 플러그인 경로 참조 업데이트 필수
- 상대 경로 사용 권장 (절대 경로는 이동 후 깨짐)
- 플러그인 버전 핀닝: `plugin_version_lock.json` 별도 관리

## 관련 컨텍스트

- [[manifest-hmac-acceptance]]
- [[obsidian-vault-move-guide]]
- [[vault-migration-safety]]
