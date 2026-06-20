---
title: GitHub API 레이트리밋과 보관 정책
date: 2026-05-31
source: daily-plus/2026-05-31.md (Card 4)
priority: P1
category: knowledge
status: distilled
tags:
- github-api
- rate-limit
- automation
- quota
- caching
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# GitHub API 레이트리밋과 보관 정책

> ChatGPT Pulse 2026-05-31 Card 4 증류 (P1 · knowledge-candidate)

## 목적

GitHub API 요청 한도와 엔드포인트 활용 방식, 효율적인 운영/자동화 설계. Rate limit 회피 전략과 실패 시 재시도 정책.

## Rate limit 수치

| 인증 방식 | 요청 한도 | 시간 윈도우 |
|----------|---------|-----------|
| 미인증 | 60 req | 1시간 |
| PAT (Personal Access Token) | 5,000 req | 1시간 |
| GitHub App (installation token) | 5,000 req | 1시간 |
| GitHub App (전체) | 15,000 req | 1시간 |
| Search API | 30 req (미인증) / 30 req (인증) | 1분 |
| GraphQL API | 5,000 포인트 | 1시간 |

## 재시도 로직

```python
import time
import requests
from functools import wraps

def github_request_with_retry(url, headers, max_retries=3):
    for attempt in range(max_retries):
        resp = requests.get(url, headers=headers)

        # Rate limit 초과 처리
        if resp.status_code == 429 or resp.status_code == 403:
            reset_time = int(resp.headers.get("X-RateLimit-Reset", 0))
            wait_sec = max(reset_time - int(time.time()), 1)
            print(f"Rate limited. Waiting {wait_sec}s...")
            time.sleep(min(wait_sec, 60))
            continue

        # 성공
        if resp.status_code == 200:
            return resp.json()

        # 기타 오류 — 지수 백오프
        time.sleep(2 ** attempt)

    raise Exception("Max retries exceeded")
```

## 캐싱 전략

응답 캐시를 사용해 불필요한 API 호출을 줄인다.

```python
import hashlib, json, time
from pathlib import Path

CACHE_DIR = Path(".github_api_cache")
CACHE_TTL = 300  # 5분

def cached_get(url, headers):
    cache_key = hashlib.md5(url.encode()).hexdigest()
    cache_file = CACHE_DIR / f"{cache_key}.json"

    if cache_file.exists():
        data = json.loads(cache_file.read_text())
        if time.time() - data["cached_at"] < CACHE_TTL:
            return data["body"]

    resp = requests.get(url, headers=headers)
    cache_file.write_text(json.dumps({
        "body": resp.json(),
        "cached_at": time.time()
    }))
    return resp.json()
```

## Conditional GET 활용

```python
# ETag 기반 조건부 GET — 변경 없으면 304 반환 (rate limit 미소모)
def conditional_get(url, headers, etag_store: dict):
    if url in etag_store:
        headers["If-None-Match"] = etag_store[url]

    resp = requests.get(url, headers=headers)

    if resp.status_code == 304:
        return None  # 변경 없음

    if "ETag" in resp.headers:
        etag_store[url] = resp.headers["ETag"]

    return resp.json()
```

## 잔여 한도 확인

```bash
curl -H "Authorization: Bearer $GH_TOKEN" \
  https://api.github.com/rate_limit \
  | jq '.resources.core'
```

## 관련 컨텍스트

- [[2026-05-30-dp-change-only-export-runbook]] — 변경 시에만 실행
- [[2026-05-31-dp-decision-first-manifest]] — API 호출 최소화 설계
