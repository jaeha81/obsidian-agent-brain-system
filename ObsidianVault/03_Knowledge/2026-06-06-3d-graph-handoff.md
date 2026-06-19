---
tags:
- status/done
- area/obsidian
- area/design
created: 2026-06-06
session: 2026-06-06b
graph_cluster: misc
---

# Obsidian 3D Galaxy Graph — 다음 세션 핸드오프

## 문제

현재 `galaxy-graph.css` + `graph.json`은 **2D 그래프뷰**만 변경함.
TikTok @metakaihos "Second cerveau galactique" 영상의 **3D 회전 효과**는 기본 Obsidian 그래프로 구현 불가.

> Obsidian 기본 그래프 = HTML Canvas 2D 렌더링 → 3D 좌표계 없음

## 해결책

**"3D Graph" 커뮤니티 플러그인** (제작: HEmile) 설치 필요.

| 항목 | 값 |
|------|-----|
| 플러그인명 | 3D Graph |
| 제작자 | HEmile |
| 설치 경로 | Obsidian Settings → Community Plugins → Browse → "3D Graph" 검색 |
| GitHub | obsidian-3d-graph |

## 다음 세션 작업 순서

1. **플러그인 설치**
   - Settings → Community Plugins → "제한 모드 해제" (이미 해제돼 있으면 skip)
   - Browse → "3D Graph" → Install → Enable

2. **3D Graph 색상 설정**
   - 플러그인 설정에서 galaxy 색상 적용:
   - 배경: `#04040f`
   - 노드 기본: `#c8d8ff`
   - 엣지(선): `rgba(100, 160, 255, 0.18)`
   - 태그 노드: `#a855f7`

3. **물리 설정 조정** (현재 graph.json 값 참고)
   - repelStrength: 22
   - linkStrength: 0.45
   - linkDistance: 380

4. **기존 2D galaxy-graph.css 유지** — 2D 그래프 뷰 fallback

## 현재 파일 상태

| 파일 | 상태 |
|------|------|
| `.obsidian/snippets/galaxy-graph.css` | 활성화됨 (2D 적용) |
| `.obsidian/appearance.json` | `galaxy-graph` enabled |
| `.obsidian/graph.json` | 우주 물리값 적용 |
| 3D Graph 플러그인 | **미설치** |

## 예상 결과

설치 완료 시: 마우스 드래그로 3D 회전, 우주 심연 배경, 컬러 성단 클러스터 — @metakaihos 영상과 동일.

---

> CL-015 참조 | 다음 세션 시작 시 "CL-015 3D Graph 플러그인 설치" 로 시작

## 관련 허브

- [[vault-galaxy-graph-bridge]] — Galaxy Graph MOC 허브
- [[jh-system]] — JH 시스템 전체
