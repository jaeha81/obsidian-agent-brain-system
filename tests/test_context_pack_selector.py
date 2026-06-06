import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import context_pack_selector


class ContextPackSelectorTests(unittest.TestCase):
    def test_select_review_pack_for_review_request(self):
        selection = context_pack_selector.select_context_pack(
            task_type="review_request",
            body="Codex review 해줘. 변경 파일만 검수해줘.",
        )

        self.assertEqual(selection["primary_worker"], "Codex Reviewer")
        self.assertIn("ObsidianVault/03_Projects/agents/codex-instructions.md", selection["packs"])
        self.assertTrue(any("review" in n.lower() or "검수" in n.lower() for n in selection["notes"]))

    def test_select_discord_pack_for_discord_pipeline_body(self):
        selection = context_pack_selector.select_context_pack(
            task_type="general",
            body="Discord 봇 응답이 끊겼을 때 fallback 경로를 확인해줘.",
        )

        self.assertEqual(selection["primary_worker"], "Bucky Operator")
        self.assertIn("ObsidianVault/00_System/ROUTING_RULES.md", selection["packs"])
        self.assertTrue(any("discord" in n.lower() or "agentbus" in n.lower() for n in selection["notes"]))

    def test_select_sync_pack_for_pc_or_storage_body(self):
        selection = context_pack_selector.select_context_pack(
            task_type="general",
            body="사무실 PC에서 저장 위치와 GitHub 동기화 상태를 확인해줘.",
        )

        # sync_agentbus rule wins ("동기화" trigger) → Bucky Operator
        self.assertEqual(selection["primary_worker"], "Bucky Operator")
        self.assertIn("ObsidianVault/05_Frameworks/guides/sync-protocol.md", selection["packs"])

    def test_format_text_includes_worker_pack_and_notes(self):
        selection = context_pack_selector.select_context_pack(
            task_type="general",
            body="Discord fallback pipeline",
        )

        text = context_pack_selector.format_text(selection)

        self.assertIn("[Context Pack Selector]", text)
        self.assertIn("Primary worker: Bucky Operator", text)
        self.assertIn("ObsidianVault/00_System/ROUTING_RULES.md", text)
        self.assertIn("AgentBus", text)


if __name__ == "__main__":
    unittest.main()
