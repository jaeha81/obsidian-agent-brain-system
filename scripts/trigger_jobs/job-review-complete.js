/**
 * Trigger.dev Job: 검수완료 알림 (Codex → Claude Code 피드백)
 * Hook 템플릿: ObsidianVault/08_Content/hook-library/hook-review-complete.md
 *
 * 트리거: Codex 검수 완료 보고 Discord 메시지 감지
 * 호스팅 결정 전 stub — SaaS / Docker 모두 동일 코드 사용 가능
 */

import { task } from "@trigger.dev/sdk/v3";

/**
 * @typedef {"LGTM" | "MINOR_ISSUES" | "NEEDS_FIX" | "BLOCKED"} Verdict
 */

export const reviewCompleteNotifyTask = task({
  id: "review-complete-notify",
  run: async (payload) => {
    const {
      taskTitle,
      verdict = "LGTM",   // LGTM | MINOR_ISSUES | NEEDS_FIX | BLOCKED
      issueCount = 0,
      issuesSummary = "",
      issuesDetail = "",
      commitHashShort,
      timestamp = new Date().toISOString(),
    } = payload;

    const needsFix = verdict === "NEEDS_FIX" || verdict === "BLOCKED";
    const readyToDeploy = verdict === "LGTM";
    const dateStr = timestamp.slice(0, 10);

    // --- Discord 피드백 메시지 (#jh-태스크보드) ---
    const discordMessage = [
      `🔍 **[검수완료]** Codex 리뷰 결과`,
      `작업: ${taskTitle}`,
      `결과: ${verdict} (${issueCount}개 이슈)`,
      issuesSummary ? issuesSummary : "",
      ``,
      `→ 수정 필요: ${needsFix}`,
      `→ 바로 배포 가능: ${readyToDeploy}`,
    ]
      .filter((l) => l !== null)
      .join("\n");

    // --- Obsidian 검수 로그 항목 ---
    const obsidianLog = [
      `## ${dateStr} — ${taskTitle}`,
      ``,
      `- verdict: ${verdict}`,
      `- issues: ${issueCount}`,
      `- commit: ${commitHashShort ?? "N/A"}`,
      `- needs_fix: ${needsFix}`,
      ``,
      `### 이슈 목록`,
      issuesDetail || "(없음)",
    ].join("\n");

    // verdict에 따른 처리
    if (verdict === "BLOCKED") {
      // TODO: 긴급 알림 전송
      // await sendUrgentAlert(`🚨 BLOCKED: ${taskTitle}`);
    }

    // TODO: Discord webhook 활성화
    // await sendDiscordMessage(process.env.DISCORD_TASKBOARD_WEBHOOK, discordMessage);

    // TODO: Obsidian 검수 로그 append
    // await appendToObsidianLog("05_Logs/codex-review-log.md", obsidianLog);

    return { ok: true, discordMessage, obsidianLog, needsFix, readyToDeploy };
  },
});
