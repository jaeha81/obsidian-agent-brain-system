# Wishket Proposal Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a file-backed Wishket proposal workflow so each posting can move through proposal creation, feedback, approval, and only then unlock development request dispatch.

**Architecture:** Store per-project workflow state in a dedicated Wishket development folder under `ObsidianVault/10_AgentBus/wishket_dev/`. Keep proposal and feedback bodies as Markdown files, with button gating driven by `status.json` injected into the static dashboard by the Wishket generator and updated through dashboard intake and Discord intake handlers.

**Tech Stack:** Python (`unittest`, file I/O, JSON), static HTML/JS in `docs/wishket.html`, existing Bucky intake flow in `scripts/discord_bot.py`

---

## File Map

- Create: `scripts/wishket_proposal_workflow.py`
  - Central helper for per-project folder paths, `status.json` load/save, proposal/feedback/approval transitions.
- Modify: `scripts/generate_wishket_dashboard.py`
  - Inject workflow status and latest proposal preview/download metadata into `docs/wishket.html`.
- Modify: `scripts/wishket_development_request.py`
  - Refuse dispatch until workflow approval exists; write `development-request.md` into the project folder on dispatch.
- Modify: `scripts/discord_bot.py`
  - Handle `wishket_proposal_request`, `wishket_feedback`, and `wishket_proposal_approval`.
- Modify: `docs/wishket.html`
  - Replace `Discord` button with `제안서 만들기`, add feedback/approval UI, and disable `개발요청` until approved.
- Modify: `tests/test_wishket_development_request.py`
  - Add gating tests tied to workflow approval state.
- Modify: `tests/test_dashboard_intake_payloads.py`
  - Add static dashboard assertions for new Wishket UI markers/payloads.
- Create: `tests/test_wishket_proposal_workflow.py`
  - State helper tests for bootstrap, transitions, and path generation.

### Task 1: Add Workflow State Helper

**Files:**
- Create: `scripts/wishket_proposal_workflow.py`
- Test: `tests/test_wishket_proposal_workflow.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_ensure_project_workspace_bootstraps_status_file(self):
    workspace = workflow.ensure_project_workspace(self.payload)
    status = json.loads((workspace / "status.json").read_text(encoding="utf-8"))
    self.assertEqual(status["workflow_state"], "idle")
    self.assertFalse(status["approved"])

def test_mark_proposal_ready_updates_version_and_file(self):
    workspace = workflow.ensure_project_workspace(self.payload)
    status = workflow.mark_proposal_ready(self.payload, "proposal-v1.md")
    self.assertEqual(status["workflow_state"], "proposal_ready")
    self.assertEqual(status["proposal_version"], 1)

def test_record_approval_allows_dashboard_or_discord_source(self):
    workspace = workflow.ensure_project_workspace(self.payload)
    workflow.record_approval(self.payload, "dashboard")
    status = workflow.load_status(self.payload["project_slug"])
    self.assertTrue(status["approved"])
    self.assertEqual(status["approved_via"], "dashboard")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_wishket_proposal_workflow -v`
Expected: `FAIL` or `ImportError` because `scripts/wishket_proposal_workflow.py` and its APIs do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
WORKFLOW_ROOT = VAULT / "10_AgentBus" / "wishket_dev"

def ensure_project_workspace(payload: dict[str, Any]) -> Path:
    slug = payload["project_slug"]
    workspace = WORKFLOW_ROOT / slug
    workspace.mkdir(parents=True, exist_ok=True)
    status_path = workspace / "status.json"
    if not status_path.exists():
        status_path.write_text(json.dumps(default_status(payload), ensure_ascii=False, indent=2), encoding="utf-8")
    return workspace

def mark_proposal_ready(payload: dict[str, Any], filename: str) -> dict[str, Any]:
    status = load_status(payload["project_slug"])
    status["workflow_state"] = "proposal_ready"
    status["proposal_version"] = _extract_version(filename)
    status["current_proposal_file"] = filename
    return save_status(payload["project_slug"], status)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_wishket_proposal_workflow -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add tests/test_wishket_proposal_workflow.py scripts/wishket_proposal_workflow.py
