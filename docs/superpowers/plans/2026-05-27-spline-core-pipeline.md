# Spline Core Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Spline 씬 카탈로그를 구축하고 Bucky 랜딩페이지 생성 파이프라인에 씬 자동 선택·임베드를 통합하며, 새 디자인 시스템 템플릿으로 교체하고 Discord 충돌 방지 및 컨펌 플로우를 추가한다.

**Architecture:** `data/spline_catalog.json` → `select_spline_scene()` → `generate()` → 새 템플릿 HTML. Discord `/pipeline` 실행 시 `_active_jobs` 충돌 방지 → 인텐트 확인 → Preview 배포 → `discord.ui.View` 버튼(즉시 배포/대시보드 수정/취소). 대시보드에서의 승인은 Discord webhook 메시지(`__BUCKY_JOB_CONFIRM__` prefix)로 `on_message`에서 감지.

**Tech Stack:** Python 3.11+, discord.py 2.x, aiohttp (urllib only), Tailwind CSS CDN, AOS.js CDN, @splinetool/viewer CDN

**Plan 2 필요:** 대시보드 구현은 `2026-05-27-spline-dashboard.md` 참조. 이 플랜 완료 후 진행.

---

## 파일 목록

| 경로 | 변경 |
|------|------|
| `data/spline_catalog.json` | 신규 생성 |
| `scripts/bucky_landing_generator.py` | 수정 (씬 선택 추가) |
| `templates/landing_page_template.html` | 전면 재작성 |
| `scripts/discord_bot.py` | 수정 (충돌방지 + 버튼 + on_message) |
| `tests/test_scene_selection.py` | 신규 생성 |

---

## Task 1: Spline 씬 카탈로그 큐레이션

**Files:**
- Create: `data/spline_catalog.json`

- [ ] **Step 1: `data/` 디렉토리 생성**

```bash
mkdir -p data
```

- [ ] **Step 2: Spline Community에서 씬 수집**

브라우저에서 `https://app.spline.design/community` 접속.
필터: `Background`, `Abstract`, `3D Objects` 카테고리.
각 씬 클릭 → `Export` 버튼 → `Viewer` 탭 → `scene.splinecode` URL 복사.

카테고리별 최소 수집 목표:
- `ai` 씬 3개 (floating orb, particle, neural)
- `saas` 씬 3개 (geometric, minimal shape, gradient blob)
- `devtool` 씬 2개 (code/terminal theme)
- `game` 씬 2개 (dynamic, neon)
- 범용 fallback 1개 (abstract sphere)

- [ ] **Step 3: 카탈로그 파일 작성**

```json
{
  "scenes": [
    {
      "id": "ai-orb-01",
      "url": "https://prod.spline.design/REPLACE_WITH_REAL_URL_1/scene.splinecode",
      "thumbnail": "https://REPLACE_WITH_THUMBNAIL_1",
      "category": ["ai", "saas"],
      "mood": ["tech", "dynamic"],
      "bg_compatible": true
    },
    {
      "id": "ai-particles-01",
      "url": "https://prod.spline.design/REPLACE_WITH_REAL_URL_2/scene.splinecode",
      "thumbnail": "https://REPLACE_WITH_THUMBNAIL_2",
      "category": ["ai"],
      "mood": ["tech", "minimal"],
      "bg_compatible": true
    },
    {
      "id": "saas-blob-01",
      "url": "https://prod.spline.design/REPLACE_WITH_REAL_URL_3/scene.splinecode",
      "thumbnail": "https://REPLACE_WITH_THUMBNAIL_3",
      "category": ["saas", "devtool"],
      "mood": ["minimal", "dynamic"],
      "bg_compatible": true
    },
    {
      "id": "saas-geo-01",
      "url": "https://prod.spline.design/REPLACE_WITH_REAL_URL_4/scene.splinecode",
      "thumbnail": "https://REPLACE_WITH_THUMBNAIL_4",
      "category": ["saas"],
      "mood": ["minimal"],
      "bg_compatible": true
    },
    {
      "id": "devtool-grid-01",
      "url": "https://prod.spline.design/REPLACE_WITH_REAL_URL_5/scene.splinecode",
      "thumbnail": "https://REPLACE_WITH_THUMBNAIL_5",
      "category": ["devtool"],
      "mood": ["tech"],
      "bg_compatible": true
    },
    {
      "id": "game-neon-01",
      "url": "https://prod.spline.design/REPLACE_WITH_REAL_URL_6/scene.splinecode",
      "thumbnail": "https://REPLACE_WITH_THUMBNAIL_6",
      "category": ["game"],
      "mood": ["dynamic"],
      "bg_compatible": true
    },
    {
      "id": "community-orb-01",
      "url": "https://prod.spline.design/REPLACE_WITH_REAL_URL_7/scene.splinecode",
      "thumbnail": "https://REPLACE_WITH_THUMBNAIL_7",
      "category": ["ai", "saas", "devtool", "game"],
      "mood": ["community"],
      "bg_compatible": true
    },
    {
      "id": "abstract-default",
      "url": "https://prod.spline.design/REPLACE_WITH_REAL_URL_8/scene.splinecode",
      "thumbnail": "https://REPLACE_WITH_THUMBNAIL_8",
      "category": ["ai", "saas", "devtool", "game"],
      "mood": ["tech", "minimal", "dynamic", "community"],
      "bg_compatible": true
    }
  ],
  "fallback_scene": "abstract-default"
}
```

**참고**: `REPLACE_WITH_REAL_URL_*`을 Step 2에서 수집한 실제 URL로 교체.

