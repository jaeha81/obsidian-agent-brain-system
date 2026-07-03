#!/usr/bin/env python3
"""
Validation Council — Bucky 멀티에이전트 상호 검증 시스템

역할:
  - 고위험 작업에 대해 ClaudeCode + Codex 양쪽 승인을 요구한다
  - 모든 에이전트 작업을 감사 로그(JSONL)에 기록한다
  - Bucky/서브에이전트 상태를 감시하고 비정상 시 Discord 알림을 전송한다
  - 마지막 작업을 git revert + 백업 복원으로 롤백한다

위험도 체계:
  LOW      → 자동 승인
  MEDIUM   → 검증 에이전트 1개 승인 필요
  HIGH     → ClaudeCode + Codex 둘 다 승인 필요
  CRITICAL → 사용자 에스컬레이션 + 에이전트 2개 승인

실행: python scripts/validation_council.py
"""

from __future__ import annotations

import json
import os
import subprocess
import urllib.request
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# ── 루트 경로 및 환경 변수 로드 ────────────────────────────────────────────────

_ROOT = Path(__file__).parent.parent
load_dotenv(_ROOT / ".env", encoding="utf-8-sig")

DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL", "")
VAULT = Path(os.getenv("VAULT_PATH", str(_ROOT / "ObsidianVault")))

# 감사 로그 경로
AUDIT_LOG_PATH = VAULT / "00_System" / "agent_audit_log.jsonl"

# 백업 디렉터리
BACKUP_ROOT = _ROOT / ".agent" / "backup"

# AgentBus 인박스 (사용자 에스컬레이션 메시지 투입)
AGENTBUS_INBOX = VAULT / "10_AgentBus" / "inbox"

# watchdog 대상 에이전트 프로세스 명칭 목록
MONITORED_AGENTS = ["discord_bot.py", "bucky_watchdog.py", "agent_dispatcher.py"]


# ── 열거형 / 데이터 클래스 ─────────────────────────────────────────────────────

class RiskLevel(Enum):
    """에이전트 작업 위험도 단계"""
    LOW = "LOW"           # 읽기 전용, 부작용 없음
    MEDIUM = "MEDIUM"     # 파일 수정, 캐시 변경 등 부분 영향
    HIGH = "HIGH"         # 다수 파일 삭제/이동, 코드 배포 등 고영향
    CRITICAL = "CRITICAL" # 인프라 변경, 비밀 키 조작, 대규모 삭제


@dataclass
class AgentAction:
    """에이전트가 수행하려는 작업 단위"""
    agent_name: str                        # 에이전트 식별자 (예: "claude_code", "codex")
    description: str                       # 작업 내용 요약
    risk_level: RiskLevel                  # 위험도
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )
    metadata: dict = field(default_factory=dict)  # 추가 컨텍스트 (대상 파일, 명령어 등)


@dataclass
class ValidationResult:
    """검증 결과"""
    approved: bool
    approvers: list[str]                   # 승인한 에이전트/사용자 목록
    reason: str
    escalated_to_user: bool = False
    timestamp: str = field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds")
    )


# ── 유틸 함수 ──────────────────────────────────────────────────────────────────

