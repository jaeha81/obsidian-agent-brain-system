---
type: skill
title: Jh Brain Maintenance
name: jh-brain-maintenance
triggers:
  - brain 점수
  - orphan 줄이기
  - 브레인 유지관리
  - brain score
  - brain health
description: JH Brain 점수 유지 절차. orphan/embed/link/timeline 관리로 brain_score 85+ 유지.
ingested_via: 'mcp:put_page'
ingested_at: '2026-06-22T17:46:48.492Z'
source_kind: 'mcp:put_page'
tags:
  - brain
  - gbrain
  - jh-system
  - maintenance
  - skill
---

# JH Brain Maintenance — Brain 점수 유지 스킬

## 목표 지표
```
brain_score: 85+
orphan_pages: 100 이하
embed_coverage: 95%+
stale_pages: 10 이하
```

## 현황 확인
```
gbrain.get_health()
→ page_count, embed_coverage, orphan_pages, brain_score 확인
```

## Orphan 줄이기 (핵심 작업)
```
gbrain.find_orphans(limit=20)
→ 각 orphan에 관련 허브 wikilink 추가
→ gbrain.add_link(source=orphan, target=hub)
```
허브 우선 연결 순서: 가장 관련성 높은 knowledge-hub → 다음 hub 순

## Embed 커버리지 복구
gbrain embed가 97% 미만이면:
```
터미널: gbrain embed --stale
→ missing embedding 일괄 처리
```

## Timeline 보강
```
gbrain.get_timeline() → 빈 날짜 확인
gbrain.add_timeline_entry(slug="<페이지>", date="<날짜>", summary="<요약>")
```

## 주기
- 매주 1회: get_health → orphan top 20 처리
- brain_score < 80: 즉시 긴급 점검

## 금지
- 허브 없이 orphan 방치 (score 저하)
- embed 100% 미만인 채 대규모 import (검색 품질 저하)