- [ ] **Step 4: 커밋**

```bash
git add data/spline_catalog.json
git commit -m "feat: Spline 씬 카탈로그 초기 버전 (8개 씬)"
```

---

## Task 2: 씬 선택 로직 + 테스트

**Files:**
- Modify: `scripts/bucky_landing_generator.py`
- Create: `tests/test_scene_selection.py`

- [ ] **Step 1: 실패 테스트 작성**

`tests/test_scene_selection.py`:

```python
import sys
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class TestSceneSelection(unittest.TestCase):

    def _make_catalog(self, tmp_dir: Path) -> Path:
        catalog = {
            "scenes": [
                {
                    "id": "ai-orb-01",
                    "url": "https://prod.spline.design/ai-orb/scene.splinecode",
                    "thumbnail": "",
                    "category": ["ai"],
                    "mood": ["tech"],
                    "bg_compatible": True,
                },
                {
                    "id": "saas-blob-01",
                    "url": "https://prod.spline.design/saas-blob/scene.splinecode",
                    "thumbnail": "",
                    "category": ["saas"],
                    "mood": ["minimal"],
                    "bg_compatible": True,
                },
                {
                    "id": "abstract-default",
                    "url": "https://prod.spline.design/default/scene.splinecode",
                    "thumbnail": "",
                    "category": ["ai", "saas", "devtool", "game"],
                    "mood": ["tech", "minimal", "dynamic", "community"],
                    "bg_compatible": True,
                },
            ],
            "fallback_scene": "abstract-default",
        }
        path = tmp_dir / "spline_catalog.json"
        path.write_text(json.dumps(catalog), encoding="utf-8")
        return path

    def test_selects_ai_scene_for_python_language(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = self._make_catalog(Path(tmp))
            with patch("scripts.bucky_landing_generator.CATALOG_PATH", catalog_path):
                with patch("scripts.bucky_landing_generator._is_url_alive", return_value=True):
                    from scripts.bucky_landing_generator import select_spline_scene
                    url = select_spline_scene(language="Python", description="AI tool", name="myai")
            self.assertIn("ai-orb", url)

    def test_selects_saas_scene_for_typescript(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = self._make_catalog(Path(tmp))
            with patch("scripts.bucky_landing_generator.CATALOG_PATH", catalog_path):
                with patch("scripts.bucky_landing_generator._is_url_alive", return_value=True):
                    from scripts.bucky_landing_generator import select_spline_scene
                    url = select_spline_scene(language="TypeScript", description="clean dashboard", name="dashboard")
            self.assertIn("saas-blob", url)

    def test_returns_fallback_when_url_dead(self):
        with tempfile.TemporaryDirectory() as tmp:
            catalog_path = self._make_catalog(Path(tmp))
            with patch("scripts.bucky_landing_generator.CATALOG_PATH", catalog_path):
                # First two URLs dead, fallback alive
                def mock_alive(url):
                    return "default" in url
                with patch("scripts.bucky_landing_generator._is_url_alive", side_effect=mock_alive):
                    from scripts.bucky_landing_generator import select_spline_scene
                    url = select_spline_scene(language="Python", description="", name="")
            self.assertIn("default", url)

    def test_returns_empty_string_when_catalog_missing(self):
        with patch("scripts.bucky_landing_generator.CATALOG_PATH", Path("/nonexistent/catalog.json")):
            from scripts.bucky_landing_generator import select_spline_scene
            url = select_spline_scene(language="Python")
        self.assertEqual(url, "")
```

- [ ] **Step 2: 테스트 실행 — FAIL 확인**

```bash
python -m pytest tests/test_scene_selection.py -v
```

Expected: `ImportError` 또는 `AttributeError` (함수 미존재)

- [ ] **Step 3: `bucky_landing_generator.py` 상단에 임포트 + 상수 추가**

`bucky_landing_generator.py` 파일 맨 위 `import` 블록 아래에 추가:

```python
import urllib.request
import uuid

CATALOG_PATH = ROOT / "data" / "spline_catalog.json"

_LANG_CATEGORY: dict[str, list[str]] = {
    "Python": ["ai", "devtool"],
    "TypeScript": ["saas", "devtool"],
    "JavaScript": ["saas", "devtool"],
    "Rust": ["devtool", "tech"],
    "Go": ["devtool", "tech"],
    "C++": ["game", "tech"],
    "C#": ["game", "tech"],
    "Java": ["saas", "enterprise"],
    "Swift": ["mobile", "saas"],
    "Kotlin": ["mobile", "saas"],
}

_MOOD_KEYWORDS: dict[str, list[str]] = {
    "dynamic": ["fast", "powerful", "blazing", "speed", "performance", "빠른", "강력"],
    "minimal": ["clean", "simple", "lightweight", "minimal", "깔끔", "단순"],
    "tech": ["api", "sdk", "cli", "framework", "library", "engine", "도구"],
    "community": ["open source", "contribute", "community", "오픈소스", "기여"],
}
```

- [ ] **Step 4: `_is_url_alive()` 함수 추가** (`DEFAULT_CONFIG` 정의 바로 위에)

```python
def _is_url_alive(url: str) -> bool:
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status < 400
    except Exception:
        return False
```

- [ ] **Step 5: `select_spline_scene()` 함수 추가** (`_is_url_alive` 바로 아래)

