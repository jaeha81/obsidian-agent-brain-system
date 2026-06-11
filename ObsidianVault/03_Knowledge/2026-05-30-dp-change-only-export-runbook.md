---
title: 변경 시에만 내보내는 런북
date: 2026-05-30
source: daily-plus/2026-05-30.md (Card 7)
priority: P1
category: knowledge
status: distilled
tags:
  - pipeline
  - diff
  - efficiency
  - deployment
  - runbook
  - daily-plus
  - knowledge
---

# 변경 시에만 내보내는 런북

> ChatGPT Pulse 2026-05-30 Card 7 증류 (P1 · knowledge-candidate)

## 목적

변경이 실질적으로 의미 있을 때만 파이프라인을 태우는 경량 운영 런북. 타임스탬프/순서만 바뀐 사소한 변화는 스킵하고, 콘텐츠/스키마/단계 수정 시만 실행한다.

## 의미 있는 변경 판단 기준

```yaml
significant_change:
  include:
    - content_hash_changed: true   # 본문 SHA-256 변경
    - schema_version_changed: true # 스키마 버전 업
    - step_count_changed: true     # 파이프라인 단계 수 변경
    - critical_field_changed:      # 핵심 필드 변경
        fields: [goal, target, artifact]
  exclude:
    - timestamp_only: true         # updated/lc 필드만 변경
    - sort_order_only: true        # 배열 순서만 변경
    - whitespace_only: true        # 공백/줄바꿈만 변경
    - comment_only: true           # 주석만 변경
```

## 차이 감지 스크립트

```python
import hashlib, json

def is_significant_change(old: dict, new: dict) -> bool:
    EXCLUDE_KEYS = {"updated", "lc", "sha256", "run_id", "ts"}

    def normalize(d):
        return {k: v for k, v in d.items() if k not in EXCLUDE_KEYS}

    old_hash = hashlib.sha256(
        json.dumps(normalize(old), sort_keys=True).encode()
    ).hexdigest()
    new_hash = hashlib.sha256(
        json.dumps(normalize(new), sort_keys=True).encode()
    ).hexdigest()

    return old_hash != new_hash


# 파이프라인 진입점
def maybe_export(old_data, new_data, pipeline_fn):
    if is_significant_change(old_data, new_data):
        pipeline_fn(new_data)
        log("export triggered — content changed")
    else:
        log("export skipped — no significant change")
```

## 실행 흐름

```
변경 감지
  ↓
is_significant_change() 호출
  ├─ False → 스킵 (로그만 남김)
  └─ True  → 파이프라인 실행
               ↓
             빌드 → 테스트 → 배포
```

## 비용 절감 기대치

- 일반적인 Obsidian 노트 편집의 ~60%는 타임스탬프 또는 메타 필드만 변경
- 이 런북 적용 시 CI 실행 횟수 약 50~60% 감소 예상
- GitHub Actions 기준: 월 2,000분 → 800~1,000분 절감

## 관련 컨텍스트

- [[2026-05-30-dp-obsidian-yaml-standard]] — SHA-256 필드 기반 변경 감지
- [[2026-05-30-dp-min-plan-package-template]] — 계획 패키지 서명
