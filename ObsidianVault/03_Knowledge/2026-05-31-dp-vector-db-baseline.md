---
title: 벡터 DB 시작 기준선
date: 2026-05-31
source: daily-plus/2026-05-31.md (Card 10)
priority: P2
category: knowledge
status: distilled
tags:
- vector-db
- rag
- postgres
- pgvector
- embedding
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 벡터 DB 시작 기준선

> ChatGPT Pulse 2026-05-31 Card 10 증류 (P2 · knowledge-candidate)

## 목적

초기에 Postgres + pgvector로 시작하고 병목 시 관리형 벡터 DB로 이전하는 현실적 접근. 초반 데이터·쿼리 패턴이 자주 바뀔 때 최적.

## pgvector 설정 방법

```sql
-- pgvector 확장 설치
CREATE EXTENSION IF NOT EXISTS vector;

-- 임베딩 테이블 생성 (1536차원 = OpenAI text-embedding-3-small)
CREATE TABLE embeddings (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id   TEXT NOT NULL,        -- 원본 문서 ID
    content     TEXT NOT NULL,        -- 원본 텍스트
    embedding   vector(1536),         -- 임베딩 벡터
    metadata    JSONB DEFAULT '{}',
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- 유사도 검색 함수
CREATE OR REPLACE FUNCTION match_embeddings(
    query_embedding vector(1536),
    match_threshold FLOAT DEFAULT 0.75,
    match_count     INT   DEFAULT 5
)
RETURNS TABLE (id UUID, content TEXT, similarity FLOAT) AS $$
BEGIN
    RETURN QUERY
    SELECT e.id, e.content,
           1 - (e.embedding <=> query_embedding) AS similarity
    FROM embeddings e
    WHERE 1 - (e.embedding <=> query_embedding) > match_threshold
    ORDER BY e.embedding <=> query_embedding
    LIMIT match_count;
END;
$$ LANGUAGE plpgsql;
```

## ivfflat vs hnsw 인덱스

| 인덱스 | 구축 속도 | 검색 속도 | 메모리 | 적합 규모 |
|--------|---------|---------|--------|---------|
| ivfflat | 빠름 | 중간 | 적음 | <1M 벡터 |
| hnsw | 느림 | 빠름 | 많음 | >100K 벡터, 정확도 우선 |

```sql
-- ivfflat 인덱스 (초기 권장)
CREATE INDEX ON embeddings USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);  -- sqrt(row_count) 권장

-- hnsw 인덱스 (규모 확장 시)
CREATE INDEX ON embeddings USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

## 이전 시점 판단 기준

pgvector에서 관리형 벡터 DB(Pinecone, Weaviate, Qdrant)로 이전을 고려할 때:

| 신호 | 임계값 | 조치 |
|------|--------|------|
| 벡터 수 | >10M | 관리형 고려 |
| 검색 지연 p99 | >500ms | 인덱스 튜닝 또는 이전 |
| Postgres CPU | >70% 지속 | 분리 필요 |
| 인덱스 구축 시간 | >1시간 | hnsw 또는 이전 |

**원칙**: 10M 벡터 이하, p99 < 500ms라면 pgvector로 충분.

## Python 연동 예시

```python
import psycopg2
import openai

def embed_and_store(text: str, source_id: str, conn):
    # 임베딩 생성
    resp = openai.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    embedding = resp.data[0].embedding

    # 저장
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO embeddings (source_id, content, embedding) VALUES (%s, %s, %s)",
            (source_id, text, embedding)
        )
    conn.commit()
```

## 관련 컨텍스트

- [[2026-05-30-dp-obsidian-agent-bridge]] — 볼트 → 임베딩 파이프라인 연동 가능
- [[2026-05-31-dp-github-api-rate-limit]] — API 호출 최적화와 함께 고려