```python
def select_spline_scene(
    language: str = "",
    description: str = "",
    name: str = "",
    topics: list[str] | None = None,
) -> str:
    """GitHub 메타데이터 → 최적 Spline 씬 URL. 매칭 실패 시 단계적 폴백."""
    if not CATALOG_PATH.exists():
        return ""

    catalog_data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    scenes = [s for s in catalog_data.get("scenes", []) if s.get("bg_compatible")]
    fallback_id = catalog_data.get("fallback_scene", "")

    # Step 1: 카테고리 필터
    categories = _LANG_CATEGORY.get(language, ["saas"])
    candidates = [s for s in scenes if any(c in s.get("category", []) for c in categories)]
    if not candidates:
        candidates = scenes

    # Step 2: mood 점수 (가중치: 이름×1.5, 설명×1.0, 토픽×0.8, 언어×0.5)
    mood_scores: dict[str, float] = {m: 0.0 for m in _MOOD_KEYWORDS}
    for mood, keywords in _MOOD_KEYWORDS.items():
        for kw in keywords:
            if kw in (name or "").lower():
                mood_scores[mood] += 1.5
            if kw in (description or "").lower():
                mood_scores[mood] += 1.0
            for topic in (topics or []):
                if kw in topic.lower():
                    mood_scores[mood] += 0.8
        if mood in _LANG_CATEGORY.get(language, []):
            mood_scores[mood] += 0.5

    best_mood = max(mood_scores, key=lambda m: mood_scores[m])

    # Step 3: 최적 씬 선택
    mood_matched = [s for s in candidates if best_mood in s.get("mood", [])]
    pool = mood_matched if mood_matched else candidates

    # Step 4: URL 유효성 확인 (죽은 씬 건너뜀)
    for scene in pool:
        if _is_url_alive(scene["url"]):
            return scene["url"]

    # Step 5: fallback 씬
    fallback = next((s for s in scenes if s["id"] == fallback_id), None)
    if fallback and _is_url_alive(fallback["url"]):
        return fallback["url"]

    return ""  # 최종 폴백 → 템플릿이 CSS 그라디언트로 처리
```

- [ ] **Step 6: 테스트 실행 — PASS 확인**

```bash
python -m pytest tests/test_scene_selection.py -v
```

Expected:
```
PASSED tests/test_scene_selection.py::TestSceneSelection::test_selects_ai_scene_for_python_language
PASSED tests/test_scene_selection.py::TestSceneSelection::test_selects_saas_scene_for_typescript
PASSED tests/test_scene_selection.py::TestSceneSelection::test_returns_fallback_when_url_dead
PASSED tests/test_scene_selection.py::TestSceneSelection::test_returns_empty_string_when_catalog_missing
```

- [ ] **Step 7: 커밋**

```bash
git add scripts/bucky_landing_generator.py tests/test_scene_selection.py
git commit -m "feat: Spline 씬 선택 로직 + 폴백 체인 + 테스트"
```

---

## Task 3: `generate()` 씬 선택 통합

**Files:**
- Modify: `scripts/bucky_landing_generator.py:136-146`

- [ ] **Step 1: `generate()` 함수 교체**

기존:
```python
def generate(config: Optional[dict] = None, output_name: Optional[str] = None) -> Path:
    merged = {**DEFAULT_CONFIG, **(config or {})}
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = render_template(template, merged)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    name = output_name or merged.get("REPO_NAME", "landing").lower().replace(" ", "-")
    out_path = OUTPUT_DIR / f"{name}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"✅ 랜딩 페이지 생성: {out_path}")
    return out_path
```

교체:
```python
def generate(
    config: Optional[dict] = None,
    output_name: Optional[str] = None,
    scene_id: Optional[str] = None,
) -> Path:
    merged = {**DEFAULT_CONFIG, **(config or {})}

    # Spline 씬 선택 (scene_id 오버라이드 우선)
    if scene_id:
        catalog_data = json.loads(CATALOG_PATH.read_text(encoding="utf-8")) if CATALOG_PATH.exists() else {}
        scene = next((s for s in catalog_data.get("scenes", []) if s["id"] == scene_id), None)
        spline_url = scene["url"] if scene else ""
    else:
        spline_url = select_spline_scene(
            language=merged.get("LANGUAGE", ""),
            description=merged.get("DESCRIPTION", ""),
            name=merged.get("REPO_NAME", ""),
            topics=merged.get("TOPICS", []),
        )

    merged["SPLINE_URL"] = spline_url
    merged["SPLINE_HINT"] = "none" if not spline_url else "spline"

    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    html = render_template(template, merged)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    name = output_name or merged.get("REPO_NAME", "landing").lower().replace(" ", "-")
    out_path = OUTPUT_DIR / f"{name}.html"
    out_path.write_text(html, encoding="utf-8")
    print(f"✅ 랜딩 페이지 생성: {out_path}")
    return out_path
```

- [ ] **Step 2: `from_github_url()` LANGUAGE/TOPICS 전달 추가**

기존:
```python
def from_github_url(github_url: str, extra: dict = None) -> Path:
    parts = github_url.rstrip("/").split("/")
    repo_name = parts[-1] if len(parts) >= 2 else "Product"
    owner = parts[-2] if len(parts) >= 2 else ""
    config = {
        "REPO_NAME": repo_name,
        "LOGO_CHAR": repo_name[0].upper(),
        "GITHUB_URL": github_url,
        **(extra or {}),
    }
    return generate(config, repo_name.lower())
```

교체:
```python
def from_github_url(github_url: str, extra: dict = None, scene_id: Optional[str] = None) -> Path:
    parts = github_url.rstrip("/").split("/")
    repo_name = parts[-1] if len(parts) >= 2 else "Product"
    config = {
        "REPO_NAME": repo_name,
        "LOGO_CHAR": repo_name[0].upper(),
        "GITHUB_URL": github_url,
        **(extra or {}),
    }
    return generate(config, repo_name.lower(), scene_id=scene_id)
```

