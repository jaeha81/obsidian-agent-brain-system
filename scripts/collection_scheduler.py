#!/usr/bin/env python3
"""
Collection Scheduler
LLM 대화 수집 파이프라인 통합 오케스트레이터.

기능:
  1. 수동 실행: --run 으로 즉시 모든 수집기 실행
  2. Windows Task Scheduler 등록: --install 로 매일 오전 6시 자동 실행 등록
  3. 등록 해제: --uninstall
  4. 상태 확인: --status

Discord 알림: DISCORD_WEBHOOK_URL 환경변수 또는 .env 파일에 설정

Usage:
    python collection_scheduler.py --run              # 즉시 전체 수집 실행
    python collection_scheduler.py --run --dry-run    # 테스트 (저장 없음)
    python collection_scheduler.py --install          # Windows Task Scheduler 등록
    python collection_scheduler.py --uninstall        # 등록 해제
    python collection_scheduler.py --status           # 스케줄 상태 확인
"""

import sys
import os
import subprocess
import logging
import argparse
import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = Path(__file__).parent
LOG_DIR = ROOT / "logs" / "collection"
TASK_NAME = "ObsidianBrain_CollectionScheduler"

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env", encoding="utf-8-sig", override=True)
except ImportError:
    pass

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s", stream=sys.stdout)
log = logging.getLogger(__name__)


# ── Discord 알림 ──────────────────────────────────────────────────────────────

def notify_discord(message: str) -> None:
    if not DISCORD_WEBHOOK_URL:
        return
    try:
        import urllib.request
        data = json.dumps({"content": message}).encode("utf-8")
        req = urllib.request.Request(
            DISCORD_WEBHOOK_URL,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        log.warning(f"Discord 알림 실패: {e}")


# ── 수집기 실행 ────────────────────────────────────────────────────────────────

_GPT_PROFILE = ROOT / ".gpt_collector_profile"
_CLAUDE_PROFILE = Path(os.environ.get("USERPROFILE", str(Path.home()))) / ".playwright-claude-sessions"

COLLECTORS = [
    {
        "name": "GPT Session Collector",
        "script": "gpt_session_collector.py",
        "args": ["--collect"],
        "dry_run_args": ["--collect", "--dry-run"],
        "login_required": True,
        "profile_path": _GPT_PROFILE,
        "login_cmd": "python scripts/gpt_session_collector.py --login",
    },
    {
        "name": "Claude Session Collector",
        "script": "claude_session_collector.py",
        "args": ["--collect"],
        "dry_run_args": ["--collect", "--dry-run"],
        "login_required": True,
        "profile_path": _CLAUDE_PROFILE,
        "login_cmd": "python scripts/claude_session_collector.py --login",
    },
    {
        "name": "Codex Log Collector",
        "script": "codex_log_collector.py",
        "args": ["--collect"],
        "dry_run_args": ["--collect", "--dry-run"],
        "login_required": False,
        "profile_path": None,
        "login_cmd": None,
    },
]


def run_collector(collector: dict, dry_run: bool = False, timeout: int = 300) -> dict:
    script = SCRIPTS_DIR / collector["script"]
    args = collector["dry_run_args"] if dry_run else collector["args"]
    cmd = [sys.executable, str(script)] + args

    result = {
        "name": collector["name"],
        "success": False,
        "skipped": False,
        "files_saved": 0,
        "error": None,
        "duration_s": 0,
    }

    # 로그인 필요 수집기인데 프로파일이 없으면 건너뜀 (실패로 보고하지 않음)
    profile_path = collector.get("profile_path")
    if collector.get("login_required") and profile_path and not Path(profile_path).exists():
        login_cmd = collector.get("login_cmd", "")
        log.warning(f"  ⏭ {collector['name']}: 로그인 프로파일 없음 — 건너뜀")
        log.warning(f"     1회 설정: {login_cmd}")
        result["skipped"] = True
        result["error"] = f"로그인 필요: {login_cmd}"
        return result

    log.info(f"실행: {collector['name']} {'[DRY-RUN]' if dry_run else ''}")

    start = datetime.now()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(ROOT),
            timeout=timeout,
        )
        result["duration_s"] = round((datetime.now() - start).total_seconds(), 1)

        if proc.returncode == 0:
            result["success"] = True
            # 저장된 파일 수 계산 (출력 줄 중 파일 경로 카운트)
            saved = [ln for ln in (proc.stdout or "").splitlines() if "\\" in ln or "/" in ln]
            result["files_saved"] = len(saved)
            log.info(f"  ✓ {collector['name']}: {result['files_saved']}개 파일, {result['duration_s']}s")
        else:
            stderr = (proc.stderr or "").strip()
            stdout = (proc.stdout or "").strip()
            result["error"] = stderr[:300] or stdout[-300:]
            log.warning(f"  ✗ {collector['name']}: {result['error']}")

    except subprocess.TimeoutExpired:
        result["error"] = f"타임아웃 ({timeout}s)"
        result["duration_s"] = timeout
        log.error(f"  ✗ {collector['name']}: 타임아웃")
    except Exception as e:
        result["error"] = str(e)
        log.error(f"  ✗ {collector['name']}: {e}")

    return result


