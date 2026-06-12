# Collaboration Admin Workflow Design

Date: 2026-06-13
Scope: `docs/bni-proposal.html`, new admin dashboard page, intake/save endpoint, Discord/Bucky routing, development-request bridge, related tests

## Goal

Turn the collaboration inquiry section at the bottom of `docs/bni-proposal.html` into a real file-backed intake flow that:

1. accepts inquiry submissions coming from the public introduction page,
2. exposes them in an admin page gated by the admin password `ljh911314`,
3. lets the admin review details, write notes, change status, and trigger the next action,
4. routes approved work into the existing Wishket-style Discord/Bucky development loop,
5. allows Bucky to dispatch Claude implementation work and Codex review work from the same workflow.

The final system should reuse the existing Wishket proposal/development flow wherever practical instead of inventing a second orchestration model.

## Operating Model

### Intake source

`docs/bni-proposal.html` keeps its existing public-facing presentation, but its bottom collaboration form becomes a real submission surface instead of a visual-only contact block.

Submitted fields:

- requester name
- requester email
- company or team
- inquiry summary
- inquiry details
- budget
- target timeline
- reference links

This intake should produce a stable internal request record even when the admin page is opened later.

### Storage model

Each collaboration inquiry is stored under a dedicated inbox root:

```text
ObsidianVault/10_AgentBus/collab_inbox/
  20260613_103000_collab-4f3b9c8a.md
  20260613_104200_collab-a12d778e.md
```

Each file is a single source of truth for one inquiry. Markdown with frontmatter is preferred because it matches the existing AgentBus patterns and remains human-readable.

Required frontmatter fields:

```yaml
type: collab_inquiry
source: bni_collab_form
request_id: collab-4f3b9c8a
status: new
created_at: 2026-06-13T10:30:00+09:00
name: Hong Gil Dong
email: hello@example.com
company: Example Studio
budget: 500
timeline: 2026-Q3
summary: AI agent dashboard build
links:
  - https://example.com/brief
discord_dispatched: false
proposal_started: false
proposal_approved: false
development_requested: false
codex_review_requested: false
```

Body sections:

- inquiry detail body
- admin notes
- activity log

The body remains editable without changing schema rules.

### Admin page

The admin page is a single-screen operational dashboard, not a split workflow across multiple tools.

New page:

```text
docs/collab-admin.html
```

Screen layout:

- left column: inquiry list with status, summary, requester, date
- center/right main pane: selected inquiry detail
- lower or side panel: admin note editor and action buttons

Supported actions:

- mark status (`new`, `reviewing`, `proposal_in_progress`, `approved`, `development_requested`, `done`, `rejected`)
- save admin note
- dispatch to Discord
- start proposal workflow
- approve proposal
- create development request
- enqueue Codex review request

The screen should act as the operational control center for this channel.

## Authentication Model

### Admin password gate

The admin page is protected by a lightweight admin gate using the password `ljh911314`.

Phase-1 rule:

- access is blocked until the correct password is entered
- successful login stores a local authenticated flag in browser session storage
- the flag only unlocks `docs/collab-admin.html`

This is a practical access gate for the current static/dashboard environment, not a strong multi-user security system.

### Security constraint

Because the password is explicitly provided in the user objective, it can be wired for the current local/admin workflow. However, the design must keep the auth logic isolated so it can later move behind a server-side gate without rewriting the admin UI.

The password should not be spread across multiple files or embedded into unrelated dashboards.

## Workflow Model

### Inquiry states

The collaboration inquiry state machine is:

1. `new`
   - inquiry submitted from public page
   - visible in admin inbox
   - no external dispatch yet

2. `reviewing`
   - admin opened and is evaluating the inquiry
   - admin notes may be added

3. `proposal_in_progress`
   - admin triggered proposal start
   - Discord/Bucky receives a collaboration proposal request
   - a dedicated workspace is created for this inquiry

4. `proposal_ready`
   - proposal draft exists
   - admin can approve or request revision

5. `approved`
   - proposal approved
   - development request is unlocked

6. `development_requested`
   - admin triggered development routing
   - Bucky routes Claude implementation and Codex review requests

7. `done`
   - work completed or handed off

8. `rejected`
   - inquiry closed without further action

### Shared workflow root

Collaboration inquiries should use a parallel workspace model to the Wishket flow:

```text
ObsidianVault/10_AgentBus/collab_dev/<request-slug>/
  status.json
  proposal-v1.md
  proposal-v2.md
  feedback.md
  development-request.md
```

The purpose is not to merge data stores blindly, but to keep the flow shape compatible with `wishket_proposal_workflow.py`.

### Status schema

The per-inquiry `status.json` should carry only operational fields:

```json
{
  "request_id": "collab-4f3b9c8a",
  "request_slug": "collab-4f3b9c8a-ai-agent-dashboard-build",
  "workflow_state": "proposal_in_progress",
  "proposal_version": 1,
  "current_proposal_file": "proposal-v1.md",
  "feedback_count": 0,
  "approved": false,
  "approved_via": null,
  "approved_at": null,
  "development_requested": false,
  "discord_dispatched": true,
  "codex_review_requested": false,
  "updated_at": "2026-06-13T11:00:00+09:00"
}
```

