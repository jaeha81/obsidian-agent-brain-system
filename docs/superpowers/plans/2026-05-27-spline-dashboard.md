# Spline Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 모바일 퍼스트 Next.js 대시보드 앱(`/intent`, `/review`, `/scene`)을 구축하고 Vercel에 배포한다. 사용자가 Discord 없이 모바일에서 랜딩페이지 의도 설정·미리보기·컨펌·씬 변경을 수행할 수 있게 한다.

**Architecture:** Next.js 14 App Router. 모든 페이지는 URL params로 job 데이터 수신 (별도 DB 불필요). 컨펌/취소 액션은 `/api/confirm` 서버리스 라우트 → Discord webhook으로 `__BUCKY_JOB_CONFIRM__` 메시지 전송 → Bot이 `on_message`에서 감지. 씬 카탈로그는 `/api/catalog` 라우트가 `data/spline_catalog.json` 기반으로 제공.

**Tech Stack:** Next.js 14 (App Router), TypeScript, Tailwind CSS, Vercel 배포

**선행 조건:** Plan 1 (`2026-05-27-spline-core-pipeline.md`) 완료 필요.

---

## 파일 목록

```
dashboard/
├── app/
│   ├── layout.tsx                 신규
│   ├── intent/page.tsx            신규
│   ├── review/page.tsx            신규
│   ├── scene/page.tsx             신규
│   └── api/
│       ├── confirm/route.ts       신규
│       └── catalog/route.ts       신규
├── components/
│   ├── MobileLayout.tsx           신규
│   └── SceneGrid.tsx              신규
├── lib/
│   └── discord.ts                 신규
├── package.json                   신규
├── tailwind.config.ts             신규
├── tsconfig.json                  신규
└── next.config.ts                 신규
```

---

## Task 1: Next.js 프로젝트 초기화

**Files:**
- Create: `dashboard/` 전체 구조

- [ ] **Step 1: Next.js 프로젝트 생성**

```bash
cd "G:/내 드라이브/obsidian-agent-brain-system"
npx create-next-app@14 dashboard --typescript --tailwind --app --no-src-dir --import-alias "@/*" --no-eslint
```

- [ ] **Step 2: 불필요한 초기 파일 제거**

```bash
cd dashboard
rm -rf app/page.tsx app/globals.css public/vercel.svg public/next.svg
```

- [ ] **Step 3: `app/globals.css` 새로 작성**

`dashboard/app/globals.css`:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

* { font-family: 'Inter', -apple-system, sans-serif; }

