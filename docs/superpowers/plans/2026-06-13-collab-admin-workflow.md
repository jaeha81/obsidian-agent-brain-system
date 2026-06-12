# Collaboration Admin Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the public collaboration inquiry section into a file-backed admin workflow that supports admin login, inquiry triage, Discord/Bucky proposal routing, and development-request dispatch into the existing Claude/Codex loop.

**Architecture:** Keep the public page static, but route submissions into `ObsidianVault/10_AgentBus/collab_inbox/` and manage them through a new static admin page backed by small Python file-workflow helpers. Reuse the Wishket operating model by introducing collaboration-specific workflow helpers and request dispatchers that create AgentBus inbox files for Claude implementation and Codex review after proposal approval.

**Tech Stack:** Static HTML/JS, Python (`unittest`, `json`, `pathlib`, markdown/frontmatter-style text files), existing AgentBus inbox conventions, existing `scripts/discord_bot.py`

---

## File Map

- Create: `scripts/collab_inquiry_store.py`
  - Inquiry file creation, loading, note updates, status updates, activity logging.
- Create: `scripts/collab_proposal_workflow.py`
  - Per-request workspace and `status.json` transitions for collaboration-origin proposals.
- Create: `scripts/collab_development_request.py`
  - Normalize a collaboration inquiry into Claude/Codex routing files.
- Create: `docs/collab-admin.html`
  - Password-gated single-screen admin control surface.
- Modify: `docs/bni-proposal.html`
  - Convert bottom collaboration block into a real submission surface with admin link.
- Modify: `scripts/discord_bot.py`
  - Add handlers for collaboration proposal, feedback, approval, and development request payloads.
- Modify: `tests/test_dashboard_intake_payloads.py`
  - Static assertions for the new collaboration public/admin HTML markers.
- Create: `tests/test_collab_inquiry_store.py`
  - Store behavior and file-shape coverage.
- Create: `tests/test_collab_proposal_workflow.py`
  - Collaboration proposal state-machine coverage.
- Create: `tests/test_collab_development_request.py`
  - Dispatch gating and routing output coverage.

### Task 1: Add Collaboration Inquiry Store

**Files:**
- Create: `scripts/collab_inquiry_store.py`
- Create: `tests/test_collab_inquiry_store.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_create_inquiry_writes_markdown_file(self):
    payload = {
        "name": "홍길동",
        "email": "hello@example.com",
        "company": "Example Studio",
        "summary": "AI agent dashboard build",
        "body": "Need proposal and development support.",
        "budget": "500",
        "timeline": "2026-Q3",
        "links": ["https://example.com/brief"],
    }
    path = store.create_inquiry(payload)
    text = path.read_text(encoding="utf-8")
    self.assertIn("type: \"collab_inquiry\"", text)
    self.assertIn("status: \"new\"", text)
    self.assertIn("Need proposal and development support.", text)

def test_update_status_appends_activity_log(self):
    path = store.create_inquiry(self.payload)
    store.update_status(path, "reviewing", actor="admin")
    text = path.read_text(encoding="utf-8")
    self.assertIn("status: \"reviewing\"", text)
    self.assertIn("admin changed status to reviewing", text)

def test_save_admin_note_persists_note_section(self):
    path = store.create_inquiry(self.payload)
    store.save_admin_note(path, "Need quick callback.")
    text = path.read_text(encoding="utf-8")
    self.assertIn("## Admin Notes", text)
    self.assertIn("Need quick callback.", text)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_collab_inquiry_store -v`
Expected: `ImportError` or `FAIL` because `scripts/collab_inquiry_store.py` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
COLLAB_INBOX = VAULT / "10_AgentBus" / "collab_inbox"

def create_inquiry(payload: dict[str, Any]) -> Path:
    normalized = normalize_inquiry(payload)
    path = COLLAB_INBOX / f"{_stamp()}_{normalized['request_id']}.md"
    path.write_text(render_inquiry_markdown(normalized), encoding="utf-8")
    return path