- [ ] **Step 3: 커밋**

```bash
git add scripts/bucky_landing_generator.py
git commit -m "feat: generate()에 Spline 씬 자동 선택 통합"
```

---

## Task 4: 새 랜딩페이지 템플릿

**Files:**
- Modify: `templates/landing_page_template.html` (전면 재작성)

- [ ] **Step 1: 기존 템플릿 백업**

```bash
cp templates/landing_page_template.html templates/landing_page_template.html.bak
```

- [ ] **Step 2: 새 템플릿 작성**

`templates/landing_page_template.html` 전체 내용을 아래로 교체:

```html
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{REPO_NAME}} — {{TAGLINE}}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link href="https://cdn.jsdelivr.net/npm/aos@2.3.4/dist/aos.css" rel="stylesheet">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="module" src="https://unpkg.com/@splinetool/viewer@1.0.76/build/spline-viewer.js"></script>
  <style>
    * { font-family: 'Inter', sans-serif; }
    body { background: #000; color: #fff; margin: 0; }

    .hero-section {
      position: relative; height: 100vh; overflow: hidden;
      display: flex; align-items: center; justify-content: center;
    }
    spline-viewer {
      position: absolute; inset: 0; width: 100%; height: 100%;
    }
    .spline-fallback {
      display: none; position: absolute; inset: 0;
      background: radial-gradient(ellipse at 50% 0%, #9b59ff22 0%, transparent 70%),
                  radial-gradient(ellipse at 80% 80%, #ff6b6b11 0%, transparent 60%), #000;
    }
    @media (max-width: 768px) {
      spline-viewer { display: none; }
      .spline-fallback { display: block; }
    }
    .hero-content {
      position: relative; z-index: 10; text-align: center;
      padding: 0 24px; max-width: 820px;
    }
    .glass-card {
      background: rgba(255,255,255,0.04);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 16px;
    }
    .gradient-text {
      background: linear-gradient(135deg, #9b59ff 0%, #ff6b6b 100%);
      -webkit-background-clip: text; -webkit-text-fill-color: transparent;
      background-clip: text;
    }
    .noise {
      position: fixed; inset: 0; pointer-events: none; opacity: 0.03; z-index: 999;
      background-image: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
    }
    .btn-primary {
      background: linear-gradient(135deg, #9b59ff, #ff6b6b);
      color: white; padding: 14px 32px; border-radius: 100px;
      font-weight: 600; font-size: 16px; text-decoration: none;
      display: inline-block; transition: opacity .2s, transform .2s;
    }
    .btn-primary:hover { opacity: .85; transform: translateY(-1px); }
    .btn-secondary {
      background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
      color: white; padding: 14px 32px; border-radius: 100px;
      font-weight: 500; font-size: 16px; text-decoration: none;
      display: inline-block; transition: background .2s;
    }
    .btn-secondary:hover { background: rgba(255,255,255,0.1); }
    .badge {
      display: inline-flex; align-items: center; gap: 6px;
      background: rgba(155,89,255,0.12); border: 1px solid rgba(155,89,255,0.3);
      color: #c4a0ff; padding: 6px 14px; border-radius: 100px;
      font-size: 13px; font-weight: 500;
    }
    section { padding: 96px 32px; }
    .section-inner { max-width: 1024px; margin: 0 auto; }
  </style>
</head>
<body>
  <div class="noise"></div>

  <!-- Nav -->
  <nav class="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-8 py-5">
    <div class="text-lg font-bold">
      <span class="gradient-text">{{LOGO_CHAR}}</span>
      <span class="text-white/60 font-normal ml-1">{{REPO_NAME}}</span>
    </div>
    <div class="flex gap-3">
      <a href="{{GITHUB_URL}}" class="btn-secondary" style="padding:10px 20px;font-size:14px">GitHub</a>
      <a href="{{CTA_URL}}" class="btn-primary" style="padding:10px 20px;font-size:14px">{{CTA_TEXT}}</a>
    </div>
  </nav>

  <!-- Hero -->
  <section class="hero-section" style="padding:0">
    <spline-viewer url="{{SPLINE_URL}}" events-target="global"></spline-viewer>
    <div class="spline-fallback"></div>
    <div class="hero-content">
      <span class="badge" style="margin-bottom:24px">{{BADGE_TEXT}}</span>
      <h1 style="font-size:clamp(2.5rem,6vw,4.5rem);font-weight:800;line-height:1.1;margin:16px 0 24px">
        <span class="gradient-text">{{HEADLINE_LINE1}}</span><br>{{HEADLINE_LINE2}}
      </h1>
      <p style="font-size:1.2rem;color:rgba(255,255,255,.55);margin-bottom:32px;max-width:520px;margin-left:auto;margin-right:auto;line-height:1.6">{{DESCRIPTION}}</p>
      <div style="display:flex;gap:16px;justify-content:center;flex-wrap:wrap">
        <a href="{{CTA_URL}}" class="btn-primary">{{CTA_PRIMARY}}</a>
        <a href="{{DEMO_URL}}" class="btn-secondary">{{CTA_SECONDARY}}</a>
      </div>
      <p style="margin-top:24px;font-size:13px;color:rgba(255,255,255,.25)">{{SOCIAL_PROOF}}</p>
    </div>
  </section>

  <!-- Stats -->
  <section>
    <div class="section-inner">
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:20px">
        {{#STATS}}
        <div class="glass-card" style="padding:28px;text-align:center" data-aos="fade-up">
          <div style="font-size:2.5rem;font-weight:800" class="gradient-text">{{STAT_VALUE}}</div>
          <div style="color:rgba(255,255,255,.45);font-size:14px;margin-top:8px">{{STAT_LABEL}}</div>
        </div>
        {{/STATS}}
      </div>
    </div>
  </section>

  <!-- Features -->
  <section style="background:rgba(255,255,255,.015)">
    <div class="section-inner">
      <div style="text-align:center;margin-bottom:56px" data-aos="fade-up">
        <h2 style="font-size:2.5rem;font-weight:700;margin-bottom:12px">{{FEATURES_TITLE}}</h2>
        <p style="color:rgba(255,255,255,.45)">{{FEATURES_SUBTITLE}}</p>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:20px">
        {{#FEATURES}}
        <div class="glass-card" style="padding:36px" data-aos="fade-up">
          <div style="font-size:2.5rem;margin-bottom:16px">{{FEATURE_ICON}}</div>
          <h3 style="font-size:1.2rem;font-weight:600;margin-bottom:10px">{{FEATURE_TITLE}}</h3>
          <p style="color:rgba(255,255,255,.45);line-height:1.6;font-size:15px">{{FEATURE_DESC}}</p>
        </div>
        {{/FEATURES}}
      </div>
    </div>
  </section>

  <!-- Steps -->
  <section>
    <div class="section-inner" style="max-width:720px">
      <h2 style="font-size:2.5rem;font-weight:700;text-align:center;margin-bottom:56px" data-aos="fade-up">{{HOWTO_TITLE}}</h2>
      {{#STEPS}}
      <div style="display:flex;gap:24px;margin-bottom:48px" data-aos="fade-up">
        <div style="font-size:2rem;font-weight:800;min-width:40px" class="gradient-text">{{STEP_NUM}}</div>
        <div>
          <h3 style="font-size:1.1rem;font-weight:600;margin-bottom:8px">{{STEP_TITLE}}</h3>
          <p style="color:rgba(255,255,255,.45);line-height:1.6;font-size:15px">{{STEP_DESC}}</p>
        </div>
      </div>
      {{/STEPS}}
    </div>
  </section>

  <!-- Pricing -->
  <section style="background:rgba(255,255,255,.015)">
    <div class="section-inner">
      <div style="text-align:center;margin-bottom:56px" data-aos="fade-up">
        <h2 style="font-size:2.5rem;font-weight:700;margin-bottom:12px">{{PRICING_TITLE}}</h2>
        <p style="color:rgba(255,255,255,.45)">{{PRICING_SUBTITLE}}</p>
      </div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:20px">
        {{#PLANS}}
        <div class="glass-card" style="padding:36px;border-color:rgba(255,255,255,.08)" data-aos="fade-up">
          {{#IS_FEATURED}}<div class="badge" style="margin-bottom:16px">추천</div>{{/IS_FEATURED}}
          <div style="font-size:1.4rem;font-weight:700;margin-bottom:4px">{{PLAN_NAME}}</div>
          <div style="color:rgba(255,255,255,.4);font-size:13px;margin-bottom:20px">{{PLAN_DESC}}</div>
          <div style="font-size:2.5rem;font-weight:800;margin-bottom:24px" class="gradient-text">{{PLAN_PRICE}}</div>
          <ul style="list-style:none;padding:0;margin:0 0 28px;display:flex;flex-direction:column;gap:10px">
            {{#PLAN_FEATURES}}
            <li style="display:flex;align-items:center;gap:8px;color:rgba(255,255,255,.6);font-size:14px">
              <span style="color:#9b59ff">✓</span> {{FEATURE}}
            </li>
            {{/PLAN_FEATURES}}
          </ul>
          <a href="{{PLAN_URL}}" class="{{PLAN_BTN_STYLE}}" style="display:block;text-align:center;padding:12px;border-radius:12px;font-weight:500;font-size:14px;text-decoration:none">{{PLAN_BTN_TEXT}}</a>
        </div>
        {{/PLANS}}
      </div>
    </div>
  </section>

  <!-- CTA Bottom -->
  <section style="text-align:center" data-aos="fade-up">
    <div class="section-inner">
      <h2 style="font-size:3rem;font-weight:800;margin-bottom:16px">{{CTA_BOTTOM_TITLE}}</h2>
      <p style="color:rgba(255,255,255,.45);margin-bottom:32px">{{CTA_BOTTOM_DESC}}</p>
      <a href="{{CTA_URL}}" class="btn-primary">{{CTA_PRIMARY}}</a>
    </div>
  </section>

  <!-- Footer -->
  <footer style="border-top:1px solid rgba(255,255,255,.08);padding:28px 32px;display:flex;align-items:center;justify-content:space-between">
    <span style="color:rgba(255,255,255,.25);font-size:13px">© {{YEAR}} {{REPO_NAME}}</span>
    <a href="{{GITHUB_URL}}" style="color:rgba(255,255,255,.25);font-size:13px;text-decoration:none">GitHub ↗</a>
  </footer>

  <script src="https://cdn.jsdelivr.net/npm/aos@2.3.4/dist/aos.js"></script>
  <script>
    AOS.init({ duration: 600, once: true, offset: 80 });
    (function() {
      var c = document.createElement('canvas');
      var gl = c.getContext('webgl') || c.getContext('experimental-webgl');
      if (!gl) {
        document.querySelectorAll('spline-viewer').forEach(function(e){ e.style.display='none'; });
        document.querySelectorAll('.spline-fallback').forEach(function(e){ e.style.display='block'; });
      }
    })();
  </script>
</body>
</html>
```