body {
  background: #000;
  color: #fff;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

.gradient-text {
  background: linear-gradient(135deg, #9b59ff 0%, #ff6b6b 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.glass-card {
  background: rgba(255, 255, 255, 0.04);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
}

.btn-primary {
  background: linear-gradient(135deg, #9b59ff, #ff6b6b);
  color: white;
  border: none;
  border-radius: 100px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.2s;
}

.btn-primary:hover { opacity: 0.85; transform: translateY(-1px); }
.btn-primary:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }

.btn-secondary {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: white;
  border-radius: 100px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-secondary:hover { background: rgba(255, 255, 255, 0.1); }
```

- [ ] **Step 4: `app/layout.tsx` 작성**

```tsx
import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'Bucky Dashboard',
  description: 'Bucky 랜딩페이지 컨펌 대시보드',
  viewport: 'width=device-width, initial-scale=1, maximum-scale=1',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ko">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  )
}
```

- [ ] **Step 5: `components/MobileLayout.tsx` 작성**

```tsx
export default function MobileLayout({
  title,
  subtitle,
  children,
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
}) {
  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="px-5 py-4 border-b border-white/8 flex items-center gap-3">
        <span className="text-xl font-bold gradient-text">B</span>
        <div>
          <div className="text-sm font-semibold">{title}</div>
          {subtitle && <div className="text-xs text-white/40">{subtitle}</div>}
        </div>
      </header>
      {/* Content */}
      <main className="flex-1 px-5 py-6 max-w-lg mx-auto w-full">{children}</main>
    </div>
  )
}
```

- [ ] **Step 6: `lib/discord.ts` 작성**

```typescript
export async function sendConfirmWebhook(
  jobId: string,
  action: 'approve' | 'cancel',
  guildId: string
): Promise<{ ok: boolean; error?: string }> {
  const webhookUrl = process.env.BUCKY_CONFIRM_WEBHOOK_URL
  if (!webhookUrl) {
    return { ok: false, error: 'BUCKY_CONFIRM_WEBHOOK_URL not configured' }
  }

  const message = `__BUCKY_JOB_CONFIRM__|${jobId}|${action}|${guildId}`
  const res = await fetch(webhookUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: message }),
  })

  if (!res.ok) {
    return { ok: false, error: `Discord webhook error: ${res.status}` }
  }
  return { ok: true }
}
```

- [ ] **Step 7: 커밋**

```bash
cd "G:/내 드라이브/obsidian-agent-brain-system"
git add dashboard/
git commit -m "feat: Next.js 대시보드 프로젝트 초기화"
```

---

## Task 2: `/api/confirm` 라우트

**Files:**
- Create: `dashboard/app/api/confirm/route.ts`

- [ ] **Step 1: 라우트 작성**

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { sendConfirmWebhook } from '@/lib/discord'

export async function POST(req: NextRequest) {
  let body: { job_id?: string; action?: string; guild_id?: string }
  try {
    body = await req.json()
  } catch {
    return NextResponse.json({ error: 'Invalid JSON' }, { status: 400 })
  }

  const { job_id, action, guild_id } = body

  if (!job_id || !action || !guild_id) {
    return NextResponse.json({ error: 'job_id, action, guild_id required' }, { status: 400 })
  }

  if (action !== 'approve' && action !== 'cancel') {
    return NextResponse.json({ error: 'action must be approve or cancel' }, { status: 400 })
  }

  const result = await sendConfirmWebhook(job_id, action, guild_id)
  if (!result.ok) {
    return NextResponse.json({ error: result.error }, { status: 500 })
  }

  return NextResponse.json({ ok: true })
}
```

- [ ] **Step 2: 커밋**

```bash
git add dashboard/app/api/confirm/
git commit -m "feat: /api/confirm — Discord webhook 컨펌 라우트"
```

---

## Task 3: `/api/catalog` 라우트

**Files:**
- Create: `dashboard/app/api/catalog/route.ts`

- [ ] **Step 1: 라우트 작성**

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { readFileSync } from 'fs'
import { join } from 'path'

export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url)
  const category = searchParams.get('category')

  try {
    const catalogPath = join(process.cwd(), '..', 'data', 'spline_catalog.json')
    const raw = readFileSync(catalogPath, 'utf-8')
    const catalog = JSON.parse(raw)

    let scenes = catalog.scenes ?? []
    if (category) {
      scenes = scenes.filter((s: { category: string[] }) =>
        s.category.includes(category)
      )
    }

    return NextResponse.json({ scenes })
  } catch {
    return NextResponse.json({ scenes: [] })
  }
}
```

- [ ] **Step 2: 커밋**

```bash
git add dashboard/app/api/catalog/
git commit -m "feat: /api/catalog — Spline 씬 카탈로그 API"
```

---

## Task 4: `/intent` 페이지

**Files:**
- Create: `dashboard/app/intent/page.tsx`

- [ ] **Step 1: 페이지 작성**

```tsx
'use client'

import { useState } from 'react'
import { useSearchParams } from 'next/navigation'
import MobileLayout from '@/components/MobileLayout'

const INTENT_OPTIONS = [
  { value: 'product', emoji: '🚀', label: '제품 홍보', desc: 'SaaS / 서비스 론칭' },
  { value: 'portfolio', emoji: '🎨', label: '포트폴리오', desc: '개발자 / 디자이너 소개' },
  { value: 'commerce', emoji: '💳', label: '수익화', desc: '결제 연동 포함' },
  { value: 'opensource', emoji: '🌱', label: '오픈소스', desc: '기여자 모집 / 커뮤니티' },
]

