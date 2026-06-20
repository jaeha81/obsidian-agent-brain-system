"""채널별 역할 파일 로딩 테스트"""
import os, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

ROLE_DIR = ROOT / "ObsidianVault" / "00_System" / "channel_roles"

CHANNEL_VARS = [
    "JH_CHAT_CHANNEL_ID",
    "JH_REPO_DASHBOARD_CHANNEL_ID",
    "JH_WISHKET_CHANNEL_ID",
    "JH_KMONG_CHANNEL_ID",
    "JH_DAILYPLUS_CHANNEL_ID",
    "JH_TASKBOARD_CHANNEL_ID",
    "JH_CLAUDE_CODE_CHANNEL_ID",
    "JH_CODEX_CHANNEL_ID",
    "JH_MYINTRO_CHANNEL_ID",
    "JH_SHORTS_CHANNEL_ID",
    "JH_CHSH_MINING_CHANNEL_ID",
    "JH_THREADS_CHANNEL_ID",
    "JH_CHRIS_CHANNEL_ID",
    "JH_CHARLIE_CHANNEL_ID",
]

ROLE_MAP = {
    "JH_CHAT_CHANNEL_ID":           "JHHUB_ROLE.md",
    "JH_REPO_DASHBOARD_CHANNEL_ID": "REPO_DASHBOARD_ROLE.md",
    "JH_WISHKET_CHANNEL_ID":        "WISHKET_ROLE.md",
    "JH_KMONG_CHANNEL_ID":          "KMONG_ROLE.md",
    "JH_DAILYPLUS_CHANNEL_ID":      "DAILYPLUS_ROLE.md",
    "JH_TASKBOARD_CHANNEL_ID":      "TASKBOARD_ROLE.md",
    "JH_CLAUDE_CODE_CHANNEL_ID":    "CLAUDE_CODE_ROLE.md",
    "JH_CODEX_CHANNEL_ID":          "CODEX_ROLE.md",
    "JH_MYINTRO_CHANNEL_ID":        "MYINTRO_ROLE.md",
    "JH_SHORTS_CHANNEL_ID":         "SHORTS_ROLE.md",
    "JH_CHSH_MINING_CHANNEL_ID":    "CHSH_MINING_ROLE.md",
    "JH_THREADS_CHANNEL_ID":        "THREADS_ROLE.md",
}

print(f"{'채널 변수':<35} {'채널ID(뒤4자리)':>14} {'Role파일':<25} 결과")
print("-" * 95)

fails = []
warns = []
for var in CHANNEL_VARS:
    ch_id = os.getenv(var, "").strip()
    role_file = ROLE_MAP.get(var, "(별도 처리)")
    ch_short = f"...{ch_id[-4:]}" if ch_id else "(미설정)"

    if not ch_id:
        status = "WARN  채널ID 미설정"
        warns.append(var)
    elif role_file == "(별도 처리)":
        status = "OK    전용 핸들러"
    else:
        role_path = ROLE_DIR / role_file
        if role_path.exists():
            content = role_path.read_text(encoding="utf-8").strip()
            status = f"OK    {len(content)}자 로드됨"
        else:
            status = f"FAIL  파일 없음"
            fails.append(var)

    print(f"{var:<35} {ch_short:>14} {role_file:<25} {status}")

print("-" * 95)
if not fails and not warns:
    print("결과: ALL PASS")
else:
    if warns:
        print(f"WARN ({len(warns)}개): {', '.join(warns)}")
    if fails:
        print(f"FAIL ({len(fails)}개): {', '.join(fails)}")
