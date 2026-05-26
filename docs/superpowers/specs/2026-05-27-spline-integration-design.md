# Spline.design 통합 설계 — Bucky 웹사이트 퀄리티 향상

**날짜**: 2026-05-27  
**상태**: 승인됨  
**범위**: 랜딩페이지 템플릿 재설계 + Spline 씬 라이브러리 + 컨펌 대시보드

---

## 목표

Bucky가 생성하는 랜딩페이지의 시각적 퀄리티를 Spline.design 수준으로 끌어올리고, 사용자가 모바일 환경에서 대시보드를 통해 결과물을 컨펌·수정할 수 있는 워크플로를 구축한다.

---

## 전체 아키텍처

```
/pipeline 실행
      ↓
[대시보드 /intent] ← 모바일에서 의도 설정
      ↓
HTML 생성 (새 템플릿) + Spline 씬 자동 선택
      ↓
Vercel Preview 배포 + Playwright 스크린샷
      ↓
Discord 알림 + [대시보드 /review] 링크
      ↓
  ┌───┴──────────────────┐
승인                   수정 요청
  ↓                       ↓
프로덕션 배포         [대시보드 /scene] or 재생성
                           ↓
                    Discord 재알림 (반복)
```

---

## Phase 1 — 템플릿 재설계

### 디자인 시스템 (Spline.design 벤치마킹)

| 항목 | 현재 | 새 설계 |
|------|------|---------|
| 배경 | `#0f0f23` 단색 | `#000000` + subtle noise texture |
| 액센트 | indigo 단색 | `#9b59ff → #ff6b6b` 그라디언트 |
| 타이포 | 시스템 폰트 | Inter (Google Fonts CDN) |
| 카드 | solid border | glassmorphism (`backdrop-blur`) |
| 히어로 높이 | 60vh | 100vh fullscreen |
| 애니메이션 | 없음 | AOS.js scroll fade-in |

### 히어로 레이아웃

```
┌─────────────────────────────────────┐
│  [Spline 3D 씬 — 전체 배경]         │  100vh
│                                     │
│  ┌─── 텍스트 오버레이 (중앙) ──┐   │
│  │  헤드라인 (Inter 700)        │   │
│  │  서브타이틀                   │   │
│  │  [CTA 버튼]                  │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

### Spline 임베드 방식

```html
<!-- <spline-viewer> 웹 컴포넌트 (빌드 불필요) -->
<script type="module" src="https://unpkg.com/@splinetool/viewer/build/spline-viewer.js"></script>
<spline-viewer url="{{SPLINE_URL}}"></spline-viewer>

<!-- WebGL 미지원 폴백 -->
<div class="spline-fallback"></div>
```

템플릿 변수:
- `{{SPLINE_URL}}` — 선택된 씬 URL
- `{{SPLINE_HINT}}` — `"none"` 이면 CSS 그라디언트로 대체

---

## Phase 2 — Spline 씬 라이브러리

### 카탈로그 구조 (`data/spline_catalog.json`)

```json
{
  "scenes": [
    {
      "id": "abstract-sphere-01",
      "url": "https://prod.spline.design/xxxx/scene.splinecode",
      "thumbnail": "https://...",
      "category": ["ai", "saas", "devtool"],
      "mood": ["tech", "minimal"],
      "bg_compatible": true
    }
  ],
  "fallback_scene": "abstract-default-01"
}
```

초기 큐레이션 목표: 20개 (Spline Community 공개 씬)

### 카테고리 매핑

| GitHub 특성 | 카테고리 |
|------------|---------|
| Python + ML 키워드 | `ai` |
| TypeScript / React | `saas`, `devtool` |
| Game / Unity | `game` |
| 설명문 감성 분석 결과 | `mood` |

### 씬 선택 로직 (`select_spline_scene()`)

```
1. GitHub 메타 → 카테고리 판별 (언어 + 토픽 키워드)
2. 카탈로그 필터링 (카테고리 일치)
3. mood 점수 계산 (가중치 적용)
   - 레포 제목 키워드    × 1.5
   - 레포 설명 키워드    × 1.0
   - GitHub 토픽 태그   × 0.8
   - 주 사용 언어        × 0.5
4. 최고 점수 씬 선택
```

### 폴백 체인

```
매칭 씬 있음 → Spline 임베드
      ↓ 없음