const MOOD_OPTIONS = [
  { value: 'minimal', label: '미니멀', desc: '깔끔하고 단순하게' },
  { value: 'dynamic', label: '다이나믹', desc: '강렬하고 임팩트 있게' },
]

export default function IntentPage() {
  const params = useSearchParams()
  const jobId = params.get('job_id') ?? ''
  const repo = params.get('repo') ?? 'Unknown'
  const guildId = params.get('guild_id') ?? ''

  const [intent, setIntent] = useState('')
  const [mood, setMood] = useState('')
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)

  async function handleSubmit() {
    if (!intent || !mood) return
    setLoading(true)

    // TODO: 실제로는 Bot에 intent 전달 API 필요 — 현재는 approve 액션으로 단순화
    // Bot이 intent를 받아 처리하는 엔드포인트를 Plan 1 확장 시 추가
    const webhookUrl = process.env.NEXT_PUBLIC_BUCKY_PIPELINE_WEBHOOK ?? ''
    if (webhookUrl) {
      await fetch(webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: `__BUCKY_INTENT__|${jobId}|${intent}|${mood}|${guildId}`,
        }),
      })
    }

    setDone(true)
    setLoading(false)
  }

  if (done) {
    return (
      <MobileLayout title="Bucky" subtitle={repo}>
        <div className="text-center mt-16">
          <div className="text-5xl mb-4">✅</div>
          <h2 className="text-xl font-bold mb-2">설정 완료!</h2>
          <p className="text-white/50 text-sm">Bucky가 랜딩페이지를 생성 중입니다.<br />Discord에서 알림을 확인하세요.</p>
        </div>
      </MobileLayout>
    )
  }

  return (
    <MobileLayout title="의도 설정" subtitle={repo}>
      <h2 className="text-lg font-bold mb-1">이 페이지의 목적은?</h2>
      <p className="text-white/40 text-sm mb-5">랜딩페이지 구성이 달라집니다</p>

      <div className="flex flex-col gap-3 mb-8">
        {INTENT_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setIntent(opt.value)}
            className={`glass-card p-4 text-left transition-all ${
              intent === opt.value
                ? 'border-purple-500/50 bg-purple-500/10'
                : ''
            }`}
          >
            <div className="flex items-center gap-3">
              <span className="text-2xl">{opt.emoji}</span>
              <div>
                <div className="font-semibold text-sm">{opt.label}</div>
                <div className="text-white/40 text-xs">{opt.desc}</div>
              </div>
              {intent === opt.value && (
                <span className="ml-auto text-purple-400">✓</span>
              )}
            </div>
          </button>
        ))}
      </div>

      <h2 className="text-lg font-bold mb-1">분위기</h2>
      <p className="text-white/40 text-sm mb-4">Spline 씬 선택에 반영됩니다</p>

      <div className="flex gap-3 mb-8">
        {MOOD_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => setMood(opt.value)}
            className={`glass-card flex-1 p-4 text-center transition-all ${
              mood === opt.value
                ? 'border-purple-500/50 bg-purple-500/10'
                : ''
            }`}
          >
            <div className="font-semibold text-sm">{opt.label}</div>
            <div className="text-white/40 text-xs mt-1">{opt.desc}</div>
          </button>
        ))}
      </div>

      <button
        onClick={handleSubmit}
        disabled={!intent || !mood || loading}
        className="btn-primary w-full py-4 text-base"
      >
        {loading ? '전송 중...' : '생성 시작 →'}
      </button>

      {jobId && (
        <p className="text-center text-white/20 text-xs mt-4">job: {jobId}</p>
      )}
    </MobileLayout>
  )
}
```

- [ ] **Step 2: 커밋**

```bash
git add dashboard/app/intent/
git commit -m "feat: /intent 페이지 — 모바일 의도 설정 UI"
```

---

## Task 5: `/review` 페이지

**Files:**
- Create: `dashboard/app/review/page.tsx`

- [ ] **Step 1: 페이지 작성**

```tsx
'use client'

