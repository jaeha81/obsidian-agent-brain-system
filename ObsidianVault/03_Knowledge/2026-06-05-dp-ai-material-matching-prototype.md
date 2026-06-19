---
title: AI 자재 매칭 1일 프로토타입
date: 2026-06-05
source: daily-plus/2026-06-05.md (Card 8)
priority: P1
category: knowledge
status: distilled
tags:
- ai
- material-matching
- clip
- ocr
- interior
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# AI 자재 매칭 1일 프로토타입

> ChatGPT Pulse 2026-06-05 Card 8 증류 (P1 · knowledge-candidate)

## 목적

현장 사진 한 장으로 비슷한 마감재를 즉시 찾아주는 초간단 프로토타입. OCR로 라벨 텍스트 추출→CLIP 임베딩으로 유사 마감재 검색→웹 미니 UI 결과.

## 기술 스택

| 레이어 | 기술 | 역할 |
|-------|-----|-----|
| OCR | Tesseract / GPT-4o Vision | 제품 라벨, 규격 텍스트 추출 |
| 임베딩 | OpenAI CLIP / clip-ViT-B/32 | 이미지 → 벡터 변환 |
| 벡터 검색 | FAISS / ChromaDB | 유사 마감재 검색 |
| 백엔드 | FastAPI | 이미지 수신 + 결과 반환 |
| 프론트엔드 | 단일 HTML 페이지 | 사진 업로드 + 결과 표시 |

## 1일 구현 순서

### 오전 (3~4시간) — 백엔드 + 임베딩

```python
# 1. CLIP 모델 로드
from transformers import CLIPModel, CLIPProcessor
import torch

model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32")
processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")

# 2. 이미지 임베딩
def embed_image(image_path: str) -> list:
    image = load_image(image_path)
    inputs = processor(images=image, return_tensors="pt")
    with torch.no_grad():
        features = model.get_image_features(**inputs)
    return features.squeeze().tolist()

# 3. FastAPI 엔드포인트
@app.post("/match")
async def match_material(file: UploadFile):
    embedding = embed_image(file)
    results = vector_db.search(embedding, top_k=5)
    return {"matches": results}
```

### 오후 (3~4시간) — 데이터 준비 + UI

- 샘플 마감재 이미지 20~50장 수집 (타일, 페인트, 목재 등)
- 각 이미지 임베딩 → FAISS 인덱스 구축
- 단일 HTML 업로드 폼 + 결과 카드 표시

## 데이터 준비

**최소 데이터셋**:
```
materials/
  tiles/       ← 타일류 이미지 10장
  paint/       ← 페인트 색상 칩 10장
  wood/        ← 목재 마감재 10장
  stone/       ← 석재류 10장
  metadata.json ← SKU, 브랜드, 가격, 규격
```

**metadata.json 스키마**:
```json
{
  "id": "TL-001",
  "name": "대리석 타일 600x600",
  "sku": "MAT-TL-001",
  "price_per_m2": 45000,
  "brand": "이건산업",
  "finish": "polished"
}
```

## MVP 범위 (Day 1 한정)

**포함**:
- 이미지 업로드 (JPG/PNG, 최대 5MB)
- CLIP 임베딩 + FAISS 검색
- 상위 5개 유사 마감재 표시 (이미지 + 이름 + 가격)

**제외** (이후 확장):
- OCR 라벨 추출 (Day 2)
- 사용자 피드백 학습 (별도)
- 견적 자동 연동 (별도)

## 관련 컨텍스트

- [[cad-estimate-4day-test-plan]], [[estimator-csv-standardization-kit]]
- 인테리어 현장 자동화 파이프라인의 자재 인식 모듈
