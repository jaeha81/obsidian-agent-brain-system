#!/usr/bin/env python3
"""Tests for context_pack_selector.py.

Covers: select_context_pack, build_instruction_packet, format_text,
inject_context_packs (security, budget, markers), CLI text/json/packet formats.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

import pytest

# scripts/ is one level up from tests/
_SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS_DIR))

from context_pack_selector import (  # noqa: E402
    _DEFAULT_MAX_CHARS,
    _REPO_ROOT,
    _resolve_safe_path,
    build_instruction_packet,
    format_text,
    inject_context_packs,
    select_context_pack,
)


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _run_cli(*args: str) -> tuple[int, str]:
    """Run context_pack_selector.py and return (exit_code, stdout).

    Uses -X utf8 to force UTF-8 I/O on Windows, consistent with the
    CLAUDE.md convention: ``python -X utf8 scripts/context_pack_selector.py``.
    """
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(_SCRIPTS_DIR / "context_pack_selector.py"), *args],
        capture_output=True,
        encoding="utf-8",
    )
    return result.returncode, result.stdout


# ---------------------------------------------------------------------------
# Original unittest tests (kept verbatim from tests/test_context_pack_selector.py)
# ---------------------------------------------------------------------------

class ContextPackSelectorTests(unittest.TestCase):
    def test_select_review_pack_for_review_request(self):
        selection = select_context_pack(
            task_type="review_request",
            body="Codex review 해줘. 변경 파일만 검수해줘.",
        )

        self.assertEqual(selection["primary_worker"], "Codex Reviewer")
        self.assertIn("ObsidianVault/03_Projects/agents/codex-instructions.md", selection["packs"])
        self.assertTrue(any("review" in n.lower() or "검수" in n.lower() for n in selection["notes"]))

    def test_select_discord_pack_for_discord_pipeline_body(self):
        selection = select_context_pack(
            task_type="general",
            body="Discord 봇 응답이 끊겼을 때 fallback 경로를 확인해줘.",
        )

        self.assertEqual(selection["primary_worker"], "Bucky Operator")
        self.assertIn("ObsidianVault/00_System/ROUTING_RULES.md", selection["packs"])
        self.assertTrue(any("discord" in n.lower() or "agentbus" in n.lower() for n in selection["notes"]))

    def test_select_sync_pack_for_pc_or_storage_body(self):
        selection = select_context_pack(
            task_type="general",
            body="사무실 PC에서 저장 위치와 GitHub 동기화 상태를 확인해줘.",
        )

        # sync_agentbus rule wins ("동기화" trigger) → Bucky Operator
        self.assertEqual(selection["primary_worker"], "Bucky Operator")
        self.assertIn("ObsidianVault/05_Frameworks/guides/sync-protocol.md", selection["packs"])

    def test_format_text_includes_worker_pack_and_notes(self):
        selection = select_context_pack(
            task_type="general",
            body="Discord fallback pipeline",
        )

        text = format_text(selection)

        self.assertIn("[Context Pack Selector]", text)
        self.assertIn("Primary worker: Bucky Operator", text)
        self.assertIn("ObsidianVault/00_System/ROUTING_RULES.md", text)
        self.assertIn("AgentBus", text)


# ---------------------------------------------------------------------------
# select_context_pack — pytest
# ---------------------------------------------------------------------------

class TestSelectContextPack:
    def test_keyword_routes_to_review(self):
        sel = select_context_pack(task_type="review", body="verify the changes")
        assert sel["key"] == "review"
        assert any("codex" in p.lower() for p in sel["packs"])

    def test_keyword_routes_to_implementation(self):
        sel = select_context_pack(task_type="implementation", body="implement new feature")
        assert sel["key"] == "implementation"

    def test_keyword_routes_to_security(self):
        sel = select_context_pack(task_type="general", body="auth and secret management")
        assert sel["key"] == "security_runtime"

    def test_fallback_to_implementation_on_no_match(self):
        sel = select_context_pack(task_type="", body="")
        assert sel["key"] == "implementation"

    def test_result_has_required_keys(self):
        sel = select_context_pack(task_type="general", body="ingest record")
        for key in ("key", "primary_worker", "role", "packs", "notes"):
            assert key in sel

    def test_packs_is_list(self):
        sel = select_context_pack(task_type="general", body="design")
        assert isinstance(sel["packs"], list)
        assert len(sel["packs"]) > 0

    def test_keyword_routes_to_video_production(self):
        sel = select_context_pack(
            task_type="general",
            body="Higgsfield MCP로 쇼츠 영상 제작 요청을 처리해줘.",
        )

        assert sel["key"] == "video_production"
        assert sel["primary_worker"] == "Bucky Video Producer"
        assert any("higgsfield-video-production" in p for p in sel["packs"])


# ---------------------------------------------------------------------------
# build_instruction_packet — pytest
# ---------------------------------------------------------------------------

class TestBuildInstructionPacket:
    def test_packet_has_required_keys(self):
        packet = build_instruction_packet(task_type="implementation", body="do the thing")
        required = {
            "project", "agent", "role", "goal", "scope",
            "constraints", "context_packs", "references",
            "verification", "done_when", "fallback",
        }
        assert required.issubset(packet.keys())

    def test_project_defaults_to_cwd(self):
        packet = build_instruction_packet(task_type="general", body="test", project="")
        assert packet["project"] == str(Path.cwd())

    def test_explicit_project_preserved(self):
        packet = build_instruction_packet(task_type="general", body="test", project="my-project")
        assert packet["project"] == "my-project"

    def test_context_packs_is_list(self):
        packet = build_instruction_packet(task_type="review", body="verify")
        assert isinstance(packet["context_packs"], list)


# ---------------------------------------------------------------------------
# format_text — pytest
# ---------------------------------------------------------------------------

class TestFormatText:
    def test_format_text_contains_key(self):
        sel = select_context_pack(task_type="review", body="")
        text = format_text(sel)
        assert "Key:" in text
        assert "review" in text

    def test_format_text_contains_packs(self):
        sel = select_context_pack(task_type="general", body="ingest")
        text = format_text(sel)
        assert "Packs:" in text

    def test_format_text_with_inject_shows_injected_section(self, tmp_path: Path):
        pack_dir = tmp_path / "ObsidianVault" / "06_Context_Packs"
        pack_dir.mkdir(parents=True)
        (pack_dir / "test.md").write_text("# ctx", encoding="utf-8")

        sel = select_context_pack(task_type="review", body="")
        sel["injected_context"] = inject_context_packs(
            ["ObsidianVault/06_Context_Packs/test.md"], vault_root=tmp_path
        )
        text = format_text(sel)
        assert "Injected Context:" in text
        assert "===" in text


# ---------------------------------------------------------------------------
# inject_context_packs — security
# ---------------------------------------------------------------------------

class TestInjectContextPacksSecurity:
    def test_blocks_absolute_path(self, tmp_path: Path):
        abs_path = str(tmp_path / "secret.txt")
        result = inject_context_packs([abs_path], vault_root=tmp_path)
        assert result[abs_path].startswith("[BLOCKED:")

    def test_blocks_dotdot_path(self, tmp_path: Path):
        traversal = "ObsidianVault/../../../etc/passwd"
        result = inject_context_packs([traversal], vault_root=tmp_path)
        assert result[traversal].startswith("[BLOCKED:")

    def test_blocks_path_outside_allowed_roots(self, tmp_path: Path):
        outside = "external_data/something.md"
        result = inject_context_packs([outside], vault_root=tmp_path)
        assert result[outside].startswith("[BLOCKED:")

    def test_reads_valid_obsidianvault_file(self, tmp_path: Path):
        pack_dir = tmp_path / "ObsidianVault" / "06_Context_Packs"
        pack_dir.mkdir(parents=True)
        (pack_dir / "test-pack.md").write_text("# test pack content", encoding="utf-8")

        result = inject_context_packs(
            ["ObsidianVault/06_Context_Packs/test-pack.md"],
            vault_root=tmp_path,
        )
        assert result["ObsidianVault/06_Context_Packs/test-pack.md"] == "# test pack content"

    def test_not_found_returns_sentinel(self, tmp_path: Path):
        result = inject_context_packs(["ObsidianVault/nonexistent.md"], vault_root=tmp_path)
        assert result["ObsidianVault/nonexistent.md"].startswith("[NOT FOUND:")

    def test_default_vault_root_is_repo_root(self):
        assert _REPO_ROOT == _SCRIPTS_DIR.parent

    def test_blocks_double_dotdot_in_middle(self, tmp_path: Path):
        traversal = "ObsidianVault/packs/../../etc/shadow"
        result = inject_context_packs([traversal], vault_root=tmp_path)
        assert result[traversal].startswith("[BLOCKED:")


# ---------------------------------------------------------------------------
# inject_context_packs — --packet + --inject policy
# ---------------------------------------------------------------------------

class TestPacketInjectCombinedPolicy:
    def test_packet_inject_adds_injected_context_key(self, tmp_path: Path):
        packet = build_instruction_packet(
            task_type="implementation", body="do something", project="test"
        )
        packet["injected_context"] = inject_context_packs(
            packet["context_packs"][:1], vault_root=tmp_path
        )
        assert "injected_context" in packet
        assert isinstance(packet["injected_context"], dict)

    def test_inject_only_adds_injected_context_to_select_output(self, tmp_path: Path):
        sel = select_context_pack(task_type="review", body="verify")
        sel["injected_context"] = inject_context_packs(sel["packs"][:1], vault_root=tmp_path)
        assert "injected_context" in sel

    def test_cli_packet_flag_produces_valid_json(self):
        code, stdout = _run_cli("--packet", "implement the new feature")
        assert code == 0
        data = json.loads(stdout)
        assert "context_packs" in data
        assert "agent" in data

    def test_cli_inject_without_packet_adds_injected_context(self):
        code, stdout = _run_cli("--inject", "--format", "json", "implement something")
        assert code == 0
        data = json.loads(stdout)
        assert "injected_context" in data
        for v in data["injected_context"].values():
            assert isinstance(v, str)

    def test_cli_packet_inject_combined(self):
        code, stdout = _run_cli("--packet", "--inject", "implement feature")
        assert code == 0
        data = json.loads(stdout)
        assert "injected_context" in data
        assert "context_packs" in data


# ---------------------------------------------------------------------------
# inject_context_packs — budget + five markers
# ---------------------------------------------------------------------------

class TestInjectBudgetAndMarkers:
    """Full DoD: max_chars budget enforcement + all five content markers.

    Markers: [BLOCKED:] [NOT FOUND:] [BINARY:] [TRUNCATED:] [BUDGET_EXHAUSTED:]
    """

    def _pack_dir(self, tmp_path: Path) -> Path:
        d = tmp_path / "ObsidianVault" / "06_Context_Packs"
        d.mkdir(parents=True)
        return d

    def _pack_path(self, name: str) -> str:
        return f"ObsidianVault/06_Context_Packs/{name}"

    # --- [BINARY:] marker ---

    def test_binary_file_returns_binary_marker(self, tmp_path: Path):
        pack_dir = self._pack_dir(tmp_path)
        (pack_dir / "binary.bin").write_bytes(b"\xff\xfe\x00\x01invalid-utf8")

        result = inject_context_packs([self._pack_path("binary.bin")], vault_root=tmp_path)
        value = result[self._pack_path("binary.bin")]
        assert value.startswith("[BINARY:")
        assert "binary.bin" in value

    # --- [TRUNCATED:] marker ---

    def test_truncation_when_file_exceeds_budget(self, tmp_path: Path):
        pack_dir = self._pack_dir(tmp_path)
        (pack_dir / "large.md").write_text("A" * 1000, encoding="utf-8")

        result = inject_context_packs(
            [self._pack_path("large.md")], vault_root=tmp_path, max_chars=100
        )
        value = result[self._pack_path("large.md")]
        assert "[TRUNCATED:" in value
        kept = value.split("\n[TRUNCATED:")[0]
        assert kept == "A" * 100

    def test_truncation_marker_contains_budget_info(self, tmp_path: Path):
        """Streaming read omits original file size; marker states chars kept and budget."""
        pack_dir = self._pack_dir(tmp_path)
        (pack_dir / "large.md").write_text("B" * 500, encoding="utf-8")

        result = inject_context_packs(
            [self._pack_path("large.md")], vault_root=tmp_path, max_chars=50
        )
        value = result[self._pack_path("large.md")]
        assert "[TRUNCATED:" in value
        assert "50" in value  # chars kept / budget appear in marker

    # --- [BUDGET_EXHAUSTED:] marker ---

    def test_budget_exhausted_skips_remaining_packs(self, tmp_path: Path):
        pack_dir = self._pack_dir(tmp_path)
        (pack_dir / "first.md").write_text("X" * 100, encoding="utf-8")
        (pack_dir / "second.md").write_text("Y" * 100, encoding="utf-8")

        result = inject_context_packs(
            [self._pack_path("first.md"), self._pack_path("second.md")],
            vault_root=tmp_path,
            max_chars=100,
        )
        assert result[self._pack_path("first.md")] == "X" * 100
        assert result[self._pack_path("second.md")].startswith("[BUDGET_EXHAUSTED:")

    def test_budget_exhausted_after_truncation(self, tmp_path: Path):
        pack_dir = self._pack_dir(tmp_path)
        (pack_dir / "a.md").write_text("A" * 200, encoding="utf-8")
        (pack_dir / "b.md").write_text("B" * 10, encoding="utf-8")

        result = inject_context_packs(
            [self._pack_path("a.md"), self._pack_path("b.md")],
            vault_root=tmp_path,
            max_chars=50,
        )
        assert "[TRUNCATED:" in result[self._pack_path("a.md")]
        assert result[self._pack_path("b.md")].startswith("[BUDGET_EXHAUSTED:")

    # --- multi-file shared budget ---

    def test_multiple_files_share_budget(self, tmp_path: Path):
        pack_dir = self._pack_dir(tmp_path)
        for name in ("p1.md", "p2.md", "p3.md"):
            (pack_dir / name).write_text("Z" * 30, encoding="utf-8")

        result = inject_context_packs(
            [self._pack_path(n) for n in ("p1.md", "p2.md", "p3.md")],
            vault_root=tmp_path,
            max_chars=70,
        )
        assert result[self._pack_path("p1.md")] == "Z" * 30
        assert result[self._pack_path("p2.md")] == "Z" * 30
        p3 = result[self._pack_path("p3.md")]
        assert "[TRUNCATED:" in p3 or p3.startswith("[BUDGET_EXHAUSTED:")

    def test_zero_budget_exhausts_all(self, tmp_path: Path):
        pack_dir = self._pack_dir(tmp_path)
        (pack_dir / "any.md").write_text("hello", encoding="utf-8")

        result = inject_context_packs(
            [self._pack_path("any.md")], vault_root=tmp_path, max_chars=0
        )
        assert result[self._pack_path("any.md")].startswith("[BUDGET_EXHAUSTED:")

    def test_exact_budget_reads_fully_without_marker(self, tmp_path: Path):
        pack_dir = self._pack_dir(tmp_path)
        (pack_dir / "exact.md").write_text("E" * 42, encoding="utf-8")

        result = inject_context_packs(
            [self._pack_path("exact.md")], vault_root=tmp_path, max_chars=42
        )
        assert result[self._pack_path("exact.md")] == "E" * 42

    def test_default_max_chars_constant_is_positive(self):
        assert isinstance(_DEFAULT_MAX_CHARS, int)
        assert _DEFAULT_MAX_CHARS > 0


# ---------------------------------------------------------------------------
# CLI — text / json / packet × inject / max-chars
# ---------------------------------------------------------------------------

class TestCLIFormats:
    """--format text, --format json, --packet — with and without --inject."""

    def _make_pack(self, tmp_path: Path, name: str, content: str) -> str:
        d = tmp_path / "ObsidianVault" / "06_Context_Packs"
        d.mkdir(parents=True, exist_ok=True)
        (d / name).write_text(content, encoding="utf-8")
        return f"ObsidianVault/06_Context_Packs/{name}"

    # text (no inject)

    def test_cli_text_format_contains_header(self):
        code, stdout = _run_cli("--format", "text", "implement something")
        assert code == 0
        assert "[Context Pack Selector]" in stdout
        assert "Key:" in stdout
        assert "Packs:" in stdout

    def test_cli_text_format_no_injected_section_by_default(self):
        code, stdout = _run_cli("--format", "text", "implement something")
        assert code == 0
        assert "Injected Context:" not in stdout

    # text + inject

    def test_cli_text_format_with_inject_shows_injected_section(self, tmp_path: Path):
        self._make_pack(tmp_path, "ctx.md", "# hello from ctx")
        code, stdout = _run_cli(
            "--format", "text", "--inject",
            "--vault-root", str(tmp_path),
            "implement something",
        )
        assert code == 0
        assert "Injected Context:" in stdout

    def test_cli_text_format_inject_shows_file_dividers(self, tmp_path: Path):
        self._make_pack(tmp_path, "ctx.md", "# content")
        code, stdout = _run_cli(
            "--format", "text", "--inject",
            "--vault-root", str(tmp_path),
            "implement something",
        )
        assert code == 0
        assert "===" in stdout

    # json (no inject)

    def test_cli_json_format_produces_valid_json(self):
        code, stdout = _run_cli("--format", "json", "review the diff")
        assert code == 0
        data = json.loads(stdout)
        assert "key" in data
        assert "packs" in data

    def test_cli_json_format_no_inject_has_no_injected_context(self):
        code, stdout = _run_cli("--format", "json", "review the diff")
        assert code == 0
        assert "injected_context" not in json.loads(stdout)

    # json + inject

    def test_cli_json_inject_adds_injected_context(self):
        code, stdout = _run_cli("--format", "json", "--inject", "implement feature")
        assert code == 0
        data = json.loads(stdout)
        assert "injected_context" in data
        assert isinstance(data["injected_context"], dict)

    def test_cli_json_inject_values_are_strings(self):
        code, stdout = _run_cli("--format", "json", "--inject", "implement feature")
        assert code == 0
        for v in json.loads(stdout)["injected_context"].values():
            assert isinstance(v, str)

    # packet (no inject)

    def test_cli_packet_produces_valid_json(self):
        code, stdout = _run_cli("--packet", "implement the new feature")
        assert code == 0
        data = json.loads(stdout)
        assert "context_packs" in data
        assert "agent" in data
        assert "injected_context" not in data

    # packet + inject

    def test_cli_packet_inject_adds_injected_context(self):
        code, stdout = _run_cli("--packet", "--inject", "implement feature")
        assert code == 0
        data = json.loads(stdout)
        assert "injected_context" in data
        assert "context_packs" in data

    def test_cli_packet_inject_values_are_strings(self):
        code, stdout = _run_cli("--packet", "--inject", "implement feature")
        assert code == 0
        for v in json.loads(stdout)["injected_context"].values():
            assert isinstance(v, str)

    # --max-chars

    def test_cli_max_chars_limits_injection(self, tmp_path: Path):
        """--max-chars 5: create all selected packs in tmp_path with 100 chars each."""
        sel = select_context_pack(task_type="implementation", body="implement something")
        for pack_rel in sel["packs"]:
            dest = tmp_path / pack_rel.replace("/", "\\")
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text("A" * 100, encoding="utf-8")

        code, stdout = _run_cli(
            "--format", "json", "--inject",
            "--vault-root", str(tmp_path),
            "--max-chars", "5",
            "implement something",
        )
        assert code == 0
        markers = "\n".join(json.loads(stdout)["injected_context"].values())
        assert "[TRUNCATED:" in markers or "[BUDGET_EXHAUSTED:" in markers

    def test_cli_max_chars_zero_exhausts_all(self, tmp_path: Path):
        self._make_pack(tmp_path, "x.md", "hello")
        code, stdout = _run_cli(
            "--format", "json", "--inject",
            "--vault-root", str(tmp_path),
            "--max-chars", "0",
            "implement something",
        )
        assert code == 0
        for v in json.loads(stdout)["injected_context"].values():
            assert "[BUDGET_EXHAUSTED:" in v or "[BLOCKED:" in v or "[NOT FOUND:" in v


# ---------------------------------------------------------------------------
# _resolve_safe_path — unit
# ---------------------------------------------------------------------------

class TestResolveSafePath:
    def test_returns_none_for_absolute(self, tmp_path: Path):
        assert _resolve_safe_path("/etc/passwd", tmp_path) is None

    def test_returns_none_for_dotdot(self, tmp_path: Path):
        assert _resolve_safe_path("ObsidianVault/../secret", tmp_path) is None

    def test_returns_none_for_disallowed_root(self, tmp_path: Path):
        assert _resolve_safe_path("D:/Projects/secret.py", tmp_path) is None

    def test_returns_path_for_valid(self, tmp_path: Path):
        (tmp_path / "ObsidianVault").mkdir()
        result = _resolve_safe_path("ObsidianVault/test.md", tmp_path)
        assert result is not None
        assert result == (tmp_path / "ObsidianVault" / "test.md").resolve()


if __name__ == "__main__":
    unittest.main()