import { useState } from 'react'
import { useSearchParams } from 'next/navigation'
import MobileLayout from '@/components/MobileLayout'

const MODIFY_OPTIONS = [
  { value: 'cta', label: 'CTA 문구 변경' },
  { value: 'color', label: '색상 / 분위기 조정' },
  { value: 'section', label: '섹션 순서 변경' },
  { value: 'scene', label: 'Spline 씬 변경' },
]

export default function ReviewPage() {
  const params = useSearchParams()
  const jobId = params.get('job_id') ?? ''
  const previewUrl = params.get('preview_url') ?? ''
  const repo = params.get('repo') ?? 'Unknown'
  const guildId = params.get('guild_id') ?? ''

  const [selected, setSelected] = useState<string[]>([])
  const [customNote, setCustomNote] = useState('')
  const [loading, setLoading] = useState(false)
  const [done, setDone] = useState(false)
  const [doneAction, setDoneAction] = useState<'approve' | 'cancel' | ''>('')

  function toggleModify(value: string) {
    setSelected((prev) =>
      prev.includes(value) ? prev.filter((v) => v !== value) : [...prev, value]
    )
  }

  async function handleAction(action: 'approve' | 'cancel') {
    setLoading(true)
    try {
      const res = await fetch('/api/confirm', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ job_id: jobId, action, guild_id: guildId }),
      })
      if (res.ok) {
        setDone(true)
        setDoneAction(action)
      } else {
        alert('오류가 발생했습니다. Discord에서 직접 처리해주세요.')
      }
    } catch {
      alert('네트워크 오류. Discord에서 직접 처리해주세요.')
    } finally {
      setLoading(false)
    }
  }

  if (done) {
    return (
      <MobileLayout title="Bucky" subtitle={repo}>
        <div className="text-center mt-16">
          <div className="text-5xl mb-4">
            {doneAction === 'approve' ? '✅' : '❌'}
          </div>
          <h2 className="text-xl font-bold mb-2">
            {doneAction === 'approve' ? '배포 요청 완료!' : '취소됨'}
          </h2>
          <p className="text-white/50 text-sm">
            Discord에서 결과를 확인하세요.
          </p>
        </div>
      </MobileLayout>
    )
  }

  return (
    <MobileLayout title="미리보기 확인" subtitle={repo}>
      {/* 미리보기 iframe */}
      {previewUrl ? (
        <div className="glass-card overflow-hidden mb-5" style={{ height: 220 }}>
          <iframe
            src={previewUrl}
            className="w-full h-full border-0 pointer-events-none"
            title="preview"
          />
        </div>
      ) : (
        <div className="glass-card flex items-center justify-center mb-5" style={{ height: 100 }}>
          <span className="text-white/30 text-sm">미리보기 URL 없음</span>
        </div>
      )}

      {previewUrl && (
        <a
          href={previewUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="block text-center text-purple-400 text-sm mb-6"
        >
          전체화면으로 보기 ↗
        </a>
      )}

      {/* 씬 변경 링크 */}
      {selected.includes('scene') && (
        <a
          href={`/scene?job_id=${jobId}&guild_id=${guildId}&repo=${repo}`}
          className="block glass-card p-3 text-center text-sm text-purple-300 mb-4"
        >
          🎨 씬 선택 대시보드 열기 →
        </a>
      )}

      {/* 수정 요청 체크박스 */}
      <h3 className="text-sm font-semibold text-white/60 mb-3">수정 요청 (선택)</h3>
      <div className="flex flex-col gap-2 mb-5">
        {MODIFY_OPTIONS.map((opt) => (
          <button
            key={opt.value}
            onClick={() => toggleModify(opt.value)}
            className={`glass-card p-3 text-left flex items-center gap-3 transition-all ${
              selected.includes(opt.value)
                ? 'border-purple-500/50 bg-purple-500/08'
                : ''
            }`}
          >
            <span
              className={`w-4 h-4 rounded border flex items-center justify-center text-xs ${
                selected.includes(opt.value)
                  ? 'bg-purple-500 border-purple-500'
                  : 'border-white/20'
              }`}
            >
              {selected.includes(opt.value) && '✓'}
            </span>
            <span className="text-sm">{opt.label}</span>
          </button>
        ))}
      </div>

      {/* 직접 입력 */}
      <textarea
        value={customNote}
        onChange={(e) => setCustomNote(e.target.value)}
        placeholder="추가 요청사항 직접 입력..."
        className="w-full glass-card p-3 text-sm text-white resize-none mb-6 bg-transparent outline-none placeholder-white/25"
        rows={3}
      />

      {/* 버튼 */}
      <div className="flex flex-col gap-3">
        <button
          onClick={() => handleAction('approve')}
          disabled={loading}
          className="btn-primary w-full py-4 text-base"
        >
          {loading ? '처리 중...' : '✅ 프로덕션 배포'}
        </button>
        <button
          onClick={() => handleAction('cancel')}
          disabled={loading}
          className="btn-secondary w-full py-3 text-sm"
        >
          ❌ 취소
        </button>
      </div>

      <p className="text-center text-white/20 text-xs mt-4">job: {jobId}</p>
    </MobileLayout>
  )
}
```

- [ ] **Step 2: 커밋**

```bash
git add dashboard/app/review/
git commit -m "feat: /review 페이지 — 미리보기 + 컨펌/취소 UI"
```

---

## Task 6: `/scene` 페이지 + `SceneGrid` 컴포넌트

**Files:**
- Create: `dashboard/app/scene/page.tsx`
- Create: `dashboard/components/SceneGrid.tsx`

- [ ] **Step 1: `SceneGrid` 컴포넌트 작성**

`dashboard/components/SceneGrid.tsx`:

```tsx
'use client'

