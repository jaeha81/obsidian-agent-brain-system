---
type: knowledge-note
date: 2026-06-03
source: daily-plus
category: knowledge-candidate
tags:
- area/ai_automation
- status/active
summary: 웹훅과 Vault 쓰기 패턴 — 중복 방지, 변경 시만 쓰기, 웹훅 → Vault 안전 쓰기용 Obsidian 트리아지 노트 형식
status: applied
applied_at: 2026-06-11
graph_cluster: daily-practice
---

# 웹훅과 Vault 쓰기 패턴

## 3원칙

1. **중복 방지** — 동일 이벤트를 Vault에 두 번 쓰지 않는다
2. **변경 시만 쓰기** — 내용이 변경된 경우에만 파일을 갱신한다
3. **트리아지 노트 형식** — 웹훅 데이터는 표준 트리아지 포맷으로 저장한다

## 중복 방지 패턴

```python
VAULT_EVENT_INDEX = "data/vault_event_index.json"

def vault_write_safe(event_id: str, content: str, file_path: str):
    index = load_json(VAULT_EVENT_INDEX)

    # 중복 체크
    if event_id in index:
        return {"status": "skipped", "reason": "duplicate"}

    # 파일 쓰기
    write_file(file_path, content)

    # 인덱스 등록
    index[event_id] = {
        "file_path": file_path,
        "written_at": datetime.now().isoformat()
    }
    save_json(VAULT_EVENT_INDEX, index)
    return {"status": "written", "file_path": file_path}
```

## 변경 시만 쓰기 패턴

```python
import hashlib

def write_only_on_change(file_path: str, new_content: str) -> bool:
    new_hash = hashlib.sha256(new_content.encode()).hexdigest()

    # 기존 파일 해시 확인
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        existing_hash = hashlib.sha256(existing_content.encode()).hexdigest()

        if existing_hash == new_hash:
            return False  # 변경 없음, 쓰기 생략

    # 변경됨 — 쓰기 실행
    write_file(file_path, new_content)
    return True
```

## Obsidian 트리아지 노트 형식

```markdown
---
type: triage-note
source: webhook
event_id: {event_id}
event_type: {event_type}
received_at: {timestamp}
status: pending
---

# 트리아지: {event_type}

## 이벤트 요약
- ID: {event_id}
- 유형: {event_type}
- 수신: {timestamp}

## 페이로드 핵심

{payload_summary}

## 처리 필요 항목

- [ ] 검토 완료
- [ ] 처리 방향 결정 (approve/hold/archive)
```

## 웹훅 → Vault 안전 쓰기 전체 흐름

```
웹훅 수신
  ↓
서명 검증 (HMAC)
  ↓ 실패 → 400, 로그 기록, Vault 쓰기 없음
  ↓ 성공
중복 체크 (event_id)
  ↓ 중복 → 200 반환, Vault 쓰기 없음
  ↓ 신규
변경 감지 (해시 비교)
  ↓ 미변경 → 200 반환, Vault 업데이트 없음
  ↓ 변경됨
트리아지 노트 생성/갱신
  ↓
event_index 업데이트
  ↓
200 반환 + Bucky 알림
```

## 허용 Vault 쓰기 경로

```
ObsidianVault/05_Orders/          # 주문 기록
ObsidianVault/06_Triage/          # 트리아지 노트
ObsidianVault/03_Knowledge/       # 지식 노트 (수동 승인 후)
```

## 금지 사항

- `.env`, API 키, 시크릿을 Vault 파일에 포함하지 않는다
- PII(개인식별정보)는 최소화 (이메일만, 결제 상세 없음)
- 검증 없이 Vault에 직접 쓰지 않는다

## 관련 노트

- [[2026-06-03-dp-ibujang-stripe-webhook]]
- [[2026-06-03-dp-verified-handoff-flow]]
- [[2026-06-03-dp-pulse-manager-manifest]]