카테고리 기본 씬
      ↓ 없음
범용 abstract 씬 (항상 존재 보장)
      ↓ URL 오류
순수 CSS 애니메이션 그라디언트
```

### URL 유효성 체크

카탈로그 로드 시 HEAD 요청으로 생존 여부 확인. 죽은 씬 자동 건너뜀.

### 모바일 폴백

```css
@media (max-width: 768px) {
  spline-viewer { display: none; }
  .spline-fallback { display: block; /* CSS 그라디언트 */ }
}
```

---

## 컨펌 대시보드 — 3개 분리

**공통 스택**: Next.js App Router + Tailwind CSS + Vercel 배포  
**공통 원칙**: 모바일 퍼스트 (375px 기준), job_id URL 파라미터 인증, 컨펌/수정 → Discord Webhook 자동 알림

### 대시보드 1 — `/intent` 의도 설정

- `/pipeline` 실행 즉시 Discord에 이 URL 전송
- 수집 항목: 페이지 목적 (제품홍보/포트폴리오/수익화/오픈소스) + 분위기 (미니멀/다이나믹)
- 30초 타임아웃 → 기본값(제품홍보)으로 자동 진행
- 제출 시 Bucky에 Webhook으로 전달 → 생성 시작

### 대시보드 2 — `/review` 미리보기·컨펌

- 생성 완료 후 Discord 알림 + 이 URL 전송
- iframe으로 실제 Preview 페이지 표시 + 전체화면 링크
- 수정 요청 체크박스: CTA 문구 / 색상 / 섹션 순서 / 직접 입력
- [✅ 프로덕션 배포] / [🔄 재생성] 버튼

### 대시보드 3 — `/scene` Spline 씬 선택

- `/review`에서 "씬 변경" 선택 시 접근
- 카테고리 필터 + 썸네일 그리드
- 씬 선택 → 즉시 미리보기 반영 → [적용] 버튼

### Discord 역할 재정의

Discord = **알림·트리거 전용**, 모든 컨펌 인터랙션은 대시보드에서 처리

```
Discord 송신:  /pipeline 실행 → /intent 링크
               생성 완료       → /review 링크
               승인 완료       → 배포 URL
               재생성 완료     → /review 링크 (재전송)
```

---

## Discord 작업 충돌 방지

```python
_active_jobs: dict[str, dict] = {}
# { guild_id: { job, intent, repo, started } }
```

- 진행 중 `/pipeline` 재실행 시 경고 메시지
- `/cancel` 커맨드로 진행 중 작업 중단 가능
- 컨텍스트 유지: 같은 guild의 추가 수정 요청을 이어받아 처리

### 의도 → 설계 매핑

| 선택 | Spline mood | 히어로 CTA | 추가 섹션 |
|------|-------------|-----------|---------|
| 제품 홍보 | `dynamic` | "지금 시작하기" | 가격표 |
| 포트폴리오 | `minimal` | "작업물 보기" | 프로젝트 갤러리 |
| 수익화 | `tech` | "구매하기" | 결제 버튼 |
| 오픈소스 | `community` | "GitHub 보기" | 기여 가이드 |

---

## Discord `/landing` 씬 오버라이드

```
/landing url:<github_url> scene:<scene_id>
```

`scene` 파라미터 없으면 자동 선택 유지.

---

## 파일 변경 목록

| 파일 | 변경 유형 |
|------|---------|
| `templates/landing_page_template.html` | 전면 재작성 |
| `scripts/bucky_landing_generator.py` | `select_spline_scene()` 추가, 충돌 방지 로직 추가 |
| `scripts/discord_bot.py` | `/cancel` 커맨드, Intent Check 플로우, `/landing` scene 파라미터 |
| `data/spline_catalog.json` | 신규 생성 (씬 20개 큐레이션) |
| `dashboard/` | Next.js 앱 신규 생성 (`/intent`, `/review`, `/scene`) |

---

## 검증 계획

- [ ] 구현 완료 후 Codex 독립 검수
- [ ] 모바일(375px) 대시보드 3개 렌더링 확인
- [ ] Spline 씬 폴백 체인 전 단계 동작 확인
- [ ] Discord 충돌 방지 — 동시 `/pipeline` 2회 실행 테스트
- [ ] 의도별 템플릿 변형 4가지 확인