import { useState, useEffect } from 'react'

interface Scene {
  id: string
  url: string
  thumbnail: string
  category: string[]
  mood: string[]
}

export default function SceneGrid({
  category,
  onSelect,
}: {
  category: string
  onSelect: (scene: Scene) => void
}) {
  const [scenes, setScenes] = useState<Scene[]>([])
  const [selected, setSelected] = useState<string>('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch(`/api/catalog?category=${category}`)
      .then((r) => r.json())
      .then((d) => {
        setScenes(d.scenes ?? [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [category])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <span className="text-white/30 text-sm">씬 불러오는 중...</span>
      </div>
    )
  }

  if (!scenes.length) {
    return (
      <div className="text-center py-12">
        <p className="text-white/30 text-sm">이 카테고리에 씬이 없습니다.</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-2 gap-3">
      {scenes.map((scene) => (
        <button
          key={scene.id}
          onClick={() => {
            setSelected(scene.id)
            onSelect(scene)
          }}
          className={`glass-card overflow-hidden text-left transition-all ${
            selected === scene.id ? 'border-purple-500/60 ring-1 ring-purple-500/40' : ''
          }`}
        >
          {/* 썸네일 */}
          <div
            className="w-full"
            style={{
              height: 100,
              background: scene.thumbnail
                ? `url(${scene.thumbnail}) center/cover`
                : 'linear-gradient(135deg, #9b59ff22, #ff6b6b11)',
            }}
          />
          <div className="p-2">
            <div className="text-xs font-medium truncate">{scene.id}</div>
            <div className="text-white/40 text-xs">{scene.mood.join(', ')}</div>
          </div>
          {selected === scene.id && (
            <div className="absolute top-2 right-2 bg-purple-500 rounded-full w-5 h-5 flex items-center justify-center text-xs">
              ✓
            </div>
          )}
        </button>
      ))}
    </div>
  )
}
```

- [ ] **Step 2: `/scene` 페이지 작성**

`dashboard/app/scene/page.tsx`:

```tsx
'use client'

import { useState } from 'react'
import { useSearchParams } from 'next/navigation'
import MobileLayout from '@/components/MobileLayout'
import SceneGrid from '@/components/SceneGrid'

const CATEGORIES = [
  { value: 'ai', label: 'AI' },
  { value: 'saas', label: 'SaaS' },
  { value: 'devtool', label: 'DevTool' },
  { value: 'game', label: 'Game' },
]

interface Scene {
  id: string
  url: string
  thumbnail: string
  category: string[]
  mood: string[]
}

export default function ScenePage() {
  const params = useSearchParams()
  const jobId = params.get('job_id') ?? ''
  const guildId = params.get('guild_id') ?? ''
  const repo = params.get('repo') ?? 'Unknown'
  const initCategory = params.get('category') ?? 'saas'

  const [category, setCategory] = useState(initCategory)
  const [selectedScene, setSelectedScene] = useState<Scene | null>(null)
  const [applying, setApplying] = useState(false)
  const [done, setDone] = useState(false)

  async function handleApply() {
    if (!selectedScene) return
    setApplying(true)

    const webhookUrl = process.env.NEXT_PUBLIC_BUCKY_PIPELINE_WEBHOOK ?? ''
    if (webhookUrl) {
      await fetch(webhookUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          content: `__BUCKY_SCENE_OVERRIDE__|${jobId}|${selectedScene.id}|${guildId}`,
        }),
      })
    }

    setDone(true)
    setApplying(false)
  }

  if (done) {
    return (
      <MobileLayout title="Bucky" subtitle={repo}>
        <div className="text-center mt-16">
          <div className="text-5xl mb-4">✅</div>
          <h2 className="text-xl font-bold mb-2">씬 변경 요청 완료!</h2>
          <p className="text-white/50 text-sm">
            Discord에서 재생성 결과를 확인하세요.
          </p>
        </div>
      </MobileLayout>
    )
  }

  return (
    <MobileLayout title="씬 선택" subtitle={repo}>
      {/* 카테고리 탭 */}
      <div className="flex gap-2 mb-5 overflow-x-auto">
        {CATEGORIES.map((cat) => (
          <button
            key={cat.value}
            onClick={() => setCategory(cat.value)}
            className={`px-4 py-2 rounded-full text-sm font-medium whitespace-nowrap transition-all ${
              category === cat.value
                ? 'btn-primary'
                : 'btn-secondary'
            }`}
          >
            {cat.label}
          </button>
        ))}
      </div>

      {/* 씬 그리드 */}
      <SceneGrid
        category={category}
        onSelect={(scene) => setSelectedScene(scene)}
      />

      {/* 적용 버튼 */}
      {selectedScene && (
        <div className="mt-6">
          <div className="glass-card p-3 mb-4 text-sm">
            <span className="text-white/40">선택된 씬: </span>
            <span className="font-medium">{selectedScene.id}</span>
          </div>
          <button
            onClick={handleApply}
            disabled={applying}
            className="btn-primary w-full py-4 text-base"
          >
            {applying ? '적용 중...' : '이 씬으로 재생성 →'}
          </button>
        </div>
      )}
    </MobileLayout>
  )
}
```

- [ ] **Step 3: 커밋**

```bash
git add dashboard/app/scene/ dashboard/components/SceneGrid.tsx
git commit -m "feat: /scene 페이지 + SceneGrid — Spline 씬 선택 UI"
```

---

## Task 7: 로컬 개발 서버 검증

- [ ] **Step 1: 환경변수 설정**

`dashboard/.env.local` 생성:

```bash
# Discord webhook (Plan 1에서 생성한 webhook URL)
BUCKY_CONFIRM_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN

