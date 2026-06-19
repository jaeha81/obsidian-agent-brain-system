---
title: JCS 검증용 1줄 스모크
date: 2026-05-29
source: daily-plus/2026-05-29.md (Card 3)
priority: P1
category: knowledge
status: distilled
tags:
- jcs
- sha256
- verification
- smoke-test
- plan-json
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# JCS 검증용 1줄 스모크

> ChatGPT Pulse 2026-05-29 Card 3 증류 (P1 · knowledge)

## 목적
버키 오케스트레이션용 1줄 검증기. plan.json의 plan 필드가 정규화된 동일 바이트 표현인지 확인하고 SHA-256 해시를 고정 값으로 비교. CI 파이프라인, 소형 디바이스, 수동 검증 모두 같은 1줄 명령으로 처리 가능.

## 핵심 내용
- **JCS(JSON Canonicalization Scheme) 정규화 방법**:
  - 키 알파벳 정렬
  - 공백 제거
  - Unicode 정규화 (NFC)
  - 숫자 정밀도 표준화
  ```python
  import json
  def jcs_normalize(obj) -> bytes:
      return json.dumps(obj, sort_keys=True, separators=(',', ':'),
                        ensure_ascii=False).encode('utf-8')
  ```
- **SHA-256 비교 스크립트 (1줄)**:
  ```bash
  python3 -c "import json,hashlib,sys; d=json.load(open('plan.json')); \
  print(hashlib.sha256(json.dumps(d['plan'],sort_keys=True,separators=(',',':')).encode()).hexdigest())"
  ```
- **CI/소형 디바이스 호환**: Python 표준 라이브러리만 사용, 외부 의존성 없음
- **고정 해시 비교**: 빌드 시 계산된 해시를 `.plan.sha256` 파일에 저장, 검증 시 비교

## 구현 체크리스트
- [ ] jcs_normalize 함수 단위 테스트 작성
- [ ] plan.json 스키마에 `plan_sha256` 필드 추가
- [ ] CI 스텝에 1줄 검증 추가
- [ ] `.plan.sha256` 참조 파일 생성 자동화
- [ ] 소형 디바이스 (Raspberry Pi) 호환 테스트

## 관련 컨텍스트
- Codex·Claude 분리 운영 패턴: `2026-05-28-dp-codex-claude-separation-pattern.md`
- 검증자와 롤백 템플릿: `2026-05-27-dp-verifier-rollback-template.md`
- 버키용 초경량 명령 3종: `2026-05-29-dp-bucky-3-lightweight-commands.md`

## 관련 노트
- [[hubs/JH System]]
