"""scripts/core/policy_engine.py 단위 테스트 — Stage 18 승인 정책 엔진 (P0-6).

플랜 필수 케이스: T0 자동 / T3 승인요구 / 미분류 기본값 + routing_policy.yaml 중복 키 금지.
"""

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core.config import load_routing_policy, load_yaml  # noqa: E402
from core.policy_engine import evaluate, load_rules, validate_rules  # noqa: E402
from core.task_spec import TaskSpec  # noqa: E402
from model_router import TASK_TO_MODEL  # noqa: E402

RULES = load_rules()  # repo 실데이터 — 대부분의 판정 테스트는 이걸로 검증


class EvaluateTests(unittest.TestCase):
    def test_t0_auto(self):
        spec = TaskSpec(task_id="task_20260712_100000_ab12", task_type="classify")
        v = evaluate(spec, RULES)
        self.assertEqual((v["tier"], v["decision"]), ("T0", "auto"), v)

    def test_t1_auto_log(self):
        v = evaluate({"task_type": "code"}, RULES)
        self.assertEqual((v["tier"], v["decision"]), ("T1", "auto_log"), v)

    def test_t3_require_approval(self):
        for task_type in ("deploy", "payment", "delete", "push"):
            v = evaluate({"task_type": task_type}, RULES)
            self.assertEqual((v["tier"], v["decision"]), ("T3", "require_approval"),
                             f"{task_type}: {v}")

    def test_unclassified_falls_to_default_tier(self):
        v = evaluate({"task_type": "아직없는유형"}, RULES)
        self.assertEqual((v["tier"], v["decision"]), ("T3", "require_approval"), v)
        self.assertIn("미분류", v["reason"])

    def test_task_type_normalized(self):
        v = evaluate({"task_type": "  Chat "}, RULES)
        self.assertEqual((v["tier"], v["decision"]), ("T0", "auto"), v)

    def test_empty_rules_conservative(self):
        v = evaluate({"task_type": "chat"}, rules={})
        self.assertEqual((v["tier"], v["decision"]), ("T3", "require_approval"), v)

    def test_non_string_task_type_conservative(self):
        v = evaluate({"task_type": None}, RULES)
        self.assertEqual(v["decision"], "require_approval", v)

    def test_tier_without_decision_conservative(self):
        rules = {"tiers": {"T9": {}}, "task_tiers": {"chat": "T9"}, "default_tier": "T9"}
        v = evaluate({"task_type": "chat"}, rules)
        self.assertEqual(v["decision"], "require_approval", v)
        self.assertIn("결손", v["reason"])

    def test_pure_no_mutation(self):
        spec = {"task_type": "chat"}
        rules_before = copy.deepcopy(RULES)
        evaluate(spec, RULES)
        self.assertEqual(spec, {"task_type": "chat"})
        self.assertEqual(RULES, rules_before)


class RulesFileTests(unittest.TestCase):
    """repo의 config/policy_rules.yaml 실데이터 계약."""

    def test_repo_rules_valid(self):
        self.assertEqual(validate_rules(RULES, routing_policy=load_routing_policy()), [])

    def test_no_toplevel_key_overlap_with_routing_policy(self):
        # 플랜 Stage 18 요구 — 라우팅(provider 후보열)과 정책(위험 티어)의 키 공간 분리
        routing = load_yaml("routing_policy.yaml")
        self.assertTrue(routing, "routing_policy.yaml 로드 실패")
        self.assertEqual(set(RULES) & set(routing), set())

    def test_dispatch_fallback_policy_pinned(self):
        # G4 권고 1 확정(07-12 사용자 A안): run 실패 시 다음 후보 재시도 금지
        self.assertIs(RULES["dispatch"]["fallback_on_run_failure"], False)

    def test_task_tiers_cover_router_vocabulary(self):
        # G5 필수수정 ② 확정(07-12 사용자 A안): 라우터 어휘 전체가 task_tiers에 명시 등록
        missing = set(TASK_TO_MODEL) - set(RULES["task_tiers"])
        self.assertEqual(missing, set(), f"task_tiers 미등록 라우터 어휘: {missing}")


class ValidateRulesTests(unittest.TestCase):
    def test_empty_rules(self):
        errors = validate_rules({})
        self.assertTrue(errors and "비어" in errors[0], errors)

    def test_missing_tier_decision(self):
        rules = copy.deepcopy(RULES)
        del rules["tiers"]["T2"]
        errors = validate_rules(rules)
        self.assertTrue(any("tiers.T2" in e for e in errors), errors)

    def test_unknown_tier_reference(self):
        rules = copy.deepcopy(RULES)
        rules["task_tiers"]["chat"] = "T9"
        errors = validate_rules(rules)
        self.assertTrue(any("T9" in e and "chat" in e for e in errors), errors)

    def test_bad_default_tier(self):
        rules = copy.deepcopy(RULES)
        rules["default_tier"] = "T9"
        errors = validate_rules(rules)
        self.assertTrue(any("default_tier" in e for e in errors), errors)

    def test_missing_dispatch_policy(self):
        rules = copy.deepcopy(RULES)
        del rules["dispatch"]
        errors = validate_rules(rules)
        self.assertTrue(any("fallback_on_run_failure" in e for e in errors), errors)

    def test_key_overlap_detected(self):
        rules = copy.deepcopy(RULES)
        rules["defaults"] = {}  # routing_policy.yaml top-level 키와 고의 충돌
        errors = validate_rules(rules, routing_policy=load_routing_policy())
        self.assertTrue(any("중복" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
