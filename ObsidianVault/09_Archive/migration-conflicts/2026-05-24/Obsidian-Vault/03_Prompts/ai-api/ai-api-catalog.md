---
type: reference
source: claude
project: 통합 AI 시스템
system: OBSIDIAN-SECOND
status: active
priority: P1
date: 2026-04-29
tags: [ai-api, catalog, routing, costs]
summary: 신규 프로젝트 시 AI API 선정 기준이 되는 카탈로그. /jh-ai-api-router 스킬과 함께 사용.
related: [04_Prompts/ai-api-routing-architect.md, skills/jh-ai-api-router]
last_review: 2026-04-29
---

# AI API 카탈로그

> **운영 원칙:** 이 카탈로그는 시작점일 뿐이다. **각 API의 무료 한도와 가격은 공식 문서로 매번 재확인**해야 한다 (라우팅 아키텍트 §12 금지사항). 이 파일은 후보 발굴용이며 최종 결정 근거가 아니다.
>
> **갱신 주기:** 분기 1회 + 새 API 도입 시 즉시. `last_review` 필드를 함께 갱신.

---

## 1. 일반 LLM (챗봇·요약·분류)

| API | 무료 한도 (재확인 필수) | 한국어 | 강점 | 주의 |
|-----|---|---|------|------|
| **Google Gemini** | 분당 호출 제한 있는 무료 티어 | ★★★★ | 멀티모달, 1M 컨텍스트, 가격 경쟁력 | 안전 필터 강함, 일부 도메인 거부 |
| **Groq** | 일일 무료 토큰 (변동) | ★★★ | 압도적 추론 속도 (Llama, Mixtral) | 모델 라인업 OSS 위주 |
| **OpenRouter** | 일부 모델 무료 | ★★★~★★★★ | 100+ 모델 단일 게이트웨이 | 유료 모델은 마진 가산 |
| **Mistral** | 무료 티어 / 무료 크레딧 | ★★★ | EU 데이터 거버넌스, 코드 최적화 | 한국어 약점 영역 있음 |
| **Cloudflare Workers AI** | 일일 호출 무료 | ★★ | 워커와 통합 (서버리스), 저비용 | 모델 풀 작음 |
| **Hugging Face Inference** | 무료 추론 (속도 제한) | ★~★★★ | OSS 모델 다양성, 자체호스팅 옵션 | 콜드 스타트, 안정성 변동 |

**선정 기준 우선순위:** 한국어 품질 > 응답 속도 > 무료 한도 > 모델 교체 가능성.

**디폴트 추천:**
- 메인: Gemini (한국어+멀티모달+컨텍스트)
- 백업: Groq (속도 보강) 또는 OpenRouter (모델 폴백)

---

## 2. 임베딩 / RAG / 세컨드 브레인 검색

| API | 무료 한도 | 한국어 | 차원 | 비고 |
|-----|---|---|---|------|
| **Jina Embeddings** | 토큰 무료 한도 | ★★★ | 768/1024 | 다국어, 빠름 |
| **Cohere Embed/Rerank** | 무료 티어 | ★★★ | 1024 | rerank 결합 시 정확도 ↑ |
| **Gemini Embedding** | Gemini 키 공유 | ★★★ | 768 | LLM과 같은 인증 |
| **HuggingFace 임베딩** | 무료 추론 | ★~★★★ | 모델별 | 자체 호스팅 가능 |
| **OpenAI Embedding** | 유료만 | ★★★ | 1536/3072 | 호환성 표준이지만 비쌈 |

**디폴트 추천:** Jina (한국어+무료) + Cohere Rerank (정확도). 데이터 ≥ 5만 청크라면 Pinecone/Qdrant 등 별도 벡터DB 필수.

---

## 3. 비전 / 이미지 이해 / 공간 분석

| API | 무료 한도 | 한국어 (캡션) | 강점 | 비고 |
|-----|---|---|------|------|
| **Gemini Vision** | Gemini 무료 한도에 포함 | ★★★ | 이미지 추론, 다중 이미지 | 메인 추천 |
| **OpenAI Vision (GPT-4o)** | 유료 | ★★★ | 추론 품질 | 비용 높음 |
| **Replicate Vision** | 시간당 크레딧 | ★★ | OSS 모델 (LLaVA 등) | 콜드 스타트 |
| **Cloudflare Workers AI Vision** | 일일 무료 | ★★ | 엣지 실행 | 모델 풀 작음 |

---

## 4. 이미지 생성 / 디자인

| API | 무료 한도 | 상업적 사용 | 강점 | 워터마크 |
|-----|---|---|------|---------|
| **Stability AI** | 무료 크레딧 | 라이선스 확인 필요 | SDXL/Stable Cascade | 없음 (보통) |
| **Replicate** | 시간당 크레딧 | 모델별 라이선스 | FLUX, Ideogram 등 | 모델별 |
| **fal.ai** | 무료 호출 | 라이선스 확인 | FLUX 빠름, 영상 일부 | 모델별 |
| **HuggingFace Spaces** | 변동 | 모델별 | 실험·MVP에 적합 | 모델별 |

