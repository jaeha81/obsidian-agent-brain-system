---
type: knowledge-note
date: 2026-06-04
source: daily-plus
category: command-payload
tags:
- area/ai_automation
- status/active
summary: 이부장용 daily manifest diff 감지 + hash/멱등성 기반 게이트 publish 자동화 kit
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# Daily Diff and Payload Kit

## 개요

이부장이 일별 manifest를 승인하고, hash+idempotency 체크 뒤 게이트 publish를 수행하는 compact ready-to-run kit. diff 감지, 승인 플로우, Obsidian 기록을 포함한다.

## 구성 요소

1. **Diff Detector** — 어제 대비 오늘 변경사항 추출
2. **Approval Gate** — 이부장 승인 인터페이스
3. **Hash Publisher** — HMAC + idempotency key로 안전한 publish
4. **Obsidian Logger** — 승인 기록 vault 저장

## 1. Diff Detector

```python
import hashlib
import json
from pathlib import Path
from datetime import date, timedelta

def detect_daily_diff(vault_path: str) -> dict:
    """오늘 변경된 Vault 파일 목록과 hash 추출"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    vault = Path(vault_path)
    changed_files = []
    
    for f in vault.rglob("*.md"):
        mtime = date.fromtimestamp(f.stat().st_mtime)
        if mtime == today:
            content = f.read_text(encoding="utf-8")
            file_hash = hashlib.sha256(content.encode()).hexdigest()[:12]
            changed_files.append({
                "path": str(f.relative_to(vault)),
                "hash": file_hash,
                "size": f.stat().st_size
            })
    
    return {
        "date": str(today),
        "total_changes": len(changed_files),
        "files": changed_files,
        "manifest_hash": hashlib.sha256(
            json.dumps(changed_files, sort_keys=True).encode()
        ).hexdigest()
    }
```

## 2. 이부장 승인 페이로드 (Discord)

```
📋 Daily Diff — {{date}}
변경 파일: {{total_changes}}개
Manifest Hash: {{manifest_hash[:8]}}

변경 목록:
{{#each files}}
- {{path}} ({{hash}})
{{/each}}

[✅ 승인] 명령어:
/ibujang approve
  --date "{{date}}"
  --manifest-hash "{{manifest_hash}}"
  --idempotency-key "daily-diff-{{date}}"
```

## 3. Hash + 멱등성 기반 Publish

```python
def gate_publish(manifest: dict, approval_signature: str, 
                  idempotency_key: str) -> dict:
    """
    검증 후 안전한 publish 실행
    - manifest hash 재계산으로 무결성 확인
    - idempotency key로 중복 publish 방지
    """
    # 1. 승인 서명 검증
    if not verify_gate_request(
        json.dumps(manifest, sort_keys=True), 
        approval_signature,
        secret=os.environ["IBUJANG_GATE_SECRET"]
    ):
        return {"status": "blocked", "reason": "signature_mismatch"}
    
    # 2. 멱등성 확인
    if check_idempotency(idempotency_key, redis_client):
        return {"status": "duplicate", "reason": "already_published"}
    
    # 3. Publish 실행
    result = execute_publish(manifest)
    
    # 4. Obsidian 기록
    log_to_obsidian(manifest, result, idempotency_key)
    
    return {"status": "published", "manifest_hash": manifest["manifest_hash"]}
```

## 4. Obsidian 기록 형식

```markdown
## Daily Diff Gate Log — {{date}}
- manifest_hash: {{hash}}
- changes: {{count}}개
- approved_by: 이부장
- idempotency_key: {{key}}
- status: published
- ts: {{timestamp}}
```

## 실행 순서

```
1. python daily_diff.py → diff 추출
2. Discord에 승인 요청 페이로드 전송
3. 이부장 /ibujang approve 실행
4. gate_publish() 호출
5. Obsidian gate_log.md 업데이트
```

## 참고

- 의존: `2026-06-04-dp-todays-plus-triage-policy.md`
- 의존: `2026-06-04-dp-bucky-ibujang-prompt.md`

## 관련 노트
- [[hubs/JH System]]