- [ ] **Step 3: 로컬에서 생성 테스트**

```bash
python scripts/bucky_landing_generator.py https://github.com/jaeha81/arki-3d-APP
```

Expected: `generated/landing_pages/arki-3d-app.html` 생성됨.
브라우저에서 열어 히어로 100vh, 그라디언트 텍스트, glassmorphism 카드 확인.

- [ ] **Step 4: 커밋**

```bash
git add templates/landing_page_template.html
git commit -m "feat: 랜딩 템플릿 전면 재설계 — Spline 디자인 시스템 적용"
```

---

## Task 5: Discord 작업 충돌 방지 + `/cancel`

**Files:**
- Modify: `scripts/discord_bot.py`

- [ ] **Step 1: 모듈 수준 `_active_jobs` 딕셔너리 추가**

`discord_bot.py`에서 `_voice_clients: dict` 선언 근처 (라인 약 100번대)를 찾아 그 아래에 추가:

```python
_active_jobs: dict[str, dict] = {}
# 구조: { guild_id: { "job_id": str, "repo": str, "out_path": Path, "channel_id": str, "started": str } }
```

- [ ] **Step 2: `_register_deploy_commands()` 내 `/cancel` 커맨드 추가**

`_register_deploy_commands()` 함수 내부, `cmd_pipeline` 함수 정의 **아래**에 추가:

