# Wishket Proposal Workflow Design

Date: 2026-06-13
Scope: `docs/wishket.html`, `scripts/generate_wishket_dashboard.py`, `scripts/discord_bot.py`, `scripts/wishket_development_request.py`, related tests

## Goal

Restructure the Wishket dashboard card actions into a controlled pre-development workflow:

1. `제안서 만들기` starts proposal work and sends a kickoff message to the Wishket Discord channel.
2. Proposal artifacts are stored in a dedicated per-project Wishket development folder.
3. The dashboard exposes proposal download and feedback actions after the first draft exists.
4. Feedback can be collected from both the dashboard and Discord.
5. Final approval can be granted from either the dashboard or Discord.
6. `개발요청` stays disabled until final approval is recorded.

This flow must keep dashboard state deterministic and file-backed, without depending on transient browser state.

## Operating Model

### Per-project folder

Each Wishket posting gets its own folder under a dedicated Wishket development root. The folder name uses the project slug already derived from the posting URL/title.

Example:

```text
ObsidianVault/10_AgentBus/wishket_dev/<project-slug>/
  status.json
  proposal-v1.md
  proposal-v2.md
  feedback.md
  final-proposal.md
  development-request.md
```

### Mixed storage strategy

- Proposal and feedback bodies are stored as Markdown documents for direct human editing and archive value.
- UI state is stored in `status.json`.
- The dashboard reads `status.json` to decide button label, enabled/disabled state, and next allowed action.

This keeps the UI logic simple while preserving readable artifacts.

## Workflow States

### State machine

The card-level workflow is:

1. `idle`
   - Visible actions: `공고보기`, `응찰기록`/`탈락`, `제안서 만들기`
   - Hidden/disabled: `피드백`, `개발요청`

2. `proposal_in_progress`
   - Trigger: user clicks `제안서 만들기`
   - Effects:
     - send Discord kickoff message to the Wishket channel
     - create project folder if missing
     - create initial `status.json`
     - request proposal generation

3. `proposal_ready`
   - Trigger: first proposal file exists and `status.json` records a ready draft
   - Visible actions:
     - `제안서 다운로드`
     - `피드백`
   - Disabled:
     - `개발요청`

4. `feedback_in_progress`
   - Trigger: dashboard feedback submission or Discord feedback intake
   - Effects:
     - append/update `feedback.md`
     - mark pending revision in `status.json`
     - allow revision upload/regeneration

5. `revision_ready`
   - Trigger: revised proposal file saved
   - Visible actions:
     - latest proposal download
     - `피드백`
     - approval actions
   - Disabled:
     - `개발요청`

6. `approved`
   - Trigger: dashboard approval or Discord approval message
   - Effects:
     - record approval source and timestamp in `status.json`
     - enable `개발요청`

7. `development_requested`
   - Trigger: user clicks `개발요청` after approval
   - Effects:
     - write `development-request.md`
     - dispatch existing Wishket development request flow

### Minimal status schema

`status.json` should carry only decision-making fields:

```json
{
  "project_id": "project-155733",
  "project_slug": "python-langchain-ai-backend",
  "workflow_state": "proposal_ready",
  "proposal_version": 2,
  "current_proposal_file": "proposal-v2.md",
  "feedback_count": 1,
  "feedback_pending": false,
  "approved": false,
  "approved_via": null,
  "approved_at": null,
  "development_requested": false,
  "last_discord_message_type": "proposal_started",
  "updated_at": "2026-06-13T10:00:00+09:00"
}
```

The implementation should avoid duplicating full proposal or feedback bodies inside JSON.

## UI Changes

## Card actions

Current `Discord` button is replaced with `제안서 만들기`.

Revised action policy:

- `제안서 만들기`
  - available only before the first draft exists
- `제안서 다운로드`
  - replaces `제안서 만들기` once a draft exists
  - always downloads the latest active proposal file
- `피드백`
  - enabled after a proposal exists
  - opens a modal with:
    - direct feedback textarea
    - submit button for dashboard feedback
    - Discord feedback request action
- `개발요청`
  - disabled until `approved == true`

The card should also expose a compact state badge such as:

- `제안서 작성중`
- `피드백 대기`
- `수정본 준비`
- `최종 승인`
- `개발요청 접수`

