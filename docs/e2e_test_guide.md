# End-to-End Test Guide
> Phase 8 — Obsidian Agent Brain System
> Created: 2026-05-22

## Overview

End-to-end verification of all integrated subsystems. Run after any major change or new phase completion.

---

## Pre-Conditions

- [ ] `configs/paths.json` exists with correct paths (not committed)
- [ ] `external_data/legalize-kr/` synced (`bash scripts/legalize_sync.sh`)
- [ ] `ObsidianVault/` open in Obsidian desktop app

---

## Test 1 — Graphify Build

```bash
python -m graphify ObsidianVault/ --output ObsidianVault/03_Projects/graphify-out/
```

**Pass criteria:**
- `graphify-out/graph.json` created/updated
- `graphify-out/GRAPH_REPORT.md` shows nodes > 0, edges > 0
- No import errors

---

## Test 2 — Graphify → AgentBus Bridge

```bash
python scripts/agentbus_graphify_bridge.py \
  --project ObsidianVault \
  --graph ObsidianVault/03_Projects/graphify-out \
  --context-pack ObsidianVault/06_Context_Packs/Graphify/ObsidianVault_graphify_pack.md
```

**Pass criteria:**
- File created at `ObsidianVault/10_AgentBus/context_requests/graphify/YYYYMMDD_*.md`
- Frontmatter contains `type: context_request`, `source: graphify`, `status: pending`
- Body contains node/edge counts; does NOT contain raw graph.json content

---

## Test 3 — LegalizeKR Search

```bash
legalize search "건축법"
```

**Pass criteria:**
- Returns ≥ 1 result
- No import/path errors

---

## Test 4 — Legal Context Pack Generation

```bash
python scripts/legalize_context_pack.py \
  --topic "도시계획법_기초" \
  --laws "도시계획법" \
  --output "ObsidianVault/06_Context_Packs/Legal/도시계획법_기초_legal_pack.md"
```

**Pass criteria:**
- Output file created
- Contains law name, article summary, frontmatter with `type: context_pack`

---

## Test 5 — legalize-mcp Server Import Check

```bash
python -c "import scripts.legalize_mcp_server; print('OK')"
```

Or dry-run via mcp dev:
```bash
python scripts/legalize_mcp_server.py
```
(Ctrl+C after startup; should not crash before accepting input)

**Pass criteria:**
- No ImportError
- Prints startup indication or waits on stdin

---

## Test 6 — Codex Review Request

```bash
python scripts/codex_request.py \
  --task-id TEST_001 \
  --subject "E2E 테스트용 리뷰 요청" \
  --files "scripts/session_end.py,scripts/codex_request.py" \
  --priority P2
```

**Pass criteria:**
- File created at `ObsidianVault/10_AgentBus/outbox/ClaudeCode/P2_*_Codex_TEST_001.md`
- Frontmatter: `from: ClaudeCode`, `to: Codex`, `status: pending`
- File list appears in body

---

## Test 7 — Session End Protocol

```bash
python scripts/session_end.py \
  --agent ClaudeCode \
  --task "E2E Test Run" \
  --result "완료" \
  --notes "Phase 8 E2E 테스트 검증"
```

**Pass criteria:**
- `ObsidianVault/10_AgentBus/reports/ClaudeCode/YYYYMMDD_*_session_report.md` created
- `ObsidianVault/00_System/HANDOFF_LOG.md` has new entry
- `ObsidianVault/00_System/AGENT_STATE.md` shows `status: standby`

---

## Test 8 — Voice Intake

```bash
echo "테스트 음성 메모입니다." > /tmp/test_transcript.txt
python scripts/voice_intake.py --file /tmp/test_transcript.txt
```

On Windows:
```powershell
"테스트 음성 메모입니다." | Out-File -FilePath "$env:TEMP\test_transcript.txt" -Encoding utf8
python scripts/voice_intake.py --file "$env:TEMP\test_transcript.txt"
```

**Pass criteria:**
- File created at `ObsidianVault/10_AgentBus/inbox/YYYYMMDD_*_voice_test_transcript.md`
- `type: voice_transcript` in frontmatter
- Transcript content in body

---

## Test 9 — Discord Intake

Create a sample file `test_discord.txt`:
```
[2026-05-22 10:00] user1: 건축법 검색해줘
[2026-05-22 10:01] user2: 좋아, 지금 실행할게
```

```bash
python scripts/discord_intake.py --file test_discord.txt --channel test-channel
```

**Pass criteria:**
- File created at `ObsidianVault/10_AgentBus/inbox/YYYYMMDD_*_discord_test-channel_*.md`
- `type: discord_intake`, `channel: test-channel` in frontmatter
- Message content in body

---

## Full Flow Summary

```
Voice/Discord Input
    → scripts/voice_intake.py / discord_intake.py
    → 10_AgentBus/inbox/

Graphify Build
    → graphify_build.sh
    → agentbus_graphify_bridge.py
    → 10_AgentBus/context_requests/graphify/

LegalizeKR
    → legalize_context_pack.py
    → 06_Context_Packs/Legal/

Codex Review Request
    → codex_request.py
    → 10_AgentBus/outbox/ClaudeCode/

Session End
    → session_end.py
    → 10_AgentBus/reports/ClaudeCode/
    → 00_System/HANDOFF_LOG.md
    → 00_System/AGENT_STATE.md
```

---

## Notes

- Phase 9 (Existing Vault Migration) is out of scope for automated E2E — requires manual review
- graph.json must NEVER appear in LLM prompts — verify agentbus_graphify_bridge.py output only contains GRAPH_REPORT.md stats
- All test output files in `ObsidianVault/` are gitignored by design
