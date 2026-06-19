---
title: 웹훅에서 옵시디언으로 안전 전달
date: 2026-05-28
source: daily-plus/2026-05-28.md (Card 1)
priority: P1
category: knowledge
status: distilled
tags:
- webhook
- obsidian
- hmac
- idempotency
- bridge
- daily-plus
- knowledge
graph_cluster: daily-practice
---

# 웹훅에서 옵시디언으로 안전 전달

> ChatGPT Pulse 2026-05-28 Card 1 증류 (P1 · knowledge)

## 목적
외부 에이전트→옵시디언 볼트로 노트를 안전하게 밀어넣는 초경량 웹훅 브리지 설계. HMAC+타임스탬프 서명 검증, 멱등성, 원자적 파일쓰기(tmp→mv) 3원칙. 데이터 손실 없이 외부 소스에서 Obsidian으로 안전한 데이터 흡수를 보장.

## 핵심 내용
- **서명 검증 구조**:
  ```python
  import hmac, hashlib, time
  def verify(payload: bytes, sig: str, secret: str, ts: int) -> bool:
      if abs(time.time() - ts) > 300:  # 5분 창
          return False
      expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
      return hmac.compare_digest(expected, sig)
  ```
- **idempotency_key 처리**: Redis 또는 SQLite로 24시간 키 보관, 중복 요청 409 반환
- **원자적 파일쓰기**:
  ```python
  import tempfile, shutil, pathlib
  def atomic_write(path: pathlib.Path, content: str):
      tmp = path.with_suffix('.tmp')
      tmp.write_text(content, encoding='utf-8')
      shutil.move(str(tmp), str(path))
  ```
- **큐 보관 방식**: 검증 실패 시 `failed_queue/` 폴더에 보관, 재시도 가능하게

## 구현 체크리스트
- [ ] HMAC 서명 검증 미들웨어 구현
- [ ] idempotency_key 저장소 선택 (Redis/SQLite) 및 TTL 설정
- [ ] atomic_write 함수 작성 및 단위 테스트
- [ ] 실패 큐 폴더 구조 및 재시도 메커니즘 구현
- [ ] 브리지 서버 엔드포인트 (`POST /ingest`) 구현

## 관련 컨텍스트
- Git 마크다운 이력: `2026-05-28-dp-markdown-git-history.md`
- 버키 최소 명령 페이로드: `2026-05-27-dp-bucky-min-command-payload.md`
- 배포 전 1분 검증 체크: `2026-05-27-dp-deploy-1min-verify.md`

## 관련 노트
- [[hubs/JH System]]
