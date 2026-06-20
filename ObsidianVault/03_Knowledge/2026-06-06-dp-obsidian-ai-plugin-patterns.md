---
title: 옵시디언 AI 플러그인 패턴
date: 2026-06-06
source: daily-plus/2026-06-06.md (Card 11)
priority: P3
category: knowledge
status: distilled
tags:
- obsidian
- ai-plugin
- local-llm
- embedding
- smart-environment
- daily-plus
- knowledge
- source/today_plus
- type/reference
- area/obsidian_brain
graph_cluster: daily-practice
---

# 옵시디언 AI 플러그인 패턴

> ChatGPT Pulse 2026-06-06 Card 11 증류 (P3 · knowledge-candidate)

## 목적

옵시디언 플러그인이 로컬 임베딩, 구조화된 에이전트 작업, 명확한 권한 경계로 제어 영역으로 진화 중. Smart Environment, Ollama, Copilot 등 활용.

## 주요 플러그인 목록

| 플러그인 | 기능 | 로컬/클라우드 | 추천 용도 |
|--------|-----|------------|---------|
| Smart Connections | 노트 간 시맨틱 검색, 임베딩 | 둘 다 | RAG, 관련 노트 발견 |
| Obsidian Copilot | ChatGPT/Claude 연동 채팅 | 클라우드 | 노트 기반 Q&A |
| Local GPT | Ollama 로컬 LLM 연동 | 로컬 | 오프라인 AI 처리 |
| Text Generator | AI 텍스트 자동 완성 | 클라우드 | 노트 작성 보조 |
| Omnisearch | 전체 텍스트 + 시맨틱 검색 | 로컬 | 빠른 검색 |
| Templater | JS 기반 동적 템플릿 | 로컬 | 에이전트 명령 실행 |

## 로컬 임베딩 설정

### Smart Connections + 로컬 임베딩

```
설정 경로: Smart Connections → Model → Local (Transformers.js)
모델: all-MiniLM-L6-v2 (영어), multilingual-e5-small (한국어)

권장 설정:
- Embed on save: ON
- Max tokens: 512
- Batch size: 10
```

### Ollama 로컬 LLM 연동

```bash
# Ollama 설치 및 모델 다운로드
ollama pull llama3.2
ollama pull nomic-embed-text  # 임베딩 전용

# 옵시디언 Local GPT 플러그인 설정
Host: http://localhost:11434
Model: llama3.2
```

## 권한 경계 설계

AI 플러그인이 볼트 내에서 수행 가능한 작업 범위:

```
읽기 전용 (모든 AI 플러그인):
  - 노트 내용 읽기
  - 임베딩 생성
  - 시맨틱 검색

쓰기 허용 (명시적 설정 필요):
  - 노트 생성: 지정 폴더만 (예: 03_Knowledge/)
  - 노트 편집: 명시적 명령 시에만
  - 태그 추가: 허용

절대 금지:
  - 00_System/ 폴더 수정
  - .obsidian/ 설정 변경
  - 플러그인 자동 설치
  - 외부 API 키 노출
```

## 비공개 RAG 구현

클라우드에 데이터를 보내지 않는 완전 로컬 RAG:

```python
# 1. 로컬 임베딩 (Ollama nomic-embed-text)
import requests

def embed_local(text: str) -> list:
    response = requests.post(
        "http://localhost:11434/api/embeddings",
        json={"model": "nomic-embed-text", "prompt": text}
    )
    return response.json()["embedding"]

# 2. 벡터 저장 (ChromaDB 로컬)
import chromadb

client = chromadb.PersistentClient(path="./vault_embeddings")
collection = client.get_or_create_collection("obsidian_vault")

# 3. 노트 인덱싱
def index_note(note_path: str, content: str):
    embedding = embed_local(content)
    collection.add(
        embeddings=[embedding],
        documents=[content],
        ids=[note_path]
    )

# 4. 검색
def search_vault(query: str, top_k: int = 5) -> list:
    query_embedding = embed_local(query)
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k
    )
    return results["documents"][0]
```

## 에이전트 작업 구조화 패턴

Templater를 사용한 구조화된 에이전트 명령:

```javascript
// Templater: 에이전트 작업 노트 생성 템플릿
<%*
const task = await tp.system.prompt("작업 내용");
const priority = await tp.system.suggester(["P0", "P1", "P2", "P3"], ["P0", "P1", "P2", "P3"]);
const today = tp.date.now("YYYY-MM-DD");

tR += `---
title: ${task}
date: ${today}
priority: ${priority}
status: pending
agent: claude
---

# ${task}

## 목표

## 컨텍스트

## 완료 기준

## 진행 이력
- ${today}: 작업 생성
`;
%>
```

## 관련 컨텍스트

- [[obsidian-backup-restore]] — 플러그인 데이터 백업 포함
- [[rbac-secrets-handoff]] — AI 플러그인 권한 경계
