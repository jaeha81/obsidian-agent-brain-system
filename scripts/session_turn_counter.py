import sys, json, os, tempfile, datetime

HANDOFF_DIR = "G:/내 드라이브/obsidian-agent-brain-system/ObsidianVault/10_AgentBus/handoffs/ClaudeCode"
WARN_TURN = 15
BLOCK_TURN = 25

def write_handoff(count, session_id):
    """세션 전환 핸드오프 노트 기록 — SessionStart 훅이 다음 세션에서 이를 감지한다."""
    try:
        os.makedirs(HANDOFF_DIR, exist_ok=True)
        path = os.path.join(HANDOFF_DIR, "latest-handoff.md")
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
        content = f"""# 자동 세션 전환 핸드오프

**기록 시각**: {now}
**전환 이유**: 세션 {count}턴 초과 (세션 관리 규칙 적용)
**세션 ID**: {session_id}

## 다음 세션 시작 시
1. 이전 작업의 완료 상태를 먼저 확인하세요
2. HANDOFF_LOG.md 및 project_session_*.md 메모리를 참고하세요
3. 미완료 P0/P1 태스크부터 재개하세요

## 세션 관리 규칙 참고
- CLAUDE.md 세션 관리 규칙: 15턴 경고, 25턴 자동 전환
- 압축 감지 시 작업 착수 전 사용자에게 알릴 것
"""
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
    except Exception:
        pass

def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode('utf-8'))
    except Exception:
        data = {}

    session_id = data.get('session_id', 'unknown')[:32]

    counter_dir = os.path.join(tempfile.gettempdir(), 'claude_turn_counters')
    os.makedirs(counter_dir, exist_ok=True)
    counter_file = os.path.join(counter_dir, f'{session_id}.json')

    if os.path.exists(counter_file):
        try:
            with open(counter_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
        except Exception:
            state = {'count': 0}
    else:
        state = {'count': 0}

    state['count'] += 1
    count = state['count']

    try:
        with open(counter_file, 'w', encoding='utf-8') as f:
            json.dump(state, f)
    except Exception:
        pass

    if count >= BLOCK_TURN:
        # 핸드오프 기록 → 다음 세션 SessionStart 훅이 자동 감지
        write_handoff(count, session_id)
        print(json.dumps({
            "continue": False,
            "stopReason": (
                f"[세션 자동 차단] {count}턴 초과. "
                "핸드오프 노트를 latest-handoff.md에 기록했습니다. "
                "새 세션을 시작하면 자동으로 이전 상황을 안내받습니다."
            )
        }))
    elif count == WARN_TURN:
        print(json.dumps({
            "systemMessage": (
                f"[세션 카운터] ⚠️ {count}턴 도달 — "
                "작업 단위 완료 후 새 세션 전환을 고려하세요. "
                f"{BLOCK_TURN}턴 초과 시 자동 차단됩니다."
            )
        }))
    elif count > WARN_TURN and (count - WARN_TURN) % 3 == 0:
        remaining = BLOCK_TURN - count
        print(json.dumps({
            "systemMessage": (
                f"[세션 카운터] ⛔ {count}턴 — "
                f"새 세션 전환 강력 권고. 자동 차단까지 {remaining}턴 남음."
            )
        }))

main()