# 파이프라인 webhook (같은 URL 또는 별도)
NEXT_PUBLIC_BUCKY_PIPELINE_WEBHOOK=https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN
```

`.env.local`을 `.gitignore`에 추가:
```bash
echo "dashboard/.env.local" >> .gitignore
```

- [ ] **Step 2: 개발 서버 실행**

```bash
cd dashboard
npm run dev
```

Expected: `http://localhost:3000` 에서 서버 실행됨

- [ ] **Step 3: `/intent` 페이지 모바일 확인**

브라우저에서:
```
http://localhost:3000/intent?job_id=test123&repo=arki-3d-APP&guild_id=12345
```

확인 항목:
- 375px 너비에서 레이아웃 깨짐 없음
- 의도 선택 시 카드 하이라이트 동작
- 분위기 선택 동작
- "생성 시작" 버튼 활성화/비활성화

- [ ] **Step 4: `/review` 페이지 확인**

```
http://localhost:3000/review?job_id=test123&repo=arki-3d-APP&guild_id=12345&preview_url=https://example.com
```

확인 항목:
- iframe 미리보기 표시
- "전체화면으로 보기" 링크 동작
- 수정 요청 체크박스 토글
- "씬 변경" 선택 시 씬 대시보드 링크 표시

- [ ] **Step 5: `/scene` 페이지 확인**

