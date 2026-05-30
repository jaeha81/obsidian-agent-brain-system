---
type: bucky-packet
project: "{{project}}"
agent: "{{agent}}"
created: "{{date}}"
status: draft
---

# Bucky 지침 패킷

> `scripts/bucky_packet_gen.py --project <repo> --goal <goal>` 로 자동 생성 가능.

---

## goal
{{goal}}

## baseline
{{baseline}}

## target_state
{{target_state}}

## scope
{{scope}}

## role
{{role}}

## constraints
- 커밋·푸시는 사용자 명시 승인 후
- 파일 삭제·이동은 dry-run 먼저
- {{extra_constraints}}

## context_packs
- ObsidianVault/00_System/BUCKY_OS_RUNBOOK.md
- {{context_pack_1}}

## references
- {{reference_1}}

## verification
```
{{verification_command}}
```

## done_when
{{done_when}}

## record_path
{{record_path}}

## next_action
{{next_action}}
