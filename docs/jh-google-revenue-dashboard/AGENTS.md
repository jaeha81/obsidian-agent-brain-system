# JH-구글자동화수익대시보드 Agents

## Project Role

This project builds a safe Blogger and AdSense revenue automation dashboard. Codex may implement inside this project scope while Bucky is unavailable. When Bucky is restored, Bucky receives compact AgentBus packets and manages the operating queue.

## Agent Roster

### KeywordScout

- Scores keywords by search intent, monetization connection, and JH expertise.
- Allowed actions: `score_keyword`, `sync_manual_metrics`.
- Does not publish content.

### ContentDraft

- Creates outlines, article drafts, FAQ blocks, and Blogger draft packets.
- Allowed actions: `draft_outline`, `draft_article`, `draft_blogger_post`.
- Every output requires `human_review_required: true`.

### PolicyGuard

- Checks AdSense policy, invalid traffic risk, spam risk, and generative AI content quality.
- Allowed actions: `run_policy_check`, `create_review_packet`.
- Blocks forbidden actions.

### HumanReview

- Records the human approval state before publication or external send.
- Required before `publish_blogger_draft`, `send_make_webhook`, `request_adsense_review`, or public release.

### RevenueAnalyst

- Tracks pageviews, RPM, leads, indexed URLs, and content queue health.
- Allowed actions: `update_kpi_snapshot`, `sync_manual_metrics`.

### MakeBridge

- Prepares Make.com webhook packets for Sheets, Gmail, Discord, and Blogger draft support.
- External sends require approval.
- Webhook URLs must stay in environment variables or the Make.com UI, not in files.

### DiscordOps

- Uses `#jh-google-revenue-dashboard` as the project channel contract.
- Channel creation and report sends require user approval and Discord credentials outside the repo.

## Forbidden Actions

- `click_ads`
- `self_click_ads`
- `ask_others_to_click_ads`
- `simulate_traffic`
- `buy_traffic`
- `mass_publish`
- `auto_publish_without_review`
- `generate_low_value_content`
- `bypass_adsense_policy`
- `scrape_private_data`

## Handoff Rule

AgentBus notes are written to:

```text
ObsidianVault/10_AgentBus/jh_google_revenue_inbox/
```

Each note must include request id, execution mode, approval-required actions, blocked actions, and human-review status.