Proposal and note bodies stay in Markdown files, not JSON blobs.

## Routing and Orchestration

### New intake type family

This channel should not impersonate Wishket. It needs its own payload types while sharing the same orchestration style.

Recommended new types:

- `collab_inquiry`
- `collab_proposal_request`
- `collab_feedback`
- `collab_proposal_approval`
- `collab_development_request`

### Discord dispatch

When the admin clicks `Discord 전송` or `제안서 시작`, the system sends a structured payload to the existing Bucky/Discord intake path.

Required payload fields:

- `type`
- `request_id`
- `request_slug`
- `source`
- `project_title` or `summary`
- `requester_name`
- `requester_email`
- `company`
- `budget`
- `timeline`
- `summary`
- `body`
- `links`
- `requested_actions`

The message must state that this originated from the collaboration inquiry inbox, not from Wishket.

### Development routing

When the admin triggers `개발요청 실행`, the system should create a normalized internal development request using a new script that mirrors the structure of `scripts/wishket_development_request.py`.

New script:

```text
scripts/collab_development_request.py
```

Responsibilities:

- normalize collaboration inquiry payloads
- split immediate versus approval-required actions
- create inbox files for Claude implementation routing
- create inbox files for Codex review routing
- enforce proposal approval before development dispatch

### Bucky role

Bucky remains the orchestration layer. Collaboration inquiries should become one more structured source feeding the same AgentBus workflow:

- public page produces inquiry file
- admin page promotes inquiry into proposal/development actions
- Discord/Bucky receives structured requests
- Claude performs implementation work
- Codex receives independent review request

This preserves the existing ecosystem instead of bypassing it.

## File Responsibilities

### `docs/bni-proposal.html`

Changes:

- convert the current bottom collaboration block into a real intake form
- add client-side submission logic
- show submission success/failure state
- add an admin entry link to `collab-admin.html`

This page should not contain admin-only logic beyond linking to the admin screen.

### `docs/collab-admin.html`

New responsibilities:

- password gate UI
- inquiry list rendering
- inquiry detail rendering
- note editing
- status update controls
- action buttons for Discord/proposal/development/review routing

This page is the human control plane for the channel.

### `scripts/collab_inquiry_store.py`

New helper script or module for:

- creating inbox files from public-form submissions
- loading inquiry list
- updating status and notes
- appending activity entries

This should keep frontmatter/body parsing out of UI-facing scripts.

### `scripts/collab_proposal_workflow.py`

New helper script or adapted parallel module for:

- ensuring workspace creation under `collab_dev`
- recording proposal start
- recording feedback
- recording approval
- marking development requested

The API should intentionally resemble `wishket_proposal_workflow.py`.

### `scripts/collab_development_request.py`

New router for collaboration-origin work:

- normalize inquiry into development payload
- produce Claude implementation inbox file
- optionally produce Codex review inbox file
- require approved proposal state before dispatch

### `scripts/discord_bot.py`

Changes:

- handle new `collab_proposal_request`
- handle new `collab_feedback`
- handle new `collab_proposal_approval`
- optionally handle `collab_development_request`

The bot should update collaboration workflow state just as it already does for Wishket.

## UI Behavior

### Public inquiry form

Required user behavior:

- submit button disabled while request is in flight
- inline validation for required fields
- success toast or confirmation panel after save
- form reset after successful submission

The page should remain usable on mobile and desktop.

### Admin dashboard

Required behavior:

- inquiry list sorted newest first
- visible state badge per inquiry
- selected inquiry remains stable while notes are edited
- action buttons disabled when prerequisites are not met
- clear audit log after each action

Example gating:

- `제안서 시작` disabled once proposal already started
- `제안 승인` only enabled when a proposal draft exists
- `개발요청 실행` only enabled when proposal is approved
- `Codex 검수 요청` only enabled after development request exists

## Error Handling

### Public form

- invalid required input should block submission locally
- failed save should surface a retryable error
- partial writes are not acceptable; each inquiry must either be saved fully or not at all

### Admin actions

- stale or missing inquiry file should show a clear error
- attempting development dispatch before approval should raise an explicit approval error
- duplicate dispatch should be idempotent where possible by reusing `request_id`

### Discord/Bucky routing

- if Discord dispatch fails, local inquiry status should not falsely claim it succeeded
- if Claude/Codex inbox file creation succeeds, that should be logged even if later steps fail

## Testing

### New tests

Add tests for:

- collaboration inquiry payload normalization
- file creation for new collaboration inquiries
- admin note/status update logic
- proposal approval gating before development dispatch
- Claude/Codex routing file creation for collaboration requests
- Discord bot support for collaboration payload types

### Regression coverage

Keep existing Wishket tests passing and add targeted assertions so the new collaboration flow does not break:

- Wishket proposal workflow routing
- Wishket development dispatch
- dashboard payload integrity

### HTML/static checks

Add assertions for:

- public collaboration form presence
- admin link presence
- admin password gate elements
- action button presence in `collab-admin.html`

## Non-Goals

This phase does not include:

- full multi-user authentication
- encrypted password storage
- email server ingestion from IMAP/Gmail inboxes
- payment processing
- replacing the existing Wishket workflow

The immediate target is to operationalize collaboration inquiries end to end inside the current dashboard environment.