## Modal behavior

Two modals are needed:

1. Proposal modal
   - already exists in `docs/wishket.html`
   - must support downloading the latest proposal file, not just previewing inline text

2. Feedback modal
   - new
   - collects dashboard-entered feedback
   - can trigger a Discord feedback request message for the same project

## Discord and Intake Behavior

### Proposal kickoff

When `제안서 만들기` is clicked:

- send a structured intake payload to the existing Bucky intake endpoint
- target channel remains the Wishket channel
- payload type should be separate from `wishket_briefing` and `wishket_development_request`
- recommended new type: `wishket_proposal_request`

Required payload fields:

- project title
- request id
- posting URL
- budget
- summary
- project slug
- desired action: `start_proposal`

Discord-facing result:

- channel receives a clear kickoff message that proposal work has started
- the message should not imply development has started

### Feedback intake

Feedback can arrive by two routes:

1. Dashboard submission
   - writes/updates `feedback.md`
   - posts a compact Discord notice that feedback was received

2. Discord message/command
   - bot parses approval/feedback payload or command
   - updates the matching project folder state

### Approval intake

Approval can arrive by two routes:

1. Dashboard final approval action
2. Discord approval action/message

Both routes must converge on the same `status.json` update logic so the button gating remains consistent.

## Generator and File Responsibilities

### `scripts/generate_wishket_dashboard.py`

Responsibilities to add:

- load per-project workflow status from the Wishket development root
- inject a `WORKFLOW_STATUS` object into `docs/wishket.html`
- continue injecting proposal preview data, but align it with the latest proposal file from workflow state

The generator should be the single source for static dashboard rendering state.

### `docs/wishket.html`

Responsibilities to change:

- replace `Discord` action with `제안서 만들기`
- render `제안서 다운로드`, `피드백`, and disabled/enabled `개발요청` based on injected workflow state
- add feedback modal
- add client-side handlers for:
  - proposal request
  - feedback submission
  - Discord feedback request
  - dashboard approval
  - development request gate checking

### `scripts/discord_bot.py`

Responsibilities to add:

- recognize `wishket_proposal_request`
- send the kickoff response/message to the Wishket channel
- record feedback and approval updates coming from Discord
- reuse the current intake path instead of creating a second transport

### `scripts/wishket_development_request.py`

Responsibilities to change:

- enforce that development dispatch only proceeds when workflow approval is recorded
- optionally write `development-request.md` into the per-project folder as the local audit artifact

## Error Handling

The dashboard should fail closed:

- if no workflow folder/status exists, show `제안서 만들기`
- if `status.json` is malformed, keep `개발요청` disabled and surface a toast error
- if proposal kickoff Discord send succeeds but file creation fails, the state remains non-approved and `개발요청` stays disabled
- if approval signals conflict, the latest valid approval event wins and is logged in status metadata

The system should never enable `개발요청` based only on the presence of a proposal file.

## Testing Strategy

### Server-side tests

Add or extend tests for:

- per-project folder/bootstrap creation
- `status.json` transitions across proposal, feedback, revision, approval, development request
- dashboard generator injection of workflow state
- development request rejection before approval
- approval acceptance from both dashboard and Discord inputs

### Dashboard/UI tests

Add focused tests for:

- initial state renders `제안서 만들기`
- proposal-ready state renders `제안서 다운로드` and `피드백`
- pre-approval state keeps `개발요청` disabled
- approved state enables `개발요청`

### Verification scope

Keep verification modular:

- targeted unittest modules only
- direct syntax validation for touched Python files
- browser check on `http://127.0.0.1:8879/wishket.html` after regeneration

## Implementation Boundaries

Included:

- Wishket dashboard button/state flow
- file-backed proposal workflow state
- Discord intake for proposal start, feedback, and approval
- final gate before development request

Excluded for now:

- PDF export
- multi-user locking
- generalized workflow engine for non-Wishket dashboards
- external storage/database migration

## Recommended Implementation Order

1. Introduce workflow storage helpers and tests.
2. Add generator support for workflow status injection.
3. Update dashboard UI rendering and client actions.
4. Extend Discord intake handling for proposal/feedback/approval.
5. Gate development request execution on approval state.
6. Verify end-to-end on the local dashboard.
