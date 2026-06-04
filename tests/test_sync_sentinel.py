import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts import sync_sentinel


class SyncSentinelTests(unittest.TestCase):
    def test_classify_storage_recognizes_google_drive_paths(self):
        path = Path("G:/Google Drive/obsidian-agent-brain-system")

        self.assertEqual(sync_sentinel.classify_storage(path), "google_drive")

    def test_build_report_marks_secondary_pc_canonical_write_as_warning(self):
        report = sync_sentinel.build_report(
            root=Path("C:/work/obsidian-agent-brain-system"),
            vault=Path("C:/work/obsidian-agent-brain-system/ObsidianVault"),
            env={"PC_ROLE": "secondary", "PC_NAME": "office"},
            hostname="OFFICE-PC",
            command_runner=lambda args: (1, "missing"),
        )

        self.assertEqual(report["pc"]["role"], "secondary")
        self.assertEqual(report["pc"]["name"], "office")
        self.assertEqual(report["runtime_risk"], "warning")
        self.assertIn("secondary_pc_canonical_write_risk", report["warnings"])

    def test_build_report_reports_git_and_docker_status_from_runner(self):
        responses = {
            ("git", "rev-parse", "--abbrev-ref", "HEAD"): (0, "main"),
            ("git", "status", "--short"): (0, ""),
            ("docker", "--version"): (0, "Docker version 27.0.0"),
        }

        def runner(args):
            return responses.get(tuple(args), (1, "unknown command"))

        with patch.object(sync_sentinel, "path_exists", return_value=True):
            report = sync_sentinel.build_report(
                root=Path("G:/Google Drive/obsidian-agent-brain-system"),
                vault=Path("G:/Google Drive/obsidian-agent-brain-system/ObsidianVault"),
                env={"PC_ROLE": "primary", "PC_NAME": "home"},
                hostname="HOME-PC",
                command_runner=runner,
            )

        self.assertEqual(report["git"]["branch"], "main")
        self.assertEqual(report["git"]["worktree"], "clean")
        self.assertEqual(report["docker"], "available")
        self.assertEqual(report["runtime_risk"], "none")

    def test_build_report_defaults_unconfigured_pc_to_secondary_unknown(self):
        report = sync_sentinel.build_report(
            root=Path("C:/work/obsidian-agent-brain-system"),
            vault=Path("C:/work/obsidian-agent-brain-system/ObsidianVault"),
            env={},
            hostname="UNREGISTERED-PC",
            command_runner=lambda args: (0, "" if args[:2] == ["git", "status"] else "main"),
        )

        self.assertEqual(report["pc"]["role"], "secondary")
        self.assertEqual(report["pc"]["name"], "unknown")
        self.assertIn("pc_identity_unconfigured", report["warnings"])
        self.assertIn("secondary_pc_canonical_write_risk", report["warnings"])

    def test_build_report_warns_when_primary_is_not_home_pc(self):
        report = sync_sentinel.build_report(
            root=Path("G:/Google Drive/obsidian-agent-brain-system"),
            vault=Path("G:/Google Drive/obsidian-agent-brain-system/ObsidianVault"),
            env={"PC_ROLE": "primary", "PC_NAME": "office"},
            hostname="OFFICE-PC",
            command_runner=lambda args: (0, "" if args[:2] == ["git", "status"] else "main"),
        )

        self.assertIn("primary_pc_name_not_home", report["warnings"])

    def test_format_text_exposes_runtime_risk_for_discord_status(self):
        report = {
            "pc": {"role": "primary", "name": "home", "hostname": "HOME-PC"},
            "workspace": "G:/Google Drive/obsidian-agent-brain-system",
            "vault": "G:/Google Drive/obsidian-agent-brain-system/ObsidianVault",
            "storage": "google_drive",
            "vault_storage": "google_drive",
            "git": {"branch": "master", "worktree": "dirty_or_unknown"},
            "docker": "available",
            "runtime_risk": "warning",
            "warnings": ["git_worktree_not_clean"],
            "next_action": "review warnings before canonical writes",
        }

        text = sync_sentinel.format_text(report)

        self.assertIn("[Sync Sentinel]", text)
        self.assertIn("Runtime risk: warning", text)
        self.assertIn("git_worktree_not_clean", text)


if __name__ == "__main__":
    unittest.main()