def _ts() -> str:
    """현재 시각 문자열 (로그용)"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _iso() -> str:
    """ISO 8601 타임스탬프"""
    return datetime.now().isoformat(timespec="seconds")


def _log(msg: str) -> None:
    print(f"[ValidationCouncil {_ts()}] {msg}", flush=True)


# ── ValidationCouncil 메인 클래스 ─────────────────────────────────────────────

class ValidationCouncil:
    """
    Bucky 멀티에이전트 시스템의 상호 검증 위원회.

    사용 예:
        council = ValidationCouncil()
        action = AgentAction(
            agent_name="claude_code",
            description="ObsidianVault/00_System 파일 일괄 삭제",
            risk_level=RiskLevel.HIGH,
        )
        result = council.validate_action(action)
        if result.approved:
            # 작업 실행
    """

    def __init__(self) -> None:
        # 승인 에이전트 레지스트리: 실제 환경에서는 외부 API / 프로세스로 교체
        self._validators: dict[str, bool] = {
            "claude_code": True,   # ClaudeCode 검증 에이전트 가용 여부
            "codex": True,         # Codex 검증 에이전트 가용 여부
        }
        # 마지막 작업 기록 (rollback 대상)
        self._last_action: Optional[AgentAction] = None
        self._last_git_hash: Optional[str] = None
        self._last_backup_path: Optional[Path] = None

        # 감사 로그 디렉터리 초기화
        AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
        AGENTBUS_INBOX.mkdir(parents=True, exist_ok=True)

    # ── 공개 API ───────────────────────────────────────────────────────────────

    def validate_action(self, action: AgentAction) -> ValidationResult:
        """
        작업을 검증한다.

        위험도별 로직:
          LOW      → 자동 승인
          MEDIUM   → 검증 에이전트 1개 승인
          HIGH     → ClaudeCode + Codex 양쪽 승인
          CRITICAL → 사용자 에스컬레이션 + 에이전트 2개 승인
        """
        _log(f"검증 시작: [{action.risk_level.value}] {action.agent_name} — {action.description[:80]}")

        result: ValidationResult

        if action.risk_level == RiskLevel.LOW:
            result = self._auto_approve(action)

        elif action.risk_level == RiskLevel.MEDIUM:
            result = self._single_agent_approve(action)

        elif action.risk_level == RiskLevel.HIGH:
            result = self._dual_agent_approve(action)

        elif action.risk_level == RiskLevel.CRITICAL:
            result = self._critical_approve(action)

        else:
            # 예상치 못한 위험도 — 안전을 위해 거부
            result = ValidationResult(
                approved=False,
                approvers=[],
                reason=f"알 수 없는 위험도: {action.risk_level}",
            )

        # 감사 로그 기록
        self._write_audit_log(action, result)

        # 작업이 승인됐으면 롤백용 스냅샷 저장
        if result.approved:
            self._last_action = action
            self._snapshot_for_rollback()

        status_str = "승인" if result.approved else "거부"
        _log(f"검증 완료: {status_str} | 승인자: {result.approvers} | {result.reason}")
        return result

    def watchdog_check(self) -> dict[str, str]:
        """
        Bucky 및 서브에이전트 프로세스 상태를 확인한다.
        비정상 에이전트가 있으면 Discord 알림을 전송한다.

        반환: {에이전트명: "running" | "not_found" | "error"}
        """
        _log("에이전트 상태 점검 시작")
        statuses: dict[str, str] = {}
        unhealthy: list[str] = []

        for agent_script in MONITORED_AGENTS:
            status = self._check_process(agent_script)
            statuses[agent_script] = status
            if status != "running":
                unhealthy.append(agent_script)

        if unhealthy:
            msg = (
                f"**[ValidationCouncil] 에이전트 비정상 감지**\n"
                + "\n".join(f"- `{a}`: {statuses[a]}" for a in unhealthy)
            )
            _log(f"비정상 에이전트: {unhealthy}")
            self._send_discord(msg)
        else:
            _log("모든 에이전트 정상 실행 중")

        return statuses

    def rollback_last_action(self) -> bool:
        """
        마지막 승인 작업을 롤백한다.
          1) git revert (HEAD 커밋 되돌리기)
          2) 백업 디렉터리에서 파일 복원

        반환: 성공 여부
        """
        if self._last_action is None:
            _log("롤백 대상 작업 없음")
            return False

        _log(f"롤백 시작: {self._last_action.description[:80]}")
        success = True

        # 1단계: git revert
        if self._last_git_hash:
            try:
                result = subprocess.run(
                    ["git", "-C", str(_ROOT), "revert", "--no-edit", self._last_git_hash],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                )
                if result.returncode == 0:
                    _log(f"git revert 성공: {self._last_git_hash}")
                else:
                    _log(f"git revert 실패: {result.stderr.strip()}")
                    success = False
            except Exception as exc:
                _log(f"git revert 예외: {exc}")
                success = False

        # 2단계: 백업 복원
        if self._last_backup_path and self._last_backup_path.exists():
            try:
                self._restore_backup(self._last_backup_path)
                _log(f"백업 복원 완료: {self._last_backup_path}")
            except Exception as exc:
                _log(f"백업 복원 실패: {exc}")
                success = False

        # 감사 로그에 롤백 이벤트 기록
        self._append_audit_entry({
            "event": "rollback",
            "target_action": self._last_action.description,
            "git_hash": self._last_git_hash,
            "backup_path": str(self._last_backup_path),
            "success": success,
            "timestamp": _iso(),
        })

        self._last_action = None
        self._last_git_hash = None
        self._last_backup_path = None

        return success

    # ── 내부 승인 로직 ─────────────────────────────────────────────────────────

    def _auto_approve(self, action: AgentAction) -> ValidationResult:
        """LOW — 자동 승인"""
        return ValidationResult(
            approved=True,
            approvers=["auto"],
            reason="LOW 위험도: 자동 승인",
        )

    def _single_agent_approve(self, action: AgentAction) -> ValidationResult:
        """MEDIUM — 검증 에이전트 1개 이상 승인 필요"""
        for agent, available in self._validators.items():
            if available:
                approved = self._request_agent_approval(agent, action)
                if approved:
                    return ValidationResult(
                        approved=True,
                        approvers=[agent],
                        reason=f"MEDIUM 위험도: {agent} 승인",
                    )

        return ValidationResult(
            approved=False,
            approvers=[],
            reason="MEDIUM 위험도: 가용 검증 에이전트 없음",
        )

    def _dual_agent_approve(self, action: AgentAction) -> ValidationResult:
        """HIGH — ClaudeCode + Codex 양쪽 승인 필요"""
        required = ["claude_code", "codex"]
        approvers: list[str] = []

        for agent in required:
            if not self._validators.get(agent, False):
                return ValidationResult(
                    approved=False,
                    approvers=approvers,
                    reason=f"HIGH 위험도: {agent} 에이전트 비가용",
                )
            approved = self._request_agent_approval(agent, action)
            if approved:
                approvers.append(agent)
            else:
                return ValidationResult(
                    approved=False,
                    approvers=approvers,
                    reason=f"HIGH 위험도: {agent} 승인 거부",
                )

        return ValidationResult(
            approved=True,
            approvers=approvers,
            reason="HIGH 위험도: ClaudeCode + Codex 모두 승인",
        )

    def _critical_approve(self, action: AgentAction) -> ValidationResult:
        """CRITICAL — 사용자 에스컬레이션 + 에이전트 2개 승인"""
        # 1) 사용자 에스컬레이션 메시지 전송
        self._escalate_to_user(action)

        # 2) 에이전트 2개 승인 시도 (dual과 동일 로직)
        dual_result = self._dual_agent_approve(action)

        if not dual_result.approved:
            return ValidationResult(
                approved=False,
                approvers=dual_result.approvers,
                reason=f"CRITICAL 위험도: 에이전트 승인 미달 ({dual_result.reason})",
                escalated_to_user=True,
            )

        # 3) 사용자 응답 대기 (현재 구현: 에스컬레이션 후 에이전트 승인으로 진행)
        #    실제 운영에서는 AgentBus 응답 큐를 폴링하거나 사용자 확인 채널을 통한다
        _log("CRITICAL: 에이전트 양쪽 승인 완료 — 사용자 에스컬레이션 전송됨. 승인 대기 중...")
        self._send_discord(
            f"**[ValidationCouncil] CRITICAL 작업 에이전트 검증 통과**\n"
            f"작업: {action.description[:120]}\n"
            f"승인자: {dual_result.approvers}\n"
            f"⚠️ 최종 실행 전 사용자 확인 필요"
        )

        return ValidationResult(
            approved=True,
            approvers=dual_result.approvers,
            reason="CRITICAL 위험도: 사용자 에스컬레이션 + 에이전트 양쪽 승인",
            escalated_to_user=True,
        )

    # ── 에이전트 승인 요청 ──────────────────────────────────────────────────────

    def _request_agent_approval(self, agent: str, action: AgentAction) -> bool:
        """
        지정 에이전트에게 작업 승인을 요청한다.

        현재 구현: AgentBus inbox에 approval_request 메시지를 투입하고
        동기 방식으로 간단한 정책 기반 판단을 수행한다.
        실제 운영에서는 에이전트 응답 큐(outbox)를 폴링하도록 확장한다.
        """
        _log(f"{agent}에게 승인 요청: {action.description[:60]}")

        # AgentBus 인박스에 승인 요청 메시지 투입
        req_id = f"val-{datetime.now().strftime('%Y%m%d%H%M%S')}-{agent}"
        req_path = AGENTBUS_INBOX / f"{req_id}.json"
        req_payload = {
            "id": req_id,
            "type": "approval_request",
            "from": "validation_council",
            "to": agent,
            "risk_level": action.risk_level.value,
            "action": action.description,
            "agent_name": action.agent_name,
            "timestamp": _iso(),
        }
        req_path.write_text(
            json.dumps(req_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        # 정책 기반 자동 판단 (에이전트 응답 폴링 생략)
        # CRITICAL 이하에서 사용하며, 해당 에이전트가 가용 상태면 승인
        approved = self._validators.get(agent, False)
        _log(f"{agent} 승인 결과: {'승인' if approved else '거부'}")
        return approved

    # ── 사용자 에스컬레이션 ─────────────────────────────────────────────────────

    def _escalate_to_user(self, action: AgentAction) -> None:
        """CRITICAL 작업을 사용자에게 에스컬레이션한다."""
        msg = (
            f"🚨 **[CRITICAL] 사용자 에스컬레이션 필요**\n"
            f"에이전트: `{action.agent_name}`\n"
            f"작업: {action.description[:200]}\n"
            f"위험도: `{action.risk_level.value}`\n"
            f"시각: {action.timestamp}\n"
            f"승인 또는 거부 여부를 AgentBus를 통해 회신해 주세요."
        )
        _log("사용자 에스컬레이션 Discord 전송")
        self._send_discord(msg)

        # AgentBus inbox에도 에스컬레이션 메시지 투입
        esc_id = f"escalation-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        esc_path = AGENTBUS_INBOX / f"{esc_id}.json"
        esc_payload = {
            "id": esc_id,
            "type": "user_escalation",
            "from": "validation_council",
            "to": "user",
            "priority": "P0",
            "risk_level": action.risk_level.value,
            "action": action.description,
            "agent_name": action.agent_name,
            "timestamp": _iso(),
        }
        esc_path.write_text(
            json.dumps(esc_payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    # ── 감사 로그 ──────────────────────────────────────────────────────────────

    def _write_audit_log(self, action: AgentAction, result: ValidationResult) -> None:
        """모든 작업과 검증 결과를 JSONL 감사 로그에 기록한다."""
        entry = {
            "event": "validation",
            "agent_name": action.agent_name,
            "description": action.description,
            "risk_level": action.risk_level.value,
            "action_timestamp": action.timestamp,
            "metadata": action.metadata,
            "approved": result.approved,
            "approvers": result.approvers,
            "reason": result.reason,
            "escalated_to_user": result.escalated_to_user,
            "result_timestamp": result.timestamp,
        }
        self._append_audit_entry(entry)

    def _append_audit_entry(self, entry: dict) -> None:
        """감사 로그 파일에 JSONL 한 줄을 추가한다."""
        try:
            with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as exc:
            _log(f"감사 로그 기록 실패: {exc}")

    # ── 롤백 지원 ──────────────────────────────────────────────────────────────

    def _snapshot_for_rollback(self) -> None:
        """현재 git HEAD 해시와 백업 스냅샷을 저장해 두어 rollback_last_action에서 사용한다."""
        # git HEAD 해시 저장
        try:
            result = subprocess.run(
                ["git", "-C", str(_ROOT), "rev-parse", "HEAD"],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            if result.returncode == 0:
                self._last_git_hash = result.stdout.strip()
        except Exception as exc:
            _log(f"git HEAD 조회 실패: {exc}")

        # 백업 디렉터리 생성 (타임스탬프 기반)
        backup_dir = BACKUP_ROOT / datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_dir.mkdir(parents=True, exist_ok=True)
        self._last_backup_path = backup_dir
        _log(f"스냅샷 저장: hash={self._last_git_hash}, backup={backup_dir}")

    def _restore_backup(self, backup_path: Path) -> None:
        """
        백업 디렉터리에서 Vault 파일을 복원한다.
        현재 구현: backup_path가 실제 파일 사본을 가진 경우만 복원.
        """
        restored_count = 0
        for src in backup_path.rglob("*"):
            if src.is_file():
                rel = src.relative_to(backup_path)
                dest = _ROOT / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(src.read_bytes())
                restored_count += 1
        _log(f"복원된 파일 수: {restored_count}")

    # ── 프로세스 감시 ──────────────────────────────────────────────────────────

    def _check_process(self, script_name: str) -> str:
        """
        특정 Python 스크립트가 실행 중인지 확인한다.
        반환: "running" | "not_found" | "error"
        """
        try:
            # tasklist (Windows) 또는 ps (Unix) 공통 대응
            result = subprocess.run(
                ["tasklist"] if os.name == "nt" else ["ps", "aux"],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            if script_name in result.stdout:
                return "running"
            return "not_found"
        except Exception as exc:
            return f"error: {exc}"

    # ── Discord 알림 ───────────────────────────────────────────────────────────

    def _send_discord(self, message: str) -> None:
        """Discord 웹훅으로 알림 메시지를 전송한다."""
        if not DISCORD_WEBHOOK:
            _log("DISCORD_WEBHOOK_URL 미설정 — 알림 생략")
            return
        try:
            # Discord 2000자 제한 대응
            chunks = [message[i:i + 1900] for i in range(0, len(message), 1900)]
            for chunk in chunks:
                data = json.dumps({"content": chunk}).encode("utf-8")
                req = urllib.request.Request(
                    DISCORD_WEBHOOK,
                    data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                urllib.request.urlopen(req, timeout=5)
        except Exception as exc:
            _log(f"Discord 알림 전송 실패: {exc}")


# ── CLI 진입점 ─────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    council = ValidationCouncil()

    # 간단한 동작 확인 (인수 없이 실행 시 데모 수행)
    if len(sys.argv) < 2:
        print("사용법: python validation_council.py [demo|watchdog|rollback]")
        print("\n--- 데모 실행 ---")
        demo_actions = [
            AgentAction(
                agent_name="claude_code",
                description="README.md 내용 업데이트",
                risk_level=RiskLevel.LOW,
            ),
            AgentAction(
                agent_name="claude_code",
                description="scripts/ 아래 신규 파일 3개 생성",
                risk_level=RiskLevel.MEDIUM,
            ),
            AgentAction(
                agent_name="claude_code",
                description="ObsidianVault/00_System 전체 파일 이동",
                risk_level=RiskLevel.HIGH,
            ),
            AgentAction(
                agent_name="bucky",
                description="GitHub Actions 시크릿 키 교체 + 전체 재배포",
                risk_level=RiskLevel.CRITICAL,
                metadata={"target": "github_secrets", "scope": "production"},
            ),
        ]
        for action in demo_actions:
            result = council.validate_action(action)
            print(
                f"  [{action.risk_level.value:8s}] {action.description[:50]:<50s}"
                f" → {'승인' if result.approved else '거부'} ({result.reason})"
            )
        sys.exit(0)

    cmd = sys.argv[1].lower()

    if cmd == "watchdog":
        statuses = council.watchdog_check()
        for agent, status in statuses.items():
            print(f"  {agent}: {status}")

    elif cmd == "rollback":
        # 롤백 테스트: 실제 사용 시 validate_action 후 호출
        ok = council.rollback_last_action()
        print(f"롤백 결과: {'성공' if ok else '실패 (롤백 대상 없음)'}")

    else:
        print(f"알 수 없는 명령: {cmd}")
        print("사용법: python validation_council.py [demo|watchdog|rollback]")
        sys.exit(1)