def run_all(dry_run: bool = False) -> list[dict]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    date_str = datetime.now().strftime("%Y-%m-%d")

    log.info(f"=== 수집 파이프라인 시작 {ts} {'[DRY-RUN]' if dry_run else ''} ===")

    results = []
    for collector in COLLECTORS:
        r = run_collector(collector, dry_run=dry_run)
        results.append(r)

    # 결과 요약
    total_files = sum(r["files_saved"] for r in results)
    success_count = sum(1 for r in results if r["success"])
    skip_count = sum(1 for r in results if r.get("skipped"))
    fail_count = len(results) - success_count - skip_count

    log.info(f"=== 완료: 성공 {success_count}/{len(results)}, 건너뜀 {skip_count}, 실패 {fail_count}, 총 {total_files}개 파일 ===")

    # 로그 저장
    log_path = LOG_DIR / f"{ts}_collection.json"
    log_data = {
        "timestamp": ts,
        "date": date_str,
        "dry_run": dry_run,
        "results": results,
        "summary": {
            "total_collectors": len(results),
            "success": success_count,
            "skipped": skip_count,
            "failed": fail_count,
            "total_files": total_files,
        }
    }
    log_path.write_text(json.dumps(log_data, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info(f"로그 저장: {log_path}")

    # Discord 알림
    if not dry_run:
        status_icon = "✅" if fail_count == 0 else "⚠️"
        msg_lines = [f"{status_icon} **수집 파이프라인 완료** ({date_str})"]
        for r in results:
            if r.get("skipped"):
                icon = "⏭"
                msg_lines.append(f"  {icon} {r['name']}: 로그인 1회 필요 (건너뜀)")
            else:
                icon = "✓" if r["success"] else "✗"
                msg_lines.append(f"  {icon} {r['name']}: {r['files_saved']}개 파일")
        if fail_count:
            msg_lines.append(f"\n⚠️ {fail_count}개 수집기 실패 — 로그 확인: `{log_path.name}`")
        if skip_count:
            msg_lines.append(f"\n💡 로그인 설정 필요 수집기 {skip_count}개 — 집 PC에서 --login 실행")
        notify_discord("\n".join(msg_lines))

    return results


# ── Windows Task Scheduler ────────────────────────────────────────────────────

def install_task() -> None:
    """Windows Task Scheduler에 매일 오전 6시 수집 작업을 등록한다."""
    script_path = Path(__file__).resolve()
    python_exe = sys.executable

    # XML 태스크 정의
    task_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Obsidian Brain — LLM 대화 자동 수집 (매일 오전 6시)</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T06:00:00</StartBoundary>
      <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT1H</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions>
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>"{script_path}" --run</Arguments>
      <WorkingDirectory>{ROOT}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

    xml_path = ROOT / "logs" / f"{TASK_NAME}.xml"
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    xml_path.write_text(task_xml, encoding="utf-16")

    try:
        result = subprocess.run(
            ["schtasks", "/Create", "/F", "/TN", TASK_NAME, "/XML", str(xml_path)],
            capture_output=True, text=True, encoding="utf-8",
        )
        if result.returncode == 0:
            log.info(f"✓ Task Scheduler 등록 완료: '{TASK_NAME}'")
            log.info("  매일 오전 6시에 자동 실행됩니다.")
        else:
            log.error(f"등록 실패: {result.stderr.strip()}")
    except FileNotFoundError:
        log.error("schtasks 명령을 찾을 수 없습니다. Windows에서만 사용 가능합니다.")


def uninstall_task() -> None:
    try:
        result = subprocess.run(
            ["schtasks", "/Delete", "/F", "/TN", TASK_NAME],
            capture_output=True, text=True, encoding="utf-8",
        )
        if result.returncode == 0:
            log.info(f"✓ Task Scheduler 등록 해제: '{TASK_NAME}'")
        else:
            log.warning(f"등록 해제 실패 (이미 없을 수 있음): {result.stderr.strip()}")
    except FileNotFoundError:
        log.error("schtasks 명령을 찾을 수 없습니다.")


# ── Wiki 스케줄 태스크 ─────────────────────────────────────────────────────────

WIKI_LINT_TASK = "ObsidianBrain_WikiLint"
MODALITY_CHECK_TASK = "ObsidianBrain_ModalityCheck"


def _register_xml_task(task_name: str, xml_body: str) -> bool:
    """XML 파일로 Windows Task Scheduler 태스크 등록. 성공 여부 반환."""
    xml_path = ROOT / "logs" / f"{task_name}.xml"
    xml_path.parent.mkdir(parents=True, exist_ok=True)
    xml_path.write_text(xml_body, encoding="utf-16")
    try:
        result = subprocess.run(
            ["schtasks", "/Create", "/F", "/TN", task_name, "/XML", str(xml_path)],
            capture_output=True,
        )
        if result.returncode == 0:
            log.info(f"✓ Task Scheduler 등록 완료: '{task_name}'")
            return True
        else:
            stderr = result.stderr.decode("cp949", errors="replace").strip()
            log.error(f"등록 실패 ({task_name}): {stderr}")
            return False
    except FileNotFoundError:
        log.error("schtasks 명령을 찾을 수 없습니다. Windows에서만 사용 가능합니다.")
        return False


def install_wiki_tasks() -> None:
    """wiki_lint (매일 03:00) + modality_check (매주 월요일 09:00) 등록."""
    python_exe = sys.executable
    script_path = Path(__file__).resolve().parent

    # wiki_lint — 매일 03:00
    lint_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Obsidian Brain — Wiki Lint (매일 03:00)</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T03:00:00</StartBoundary>
      <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
    </CalendarTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT30M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions>
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>-X utf8 "{script_path / 'wiki_lint.py'}" --report</Arguments>
      <WorkingDirectory>{ROOT}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

    # modality_check — 매주 월요일 09:00
    modality_xml = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>Obsidian Brain — Modality Check (매주 월요일 09:00)</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>2026-01-01T09:00:00</StartBoundary>
      <ExecutionTimeLimit>PT15M</ExecutionTimeLimit>
      <Enabled>true</Enabled>
      <ScheduleByWeek>
        <DaysOfWeek>
          <Monday />
        </DaysOfWeek>
        <WeeksInterval>1</WeeksInterval>
      </ScheduleByWeek>
    </CalendarTrigger>
  </Triggers>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <ExecutionTimeLimit>PT15M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions>
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>-X utf8 "{script_path / 'modality_check.py'}" --notify</Arguments>
      <WorkingDirectory>{ROOT}</WorkingDirectory>
    </Exec>
  </Actions>
</Task>"""

    ok1 = _register_xml_task(WIKI_LINT_TASK, lint_xml)
    ok2 = _register_xml_task(MODALITY_CHECK_TASK, modality_xml)

    if ok1 and ok2:
        log.info("Wiki 스케줄 등록 완료:")
        log.info(f"  {WIKI_LINT_TASK}: 매일 03:00 — wiki_lint.py --report")
        log.info(f"  {MODALITY_CHECK_TASK}: 매주 월요일 09:00 — modality_check.py --notify")
    else:
        log.warning("일부 태스크 등록 실패 — 위 오류 메시지 확인")


def uninstall_wiki_tasks() -> None:
    for task in (WIKI_LINT_TASK, MODALITY_CHECK_TASK):
        try:
            result = subprocess.run(
                ["schtasks", "/Delete", "/F", "/TN", task],
                capture_output=True, text=True, encoding="utf-8",
            )
            if result.returncode == 0:
                log.info(f"✓ 등록 해제: '{task}'")
            else:
                log.warning(f"등록 해제 실패 (이미 없을 수 있음): {task}")
        except FileNotFoundError:
            log.error("schtasks 명령을 찾을 수 없습니다.")


def check_wiki_status() -> None:
    for task in (WIKI_LINT_TASK, MODALITY_CHECK_TASK):
        result = subprocess.run(
            ["schtasks", "/Query", "/FO", "LIST", "/TN", task],
            capture_output=True, text=True, encoding="utf-8",
        )
        if result.returncode == 0:
            for line in result.stdout.splitlines():
                if line.strip():
                    print(f"  {line}")
        else:
            log.info(f"'{task}' 미등록")


def check_status() -> None:
    try:
        result = subprocess.run(
            ["schtasks", "/Query", "/FO", "LIST", "/TN", TASK_NAME],
            capture_output=True, text=True, encoding="utf-8",
        )
        if result.returncode == 0:
            print(result.stdout)
        else:
            log.info(f"Task '{TASK_NAME}' 미등록 상태")
    except FileNotFoundError:
        log.error("schtasks 명령을 찾을 수 없습니다.")

    # 최근 로그 요약
    if LOG_DIR.exists():
        logs = sorted(LOG_DIR.glob("*_collection.json"), reverse=True)[:3]
        if logs:
            print("\n=== 최근 수집 로그 ===")
            for lf in logs:
                try:
                    data = json.loads(lf.read_text(encoding="utf-8"))
                    s = data.get("summary", {})
                    print(f"  [{data['date']}] 성공: {s.get('success')}/{s.get('total_collectors')}, 파일: {s.get('total_files')}")
                except Exception:
                    pass


# ── 진입점 ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Collection Scheduler — LLM 대화 수집 파이프라인")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--run", action="store_true", help="즉시 전체 수집 실행")
    group.add_argument("--install", action="store_true", help="Windows Task Scheduler 등록 (매일 오전 6시)")
    group.add_argument("--uninstall", action="store_true", help="Task Scheduler 등록 해제")
    group.add_argument("--status", action="store_true", help="스케줄 및 최근 로그 상태 확인")
    group.add_argument("--install-wiki", action="store_true", help="Wiki Lint (매일 03:00) + Modality Check (매주 월요일 09:00) 등록")
    group.add_argument("--uninstall-wiki", action="store_true", help="Wiki 스케줄 태스크 해제")
    group.add_argument("--status-wiki", action="store_true", help="Wiki 스케줄 태스크 상태 확인")
    parser.add_argument("--dry-run", action="store_true", help="실제 저장 없이 테스트")
    args = parser.parse_args()

    if args.install:
        install_task()
    elif args.uninstall:
        uninstall_task()
    elif args.status:
        check_status()
    elif args.install_wiki:
        install_wiki_tasks()
    elif args.uninstall_wiki:
        uninstall_wiki_tasks()
    elif args.status_wiki:
        check_wiki_status()
    else:
        # --run 또는 인수 없이 실행
        results = run_all(dry_run=args.dry_run)
        failed = [r for r in results if not r["success"] and not r.get("skipped")]
        sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
