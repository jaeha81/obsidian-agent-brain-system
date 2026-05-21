# Agent Config Example
> Copy this file as `agent_config.md` and fill in actual values.
> DO NOT commit `agent_config.md` — it contains local paths.

## Claude Code Settings

```yaml
claude_code:
  context_window_limit: 100000  # tokens
  max_file_read_lines: 200       # 대형 파일 읽기 제한
  vault_root: "{obsidian_vault}" # paths.json 의 obsidian_vault 참조
  agentbus_inbox: "{obsidian_vault}/10_AgentBus/inbox"
  agentbus_outbox: "{obsidian_vault}/10_AgentBus/outbox/ClaudeCode"
```

## Graphify Settings

```yaml
graphify:
  source_dir: "{obsidian_vault}/03_Projects"
  output_dir: "{google_drive}/external_data/graphify_selected"
  ignore_file: "{github_repo}/.graphifyignore"
  max_files_per_run: 500
```

## LegalizeKR Settings

```yaml
legalize_kr:
  data_dir: "{google_drive}/external_data/legalize-kr"
  mode: "mcp"  # "cli" 또는 "mcp"
  context_pack_output: "{obsidian_vault}/06_Context_Packs/Legal"
```

## Backup Settings

```yaml
backup:
  source: "{obsidian_vault}"
  destination: "{google_drive}/backups"
  retention_days: 30
  naming: "vault-backup-{YYYYMMDD}"
```
