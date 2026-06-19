---
title: 버키용 옵시디언 YAML 표준
date: 2026-05-30
source: daily-plus/2026-05-30.md (Card 6)
priority: P1
category: knowledge
status: distilled
tags:
- yaml
- obsidian
- frontmatter
- jcs
- sha256
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 버키용 옵시디언 YAML 표준

> ChatGPT Pulse 2026-05-30 Card 6 증류 (P1 · knowledge-candidate)

## 목적

노트/명세를 에이전트가 안전하게 읽고 쓸 수 있는 표준 프런트매터. 짧은 키만 사용하고 JCS+SHA-256 검증을 강제한다.

## 최소 키 스키마

```yaml
---
id: "note-uuid-v4"          # 불변 고유 ID
title: "노트 제목"           # 사람이 읽는 제목
tags:                        # 소문자, 하이픈 구분
  - tag1
  - tag2
cat: knowledge               # 카테고리: knowledge | task | project | system
lc: "2026-05-30T09:00:00Z"  # last_confirmed — 에이전트가 마지막으로 검토한 시각
rflag: false                 # review_flag — 검토 필요 여부
created: "2026-05-30"
updated: "2026-05-30"
sha256: "abc123..."          # JCS 정규화 후 SHA-256 (아래 계산법 참고)
---
```

## 필드 규칙

| 키 | 타입 | 규칙 |
|----|------|------|
| id | string | UUID v4, 생성 후 변경 금지 |
| title | string | 50자 이하 권장 |
| tags | list | 소문자, 하이픈, 영문 또는 한글 허용 |
| cat | enum | knowledge / task / project / system |
| lc | ISO8601 | 에이전트 검토 시 자동 업데이트 |
| rflag | bool | 사람 또는 에이전트가 true 설정 시 검토 대기열 진입 |
| sha256 | string | 노트 본문 변경 시 재계산 필수 |

## JCS 정규화 방법

JCS(JSON Canonicalization Scheme, RFC 8785) 규칙:
1. YAML 프런트매터를 JSON으로 변환 (`sha256` 필드 제외)
2. 키를 UTF-8 코드포인트 기준 오름차순 정렬
3. 공백 없이 직렬화

```python
import json, hashlib

def compute_sha256(frontmatter: dict) -> str:
    payload = {k: v for k, v in frontmatter.items() if k != "sha256"}
    canonical = json.dumps(payload, sort_keys=True,
                           ensure_ascii=False, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()
```

## SHA-256 필드 계산법

노트 저장 시:
1. `sha256` 필드를 제거한 YAML 프런트매터 + 본문 전체를 JCS 직렬화
2. SHA-256 해시 계산
3. 결과를 `sha256` 필드에 기록

에이전트 읽기 시:
1. 현재 `sha256` 값 저장
2. 위 과정 재계산
3. 불일치 → `rflag: true` 자동 설정, 감사 로그 기록

## 관련 컨텍스트

- [[2026-05-30-dp-min-plan-package-template]] — 계획 패키지의 서명 방식 동일
- [[2026-05-31-dp-yaml-graph-color-acl]] — YAML 필드 기반 그래프 색상 매핑
