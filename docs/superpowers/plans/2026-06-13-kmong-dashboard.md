# Kmong Dashboard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an independent Kmong monetization dashboard that routes work through Bucky, supports Bucky-managed login requests, and keeps customer-facing actions approval-gated.

**Architecture:** Reuse the existing static dashboard -> local Bucky intake -> Discord channel pattern. Keep credential material out of HTML, source, logs, and AgentBus notes by reading login settings from environment variables only and reporting challenge states instead of bypassing them.

**Tech Stack:** Python standard library, static HTML/JS, existing Bucky `/intake` queue, Discord bot dashboard routing.

---

## File Map

- Create: `scripts/kmong_workflow.py`
  - Normalizes Kmong login/work payloads, defines approval-required actions, writes safe AgentBus notes, and validates credential-source policy.
- Create: `tests/test_kmong_workflow.py`
  - Covers payload normalization, approval gate splitting, login challenge status, and no-secret rendering.
- Create: `docs/kmong.html`
  - Static dashboard for login status, sync requests, inquiry cards, work-state tracking, and Bucky intake buttons.
- Modify: `scripts/discord_bot.py`
  - Adds `JH_KMONG_CHANNEL_ID`, auto channel registration, intake channel allow-list, and dashboard type routing for `kmong`.
- Modify: `tests/test_intake_channel_allowed.py`
  - Adds `JH_KMONG_CHANNEL_ID` to intake registration coverage.
- Modify: `tests/test_dashboard_intake_payloads.py`
  - Adds static assertions for the Kmong dashboard payload and security markers.

## Tasks

- [ ] Write failing tests for `kmong_workflow`, dashboard markers, and Discord intake registration.
- [ ] Implement `scripts/kmong_workflow.py` with no external login side effects by default.
- [ ] Add `docs/kmong.html` as a static Bucky intake dashboard.
- [ ] Wire `kmong` into `scripts/discord_bot.py` channel registration and intake map.
- [ ] Run focused tests: `python -m unittest tests.test_kmong_workflow tests.test_intake_channel_allowed tests.test_dashboard_intake_payloads -v`.
- [ ] Run cache-free syntax checks for changed Python files.
