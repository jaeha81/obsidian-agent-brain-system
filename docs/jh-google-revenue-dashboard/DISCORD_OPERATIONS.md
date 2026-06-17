# Discord Operations

## Channel

Create this channel when Discord admin access is available:

```text
jh-google-revenue-dashboard
```

Recommended category:

```text
JH Revenue OS
```

## Message Types

| Type | Purpose |
|---|---|
| `queue.created` | A keyword, draft, review, or KPI request entered AgentBus |
| `review.waiting` | Human review is required before publication or external send |
| `policy.blocked` | A forbidden action was requested and blocked |
| `metrics.weekly` | Weekly pageview, RPM, lead, and content summary |
| `make.ready` | Make.com payload is prepared but not sent |

## Credential Rule

Do not store Discord bot tokens, webhook URLs, channel ids, or OAuth secrets in this repository. Use environment variables or Discord/Make.com secret storage.

Suggested environment variable names:

```text
DISCORD_BOT_TOKEN
DISCORD_GUILD_ID
DISCORD_JH_GOOGLE_REVENUE_CHANNEL_ID
MAKE_JH_GOOGLE_REVENUE_WEBHOOK_URL
```

## Approval Rule

The following require explicit user approval:

- Create or delete Discord channels.
- Send external Discord messages from automation.
- Trigger Make.com webhooks.
- Publish Blogger drafts.
- Submit AdSense review or change monetization settings.
