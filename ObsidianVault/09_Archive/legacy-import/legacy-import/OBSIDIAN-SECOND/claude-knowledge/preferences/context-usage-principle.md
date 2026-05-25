# Context Usage Principle

> Created from 2026-05-16 ops update. Source PC: home PC (user1).

## Principle

Use the smallest current source that can answer the question. When the user provides a complete summary, treat that summary as working context and avoid reading the underlying file unless verification is needed.

## Plan Mode / Empty Project Exception

If a project appears empty or the source path is unknown, do not perform broad exploration. Ask for or infer the intended source, then inspect narrowly.

## PC Environment Detection

Detect PC environment with low-cost checks only, such as `Test-Path` and `whoami`. Do not read global instructions or large logs only to identify the PC.
