import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


def read_text(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class RepoDashboardIntakePayloadTests(unittest.TestCase):
    def test_repo_single_item_payload_has_required_plan_fields(self):
        html = read_text("docs/index.html")
        self.assertIn("dashboard_type: 'repo'", html)
        self.assertIn("target_channel: 'jh-레포대시보드", html)
        self.assertIn("item_id: repo.id", html)
        self.assertIn("repo_description: repo.desc", html)
        self.assertIn("dashboard_context: buildRepoDashboardContext()", html)
        self.assertIn("briefing_instruction: buildRepoBriefingInstruction(repo)", html)
        self.assertIn("source_dashboard_url: location.href", html)
        self.assertIn("request_id: `repo-${repo.id}-${Date.now()}`", html)

    def test_repo_batch_payload_has_required_plan_fields(self):
        html = read_text("docs/index.html")
        self.assertIn("dashboard_type: 'repo'", html)
        self.assertIn("target_channel: 'jh-레포대시보드", html)
        self.assertIn("item_id: checked.map(r => r.id).join(',')", html)
        self.assertIn("dashboard_context: buildRepoDashboardContext()", html)
        self.assertIn("briefing_instruction: buildRepoBatchBriefingInstruction(checked)", html)
        self.assertIn("source_dashboard_url: location.href", html)
        self.assertIn("request_id: `repo-batch-${Date.now()}`", html)

    def test_repo_batch_start_action_routes_to_bucky_in_bot(self):
        bot = read_text("scripts/discord_bot.py")
        self.assertIn('"batch_start"', bot)
        self.assertIn('action in {"start", "batch_start", "analyze", "review"}', bot)

    def test_repo_intake_uses_rich_briefing_before_generic_ack(self):
        bot = read_text("scripts/discord_bot.py")
        self.assertIn("def _build_repo_intake_ack", bot)
        self.assertIn("def _build_repo_intake_prompt", bot)
        repo_branch_index = bot.index('if dashboard_type == "repo" and action in {"start", "batch_start", "analyze", "review"} and channel:')
        self.assertLess(repo_branch_index, bot.index("briefing = ("))
        repo_branch = bot[repo_branch_index:]
        self.assertIn("_build_repo_intake_ack(payload)", repo_branch)
        self.assertIn("_build_repo_intake_prompt(payload)", repo_branch)

    def test_repo_dashboard_does_not_render_knowledge_intake(self):
        html = read_text("docs/index.html")
        self.assertNotIn("Chris Knowledge Intake", html)
        self.assertNotIn('aria-label="Bucky knowledge intake"', html)
        self.assertNotIn("function extractYoutubeWatchUrl", html)
        self.assertNotIn("dashboard_type: 'knowledge_intake'", html)


class WishketDashboardIntakePayloadTests(unittest.TestCase):
    def test_wishket_payload_has_stable_request_id(self):
        html = read_text("docs/wishket.html")
        self.assertIn("request_id:", html)
        self.assertIn("wishket-", html)

    def test_wishket_development_request_is_immediate_execution(self):
        html = read_text("docs/wishket.html")
        self.assertIn("approval_required: false", html)
        self.assertIn("execution_mode: 'immediate'", html)
        self.assertIn("Bucky immediate execution request for Claude/Codex routing.", html)

    def test_wishket_payload_has_target_channel_and_source_url(self):
        html = read_text("docs/wishket.html")
        self.assertIn("target_channel: 'jh-위시켓", html)
        self.assertIn("source_dashboard_url: location.href", html)

    def test_wishket_dashboard_has_workflow_status_map_and_helper(self):
        html = read_text("docs/wishket.html")
        self.assertIn("const WORKFLOW_STATUS =", html)
        self.assertIn("function getWishketWorkflowStatus", html)
        self.assertIn("workflow_state", html)

    def test_wishket_dashboard_replaces_discord_button_with_proposal_request(self):
        html = read_text("docs/wishket.html")
        self.assertNotIn(">Discord<", html)
        self.assertIn("제안서 만들기", html)
        self.assertIn("requestWishketProposal", html)
        self.assertIn("type:'wishket_proposal_request'", html)

    def test_wishket_dashboard_requires_approval_before_development_request(self):
        html = read_text("docs/wishket.html")
        self.assertIn("disabled: !workflow.approved", html)
        self.assertIn("sendProposalFeedback", html)
        self.assertIn("approveProposal", html)


class KmongDashboardIntakePayloadTests(unittest.TestCase):
    def test_kmong_dashboard_has_bucky_intake_payload_markers(self):
        html = read_text("docs/kmong.html")
        self.assertIn("dashboard_type: 'kmong'", html)
        self.assertIn("target_channel: 'jh-크몽수익화'", html)
        self.assertIn("request_id: `kmong-${action}-${Date.now()}`", html)
        self.assertIn("source_dashboard_url: location.href", html)
        self.assertIn("sendKmongPayload", html)

    def test_kmong_dashboard_does_not_capture_passwords(self):
        html = read_text("docs/kmong.html")
        self.assertIn("KMONG_EMAIL / KMONG_PASSWORD", html)
        self.assertIn("manual_auth_required", html)
        self.assertNotIn('type="password"', html)
        self.assertNotIn("localStorage.setItem('kmongPassword", html)

    def test_discord_bot_routes_kmong_dashboard_type(self):
        bot = read_text("scripts/discord_bot.py")
        self.assertIn("JH_KMONG_CHANNEL_ID", bot)
        self.assertIn('"kmong":', bot)
        self.assertIn("jh-크몽수익화", bot)


class CollaborationAdminWorkflowStaticTests(unittest.TestCase):
    def test_bni_page_has_collab_submission_form(self):
        html = read_text("docs/bni-proposal.html")
        self.assertIn('id="collab-inquiry-form"', html)
        self.assertIn('name="requester_email"', html)
        self.assertIn("submitCollabInquiry", html)

    def test_bni_page_links_to_admin_dashboard(self):
        html = read_text("docs/bni-proposal.html")
        self.assertIn('href="collab-admin.html"', html)
        self.assertIn("협업문의 관리자", html)

    def test_collab_admin_page_has_password_gate(self):
        html = read_text("docs/collab-admin.html")
        self.assertIn("ljh911314", html)
        self.assertIn("sessionStorage", html)
        self.assertIn("collab-admin-auth", html)

    def test_collab_admin_page_has_required_action_controls(self):
        html = read_text("docs/collab-admin.html")
        self.assertIn("Discord 전송", html)
        self.assertIn("제안서 시작", html)
        self.assertIn("개발요청 실행", html)
        self.assertIn("Codex 검수 요청", html)
        self.assertIn("X-Collab-Admin-Password", html)


class DashboardProgressUiTests(unittest.TestCase):
    def test_repo_dashboard_script_blocks_are_well_formed(self):
        html = read_text("docs/index.html")
        self.assertEqual(html.count("<script"), html.count("</script>"))
        inline_scripts = re.findall(r"<script(?:\s[^>]*)?>([\s\S]*?)</script>", html)
        self.assertTrue(inline_scripts)
        for script in inline_scripts:
            self.assertNotIn("<script", script)

    def test_repo_dashboard_has_progress_state_handlers(self):
        html = read_text("docs/index.html")
        for marker in (
            "function saveRepoProgress",
            "function setRepoProgressState",
            "function captureRepoNextPlan",
            "function resumeRepoSession",
            "function enhanceRepoProgressPanels",
        ):
            self.assertIn(marker, html)

    def test_wishket_dashboard_has_progress_state_handlers(self):
        html = read_text("docs/wishket.html")
        for marker in (
            "function saveWishketProgress",
            "function setWishketProgressState",
            "function captureWishketNextPlan",
            "function resumeWishketSession",
            "function enhanceWishketProgressPanels",
        ):
            self.assertIn(marker, html)

    def test_repo_dashboard_has_result_summary_panel(self):
        html = read_text("docs/index.html")
        self.assertIn('data-dashboard-results="repo"', html)
        self.assertIn("repoResultDispatched", html)
        self.assertIn("repoResultPlanning", html)
        self.assertIn("repoResultReady", html)
        self.assertIn("repoResultStopped", html)
        self.assertIn("function updateRepoResultSummary", html)

    def test_wishket_dashboard_has_result_summary_panel(self):
        html = read_text("docs/wishket.html")
        self.assertIn('data-dashboard-results="wishket"', html)
        self.assertIn("wishketResultDispatched", html)
        self.assertIn("wishketResultPlanning", html)
        self.assertIn("wishketResultReady", html)
        self.assertIn("wishketResultStopped", html)
        self.assertIn("function updateWishketResultSummary", html)


class GlobalOperatingPolicyTests(unittest.TestCase):
    def test_repo_dashboard_shows_official_channel_and_local_control_policy(self):
        html = read_text("docs/index.html")
        self.assertIn("jh-chat", html)
        self.assertIn("jh-레포대시보드", html)
        self.assertIn("공식", html)
        self.assertIn("Chrome extension, Vercel, Supabase, local PC control, bot restart", html)

    def test_wishket_dashboard_shows_official_channel_and_local_control_policy(self):
        html = read_text("docs/wishket.html")
        self.assertIn("jh-chat", html)
        self.assertIn("jh-위시켓", html)
        self.assertIn("공식", html)
        self.assertIn("Chrome extension, Vercel, Supabase, local PC control", html)

    def test_daily_plus_dashboard_shows_official_channel_and_local_control_policy(self):
        html = read_text("docs/daily-plus.html")
        self.assertIn("jh-chat", html)
        self.assertIn("jh-오늘의플러스", html)
        self.assertIn("jh-chris", html)
        self.assertIn("공식", html)
        self.assertIn("Chrome extension, Vercel, Supabase, local PC control, bot restart", html)

    def test_task_and_checklist_show_official_channel_policy(self):
        task_html = read_text("docs/task-board.html")
        checklist_html = read_text("docs/checklist.html")
        for html in (task_html, checklist_html):
            self.assertIn("jh-chat", html)
            self.assertIn("jh-태스크보드", html)
            self.assertIn("공식", html)
            self.assertIn("Chrome extension, Vercel, Supabase, local PC control, bot restart", html)


class TaskChecklistRoleTests(unittest.TestCase):
    def test_task_board_defines_role_separation(self):
        html = read_text("docs/task-board.html")
        self.assertIn("Task operations channel:", html)
        self.assertIn("jh-태스크보드", html)
        self.assertIn("immediate execution request", html)

    def test_checklist_defines_role_separation(self):
        html = read_text("docs/checklist.html")
        self.assertIn("Task operations channel:", html)
        self.assertIn("jh-태스크보드", html)
        self.assertIn("Execution handoff:", html)


class RouterFieldConsistencyTests(unittest.TestCase):
    def test_task_board_payloads_have_request_id(self):
        html = read_text("docs/task-board.html")
        self.assertIn("request_id: `task-${task.id}-${Date.now()}`", html)
        self.assertIn("request_id: `task-${id}-${Date.now()}`", html)
        self.assertIn("return local ? '/intake' : '';", html)
        self.assertIn("dashboard_type: 'task_board'", html)
        self.assertIn("showToast(`⏳ ${id} 재개 전송 중...`)", html)
        self.assertIn("Bucky 전송 실패", html)
        self.assertIn("if (navigator.clipboard?.writeText)", html)

    def test_checklist_payload_has_request_id(self):
        html = read_text("docs/checklist.html")
        self.assertIn("request_id: `checklist-${task.id}-${Date.now()}`", html)

    def test_daily_plus_payload_has_source_dashboard_url(self):
        html = read_text("docs/daily-plus.html")
        self.assertIn("source_dashboard_url: location.href", html)

    def test_channel_map_covers_all_dashboard_types(self):
        bot = read_text("scripts/discord_bot.py")
        for dtype in ("repo", "wishket", "collab", "daily_plus", "task_board", "taskboard", "checklist", "knowledge_intake"):
            self.assertIn(f'"{dtype}"', bot)
        self.assertIn("JH_MYINTRO_CHANNEL_ID", bot)

    def test_wishket_bot_handles_proposal_request_payload(self):
        bot = read_text("scripts/discord_bot.py")
        self.assertIn('"wishket_proposal_request"', bot)
        self.assertIn("_handle_wishket_proposal_request", bot)

    def test_wishket_bot_handles_feedback_and_approval_payloads(self):
        bot = read_text("scripts/discord_bot.py")
        self.assertIn('"wishket_feedback"', bot)
        self.assertIn('"wishket_proposal_approval"', bot)
        self.assertIn("_handle_wishket_feedback_payload", bot)
        self.assertIn("_handle_wishket_proposal_approval_payload", bot)

    def test_collab_bot_handles_proposal_request_payload(self):
        bot = read_text("scripts/discord_bot.py")
        self.assertIn('"collab_proposal_request"', bot)
        self.assertIn("_handle_collab_proposal_request", bot)

    def test_collab_bot_handles_feedback_and_approval_payloads(self):
        bot = read_text("scripts/discord_bot.py")
        self.assertIn('"collab_feedback"', bot)
        self.assertIn('"collab_proposal_approval"', bot)
        self.assertIn("_handle_collab_feedback_payload", bot)
        self.assertIn("_handle_collab_proposal_approval_payload", bot)

    def test_repo_dashboard_no_longer_contains_knowledge_intake_payload_logic(self):
        html = read_text("docs/index.html")
        self.assertNotIn("function extractYoutubeWatchUrl", html)
        self.assertNotIn("dashboard_type: 'knowledge_intake'", html)
        self.assertNotIn("target_channel: 'jh-chris'", html)
        self.assertNotIn("action: youtubeUrl ? 'watch' : 'capture'", html)

    def test_knowledge_intake_routes_to_chris_channel(self):
        bot = read_text("scripts/discord_bot.py")
        self.assertIn('"knowledge_intake": lambda: JH_CHRIS_CHANNEL_ID or JH_CHAT_CHANNEL_ID', bot)

    def test_knowledge_intake_watch_routes_to_youtube_capture_before_bucky_wait(self):
        bot = read_text("scripts/discord_bot.py")
        self.assertIn("async def _handle_dashboard_watch_payload", bot)
        self.assertIn("def _extract_youtube_url_from_payload", bot)
        self.assertIn('content.startswith("/watch ")', bot)
        self.assertIn("capture_youtube(watch_url, tags)", bot)
        branch = bot[bot.index("if await _handle_dashboard_watch_payload(payload, channel):"):]
        self.assertLess(
            branch.index("if await _handle_dashboard_watch_payload(payload, channel):"),
            branch.index('if dashboard_type == "daily_plus" and channel:'),
        )

    def test_task_board_intake_sends_immediate_discord_ack_before_bucky(self):
        bot = read_text("scripts/discord_bot.py")
        branch = bot[bot.index('if dashboard_type in {"daily_plus", "task_board", "taskboard", "checklist"}'):]
        self.assertIn("[Intake: {dashboard_type}] `{action}` 수신 — Bucky 처리 시작", branch)
        self.assertIn("ack_lines.append(f\"- request_id: `{request_id[:12]}`\")", branch)
        self.assertLess(
            branch.index("await channel.send(\"\\n\".join(ack_lines))"),
            branch.index("reply = await asyncio.wait_for("),
        )

    def test_discord_bot_subprocess_text_decoding_is_error_tolerant(self):
        bot = read_text("scripts/discord_bot.py")
        for match in re.finditer(r"text=True", bot):
            window = bot[match.start():match.start() + 120]
            self.assertIn('errors="replace"', window)

    def test_daily_plus_execute_dispatches_task_instead_of_waiting_for_chat_reply(self):
        bot = read_text("scripts/discord_bot.py")
        branch = bot[bot.index('if dashboard_type == "daily_plus" and channel:'):]
        self.assertIn('if action in {"execute", "approve_execute"}:', branch)
        self.assertIn("_dispatch_dashboard_execution_task(payload, channel)", branch)
        self.assertLess(
            branch.index("_dispatch_dashboard_execution_task(payload, channel)"),
            branch.index("reply = await asyncio.wait_for("),
        )

    def test_auto_executable_checklist_resume_dispatches_worker_task(self):
        bot = read_text("scripts/discord_bot.py")
        branch = bot[bot.index('if dashboard_type == "checklist" and action == "resume_task" and channel:'):]
        self.assertIn("_checklist_requires_manual_action(payload)", branch)
        self.assertIn("_dispatch_dashboard_execution_task({**payload, \"action\": \"execute\"}, channel)", branch)
        self.assertLess(
            branch.index("_dispatch_dashboard_execution_task({**payload, \"action\": \"execute\"}, channel)"),
            branch.index('if dashboard_type in {"daily_plus", "task_board", "taskboard", "checklist"}'),
        )

    def test_checklist_payload_marks_resume_task_as_auto_executable_candidate(self):
        html = read_text("docs/checklist.html")
        self.assertIn("requires_user_approval: isManualChecklistTask(task)", html)
        self.assertIn("execution_mode: isManualChecklistTask(task) ? \"approval_required\" : \"auto_executable\"", html)

    def test_dashboard_execution_task_uses_worker_pool(self):
        bot = read_text("scripts/discord_bot.py")
        self.assertIn("async def _dispatch_dashboard_execution_task", bot)
        self.assertIn('source="dashboard-intake"', bot)
        self.assertIn("pool.register_task(task", bot)
        self.assertIn("pool.submit(task)", bot)


class AppSessionDashboardTests(unittest.TestCase):
    def test_app_session_payload_has_required_fields(self):
        html = read_text("docs/app-session.html")
        self.assertIn("dashboard_type: 'app_session'", html)
        self.assertIn("target_channel", html)
        self.assertIn("target_app", html)
        self.assertIn("request_id", html)
        self.assertIn("source_dashboard_url: location.href", html)

    def test_app_session_routes_to_correct_channels(self):
        html = read_text("docs/app-session.html")
        self.assertIn("jh-클로드코드앱", html)
        self.assertIn("jh-코덱스앱", html)

    def test_app_session_has_required_actions(self):
        html = read_text("docs/app-session.html")
        self.assertIn("action: 'start'", html)
        for action in ("resume", "stop", "status"):
            self.assertIn(f"'{action}'", html)

    def test_app_session_shows_official_channel_policy(self):
        html = read_text("docs/app-session.html")
        self.assertIn("jh-chat", html)
        self.assertIn("jh-클로드코드앱", html)
        self.assertIn("jh-코덱스앱", html)
        self.assertIn("Chrome extension, Vercel, Supabase, local PC control, bot restart", html)

    def test_app_session_requires_user_approval(self):
        html = read_text("docs/app-session.html")
        self.assertIn("requires_user_approval: true", html)
        self.assertIn("execution_mode: 'user_approved_pc_control'", html)

    def test_app_session_has_all_status_states(self):
        html = read_text("docs/app-session.html")
        for state in ("waiting", "approval", "open", "prompt_needed", "running", "done", "blocked"):
            self.assertIn(state, html)


class AppSessionBridgeTests(unittest.TestCase):
    def test_app_session_bridge_defines_request_format(self):
        src = read_text("scripts/app_session_bridge.py")
        for field in ("app_session_request", "app_session_status", "requires_user_approval",
                      "execution_mode", "user_approved_pc_control", "manual_action_required"):
            self.assertIn(field, src)

    def test_app_session_bridge_does_not_perform_pc_control(self):
        src = read_text("scripts/app_session_bridge.py")
        self.assertNotIn("subprocess.run", src)
        self.assertNotIn("os.system", src)
        self.assertIn("manual_action_required", src)


if __name__ == "__main__":
    unittest.main()