def update_status(path: Path, status: str, actor: str = "admin") -> Path:
    record = load_inquiry(path)
    record["frontmatter"]["status"] = status
    record["activity"].append(f"{_iso()} {actor} changed status to {status}")
    write_inquiry(path, record)
    return path

def save_admin_note(path: Path, note: str) -> Path:
    record = load_inquiry(path)
    record["admin_notes"] = note.strip()
    record["activity"].append(f"{_iso()} admin saved note")
    write_inquiry(path, record)
    return path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_collab_inquiry_store -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/collab_inquiry_store.py tests/test_collab_inquiry_store.py
git commit -m "feat: add collaboration inquiry store"
```

### Task 2: Add Collaboration Proposal Workflow State

**Files:**
- Create: `scripts/collab_proposal_workflow.py`
- Create: `tests/test_collab_proposal_workflow.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_ensure_workspace_bootstraps_status_json(self):
    workspace = workflow.ensure_workspace(self.payload)
    status = json.loads((workspace / "status.json").read_text(encoding="utf-8"))
    self.assertEqual(status["workflow_state"], "new")
    self.assertFalse(status["approved"])

def test_mark_proposal_started_updates_state(self):
    workflow.ensure_workspace(self.payload)
    status = workflow.mark_proposal_started(self.payload, "admin")
    self.assertEqual(status["workflow_state"], "proposal_in_progress")
    self.assertTrue(status["discord_dispatched"])

