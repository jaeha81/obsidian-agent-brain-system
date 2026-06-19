---
title: 2026년 한국어 TTS 요금 비교
date: 2026-06-07
source: daily-plus/2026-06-07.md (Card 9)
priority: P2
category: knowledge
status: distilled
tags:
- tts
- korean
- pricing
- google-cloud
- clova
- openai
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 2026년 한국어 TTS 요금 비교

> ChatGPT Pulse 2026-06-07 Card 9 증류 (P2 · knowledge-candidate)

## 목적

2026년 기준 한국어 TTS 서비스 요금을 비교해 PoC 및 상용 서비스 선택 기준을 제공한다.

## 서비스별 요금 비교표

| 서비스 | 무료 한도 | 요금 | 한국어 품질 | 비고 |
|--------|-----------|------|------------|------|
| Google Cloud TTS | 월 100만 자 (WaveNet 기준 100만) | $16/100만 자 (WaveNet) | 상 | Studio 음성 별도 요금 |
| CLOVA Speech (NAVER) | 무료 티어 제한적 | 별도 문의 / 사용량 기반 | 최상 | 한국어 특화, 기업용 |
| OpenAI TTS | 없음 | $15/100만 자 | 중상 | 한국어 accent 있음 |
| ElevenLabs | 월 10,000자 | $5~/월 (구독) | 중상 | 감정 표현 강점 |
| Azure TTS | 월 50만 자 (표준) | $4/100만 자 | 상 | Neural 음성 지원 |

## 무료 한도 요약

- **Google Cloud TTS**: Standard 음성 월 400만 자 무료, WaveNet/Studio는 별도
- **Azure TTS**: 표준 음성 월 50만 자, Neural 음성 월 50만 자 (첫 12개월)
- **ElevenLabs**: 월 10,000자 (약 10분 분량)
- **OpenAI TTS**: 무료 한도 없음, 즉시 과금

## PoC 설계 시 선택 기준

| 상황 | 추천 서비스 |
|------|------------|
| 빠른 프로토타입 | Google Cloud TTS (무료 한도 크고 문서 풍부) |
| 최고 한국어 품질 | CLOVA Speech |
| 감정/자연스러운 음성 | ElevenLabs |
| 비용 최소화 | Azure TTS (첫 12개월 무료 한도 활용) |

## 비용 계산 예시

일일 현장 보고 5개 × 평균 500자 = 2,500자/일
월 75,000자 → Google Cloud WaveNet 기준 $1.2/월

## 관련 컨텍스트

- [[samsung-tablet-voice-setup]]
- [[privacy-first-stt-ops]]
- TTS + STT 통합 파이프라인은 비용 합산 계획 필요
