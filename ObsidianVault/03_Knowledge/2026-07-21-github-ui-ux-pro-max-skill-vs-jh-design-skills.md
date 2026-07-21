---
type: knowledge
project: design-tooling
source: https://github.com/nextlevelbuilder/ui-ux-pro-max-skill
agent: Claude Code
status: done
created: 2026-07-21
tags:
  - design
  - skill-comparison
  - ai_automation
next_action: "사용자 승인 시 uipro CLI 설치 검토"
---

# ui-ux-pro-max-skill vs 기존 JH 디자인 스킬 비교

## 결론 먼저

`ui-ux-pro-max-skill`은 기존 JH 디자인 스킬(`soft-skill`, `taste-skill`, `gpt-tasteskill`, `stitch-skill`, `minimalist-skill`, `brutalist-skill`, `redesign-skill`)을 **대체하지 않는다**. 서로 다른 레이어를 담당하므로 **결정 레이어(decision layer) + 실행 레이어(execution layer)** 조합으로 보완 사용을 권고한다.

| 레이어 | 담당 스킬 | 하는 일 |
|---|---|---|
| **결정** (어떤 스타일을 쓸지) | `ui-ux-pro-max-skill` (미설치) | 산업/제품 유형 입력 → BM25 검색으로 84개 스타일·192개 팔레트·74개 폰트조합·34개 랜딩패턴·22개 기술스택 중 매칭값 자동 추천 |
| **실행** (그 스타일을 어떻게 코딩할지) | `soft-skill`, `gpt-tasteskill`, `stitch-skill`, `minimalist-skill`, `brutalist-skill` | 선택된 스타일 하나를 픽셀·모션·컴포넌트 단위로 극한까지 구현 (더블베젤, 매그네틱 버튼, GSAP 스크럽, 스프링 물리 등) |
| **감사/업그레이드** | `redesign-skill` | 이미 존재하는 화면을 감지·진단·개선 (ui-ux-pro-max-skill엔 이 워크플로우 없음) |
| **역변환** (이미지→코드) | `jh-design-to-code-handoff`, `image-to-code-skill` | Figma/스크린샷을 코드로. ui-ux-pro-max-skill은 반대 방향(무에서 생성)만 다룸 |

## 구조적 차이

기존 JH 스킬들(soft/taste/gpt-taste/stitch/minimalist/brutalist)은 전부 **하나의 확정된 미학을 프롬프트로 강제하는 markdown 지침**이다. 스타일 선택은 사람(또는 스킬 트리거 키워드)이 미리 정해서 호출해야 한다 — "이 프로젝트엔 minimalist-skill을 쓸지 brutalist-skill을 쓸지"는 스킬 밖에서 판단된다.

`ui-ux-pro-max-skill`은 반대로 **"어떤 스타일을 골라야 하는가"를 자동화하는 추론 엔진**이다. npm CLI(`ui-ux-pro-max-cli`)로 실제 코드/JSON 데이터(161개 산업별 규칙, BM25 검색)를 실행해 산업 설명 하나로 패턴+스타일+컬러+타이포+이펙트+안티패턴+체크리스트 전체 세트를 뽑아준다. 순수 프롬프트가 아니라 실행 가능한 도구다.

## 기능 비교표

| 기능 | ui-ux-pro-max-skill | 기존 JH 스킬 |
|---|---|---|
| 산업별 자동 스타일 추천 | ✅ (161개 규칙 엔진) | ❌ 없음 — 사람이 스킬 선택 |
| 실행 방식 | npm CLI + JSON 데이터 (BM25 검색) | markdown 프롬프트 지침 |
| 모션/마이크로인터랙션 코딩 디테일 | 낮음 (권장 이펙트 목록 수준) | 매우 높음 (soft-skill의 더블베젤·매그네틱 버튼·스프링 물리, gpt-tasteskill의 GSAP 스크럽 등) |
| 대상 플랫폼 | 22개 스택 — React/Vue/Svelte 외에 SwiftUI/Flutter/Jetpack Compose/WPF/UWP/JavaFX 등 **네이티브 포함** | 웹(React/Tailwind/HTML) 전용 |
| 차트/대시보드 타입 추천 | 25개 차트 타입 내장 | 없음 (`dataviz` 스킬이 별도로 존재, 겹치지 않음) |
| 기존 화면 감사/업그레이드 | ❌ | ✅ (`redesign-skill`) |
| 브랜드 아이덴티티/로고 | 프리미엄(유료) 티어에서만 | JH `brandkit` 스킬이 이미 별도 커버 |
| 라이선스/설치 | 오픈소스 기본판 + 프리미엄 업셀, npm 전역 설치 필요 | 로컬 markdown, 설치 불필요 |

## 반영 사항 (Vault 업데이트)

- `06_Context_Packs/bucky-design-improvement-policy.md`의 "연계 스킬" 표에 `ui-ux-pro-max-skill` 행 추가 (미설치 상태 명시, 이 노트로 링크).
- 신규 프로젝트에서 **산업/타겟이 불명확한 초기 단계**(예: "인테리어 회사 랜딩페이지 만들어줘" 처럼 스타일 지정 없이 들어오는 요청)에는 ui-ux-pro-max-skill을 결정 레이어로 먼저 쓰고, 나온 추천 스타일에 맞는 실행 스킬(soft/minimalist/brutalist 등)로 넘기는 2단계 흐름을 권고. 스타일이 이미 정해진 요청(예: "미니멀하게", "브루탈리즘으로")은 기존처럼 실행 스킬 바로 호출.

## 설치 여부 — 사용자 승인 대기

`uipro init --ai claude`는 전역 npm 패키지 설치 + 프로젝트 파일 생성(스킬 등록)을 수반하는 환경 변경 작업이라 이번 세션에서 실행하지 않았다. 승인 시:
```bash
npm install -g ui-ux-pro-max-cli
uipro init --ai claude
```
또는 Claude Code 플러그인 마켓플레이스 경유:
```
/plugin marketplace add nextlevelbuilder/ui-ux-pro-max-skill
/plugin install ui-ux-pro-max@ui-ux-pro-max-skill
```

[[bucky-design-improvement-policy]]
