---
title: 클라우드 코드 플러그인 계획
date: 2026-06-01
source: daily-plus/2026-06-01.md (Card 7)
priority: P1
category: knowledge
status: distilled
tags:
- plugin
- serverless
- deployment
- api-contract
- security
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# 클라우드 코드 플러그인 계획

> Daily Plus Pulse 2026-06-01 Card 7 증류 (P1 · knowledge-candidate)

## 목적

작은 서버사이드 스크립트를 안전하게 배포·운영하는 초간단 플랫폼 3단계 구현 가이드. API 계약 정의→실행 환경→보안·모니터링.

## Phase 1 — API 계약 포맷

```yaml
# plugin-manifest.yaml
name: estimator-normalizer
version: "1.0.0"
runtime: python3.11
entry: handler.py::run
timeout_ms: 5000
memory_mb: 128

inputs:
  - name: csv_raw
    type: string
    required: true
    max_bytes: 1048576  # 1MB
  - name: output_format
    type: enum
    values: ["json", "csv", "xlsx"]
    default: "json"

outputs:
  - name: normalized
    type: object
  - name: warnings
    type: array

auth:
  type: bearer_token
  env_var: PLUGIN_SECRET

rate_limit:
  requests_per_minute: 30
  burst: 10
```

```python
# handler.py
def run(inputs: dict, context: dict) -> dict:
    """플러그인 진입점 — 표준 시그니처 필수"""
    csv_raw = inputs["csv_raw"]
    fmt = inputs.get("output_format", "json")
    # ... 처리 로직
    return {
        "normalized": result,
        "warnings": warnings
    }
```

## Phase 2 — 실행 환경 선택지

| 환경 | 장점 | 단점 | 추천 용도 |
|------|-----|------|--------|
| Vercel Functions | 무료, 빠른 배포 | 10s 타임아웃, 메모리 제한 | 경량 API, 웹훅 |
| Cloudflare Workers | 초저지연, 글로벌 | 런타임 제한 (no Node.js) | 엣지 로직 |
| Railway | 풀 컨테이너, 유연 | 유료 ($5/월~) | 장시간 실행 |
| AWS Lambda | 성숙한 생태계 | 복잡한 설정 | 대용량, 규모화 |

**MVP 추천**: Vercel Functions (무료 + 1분 배포)

```bash
# Vercel 배포
mkdir -p api && cat > api/plugin.py << 'EOF'
from http.server import BaseHTTPRequestHandler
import json

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # 플러그인 핸들러
        body = json.loads(self.rfile.read(int(self.headers['Content-Length'])))
        result = run(body, {})
        self.send_response(200)
        self.end_headers()
        self.wfile.write(json.dumps(result).encode())
EOF
vercel --prod
```

## Phase 3 — 보안 체크리스트

```
인증/인가
  [x] Bearer Token 또는 API Key 필수
  [x] 환경변수로만 시크릿 관리 (하드코딩 금지)
  [x] 요청 서명 검증 (HMAC-SHA256)

입력 검증
  [x] 최대 페이로드 크기 제한 (1MB)
  [x] 입력 타입/범위 유효성 검사
  [x] SQL/Command Injection 방어 (입력 이스케이프)

Rate Limiting
  [x] IP 기반 분당 요청 제한
  [x] 버스트 제한 설정

모니터링
  [x] 모든 요청 구조화 로그 기록
  [x] 오류율 > 5% 시 알림
  [x] 응답시간 P95 추적

배포
  [x] 스테이징 환경 먼저 검증
  [x] 프로덕션 배포 전 smoke test
  [x] 롤백 절차 문서화
```

## MVP 범위

| 포함 | 제외 |
|------|------|
| 단일 플러그인 배포 | 멀티테넌트 |
| Bearer Token 인증 | OAuth/SSO |
| Vercel Functions | 컨테이너 오케스트레이션 |
| 기본 Rate Limiting | 동적 스케일링 |
| 구조화 로그 | 분산 트레이싱 |

## 구현 우선순위

- [ ] `plugin-manifest.yaml` 스키마 정의
- [ ] `handler.py` 표준 진입점 템플릿 작성
- [ ] Vercel Functions 배포 스크립트
- [ ] Bearer Token 미들웨어 구현
- [ ] Rate Limiting 미들웨어 추가

## 관련 컨텍스트

- Bucky 에이전트 플러그인 실행 환경 기반
- [[수익-우선-안전-매니페스트]], [[텔레메트리-롤백-감사-운영서]]