```python
    @tree.command(name="cancel", description="진행 중인 파이프라인 작업 취소")
    async def cmd_cancel(interaction: discord.Interaction) -> None:
        guild_id = str(interaction.guild_id)
        job = _active_jobs.pop(guild_id, None)
        if job:
            await interaction.response.send_message(
                f"❌ `{job['repo']}` 파이프라인이 취소되었습니다."
            )
        else:
            await interaction.response.send_message(
                "ℹ️ 현재 진행 중인 작업이 없습니다.", ephemeral=True
            )
```

- [ ] **Step 3: `discord.ui.View` 클래스 추가**

`_register_deploy_commands()` 함수 **정의 바로 위**에 추가:

```python
class _PipelineConfirmView(discord.ui.View):
    """파이프라인 Preview 컨펌 버튼 뷰 (15분 타임아웃)."""

    def __init__(self, job_id: str, guild_id: str, repo_name: str, preview_url: str, out_path) -> None:
        super().__init__(timeout=900)
        self.job_id = job_id
        self.guild_id = guild_id
        self.repo_name = repo_name
        self.preview_url = preview_url
        self.out_path = out_path

    @discord.ui.button(label="✅ 바로 배포", style=discord.ButtonStyle.green)
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer()
        job = _active_jobs.get(self.guild_id)
        if not job or job.get("job_id") != self.job_id:
            await interaction.followup.send("⚠️ 이미 처리된 작업입니다.", ephemeral=True)
            return
        await interaction.followup.send(f"⚙️ 프로덕션 배포 시작...")
        sys.path.insert(0, str(_ROOT / "scripts"))
        from bucky_vercel_deploy import deploy_landing_page as _deploy_landing
        result = await asyncio.to_thread(_deploy_landing, self.repo_name, self.out_path)
        _active_jobs.pop(self.guild_id, None)
        if result.get("success"):
            await interaction.followup.send(
                f"✅ **{self.repo_name}** 배포 완료!\n🌐 {result.get('url', '확인 중...')}"
            )
        else:
            await interaction.followup.send(
                f"❌ 배포 실패: {result.get('error', '')[:300]}"
            )
        self.stop()

    @discord.ui.button(label="✏️ 대시보드에서 수정", style=discord.ButtonStyle.secondary)
    async def open_dashboard(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        dashboard_url = os.getenv("BUCKY_DASHBOARD_URL", "").rstrip("/")
        import urllib.parse
        params = urllib.parse.urlencode({
            "job_id": self.job_id,
            "preview_url": self.preview_url,
            "repo": self.repo_name,
            "guild_id": self.guild_id,
        })
        review_url = f"{dashboard_url}/review?{params}"
        await interaction.response.send_message(
            f"📱 모바일에서 대시보드 열기:\n{review_url}", ephemeral=True
        )

    @discord.ui.button(label="❌ 취소", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        _active_jobs.pop(self.guild_id, None)
        await interaction.response.send_message(f"❌ `{self.repo_name}` 파이프라인 취소됨.")
        self.stop()
```

- [ ] **Step 4: 커밋**

```bash
git add scripts/discord_bot.py
git commit -m "feat: Discord 작업 충돌 방지 + /cancel + PipelineConfirmView"
```

---

## Task 6: `/pipeline` 충돌 방지 + Preview 플로우 적용

**Files:**
- Modify: `scripts/discord_bot.py:1138-1168`

- [ ] **Step 1: `cmd_pipeline` 함수 전체 교체**

기존 `cmd_pipeline` 함수 내용을 아래로 교체:

