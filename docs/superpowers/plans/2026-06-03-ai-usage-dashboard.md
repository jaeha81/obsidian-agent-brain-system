# AI Usage Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a static dashboard that shows Codex and Claude Code subscription usage, recommended allocation, reset-window planning, and fallback actions when usage limits interrupt development.

**Architecture:** Reuse `scripts/subscription_roi.py` as the collection and calculation layer. Add a focused static HTML generator under `scripts/generate_ai_usage_dashboard.py`, then link `docs/ai-usage.html` from the public dashboards.

**Tech Stack:** Python standard library, existing Codex/Claude JSONL session logs, static GitHub Pages HTML.

---

### Task 1: Subscription Usage Calculations

**Files:**
- Modify: `scripts/subscription_roi.py`
- Test: `tests/test_subscription_roi.py`

- [x] **Step 1: Write failing tests**

Add tests that build in-memory `AgentReport` samples and assert utilization, cost per session, and fallback recommendations.

- [x] **Step 2: Run tests to verify failure**

Run: `python -m unittest tests.test_subscription_roi -v`
Expected before implementation: import errors for the new calculation functions.

- [x] **Step 3: Implement calculations**

Add configurable monthly cost, reset-hours, target session helpers, and a compact recommendation function.

- [x] **Step 4: Re-run tests**

Run: `python -m unittest tests.test_subscription_roi -v`
Expected: PASS.

### Task 2: Static Dashboard Generator

**Files:**
- Create: `scripts/generate_ai_usage_dashboard.py`
- Create: `docs/ai-usage.html`
- Test: `tests/test_subscription_roi.py`

- [x] **Step 1: Write failing dashboard marker test**

Assert rendered HTML includes `AI Usage`, `Claude Code`, `Codex`, reset-window text, and fallback guardrails.

- [x] **Step 2: Implement generator**

Generator collects 7-day and 30-day reports, renders a static operational page, and writes `docs/ai-usage.html`.

- [x] **Step 3: Run generator**

Run: `python scripts/generate_ai_usage_dashboard.py`
Expected: writes `docs/ai-usage.html`.

### Task 3: Public Dashboard Links

**Files:**
- Modify: `docs/index.html`
- Modify: `scripts/generate_daily_plus_dashboard.py`
- Regenerate: `docs/daily-plus.html`

- [x] **Step 1: Add navigation links**

Add `AI Usage` links to the repo dashboard and Daily Plus generated nav.

- [x] **Step 2: Regenerate Daily Plus dashboard**

Run: `python scripts/generate_daily_plus_dashboard.py`
Expected: `docs/daily-plus.html` contains the `AI Usage` nav link.

### Task 4: Verification

**Files:**
- Verify: `scripts/subscription_roi.py`
- Verify: `scripts/generate_ai_usage_dashboard.py`
- Verify: `docs/ai-usage.html`

- [x] **Step 1: Run focused tests**

Run: `python -m unittest tests.test_subscription_roi -v`

- [x] **Step 2: Compile without pycache writes**

Run: `$env:PYTHONDONTWRITEBYTECODE='1'; python -m py_compile scripts\subscription_roi.py scripts\generate_ai_usage_dashboard.py`

- [x] **Step 3: Inspect git diff**

Run: `git diff -- scripts/subscription_roi.py scripts/generate_ai_usage_dashboard.py tests/test_subscription_roi.py docs/index.html scripts/generate_daily_plus_dashboard.py docs/ai-usage.html docs/daily-plus.html`

No commit or push in this repo unless the user explicitly changes the AGENTS.md rule.