def test_record_approval_unlocks_development(self):
    workflow.ensure_workspace(self.payload)
    status = workflow.record_approval(self.payload, "admin")
    self.assertEqual(status["workflow_state"], "approved")
    self.assertTrue(status["approved"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_collab_proposal_workflow -v`
Expected: `ImportError` or `FAIL` because the workflow helper does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
WORKFLOW_ROOT = VAULT / "10_AgentBus" / "collab_dev"

def ensure_workspace(payload: dict[str, Any]) -> Path:
    slug = payload["request_slug"]
    workspace = WORKFLOW_ROOT / slug
    workspace.mkdir(parents=True, exist_ok=True)
    status_path = workspace / "status.json"
    if not status_path.exists():
        status_path.write_text(json.dumps(default_status(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    return workspace

def mark_proposal_started(payload: dict[str, Any], source: str) -> dict[str, Any]:
    status = load_status(payload["request_slug"])
    status["workflow_state"] = "proposal_in_progress"
    status["discord_dispatched"] = True
    status["updated_via"] = source
    return save_status(payload["request_slug"], status)

def record_approval(payload: dict[str, Any], source: str) -> dict[str, Any]:
    status = load_status(payload["request_slug"])
    status["workflow_state"] = "approved"
    status["approved"] = True
    status["approved_via"] = source
    return save_status(payload["request_slug"], status)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_collab_proposal_workflow -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/collab_proposal_workflow.py tests/test_collab_proposal_workflow.py
git commit -m "feat: add collaboration proposal workflow state"
```

### Task 3: Add Collaboration Development Request Router

**Files:**
- Create: `scripts/collab_development_request.py`
- Create: `tests/test_collab_development_request.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_normalize_payload_builds_request_slug_and_actions(self):
    payload = router.normalize_payload({
        "request_id": "collab-1234",
        "summary": "AI dashboard build",
        "email": "hello@example.com",
    })
    self.assertEqual(payload["type"], "collab_development_request")
    self.assertIn("route_to_claude_for_implementation", payload["requested_actions"])

def test_dispatch_rejects_unapproved_workflow(self):
    payload = router.normalize_payload(self.base_payload)
    workflow.ensure_workspace(payload)
    with self.assertRaisesRegex(PermissionError, "approved"):
        router.dispatch_request(payload, require_workflow_approval=True)

def test_dispatch_creates_claude_and_codex_inbox_files_after_approval(self):
    payload = router.normalize_payload(self.base_payload)
    workflow.ensure_workspace(payload)
    workflow.record_approval(payload, "admin")
    mode, claude_path, codex_path = router.dispatch_request(payload, require_workflow_approval=True)
    self.assertEqual(mode, "immediate")
    self.assertTrue(claude_path.exists())
    self.assertTrue(codex_path.exists())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_collab_development_request -v`
Expected: `ImportError` or `FAIL` because the collaboration dispatcher does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
REQUEST_TYPE = "collab_development_request"

def normalize_payload(data: dict[str, Any]) -> dict[str, Any]:
    summary = str(data.get("summary") or "").strip()
    request_id = str(data.get("request_id") or uuid.uuid4())
    request_slug = safe_slug(summary, fallback=request_id)
    return {
        "type": REQUEST_TYPE,
        "request_id": request_id,
        "request_slug": request_slug,
        "project_title": summary or request_slug,
        "summary": summary,
        "email": str(data.get("email") or "").strip(),
        "requested_actions": [
            "generate_development_plan",
            "route_to_claude_for_implementation",
            "route_to_codex_for_review",
        ],
    }

def dispatch_request(payload: dict[str, Any], require_workflow_approval: bool = False) -> tuple[str, Path, Path]:
    if require_workflow_approval:
        status = workflow.load_status(payload["request_slug"])
        if not status.get("approved"):
            raise PermissionError("Collaboration proposal workflow is not approved yet.")
    claude_path = enqueue_claude_request(payload)
    codex_path = enqueue_codex_review_request(payload)
    workflow.mark_development_requested(payload, "admin")
    return "immediate", claude_path, codex_path
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_collab_development_request -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/collab_development_request.py tests/test_collab_development_request.py
git commit -m "feat: add collaboration development request routing"
```

### Task 4: Add Collaboration Discord Intake Handlers

**Files:**
- Modify: `scripts/discord_bot.py`
- Modify: `tests/test_dashboard_intake_payloads.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_discord_bot_handles_collab_proposal_payload(self):
    bot = read_text("scripts/discord_bot.py")
    self.assertIn('"collab_proposal_request"', bot)
    self.assertIn("_handle_collab_proposal_request", bot)

def test_discord_bot_handles_collab_feedback_and_approval(self):
    bot = read_text("scripts/discord_bot.py")
    self.assertIn('"collab_feedback"', bot)
    self.assertIn('"collab_proposal_approval"', bot)
    self.assertIn("_handle_collab_feedback_payload", bot)
    self.assertIn("_handle_collab_proposal_approval_payload", bot)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_dashboard_intake_payloads.RouterFieldConsistencyTests -v`
Expected: `FAIL` because collaboration payload markers are not present yet.

- [ ] **Step 3: Write minimal implementation**

```python
async def _handle_collab_proposal_request(payload: dict, channel) -> bool:
    if payload.get("type") != "collab_proposal_request":
        return False
    from collab_development_request import normalize_payload
    import collab_proposal_workflow as workflow
    normalized = normalize_payload(payload)
    workflow.ensure_workspace(normalized)
    workflow.mark_proposal_started(normalized, "discord")
    await channel.send(f"**Collaboration proposal started**\n- request: `{normalized['request_slug']}`")
    return True

async def _handle_collab_proposal_approval_payload(payload: dict, channel) -> bool:
    if payload.get("type") != "collab_proposal_approval":
        return False
    from collab_development_request import normalize_payload
    import collab_proposal_workflow as workflow
    normalized = normalize_payload(payload)
    workflow.record_approval(normalized, "discord")
    await channel.send(f"**Collaboration proposal approved**\n- request: `{normalized['request_slug']}`")
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_dashboard_intake_payloads.RouterFieldConsistencyTests -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/discord_bot.py tests/test_dashboard_intake_payloads.py
git commit -m "feat: add collaboration discord intake handlers"
```

### Task 5: Convert Public Collaboration Section Into Real Intake

**Files:**
- Modify: `docs/bni-proposal.html`
- Modify: `tests/test_dashboard_intake_payloads.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_bni_page_has_collab_submission_form(self):
    html = read_text("docs/bni-proposal.html")
    self.assertIn('id="collab-inquiry-form"', html)
    self.assertIn('name="requester_email"', html)
    self.assertIn("submitCollabInquiry", html)

def test_bni_page_links_to_admin_dashboard(self):
    html = read_text("docs/bni-proposal.html")
    self.assertIn('href="collab-admin.html"', html)
    self.assertIn("협업문의 관리자", html)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_dashboard_intake_payloads -v`
Expected: `FAIL` because the current public page does not expose a real collaboration intake form or admin link markers.

- [ ] **Step 3: Write minimal implementation**

```html
<form id="collab-inquiry-form">
  <input name="requester_name" required>
  <input name="requester_email" type="email" required>
  <input name="company">
  <input name="budget">
  <textarea name="summary" required></textarea>
  <textarea name="body" required></textarea>
  <button type="submit" id="collab-submit-btn">문의 보내기</button>
</form>
<a href="collab-admin.html">협업문의 관리자</a>
```

```javascript
async function submitCollabInquiry(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const payload = {
    type: "collab_inquiry",
    requester_name: form.requester_name.value.trim(),
    requester_email: form.requester_email.value.trim(),
    company: form.company.value.trim(),
    summary: form.summary.value.trim(),
    body: form.body.value.trim(),
  };
  // save locally or post to the local intake bridge
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_dashboard_intake_payloads -v`
Expected: `OK` for the new public collaboration markers.

- [ ] **Step 5: Commit**

```bash
git add docs/bni-proposal.html tests/test_dashboard_intake_payloads.py
git commit -m "feat: add collaboration inquiry intake form"
```

### Task 6: Build Password-Gated Collaboration Admin Page

**Files:**
- Create: `docs/collab-admin.html`
- Modify: `tests/test_dashboard_intake_payloads.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_collab_admin_page_has_password_gate(self):
    html = read_text("docs/collab-admin.html")
    self.assertIn("ljh911314", html)
    self.assertIn("sessionStorage", html)
    self.assertIn("collab-admin-auth", html)

def test_collab_admin_page_has_required_action_controls(self):
    html = read_text("docs/collab-admin.html")
    self.assertIn("Discord 전송", html)
    self.assertIn("제안서 시작", html)
    self.assertIn("개발요청 실행", html)
    self.assertIn("Codex 검수 요청", html)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_dashboard_intake_payloads -v`
Expected: `FAIL` because `docs/collab-admin.html` does not exist yet.

- [ ] **Step 3: Write minimal implementation**

```html
<div id="collab-admin-login">
  <input id="collab-admin-password" type="password">
  <button onclick="unlockCollabAdmin()">로그인</button>
</div>
<section id="collab-admin-app" hidden>
  <aside id="collab-inquiry-list"></aside>
  <main id="collab-inquiry-detail"></main>
  <textarea id="collab-admin-note"></textarea>
  <button>Discord 전송</button>
  <button>제안서 시작</button>
  <button>개발요청 실행</button>
  <button>Codex 검수 요청</button>
</section>
```

```javascript
function unlockCollabAdmin() {
  const value = document.getElementById("collab-admin-password").value;
  if (value === "ljh911314") {
    sessionStorage.setItem("collab-admin-auth", "ok");
    renderCollabAdmin();
  }
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_dashboard_intake_payloads -v`
Expected: `OK` for the new admin page markers.

- [ ] **Step 5: Commit**

```bash
git add docs/collab-admin.html tests/test_dashboard_intake_payloads.py
git commit -m "feat: add collaboration admin dashboard shell"
```

### Task 7: Wire Admin Actions To Collaboration Workflow Helpers

**Files:**
- Modify: `docs/collab-admin.html`
- Modify: `scripts/collab_inquiry_store.py`
- Modify: `scripts/collab_proposal_workflow.py`
- Modify: `scripts/collab_development_request.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_mark_development_requested_updates_workflow_status(self):
    workflow.ensure_workspace(self.payload)
    workflow.record_approval(self.payload, "admin")
    status = workflow.mark_development_requested(self.payload, "admin")
    self.assertTrue(status["development_requested"])
    self.assertEqual(status["workflow_state"], "development_requested")
```

Add static assertion:

```python
self.assertIn("saveCollabAdminNote", html)
self.assertIn("dispatchCollabDevelopmentRequest", html)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_collab_proposal_workflow tests.test_dashboard_intake_payloads -v`
Expected: `FAIL` because development-request state and admin action hooks are not fully connected yet.

- [ ] **Step 3: Write minimal implementation**

```python
def mark_development_requested(payload: dict[str, Any], source: str) -> dict[str, Any]:
    status = load_status(payload["request_slug"])
    status["development_requested"] = True
    status["workflow_state"] = "development_requested"
    status["updated_via"] = source
    return save_status(payload["request_slug"], status)
```

```javascript
async function dispatchCollabDevelopmentRequest() {
  // load selected inquiry payload
  // call local bridge or emit structured intake payload
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_collab_proposal_workflow tests.test_dashboard_intake_payloads -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add docs/collab-admin.html scripts/collab_proposal_workflow.py scripts/collab_development_request.py
git commit -m "feat: wire collaboration admin actions to workflow"
```

### Task 8: Full Verification Pass

**Files:**
- Verify only

- [ ] **Step 1: Run focused collaboration tests**

Run: `python -m unittest tests.test_collab_inquiry_store tests.test_collab_proposal_workflow tests.test_collab_development_request -v`
Expected: `OK`

- [ ] **Step 2: Run existing impacted regression tests**

Run: `python -m unittest tests.test_wishket_development_request tests.test_dashboard_intake_payloads -v`
Expected: `OK`

- [ ] **Step 3: Run cache-free syntax verification**

Run:

```powershell
@'
from pathlib import Path
for rel in [
    'scripts/collab_inquiry_store.py',
    'scripts/collab_proposal_workflow.py',
    'scripts/collab_development_request.py',
    'scripts/discord_bot.py',
]:
    source = Path(rel).read_text(encoding='utf-8')
    compile(source, rel, 'exec')
print('COMPILE_OK')
'@ | python -
```

Expected: `COMPILE_OK`

- [ ] **Step 4: Rebuild or preview the relevant dashboards**

Run:

```bash
python scripts/generate_wishket_dashboard.py
```

Expected: dashboard regeneration completes without removing the new collaboration admin links or breaking existing Wishket workflow markers.

- [ ] **Step 5: Browser verification**

Run local preview and confirm:

- `http://127.0.0.1:8879/bni-proposal.html` shows a real collaboration form and admin link
- `http://127.0.0.1:8879/collab-admin.html` shows password gate
- entering `ljh911314` reveals inquiry list/detail/action controls

- [ ] **Step 6: Commit**

```bash
git add docs/bni-proposal.html docs/collab-admin.html scripts/collab_inquiry_store.py scripts/collab_proposal_workflow.py scripts/collab_development_request.py scripts/discord_bot.py tests/test_collab_inquiry_store.py tests/test_collab_proposal_workflow.py tests/test_collab_development_request.py tests/test_dashboard_intake_payloads.py
git commit -m "feat: add collaboration admin workflow"
```

## Self-Review

- Spec coverage: public intake, admin auth, admin dashboard actions, proposal gating, Discord/Bucky routing, Claude/Codex request creation, and verification are all mapped to tasks above.
- Placeholder scan: no `TODO`, `TBD`, or vague “add tests later” steps remain.
- Type consistency: the plan consistently uses `request_id`, `request_slug`, `collab_inquiry`, `collab_proposal_request`, and `collab_development_request` across all tasks.