```
http://localhost:3000/scene?job_id=test123&repo=arki-3d-APP&guild_id=12345&category=ai
```

확인 항목:
- 카테고리 탭 전환
- SceneGrid 카드 렌더링 (카탈로그 API 호출)
- 씬 선택 시 "적용" 버튼 표시

- [ ] **Step 6: 커밋**

```bash
git add dashboard/.gitignore
git commit -m "chore: dashboard .env.local gitignore 추가"
```

---

## Task 8: Vercel 배포

- [ ] **Step 1: Vercel 프로젝트 생성**

```bash
cd dashboard
npx vercel --yes
```

프롬프트:
- `Set up and deploy "dashboard"?` → Y
- `Which scope?` → 계정 선택
- `Link to existing project?` → N
- `Project name?` → `bucky-dashboard`
- `In which directory is your code located?` → `./`

- [ ] **Step 2: 환경변수 설정**

```bash
npx vercel env add BUCKY_CONFIRM_WEBHOOK_URL production
# 값: Discord webhook URL 입력

npx vercel env add NEXT_PUBLIC_BUCKY_PIPELINE_WEBHOOK production
# 값: Discord webhook URL 입력
```

- [ ] **Step 3: 프로덕션 배포**

```bash
npx vercel --prod
```

Expected 출력:
```
✅  Production: https://bucky-dashboard.vercel.app [3s]
```

- [ ] **Step 4: Bot 환경변수 업데이트**

`.env` (또는 서버 환경변수):

```bash
BUCKY_DASHBOARD_URL=https://bucky-dashboard.vercel.app
```

Bot 재시작.

- [ ] **Step 5: 엔드투엔드 테스트**

Discord에서:
```
/pipeline url:https://github.com/jaeha81/arki-3d-APP
```

확인 흐름:
1. Discord "⚙️ 생성 중..." 메시지
2. Discord Preview 링크 + 버튼 3개 표시
3. "✏️ 대시보드에서 수정" 클릭 → `/review` URL 수신
4. 모바일에서 `/review` 열기 → iframe 표시
5. "✅ 프로덕션 배포" 탭 → Discord에서 배포 완료 알림 확인

- [ ] **Step 6: 최종 커밋**

```bash
cd "G:/내 드라이브/obsidian-agent-brain-system"
git add dashboard/
git commit -m "feat: Bucky 대시보드 Vercel 배포 완료"
```

---

## 완료 체크리스트

- [ ] `/intent` — 모바일 375px에서 의도/분위기 선택 동작
- [ ] `/review` — iframe 미리보기 + 승인/취소 버튼 Discord 연동
- [ ] `/scene` — 카탈로그 API 호출 + 씬 그리드 표시
- [ ] `/api/confirm` — Discord webhook 전송 확인
- [ ] `/api/catalog` — spline_catalog.json 읽기 확인
- [ ] Vercel 배포 URL 확인 (`https://bucky-dashboard.vercel.app`)
- [ ] Bot `BUCKY_DASHBOARD_URL` 환경변수 업데이트
- [ ] 엔드투엔드 플로우 1회 완주
- [ ] **Codex 독립 검수** (구현 완료 후 `/jh-codex-verify` 실행)
