"""scripts/core/config.py 단위 테스트 — V3 Stage 3 config 단일화 스캐폴드."""

import importlib
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from core import config  # noqa: E402


class PathTests(unittest.TestCase):
    def test_paths_resolve_to_repo(self):
        self.assertEqual(config.ROOT, ROOT)
        self.assertEqual(config.PATHS["vault"], ROOT / "ObsidianVault")
        self.assertEqual(config.PATHS["agent_bus"], ROOT / "ObsidianVault" / "10_AgentBus")
        self.assertEqual(config.PATHS["data"], ROOT / "data")
        self.assertEqual(config.PATHS["docs"], ROOT / "docs")

    def test_all_paths_exist(self):
        for key, path in config.PATHS.items():
            self.assertTrue(path.is_dir(), f"{key} 경로 없음: {path}")

    def test_env_root_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["BUCKY_ROOT"] = tmp
            try:
                importlib.reload(config)
                self.assertEqual(config.ROOT, Path(tmp).resolve())
            finally:
                os.environ.pop("BUCKY_ROOT", None)
                importlib.reload(config)
        self.assertEqual(config.ROOT, ROOT)

    def test_invalid_env_root_falls_back(self):
        os.environ["BUCKY_ROOT"] = str(ROOT / "존재하지않는폴더")
        try:
            importlib.reload(config)
            self.assertEqual(config.ROOT, ROOT)
        finally:
            os.environ.pop("BUCKY_ROOT", None)
            importlib.reload(config)


class LoaderTests(unittest.TestCase):
    def test_missing_file_returns_empty(self):
        self.assertEqual(config.load_yaml("no_such_file.yaml"), {})

    def test_broken_yaml_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp) / "bad.yaml"
            bad.write_text("key: [unclosed", encoding="utf-8")
            self.assertEqual(config.load_yaml("bad.yaml", config_dir=Path(tmp)), {})

    def test_non_dict_yaml_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            listy = Path(tmp) / "list.yaml"
            listy.write_text("- a\n- b\n", encoding="utf-8")
            self.assertEqual(config.load_yaml("list.yaml", config_dir=Path(tmp)), {})

    def test_bom_yaml_loads(self):
        with tempfile.TemporaryDirectory() as tmp:
            bom = Path(tmp) / "bom.yaml"
            bom.write_bytes(b"\xef\xbb\xbfkey: value\n")
            self.assertEqual(config.load_yaml("bom.yaml", config_dir=Path(tmp)), {"key": "value"})


class BuckyYamlTests(unittest.TestCase):
    def setUp(self):
        self.data = config.load_bucky()

    def test_required_sections(self):
        for key in ("system", "paths", "oracle"):
            self.assertIn(key, self.data)

    def test_paths_match_config_py(self):
        rel = self.data["paths"]
        self.assertEqual(config.ROOT / rel["vault"], config.VAULT)
        self.assertEqual(config.ROOT / rel["agent_bus"], config.AGENT_BUS)
        self.assertEqual(config.ROOT / rel["data"], config.DATA)
        self.assertEqual(config.ROOT / rel["docs"], config.DOCS)

    def test_oracle_is_queue_of_record(self):
        oracle = self.data["oracle"]
        self.assertTrue(oracle["queue_of_record"])
        # 실측 env 키 이름과 일치 (oracle/core/client.py)
        self.assertEqual(oracle["api_url_env"], "ORACLE_API_URL")
        self.assertEqual(oracle["token_env"], "BUCKY_API_TOKEN")


class ModelRegistryTests(unittest.TestCase):
    def setUp(self):
        self.providers = config.load_model_registry().get("providers", {})

    def test_five_providers_defined(self):
        expected = {"claude_code", "codex_pro", "openai_gpt", "gemini", "anthropic_api"}
        self.assertEqual(set(self.providers.keys()), expected)

    def test_openai_disabled(self):
        self.assertFalse(self.providers["openai_gpt"]["enabled"])

    def test_env_keys_are_names_not_values(self):
        # 실제 키 값 금지 — env_keys에는 대문자 env 변수 "이름"만 허용
        for name, spec in self.providers.items():
            for key in spec.get("env_keys", []):
                self.assertRegex(key, r"^[A-Z][A-Z0-9_]*$", f"{name}.env_keys에 env 이름이 아닌 값: {key}")

    def test_gemini_default_matches_gemini_client(self):
        self.assertEqual(self.providers["gemini"]["models"]["default"], "gemini-2.0-flash")


class RoutingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.policy = config.load_routing_policy()

    def test_default_chain_providers_exist_in_registry(self):
        providers = set(config.load_model_registry().get("providers", {}))
        chain = self.policy["defaults"]["provider_chain"]
        self.assertTrue(chain)
        for p in chain:
            self.assertIn(p, providers)

    def test_review_routes_to_codex_first(self):
        self.assertEqual(self.policy["overrides"]["review"][0], "codex_pro")


class SelfTestTests(unittest.TestCase):
    def test_self_test_passes(self):
        self.assertEqual(config.self_test(), 0)


if __name__ == "__main__":
    unittest.main()