```python
    @tree.command(name="pipeline", description="GitHub 레포 URL → 랜딩 페이지 생성 + 컨펌 후 Vercel 배포")
    @app_commands.describe(repo_url="GitHub 레포 URL (예: https://github.com/user/repo)")
    async def cmd_pipeline(interaction: discord.Interaction, repo_url: str) -> None:
        await interaction.response.defer(thinking=True)
        guild_id = str(interaction.guild_id)

        # 충돌 방지
        if guild_id in _active_jobs:
            existing = _active_jobs[guild_id]
            await interaction.followup.send(
                f"⚠️ **`{existing['repo']}`** 작업이 진행 중입니다.\n"
                f"완료 후 다시 시도하거나 `/cancel`로 취소하세요."
            )
            return

        try:
            sys.path.insert(0, str(_ROOT / "scripts"))
            from bucky_landing_generator import from_github_url as _gen
            from bucky_vercel_deploy import deploy_landing_page as _deploy_landing

            parts = repo_url.rstrip("/").split("/")
            repo_name = parts[-1] if len(parts) >= 2 else "product"
            job_id = str(uuid.uuid4())[:8]

            # 작업 등록
            _active_jobs[guild_id] = {
                "job_id": job_id,
                "repo": repo_name,
                "out_path": None,
                "channel_id": str(interaction.channel_id),
                "started": datetime.now().isoformat(),
            }

            await interaction.followup.send(f"⚙️ `{repo_name}` 랜딩페이지 생성 중...")
            out_path = await asyncio.to_thread(_gen, repo_url)
            _active_jobs[guild_id]["out_path"] = out_path

            # Preview 배포
            await interaction.followup.send("⚙️ Preview 배포 중...")
            preview_result = await asyncio.to_thread(
                _deploy_landing, repo_name, out_path
            )
            preview_url = preview_result.get("url", "") if preview_result.get("success") else ""

            # 컨펌 버튼 전송
            view = _PipelineConfirmView(job_id, guild_id, repo_name, preview_url, out_path)
            msg = (
                f"✅ **`{repo_name}`** 랜딩페이지 생성 완료!\n"
                f"🔗 미리보기: {preview_url or '배포 실패 — 로컬 파일 첨부됨'}\n\n"
                f"어떻게 하시겠어요?"
            )
            if preview_url:
                await interaction.followup.send(msg, view=view)
            else:
                await interaction.followup.send(
                    msg, view=view,
                    file=discord.File(str(out_path), filename=out_path.name),
                )

        except Exception as e:
            _active_jobs.pop(guild_id, None)
            await interaction.followup.send(f"⚠️ 파이프라인 오류: {e}")
            print(f"[Deploy] pipeline 오류: {e}", flush=True)
```

`uuid` 임포트가 없으면 `discord_bot.py` 상단에 추가:
```python
import uuid
```

- [ ] **Step 2: 커밋**

```bash
git add scripts/discord_bot.py
git commit -m "feat: /pipeline 충돌 방지 + Preview 컨펌 버튼 플로우"
```

---

## Task 7: `/landing` scene 오버라이드 파라미터

**Files:**
- Modify: `scripts/discord_bot.py:1092-1106`

- [ ] **Step 1: `cmd_landing` 함수 교체**

기존:
```python
    @tree.command(name="landing", description="GitHub 레포 URL → 프리미엄 랜딩 페이지 생성 후 HTML 파일 전송")
    @app_commands.describe(repo_url="GitHub 레포 URL (예: https://github.com/user/repo)")
    async def cmd_landing(interaction: discord.Interaction, repo_url: str) -> None:
        await interaction.response.defer(thinking=True)
        try:
            sys.path.insert(0, str(_ROOT / "scripts"))
            from bucky_landing_generator import from_github_url as _gen
            out_path = await asyncio.to_thread(_gen, repo_url)
            await interaction.followup.send(
                f"✅ **랜딩 페이지 생성 완료!**\n📦 `{out_path.name}`",
                file=discord.File(str(out_path), filename=out_path.name),
            )
        except Exception as e:
            await interaction.followup.send(f"⚠️ 랜딩 페이지 생성 오류: {e}")
            print(f"[Deploy] landing 오류: {e}", flush=True)
```

교체:
```python
    @tree.command(name="landing", description="GitHub 레포 URL → 프리미엄 랜딩 페이지 생성 후 HTML 파일 전송")
    @app_commands.describe(
        repo_url="GitHub 레포 URL (예: https://github.com/user/repo)",
        scene="씬 ID 지정 (비워두면 자동 선택, 예: ai-orb-01)",
    )
    async def cmd_landing(
        interaction: discord.Interaction,
        repo_url: str,
        scene: str = "",
    ) -> None:
        await interaction.response.defer(thinking=True)
        try:
            sys.path.insert(0, str(_ROOT / "scripts"))
            from bucky_landing_generator import from_github_url as _gen
            scene_id = scene.strip() or None
            out_path = await asyncio.to_thread(_gen, repo_url, scene_id=scene_id)
            scene_note = f" (씬: `{scene_id}`)" if scene_id else ""
            await interaction.followup.send(
                f"✅ **랜딩 페이지 생성 완료!**{scene_note}\n📦 `{out_path.name}`",
                file=discord.File(str(out_path), filename=out_path.name),
            )
        except Exception as e:
            await interaction.followup.send(f"⚠️ 랜딩 페이지 생성 오류: {e}")
            print(f"[Deploy] landing 오류: {e}", flush=True)
```

- [ ] **Step 2: 커밋**

```bash
git add scripts/discord_bot.py
git commit -m "feat: /landing에 scene 오버라이드 파라미터 추가"
```

---

## Task 8: 대시보드 승인 webhook 수신 (`on_message`)

**Files:**
- Modify: `scripts/discord_bot.py` — `on_message` 메서드

- [ ] **Step 1: `on_message` 메서드 상단에 webhook 처리 블록 추가**

`on_message` 함수에서 `if message.author == self.user: return` 바로 아래에 추가:

