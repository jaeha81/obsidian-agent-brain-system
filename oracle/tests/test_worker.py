#!/usr/bin/env python3
"""Bucky Core 폴링 워커 검증 스위트 (Phase 3-⑤).

실서버(api_server.py)를 subprocess로 기동하고 worker.run_once를 in-process로 호출해
claim→running→completed(및 handle_task 예외→failed) 왕복을 검증한다.
test_client.py와 동일한 러너 스타일.

Usage:
    python -X utf8 oracle/tests/test_worker.py
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CORE = REPO / "oracle" / "core"
AGENTS_YAML = CORE / "agents.yaml"
TOKEN = "test-token-worker"
AGENT = "home-pc-agent"

sys.path.insert(0, str(CORE))
import worker  # noqa: E402
from client import submit_task, get_task  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="bucky_worker_test_"))

# Stage 19: 기본 config가 policy shadow라 handle_task가 policy_decision을 방출한다.
# 이 러너의 모든 in-process emit을 임시 경로로 격리 — 실로그(05_Logs) 오염 방지.
from core import event_log  # noqa: E402  (worker import가 scripts를 sys.path에 올린 뒤)

event_log.EVENTS_PATH = TMP / "events.jsonl"
with socket.socket() as _s:  # 빈 포트 확보 — 고정 포트 충돌 방지
    _s.bind(("127.0.0.1", 0))
    PORT = _s.getsockname()[1]
BASE = f"http://127.0.0.1:{PORT}"

PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS {name}")
    else:
        FAIL += 1
        print(f"  FAIL {name} {detail}")


def _boom(task):  # handle_task 예외 경로 검증용
    raise RuntimeError("boom")


print("== 폴링 워커 테스트 (실서버) ==")
env = dict(
    os.environ,
    BUCKY_API_TOKEN=TOKEN,
    BUCKY_DB_PATH=str(TMP / "worker.db"),
    BUCKY_LOG_DIR=str(TMP / "logs"),
    BUCKY_AGENTS_FILE=str(AGENTS_YAML),
)
os.environ.pop("BUCKY_API_TOKEN", None)
os.environ.pop("ORACLE_API_URL", None)

server = subprocess.Popen(
    [sys.executable, "-X", "utf8", str(CORE / "api_server.py"),
     "--host", "127.0.0.1", "--port", str(PORT)],
    env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
)
try:
    for _ in range(50):
        try:
            urllib.request.urlopen(BASE + "/health", timeout=2)
            break
        except OSError:
            time.sleep(0.2)

    # W1 빈 큐 → run_once None
    check("W1 빈 큐 → run_once None",
          worker.run_once(AGENT, base_url=BASE, token=TOKEN) is None)

    # W2~W3 submit → run_once가 선점·실행·완료 보고 (result = AgentResult 규약, Stage 8)
    AGENT_RESULT_FIELDS = {"agent", "status", "summary", "files_changed",
                           "commands_run", "test_result", "risks", "next_actions"}
    res = submit_task("chat", payload={"instruction": "안녕"}, target_agent=AGENT,
                      base_url=BASE, token=TOKEN)
    tid = res["task_id"]
    done = worker.run_once(AGENT, base_url=BASE, token=TOKEN)
    check("W2 run_once가 해당 태스크 처리", done == tid, f"got {done}")
    task = get_task(tid, base_url=BASE, token=TOKEN)
    result = task.get("result") or {}
    check("W3 completed + AgentResult 형식 result (echo 보존)",
          task["status"] == "completed"
          and set(result) == AGENT_RESULT_FIELDS
          and result["agent"] == AGENT
          and result["status"] == "completed"
          and "안녕" in result["summary"],
          f"got {task}")

    # W4 타깃 격리 — office-pc-agent는 home-pc 태스크를 못 가져감
    submit_task("chat", payload={"x": 1}, target_agent=AGENT, base_url=BASE, token=TOKEN)
    check("W4 다른 에이전트 run_once → None",
          worker.run_once("office-pc-agent", base_url=BASE, token=TOKEN) is None)
    worker.run_once(AGENT, base_url=BASE, token=TOKEN)  # 청소: home-pc가 소진

    # W5~W6 handle_task 예외 → failed 보고 (워커는 죽지 않고 task_id 반환)
    res3 = submit_task("chat", payload={"boom": True}, target_agent=AGENT,
                       base_url=BASE, token=TOKEN)
    tid3 = res3["task_id"]
    orig = worker.handle_task
    worker.handle_task = _boom
    try:
        done3 = worker.run_once(AGENT, base_url=BASE, token=TOKEN)
    finally:
        worker.handle_task = orig
    check("W5 예외 태스크도 처리 후 task_id 반환", done3 == tid3, f"got {done3}")
    task3 = get_task(tid3, base_url=BASE, token=TOKEN)
    result3 = task3.get("result") or {}
    check("W6 handle_task 예외 → status failed + AgentResult(failed) 기록",
          task3["status"] == "failed"
          and result3.get("agent") == AGENT
          and result3.get("status") == "failed"
          and "boom" in result3.get("summary", ""),
          f"got {task3}")

    # W7 handle_task가 failed AgentResult를 반환하면 서버 상태도 failed로 보고
    res4 = submit_task("chat", payload={"instruction": "x"}, target_agent=AGENT,
                       base_url=BASE, token=TOKEN)
    tid4 = res4["task_id"]
    orig = worker.handle_task
    worker.handle_task = lambda task: worker.AgentResult(
        agent=AGENT, status="failed", summary="검증 실패 스텁").to_dict()
    try:
        done4 = worker.run_once(AGENT, base_url=BASE, token=TOKEN)
    finally:
        worker.handle_task = orig
    task4 = get_task(tid4, base_url=BASE, token=TOKEN)
    check("W7 failed AgentResult 반환 → 서버 status failed",
          done4 == tid4 and task4["status"] == "failed"
          and (task4.get("result") or {}).get("status") == "failed",
          f"got {task4}")
finally:
    server.kill()
    server.wait()

# W8~W10은 서버 불필요 — handle_task 계약을 직접 검증한다.
# W8 정본 병합 — payload가 큐 레코드의 task_id/task_type/priority를 덮어쓸 수 없다
r8 = worker.handle_task({
    "task_id": "task_20260711_120000_abcd", "task_type": "chat",
    "priority": "normal", "target_agent": AGENT,
    "payload": {"task_id": "evil", "task_type": "hack", "priority": "urgent",
                "instruction": "x"},
})
check("W8 큐 레코드 정본 필드가 payload를 이긴다",
      r8["status"] == "completed" and "echo(chat)" in r8["summary"], f"got {r8}")

# W9 invalid 레코드(task_id 형식 위반) → 예외 없이 AgentResult(failed)
r9 = worker.handle_task({"task_id": "not-oracle-format", "task_type": "chat",
                         "payload": {}})
check("W9 TaskSpec 검증 실패 → AgentResult(failed)",
      r9["status"] == "failed" and "TaskSpec" in r9["summary"], f"got {r9}")

# W10 클래스 정체성 — worker와 ProviderAdapter가 같은 core.task_spec.TaskSpec을 쓴다
import importlib  # noqa: E402
_canon = importlib.import_module("core.task_spec")
check("W10 worker.TaskSpec is core.task_spec.TaskSpec",
      worker.TaskSpec is _canon.TaskSpec)

# ── W11~W14 — Stage 17 어댑터 디스패치 (서버 불필요, 이벤트는 임시 경로로 격리) ──
# worker import가 scripts를 sys.path에 올린 뒤라 core.*/model_router/providers 접근 가능.
import model_router  # noqa: E402
import providers  # noqa: E402
from core.provider_adapter import Estimate  # noqa: E402

# W11 리포 기본 config → 플래그 off (off일 때 echo 동작 자체는 W2~W3·W8이 회귀 보증)
check("W11 기본 features.worker_adapter_dispatch=false → 디스패치 비활성",
      worker._dispatch_enabled() is False)

DISPATCH_TASK = {
    "task_id": "task_20260712_090000_ab12", "task_type": "chat",
    "target_agent": AGENT, "payload": {"instruction": "hello"},
}


class _FakeAdapter:
    """estimate/run 계약만 흉내내는 스텁 — ok=False면 실행 불가 provider."""

    def __init__(self, name, ok=True):
        self.name, self._ok = name, ok

    def estimate(self, spec):
        return Estimate(self.name, self._ok, "sonnet" if self._ok else "",
                        "" if self._ok else "disabled 스텁")

    def run(self, spec, instruction=""):
        return worker.AgentResult(agent=self.name, status="completed",
                                  summary=f"adapter({self.name}): {instruction}")


def dispatch_case(chain, factory, *, policy_mode=None):
    """플래그 on + 가짜 체인/어댑터로 handle_task 실행 → (result, 기록된 이벤트 목록).

    policy_mode를 주면 정책 모드를 고정한다("" = off/상담 안 함). 생략하면 리포 config
    기본값(shadow)이 그대로 쓰인다 — 기존 W12~W15·W21은 이 경로를 유지한다.
    """
    tmp_log = Path(tempfile.mkdtemp(prefix="bucky_ev_")) / "events.jsonl"
    orig = (worker._dispatch_enabled, worker._policy_mode,
            model_router.provider_candidates,
            providers.get_adapter, event_log.EVENTS_PATH)
    worker._dispatch_enabled = lambda: True
    if policy_mode is not None:
        worker._policy_mode = lambda: policy_mode
    model_router.provider_candidates = lambda task_type, policy=None: list(chain)
    providers.get_adapter = lambda name, registry=None: factory(name)
    event_log.EVENTS_PATH = tmp_log
    try:
        result = worker.handle_task(dict(DISPATCH_TASK))
    finally:
        (worker._dispatch_enabled, worker._policy_mode,
         model_router.provider_candidates,
         providers.get_adapter, event_log.EVENTS_PATH) = orig
    events = []
    if tmp_log.is_file():
        events = [json.loads(ln) for ln in
                  tmp_log.read_text(encoding="utf-8").splitlines()]
    return result, events


# W12 on 디스패치 — 어댑터 결과 반환 + model_decision 이벤트(스키마 payload) 기록
r12, ev12 = dispatch_case(["fake_ok"], lambda name: _FakeAdapter(name))
md12 = [e for e in ev12 if e["kind"] == "model_decision"]
check("W12 플래그 on → 어댑터 결과 + model_decision 이벤트",
      r12["status"] == "completed" and r12["summary"] == "adapter(fake_ok): hello"
      and len(md12) == 1
      and md12[0]["task_id"] == DISPATCH_TASK["task_id"]
      and md12[0]["payload"]["selected_provider"] == "fake_ok"
      and md12[0]["payload"]["provider_chain"] == ["fake_ok"],
      f"got {r12} / events {ev12}")

# W13 disabled 폴백 — 1순위 실행 불가면 다음 provider가 실행
r13, ev13 = dispatch_case(["dead", "live"],
                          lambda name: _FakeAdapter(name, ok=(name == "live")))
check("W13 1순위 disabled → 2순위 폴백 실행",
      r13["status"] == "completed" and r13["summary"] == "adapter(live): hello",
      f"got {r13}")

# W15 (G4 필수수정 ②) — 폴백 실행 시 model_decision.selected_provider == 실제 실행 provider
md15 = [e for e in ev13 if e["kind"] == "model_decision"]
check("W15 폴백 시 selected_provider == 실제 실행 provider",
      len(md15) == 1
      and md15[0]["payload"]["selected_provider"] == r13["agent"] == "live"
      and md15[0]["payload"]["provider_chain"] == ["dead", "live"],
      f"got {r13} / events {ev13}")

# W14 전 provider 실행 불가 → 명시적 failed + worker_dispatch_failed 이벤트
#     결정된 provider가 없으므로 model_decision은 방출하지 않는다 (G4 필수수정 ①)
r14, ev14 = dispatch_case(["dead"], lambda name: _FakeAdapter(name, ok=False))
df14 = [e for e in ev14 if e["kind"] == "worker_dispatch_failed"]
check("W14 실행 가능 provider 없음 → 명시적 failed + 이벤트 (model_decision 없음)",
      r14["status"] == "failed" and "디스패치 실패" in r14["summary"]
      and "dead" in r14["summary"]
      and len(df14) == 1 and df14[0]["payload"]["provider_chain"] == ["dead"]
      and df14[0]["payload"]["skipped"]
      and not [e for e in ev14 if e["kind"] == "model_decision"],
      f"got {r14} / events {ev14}")

# ── W16~W21 — Stage 19 정책 shadow 상담 (서버 불필요, 이벤트는 임시 경로로 격리) ──
from core import config as core_config  # noqa: E402
from core import policy_engine  # noqa: E402
from core import usage_ledger  # noqa: E402

# W16 리포 기본 config → shadow 모드 (배선 기본값 = 관측 on, 차단 없음)
check("W16 기본 features.policy_enforcement=shadow → 상담 활성",
      worker._policy_mode() == "shadow", f"got {worker._policy_mode()!r}")

ECHO_TASK = {
    "task_id": "task_20260712_100000_cd34", "task_type": "chat",
    "target_agent": AGENT, "payload": {"instruction": "hello"},
}


def policy_case(mode, *, monthly=None, summary=None, eval_fn=None,
                load_fn=None, summary_fn=None):
    """echo 경로(dispatch off) + 지정 policy 모드로 handle_task 실행 → (result, 이벤트 목록).

    load_fn / summary_fn은 config 로드·usage 집계가 예외를 던지는 상황을 주입한다
    (관측의 어떤 실패도 실행을 막지 않는다 — ADR-0003, W23·W24가 고정).
    """
    tmp_log = Path(tempfile.mkdtemp(prefix="bucky_pol_")) / "events.jsonl"
    fake_cfg = {"features": {"worker_adapter_dispatch": False,
                             "policy_enforcement": mode}}
    if monthly is not None:
        fake_cfg["budget"] = {"monthly_warn_usd": monthly}
    orig = (core_config.load_bucky, policy_engine.evaluate,
            usage_ledger.month_summary, event_log.EVENTS_PATH)
    core_config.load_bucky = load_fn or (lambda: fake_cfg)
    if eval_fn is not None:
        policy_engine.evaluate = eval_fn
    if summary_fn is not None:
        usage_ledger.month_summary = summary_fn
    elif summary is not None:
        usage_ledger.month_summary = lambda month=None, **kw: summary
    event_log.EVENTS_PATH = tmp_log
    try:
        result = worker.handle_task(dict(ECHO_TASK))
    finally:
        (core_config.load_bucky, policy_engine.evaluate,
         usage_ledger.month_summary, event_log.EVENTS_PATH) = orig
    events = []
    if tmp_log.is_file():
        events = [json.loads(ln) for ln in
                  tmp_log.read_text(encoding="utf-8").splitlines()]
    return result, events


def _dumps(d):
    return json.dumps(d, sort_keys=True, ensure_ascii=False)


# W17 필수 회귀 — shadow에서 기존 동작 바이트 동일 + policy_decision 이벤트만 추가
r_off, ev_off = policy_case("off")
r_sh, ev_sh = policy_case("shadow")
pd17 = [e for e in ev_sh if e["kind"] == "policy_decision"]
check("W17 shadow: echo 결과 off와 바이트 동일 + policy_decision 1건 (chat→T0/auto)",
      _dumps(r_off) == _dumps(r_sh)
      and not ev_off
      and len(pd17) == 1
      and pd17[0]["task_id"] == ECHO_TASK["task_id"]
      and pd17[0]["payload"]["tier"] == "T0"
      and pd17[0]["payload"]["decision"] == "auto"
      and pd17[0]["payload"]["mode"] == "shadow",
      f"got {r_sh} / off_ev {ev_off} / sh_ev {ev_sh}")


# W18 상담 내부 예외 → 실행 불간섭 (관측이 실행을 막지 않는다, ADR-0003)
def _eval_boom(spec, rules=None):
    raise RuntimeError("policy boom")


r18, ev18 = policy_case("shadow", eval_fn=_eval_boom)
check("W18 정책 상담 내부 예외 → echo 결과 불변·예외 미전파",
      _dumps(r18) == _dumps(r_off)
      and not [e for e in ev18 if e["kind"] == "policy_decision"],
      f"got {r18} / events {ev18}")

# W19~W20 예산 경고 — 월 합계 추정 비용 임계 초과 시에만 budget_warning
S_OVER = {"month": "2026-07", "records": 3, "tokens_in": 1, "tokens_out": 1,
          "cost_usd": 51.5, "by_model": {}}
r19, ev19 = policy_case("shadow", monthly=50, summary=S_OVER)
bw19 = [e for e in ev19 if e["kind"] == "budget_warning"]
check("W19 월 합계 임계 초과 → budget_warning 이벤트 (실행은 정상 완료)",
      r19["status"] == "completed" and len(bw19) == 1
      and bw19[0]["payload"]["cost_usd"] == 51.5
      and bw19[0]["payload"]["threshold_usd"] == 50.0
      and bw19[0]["payload"]["month"] == "2026-07",
      f"got {ev19}")

r20, ev20 = policy_case("shadow", monthly=50, summary=dict(S_OVER, cost_usd=49.0))
check("W20 임계 이하 → budget_warning 없음 (policy_decision만)",
      not [e for e in ev20 if e["kind"] == "budget_warning"]
      and len([e for e in ev20 if e["kind"] == "policy_decision"]) == 1,
      f"got {ev20}")

# W21 디스패치 경로에서도 상담 — W12 이벤트에 policy_decision이 model_decision보다 앞
check("W21 디스패치 경로 상담 — policy_decision이 model_decision보다 먼저 방출",
      ev12 and ev12[0]["kind"] == "policy_decision"
      and [e for e in ev12 if e["kind"] == "model_decision"],
      f"got {ev12}")

# ── W22~W24 — G5 비차단 권고 이행 (07-14) ──

# W22 (권고 ①) — W17은 echo 경로만 고정했다. 디스패치 경로에서도 shadow 상담이
#     반환값을 바꾸지 않음을 고정한다 (shadow 규약은 실행 경로와 무관하다, ADR-0004)
r_dsp_off, ev_dsp_off = dispatch_case(
    ["fake_ok"], lambda name: _FakeAdapter(name), policy_mode="")
r_dsp_sh, ev_dsp_sh = dispatch_case(
    ["fake_ok"], lambda name: _FakeAdapter(name), policy_mode="shadow")
pd22 = [e for e in ev_dsp_sh if e["kind"] == "policy_decision"]
check("W22 shadow: 디스패치 결과 off와 바이트 동일 + policy_decision 1건만 추가",
      _dumps(r_dsp_off) == _dumps(r_dsp_sh)
      and not [e for e in ev_dsp_off if e["kind"] == "policy_decision"]
      and len(pd22) == 1
      and pd22[0]["task_id"] == DISPATCH_TASK["task_id"]
      and pd22[0]["payload"]["mode"] == "shadow"
      and [e for e in ev_dsp_off if e["kind"] == "model_decision"],
      f"off {r_dsp_off}/{ev_dsp_off} / shadow {r_dsp_sh}/{ev_dsp_sh}")


# 주입한 예외가 실제로 터졌는지 센다 — 호출조차 안 됐다면 W23·W24는 아무것도 검증하지
# 않은 채 통과한다(가드가 사라져도 못 잡는 공허한 테스트). 호출 횟수도 함께 고정한다.
_boom = {"load": 0, "summary": 0}


# W23 (권고 ②) — config 로드 실패. W18은 evaluate 예외만 덮었다.
def _load_boom():
    _boom["load"] += 1
    raise RuntimeError("config boom")


r23, ev23 = policy_case("shadow", load_fn=_load_boom)
check("W23 config 로드 실패 → 상담 생략·echo 결과 불변·예외 미전파 (로드가 실제로 터짐)",
      _boom["load"] > 0 and _dumps(r23) == _dumps(r_off) and not ev23,
      f"load_calls={_boom['load']} / got {r23} / events {ev23}")


# W24 (권고 ②) — usage 집계 예외. 앞서 방출된 policy_decision은 남고 실행은 무영향.
def _summary_boom(month=None, **kw):
    _boom["summary"] += 1
    raise RuntimeError("ledger boom")


r24, ev24 = policy_case("shadow", monthly=50, summary_fn=_summary_boom)
check("W24 month_summary 예외 → budget_warning 없음·policy_decision 유지·결과 불변 (집계가 실제로 터짐)",
      _boom["summary"] == 1 and _dumps(r24) == _dumps(r_off)
      and len([e for e in ev24 if e["kind"] == "policy_decision"]) == 1
      and not [e for e in ev24 if e["kind"] == "budget_warning"],
      f"summary_calls={_boom['summary']} / got {r24} / events {ev24}")

print(f"\n결과: {PASS} PASS / {FAIL} FAIL (총 {PASS + FAIL})")
sys.exit(1 if FAIL else 0)
