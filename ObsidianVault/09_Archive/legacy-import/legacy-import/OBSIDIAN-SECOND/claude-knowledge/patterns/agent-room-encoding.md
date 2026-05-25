# Agent Room Encoding Pattern

> Created from 2026-05-16 session-state sync. Source PC: home PC (user1).

## Pattern

Agent Room JSONL is append-only shared state. Prefer PowerShell `Get-Content -Encoding UTF8` and `ConvertFrom-Json` for parsing on Windows.

## Avoid

- Do not parse large Agent Room logs with broad full-file reads unless bounded by tail, date, speaker, status, or loop id.
- Do not assume mojibake text is authoritative when a UTF-8 parse path is available.
- Do not mark review items done without checking the referenced loop id and current status.

## Useful Query Shape

Filter by `speaker`, `target`, `status`, `taskType`, `replyTo`, and recent `createdAt` before summarizing.
