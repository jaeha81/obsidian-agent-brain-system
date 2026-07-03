"""봇 자체 업데이트 및 재시작 스크립트
사용법: python scripts/bot_self_update.py
git pull 후 10초 뒤 봇 프로세스를 새 코드로 재시작합니다.
"""
import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent


def main():
    print("[bot_self_update] 시작", flush=True)

    # 1. git pull
    print("[bot_self_update] git pull origin master ...", flush=True)
    result = subprocess.run(
        ["git", "pull", "origin", "master"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    print(f"[bot_self_update] stdout: {result.stdout.strip()}", flush=True)
    if result.stderr.strip():
        print(f"[bot_self_update] stderr: {result.stderr.strip()}", flush=True)

    if result.returncode != 0:
        print(f"[bot_self_update] git pull 실패 rc={result.returncode}", flush=True)
        return

    print("[bot_self_update] git pull 완료", flush=True)

    # 2. 재시작 PowerShell 스크립트 생성
    restart_script = ROOT / "restart_bot_temp.ps1"
    python_exe = sys.executable.replace("\\", "/")
    root_path = str(ROOT).replace("\\", "/")

    ps_content = f"""# 봇 자동 재시작 (임시 파일 - 실행 후 자동 삭제)
Write-Host "[restart] 10초 대기..."
Start-Sleep -Seconds 10

$proc = Get-WmiObject Win32_Process | Where-Object {{$_.CommandLine -like '*discord_bot.py*'}} | Select-Object -First 1
if ($proc) {{
    Write-Host "[restart] 기존 봇 PID $($proc.ProcessId) 종료"
    Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
}} else {{
    Write-Host "[restart] 기존 봇 프로세스 없음"
}}

Write-Host "[restart] 새 봇 시작"
Set-Location '{root_path}'
Start-Process -FilePath '{python_exe}' -ArgumentList 'scripts/discord_bot.py' -WorkingDirectory '{root_path}'

Write-Host "[restart] 완료"
Start-Sleep -Seconds 2
Remove-Item $MyInvocation.MyCommand.Path -Force -ErrorAction SilentlyContinue
"""

    restart_script.write_text(ps_content, encoding="utf-8")
    print(f"[bot_self_update] 재시작 스크립트 생성: {restart_script.name}", flush=True)

    # 3. 재시작 스크립트 DETACHED 실행
    subprocess.Popen(
        [
            "powershell",
            "-WindowStyle", "Hidden",
            "-ExecutionPolicy", "Bypass",
            "-File", str(restart_script),
        ],
        creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True,
        cwd=str(ROOT),
    )

    print("[bot_self_update] 재시작 스크립트 실행됨. 10초 후 봇 재시작.", flush=True)
    return "✅ git pull 완료. 10초 후 봇이 새 코드로 재시작됩니다."


if __name__ == "__main__":
    result = main()
    if result:
        print(result)