**주의:** 상업 프로젝트는 **모델 라이선스 + 학습 데이터 출처**를 별도 검토. 인물 이미지는 동의·초상권 별도.

---

## 5. 음성 인식 (회의록·현장 기록)

| API | 무료 한도 | 한국어 인식률 | 비고 |
|-----|---|---|------|
| **AssemblyAI** | 무료 크레딧 | ★★★★ | 화자 분리, 요약 부가 기능 |
| **Deepgram** | 무료 크레딧 | ★★★ | 실시간 스트리밍 강점 |
| **Google Speech-to-Text** | 월 무료 분량 | ★★★★ | 안정적 |
| **OpenAI Whisper API** | 유료만 | ★★★★ | 정확도 표준 |
| **HuggingFace Whisper** | 무료 추론 | ★★★ | 자체 호스팅 옵션 |

---

## 6. 음성 합성 (TTS)

| API | 무료 한도 | 한국어 자연도 | 상업 사용 |
|-----|---|---|---------|
| **ElevenLabs** | 월 한도 (변동) | ★★★ | 플랜별 명시 |
| **Google TTS** | 월 무료 분량 | ★★★ | 가능 |
| **Azure TTS** | 무료 시간 | ★★★★ | 가능 (라이선스 확인) |
| **PlayHT** | 무료 크레딧 | ★★ | 플랜별 |
| **HuggingFace TTS** | 무료 추론 | ★~★★ | 모델별 |

---

## 7. OCR / 견적서 / 시방서 / 영수증

| API | 무료 한도 | 한글 인식률 | 표 인식 |
|-----|---|---|---------|
| **Naver CLOVA OCR** | 무료 호출 한도 | ★★★★★ | 양호 |
| **Upstage Document AI** | 무료 한도 | ★★★★ | 우수 (한국어 표) |
| **Google Vision OCR** | 월 무료 분량 | ★★★★ | 양호 |
| **Azure Document Intelligence** | 무료 시간 | ★★★ | 우수 (양식·표) |
| **Tesseract** | 오픈소스 | ★★ | 약함 |

**견적·시방서 등 한국어 도메인:** CLOVA OCR + Upstage 조합이 강력.

---

## 8. 자동화 연동 / 백엔드 게이트웨이

| 도구 | 무료 한도 | API Key 보호 | 강점 |
|------|---|---|------|
| **Make.com** | 월 무료 시나리오 | ✓ (시크릿 매니저) | 노코드 워크플로우 |
| **n8n** | 자체 호스팅 무료 | ✓ | 자체 호스팅, 강력 |
| **Cloudflare Workers** | 일일 무료 호출 | ✓ (env vars) | 엣지, 빠름 |
| **Supabase Edge Functions** | 무료 한도 | ✓ | DB 통합 |
| **Google Apps Script** | 사용자 일일 한도 | ✓ | Google Workspace 연동 |
| **FastAPI 자체 호스팅** | 인프라 비용만 | ✓ | 풀 컨트롤 |

---

## 비용 통제 체크리스트 (모든 프로젝트 공통)

- [ ] 간단한 분류·요약·태깅은 **저비용/무료 모델** 우선
- [ ] 고성능 모델(GPT-4o, Claude Opus)은 **관리자 승인 또는 유료 사용자 전용**
- [ ] 사용자별 **일일 호출 제한** 설정
- [ ] 동일 요청 **반복 호출 차단** (해시 캐시)
- [ ] 로그에 `modelUsed, requestType, estimatedCost, status` 필수
- [ ] 무료 한도 초과 시 **무한 재시도 금지** (백업 모델로 폴백)
- [ ] 이미지·음성·문서 파일 **저장 기간 명시** + 자동 삭제
- [ ] 외부 API 장애 시 **안전한 사용자 메시지** 반환

---

## 보안 체크리스트

- [ ] API Key는 **백엔드 환경변수만** (프론트 절대 금지)
- [ ] `.env` 는 `.gitignore` 포함 검증
- [ ] 모든 호출 백엔드 프록시 경유
- [ ] 사용자별 인증 + 요청 검증
- [ ] 개인정보·민감정보 처리 시 **별도 검토 + 마스킹**
- [ ] 음성·문서 업로드 시 **파일 크기·타입 제한**

---

## 사용 흐름

1. 신규 프로젝트 시 `/jh-ai-api-router` 스킬 호출
2. 스킬이 본 카탈로그를 읽어 후보 분류
3. 라우팅 아키텍트(`ai-api-routing-architect.md`)의 7가지 역할 순서대로 분석
4. `{프로젝트}/wiki/api-stack.md`에 결과 저장
5. 분기마다 `last_review` 갱신 + 새 API/가격 변동 반영

---

## 참조

- 라우팅 아키텍트 프롬프트: `04_Prompts/ai-api-routing-architect.md`
- 호출 스킬: `~/.claude/skills/jh-ai-api-router/SKILL.md`
- 결과 저장 위치: `{프로젝트}/wiki/api-stack.md`
