---
title: 세 단계 미리보기 경로
date: 2026-05-31
source: daily-plus/2026-05-31.md (Card 7)
priority: P1
category: knowledge
status: distilled
tags:
- preview
- deployment
- static
- docker
- edge
- daily-plus
- knowledge
- source/today_plus
- type/reference
graph_cluster: daily-practice
---

# 세 단계 미리보기 경로

> ChatGPT Pulse 2026-05-31 Card 7 증류 (P1 · knowledge-candidate)

## 목적

코드 변경사항을 미리보기 환경으로 확인하는 3가지 실전 패턴. 정적 프리뷰(SPA/정적 사이트), Docker 기반, 엣지/CDN 배포 방식을 비교한다.

## 3가지 패턴 비교표

| 항목 | 패턴 1: 정적 프리뷰 | 패턴 2: Docker 기반 | 패턴 3: 엣지/CDN |
|------|-----------------|----------------|--------------|
| 복잡도 | 낮음 | 중간 | 낮음~중간 |
| 비용 | 무료~저가 | 중간 | 저가 |
| 속도 | 빠름 (1~2분) | 중간 (3~8분) | 빠름 (1~3분) |
| 서버 필요 | 불필요 | 필요 | 불필요 |
| 동적 기능 | 제한적 | 완전 지원 | Serverless 지원 |
| 적합 프로젝트 | SPA, 정적 문서 | 풀스택 앱 | 글로벌 정적+함수 |

## 패턴 1: 정적 프리뷰 (Vercel/Netlify)

```yaml
# .github/workflows/preview.yml
on:
  pull_request:
jobs:
  preview:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build
      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.ORG_ID }}
          vercel-project-id: ${{ secrets.PROJECT_ID }}
```

## 패턴 2: Docker 기반

```dockerfile
# Dockerfile.preview
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

```bash
# PR 번호별 컨테이너 실행
docker build -t preview-pr-$PR_NUMBER -f Dockerfile.preview .
docker run -d -p $((3000+PR_NUMBER)):3000 --name preview-$PR_NUMBER preview-pr-$PR_NUMBER
```

## 패턴 3: 엣지/CDN (Cloudflare Pages)

```yaml
# wrangler.toml
name = "my-app-preview"
pages_build_output_dir = "dist"

[env.preview]
  vars = { ENVIRONMENT = "preview" }
```

```bash
# Cloudflare Pages 배포
npx wrangler pages deploy dist --project-name=my-app --branch=pr-$PR_NUMBER
```

## 프로젝트별 선택 기준

```
마케팅 사이트 / 문서 → 패턴 1 (정적)
풀스택 앱 (DB 필요) → 패턴 2 (Docker)
글로벌 SaaS / 엣지 함수 → 패턴 3 (엣지)
```

## 관련 컨텍스트

- [[2026-05-31-dp-bucky-trigger-smoke-hook]] — 스모크 테스트 후 프리뷰 URL 첨부
- [[2026-05-31-dp-decision-first-manifest]] — 배포 결정 매니페스트
