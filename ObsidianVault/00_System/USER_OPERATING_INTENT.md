---
type: operating-intent
status: active
created: 2026-06-15
owner: user
---

# User Operating Intent

The Obsidian Brain System is the user's long-term operating system for agent-assisted work.

The system must preserve the user's accumulated investment, context, rules, and project structure while still allowing growth, expansion, upgrades, evolution, and improvement.

## Why This System Exists

The Obsidian Brain System was built to make AI use more efficient, not more chaotic.

Its core purpose is:

1. Efficient AI use
2. Stronger memory across sessions
3. Efficient context management
4. User feedback driven evolution
5. Daily Plus and GPT conversation capture
6. Obsidian knowledge-base strengthening
7. Selective retrieval through LLM Wiki, Graphify, Context Packs, and exact references

If these functions are not working, the system is failing its reason for existing.

## Top-Level Goal

Restore and stabilize the Obsidian Brain System after the post-2026-06-05 drift period, then maintain it as a reliable user-centered operating system.

## Knowledge Growth Loop

The user has invested significant time using Daily Plus and GPT conversations to strengthen the Obsidian Brain System. This feedback loop is core infrastructure, not optional content.

The intended loop is:

1. User explores and refines ideas through GPT and Daily Plus.
2. Important signals are saved into the Obsidian knowledge base.
3. The knowledge base becomes a curated library, not a raw context dump.
4. Existing LLM Wiki, Graphify, Context Packs, and related routing tools help agents find the right knowledge.
5. Agents read targeted, relevant knowledge instead of loading all content.
6. New learning improves future work without bloating every prompt.

## Knowledge Base Rule

Do not treat "important" as meaning "every AI must read everything." Important knowledge must be stored, indexed, connected, and retrieved selectively.

The Obsidian knowledge base should function like a library:

- Daily Plus captures evolving user thinking.
- LLM Wiki organizes reusable knowledge.
- Graphify exposes relationships and navigation.
- Context Packs provide compact operating packets.
- Agents should use targeted retrieval and exact references.

## Core Requirements

1. User intent outranks temporary task momentum.
2. Each project folder should carry its own local instruction packet.
3. Bucky orchestrates real work; Charlie audits system integrity.
4. Codex reviews independently and can implement only when explicitly asked.
5. Claude Code implements, but must not override user authority or project instructions.
6. Changes to instructions, routing, dashboards, Discord, Daily Plus, or runtime behavior require evidence-backed verification.
7. Growth and improvement are welcome when they preserve system balance.
8. Drift, stale context, role invasion, and repeated errors must be recorded and prevented.
9. Daily Plus and the Obsidian knowledge feedback loop must be protected as a primary user investment.
10. Knowledge retrieval must be selective, indexed, and evidence-backed instead of broad context dumping.
11. Session feedback and user corrections must become durable improvements instead of disappearing in the next session.

## Shared Degradation Rule

The critical failure to prevent is not one bad answer from one agent. The critical failure is when Bucky, Codex, and Claude Code all become less capable together because the user's requests, local instructions, and Bucky context create conflicting or stale operating signals.

When that happens, agents must stop treating the latest small task as the whole mission. They must return to this operating intent, identify the authority conflict, and report the recovery path.

## Local Instruction Packet Rule

When work starts in a folder, the folder should have enough local instruction context for Codex and Claude Code to operate without depending on live Bucky memory.

Minimum packet:

- `AGENTS.md` for Codex behavior
- `CLAUDE.md` for Claude Code behavior
- `OPERATING_INTENT.md` when the project has user-specific long-term goals

If the packet is missing, agents should stop broad work and request or generate a project instruction packet for user approval.

## Recovery Priority

1. Protect current user data and vault structure.
2. Identify authority conflicts.
3. Separate normal improvement from drift.
4. Restore reliable instruction flow.
5. Rebuild runtime confidence with direct evidence.
6. Add monitoring only where it prevents repeat failure.

## Charlie Guardrail

Charlie must remain an audit and maintenance system. It should not become another orchestration layer. Its default action is to detect, record, classify, and report.

## Efficiency Rule

Do not make the user pay token cost for agents relaying instructions to each other in loops. Assign work clearly:

- Codex handles independent review, deterministic checks, and explicit implementation.
- Claude Code handles implementation only inside approved scope.
- Bucky handles practical work orchestration.
- Charlie handles system audit and drift prevention.

If an agent can complete its assigned work from local instructions, it should proceed without asking another agent to restate the same instructions.

## Session Continuity Rule

The system must not lose improvements, user corrections, or operating lessons when a chat session grows too large.

Agents must treat excessive context use, repeated restatement, and late-session confusion as operational risks. When a session should end or move to a new session, the agent must brief the user with:

1. Why the session should end now.
2. What was changed or learned.
3. Which files hold the durable state.
4. What the next session must read first.
5. What must not be repeated.

Session handoff exists to preserve user investment. It is not optional cleanup.