git commit -m "feat: add wishket proposal workflow state helpers"
```

### Task 2: Gate Development Requests on Approval

**Files:**
- Modify: `scripts/wishket_development_request.py`
- Modify: `tests/test_wishket_development_request.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_dispatch_request_rejects_unapproved_workflow(self):
    payload = normalize_payload({...})
    with self.assertRaisesRegex(PermissionError, "approved"):
        dispatch_request(payload, require_workflow_approval=True)

def test_dispatch_request_allows_approved_workflow(self):
    payload = normalize_payload({...})
    workflow.record_approval(payload, "dashboard")
    mode, claude_path, codex_path = dispatch_request(payload, require_workflow_approval=True)
    self.assertEqual(mode, "immediate")
    self.assertTrue(claude_path.exists())
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_wishket_development_request.TestRoutingOutputs -v`
Expected: `FAIL` because `dispatch_request` does not check workflow approval yet.

- [ ] **Step 3: Write minimal implementation**

```python
def ensure_workflow_approved(payload: dict[str, Any]) -> None:
    status = proposal_workflow.load_status(payload["project_slug"])
    if not status.get("approved"):
        raise PermissionError("Wishket proposal workflow is not approved yet.")

def dispatch_request(payload: dict[str, Any], require_workflow_approval: bool = False) -> tuple[str, Path, Path | None]:
    if require_workflow_approval:
        ensure_workflow_approved(payload)
    ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_wishket_development_request.TestRoutingOutputs -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add tests/test_wishket_development_request.py scripts/wishket_development_request.py
git commit -m "feat: gate wishket development requests on approval"
```

### Task 3: Inject Workflow State Into Dashboard

**Files:**
- Modify: `scripts/generate_wishket_dashboard.py`
- Modify: `tests/test_dashboard_intake_payloads.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_wishket_dashboard_injects_workflow_status_map(self):
    html = read_text("docs/wishket.html")
    self.assertIn("const WORKFLOW_STATUS =", html)
    self.assertIn("workflow_state", html)

def test_wishket_dashboard_renders_proposal_create_button_marker(self):
    html = read_text("docs/wishket.html")
    self.assertIn("function getWishketWorkflowStatus", html)
    self.assertIn("제안서 만들기", html)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_dashboard_intake_payloads.WishketDashboardIntakePayloadTests -v`
Expected: `FAIL` because workflow markers are not present yet.

- [ ] **Step 3: Write minimal implementation**

```python
def load_workflow_statuses() -> dict:
    statuses = {}
    for status_path in sorted(WORKFLOW_ROOT.glob("*/status.json")):
        status = json.loads(status_path.read_text(encoding="utf-8"))
        statuses[status["project_id"]] = status
    return statuses

updated = re.sub(
    r"(// .*WORKFLOW STATUS.*\n)const WORKFLOW_STATUS = \{[\s\S]*?\};",
    lambda m: m.group(1) + "const WORKFLOW_STATUS = " + json.dumps(load_workflow_statuses(), ensure_ascii=False, indent=2) + ";",
    updated,
)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_dashboard_intake_payloads.WishketDashboardIntakePayloadTests -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add tests/test_dashboard_intake_payloads.py scripts/generate_wishket_dashboard.py
git commit -m "feat: inject wishket workflow state into dashboard"
```

### Task 4: Update Wishket Dashboard Actions

**Files:**
- Modify: `docs/wishket.html`
- Modify: `tests/test_dashboard_intake_payloads.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_wishket_dashboard_replaces_discord_button_with_proposal_request(self):
    html = read_text("docs/wishket.html")
    self.assertNotIn(">Discord<", html)
    self.assertIn(">제안서 만들기<", html)
    self.assertIn("type:'wishket_proposal_request'", html)