```python
        # 대시보드 → Discord webhook 컨펌 감지
        # 형식: __BUCKY_JOB_CONFIRM__|{job_id}|{action}|{guild_id}
        content_raw = message.content.strip()
        if content_raw.startswith("__BUCKY_JOB_CONFIRM__") and getattr(message, "webhook_id", None):
            parts = content_raw.split("|")
            if len(parts) == 4:
                _, job_id, action, g_id = parts
                job = _active_jobs.get(g_id)
                if job and job.get("job_id") == job_id:
                    if action == "approve":
                        await message.channel.send(f"⚙️ 대시보드 승인 — `{job['repo']}` 배포 시작...")
                        sys.path.insert(0, str(_ROOT / "scripts"))
                        from bucky_vercel_deploy import deploy_landing_page as _dl
                        result = await asyncio.to_thread(_dl, job["repo"], job["out_path"])
                        _active_jobs.pop(g_id, None)
                        if result.get("success"):
                            await message.channel.send(
                                f"✅ **{job['repo']}** 배포 완료!\n🌐 {result.get('url', '')}"
                            )
                        else:
                            await message.channel.send(f"❌ 배포 실패: {result.get('error','')[:300]}")
                    elif action == "cancel":
                        _active_jobs.pop(g_id, None)
                        await message.channel.send(f"❌ `{job['repo']}` 파이프라인이 취소되었습니다.")
            return
```

- [ ] **Step 2: 전체 테스트 실행**

```bash
python -m pytest tests/ -v
```

Expected: 기존 테스트 + 새 씬 선택 테스트 모두 PASS

- [ ] **Step 3: 최종 커밋**

```bash
git add scripts/discord_bot.py
git commit -m "feat: on_message — 대시보드 webhook 컨펌 수신 처리"
```

---

## Task 9: 환경변수 문서화

**Files:**
- Modify: `README.md` 또는 `.env.example` (존재하는 쪽)

- [ ] **Step 1: `.env.example`에 새 변수 추가**

```bash
# Spline 대시보드 URL (Plan 2 완료 후 채움)
BUCKY_DASHBOARD_URL=https://bucky-dashboard.vercel.app

# 대시보드 → Bot 컨펌용 Discord Webhook URL
# Discord 서버 설정 → 연동 → 웹후크 → 새 웹후크 생성 → URL 복사
BUCKY_CONFIRM_WEBHOOK_URL=https://discord.com/api/webhooks/xxx/yyy
```

- [ ] **Step 2: 최종 커밋**

```bash
git add .env.example
git commit -m "docs: Spline 통합 환경변수 문서화"
```

---

## Task 10: 씬 오버라이드 webhook 수신 (`on_message`)

**Files:**
- Modify: `scripts/discord_bot.py` — `on_message` 메서드

- [ ] **Step 1: `__BUCKY_SCENE_OVERRIDE__` 처리 블록 추가**

Task 8에서 추가한 `__BUCKY_JOB_CONFIRM__` 처리 블록 **바로 아래**에 추가:

```python
        # 대시보드 → 씬 오버라이드 감지
        # 형식: __BUCKY_SCENE_OVERRIDE__|{job_id}|{scene_id}|{guild_id}
        if content_raw.startswith("__BUCKY_SCENE_OVERRIDE__") and getattr(message, "webhook_id", None):
            parts = content_raw.split("|")
            if len(parts) == 4:
                _, job_id, scene_id, g_id = parts
                job = _active_jobs.get(g_id)
                if job and job.get("job_id") == job_id:
                    await message.channel.send(
                        f"🎨 씬 변경 요청 — `{scene_id}` 으로 재생성 중..."
                    )
                    sys.path.insert(0, str(_ROOT / "scripts"))
                    from bucky_landing_generator import from_github_url as _gen
                    new_out = await asyncio.to_thread(
                        _gen, f"https://github.com/{job['repo']}", scene_id=scene_id
                    )
                    job["out_path"] = new_out
                    from bucky_vercel_deploy import deploy_landing_page as _dl
                    prev = await asyncio.to_thread(_dl, job["repo"], new_out)
                    preview_url = prev.get("url", "") if prev.get("success") else ""
                    dashboard_url = os.getenv("BUCKY_DASHBOARD_URL", "").rstrip("/")
                    import urllib.parse
                    review_params = urllib.parse.urlencode({
                        "job_id": job_id, "preview_url": preview_url,
                        "repo": job["repo"], "guild_id": g_id,
                    })
                    await message.channel.send(
                        f"✅ 씬 변경 완료! 다시 확인하세요:\n"
                        f"🔗 {preview_url or '미리보기 없음'}\n"
                        f"📱 {dashboard_url}/review?{review_params}"
                    )
            return
```

- [ ] **Step 2: 커밋**

```bash
git add scripts/discord_bot.py
git commit -m "feat: on_message — 씬 오버라이드 webhook 감지 + 재생성"
```

---

## 완료 체크리스트

- [ ] `data/spline_catalog.json` — 실제 Spline URL 8개 이상
- [ ] `select_spline_scene()` 테스트 4개 PASS
- [ ] 새 템플릿으로 로컬 생성 확인 (브라우저 확인)
- [ ] `/pipeline` 충돌 방지 동작 (동시 2회 실행 시 경고)
- [ ] `/cancel` 동작 확인
- [ ] `/landing scene:ai-orb-01` 씬 오버라이드 동작
- [ ] `__BUCKY_JOB_CONFIRM__` webhook 메시지 수신 → 배포 확인
- [ ] `__BUCKY_SCENE_OVERRIDE__` webhook 메시지 수신 → 재생성 확인
- [ ] **Codex 독립 검수** (구현 완료 후 `/jh-codex-verify` 실행)