def test_wishket_dashboard_keeps_development_request_disabled_before_approval(self):
    html = read_text("docs/wishket.html")
    self.assertIn("disabled: !status.approved", html)
    self.assertIn("sendProposalFeedback", html)
    self.assertIn("approveProposal", html)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_dashboard_intake_payloads.WishketDashboardIntakePayloadTests -v`
Expected: `FAIL` because the UI still renders `Discord` and ungated `개발요청`.

- [ ] **Step 3: Write minimal implementation**

```javascript
function getWishketWorkflowStatus(id) {
  return WORKFLOW_STATUS[id] || { workflow_state: 'idle', approved: false, proposal_version: 0 };
}

async function requestWishketProposal(id) {
  const payload = { type:'wishket_proposal_request', ... };
  await postToIntake(payload);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_dashboard_intake_payloads.WishketDashboardIntakePayloadTests -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add docs/wishket.html tests/test_dashboard_intake_payloads.py
git commit -m "feat: add wishket proposal workflow actions"
```

### Task 5: Add Discord Proposal, Feedback, and Approval Intake

**Files:**
- Modify: `scripts/discord_bot.py`
- Modify: `tests/test_dashboard_intake_payloads.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_wishket_bot_handles_proposal_request_payload(self):
    bot = read_text("scripts/discord_bot.py")
    self.assertIn('"wishket_proposal_request"', bot)
    self.assertIn("_handle_wishket_proposal_payload", bot)

def test_wishket_bot_handles_feedback_and_approval_payloads(self):
    bot = read_text("scripts/discord_bot.py")
    self.assertIn('"wishket_feedback"', bot)
    self.assertIn('"wishket_proposal_approval"', bot)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_dashboard_intake_payloads.RouterFieldConsistencyTests -v`
Expected: `FAIL` because the new payload handlers do not exist yet.

- [ ] **Step 3: Write minimal implementation**

```python
async def _handle_wishket_proposal_payload(payload, channel):
    normalized = normalize_payload(payload)
    workspace = wishket_proposal_workflow.ensure_project_workspace(normalized)
    wishket_proposal_workflow.mark_proposal_started(normalized)
    await channel.send(...)
    return True
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_dashboard_intake_payloads.RouterFieldConsistencyTests -v`
Expected: `OK`

- [ ] **Step 5: Commit**

```bash
git add scripts/discord_bot.py tests/test_dashboard_intake_payloads.py
git commit -m "feat: handle wishket proposal workflow intake"
```

### Task 6: End-to-End Verification

**Files:**
- Verify: `scripts/wishket_proposal_workflow.py`
- Verify: `scripts/wishket_development_request.py`
- Verify: `scripts/generate_wishket_dashboard.py`
- Verify: `scripts/discord_bot.py`
- Verify: `docs/wishket.html`

- [ ] **Step 1: Run targeted unit tests**

```bash
python -m unittest tests.test_wishket_proposal_workflow -v
python -m unittest tests.test_wishket_development_request -v
python -m unittest tests.test_dashboard_intake_payloads.WishketDashboardIntakePayloadTests -v
```

- [ ] **Step 2: Run syntax validation**

```bash
@'
from pathlib import Path
for rel in [
    "scripts/wishket_proposal_workflow.py",
    "scripts/wishket_development_request.py",
    "scripts/generate_wishket_dashboard.py",
    "scripts/discord_bot.py",
]:
    source = Path(rel).read_text(encoding="utf-8")
    compile(source, rel, "exec")
print("COMPILE_OK")
'@ | python -
```

- [ ] **Step 3: Regenerate and visually verify dashboard**

```bash
python scripts/generate_wishket_dashboard.py
```

Expected:
- `docs/wishket.html` contains `제안서 만들기`
- pre-approval cards keep `개발요청` disabled
- proposal-ready cards expose `제안서 다운로드` and `피드백`

- [ ] **Step 4: Commit**

```bash
git add scripts/wishket_proposal_workflow.py scripts/wishket_development_request.py scripts/generate_wishket_dashboard.py scripts/discord_bot.py docs/wishket.html tests/test_wishket_proposal_workflow.py tests/test_wishket_development_request.py tests/test_dashboard_intake_payloads.py
git commit -m "feat: add wishket proposal workflow"
```
