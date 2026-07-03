/**
 * Trigger.dev Job: 세션시작 알림
 * Hook 템플릿: ObsidianVault/08_Content/hook-library/hook-session-start.md
 *
 * 트리거: Claude Code PreSession 훅 또는 수동 POST
 * 호스팅 결정 전 stub — SaaS / Docker 모두 동일 코드 사용 가능
 */

import { task } from "@trigger.dev/sdk/v3";

export const sessionStartNotifyTask = task({
  id: "session-start-notify",
  run: async (payload) => {
    const {
      sessionId,
      prevSessionId,
      sessionGoal = "(미설정)",
      contextPacks = [],
      date,
      time,
      timestamp = new Date().toISOString(),
    } = payload;

    const dateStr = date ?? timestamp.slice(0, 10);
    const timeStr = time ?? timestamp.slice(11, 16);

    // --- Discord 알림 메시지 ---
    const discordMessage = [
      `🟢 **[세션시작]** Claude Code 활성화`,
      `📋 이전 세션: ${prevSessionId ?? "없음"}`,
      `🎯 Goal: ${sessionGoal}`,
      `📅 ${dateStr} ${timeStr}`,
    ].join("\n");

    // --- Obsidian 세션 로그 항목 ---
    const obsidianLog = [
      `## ${dateStr} ${timeStr} — 세션시작`,
      ``,
      `- session_id: ${sessionId ?? "unknown"}`,
      `- prev_session: ${prevSessionId ?? "없음"}`,
      `- goal: ${sessionGoal}`,
      `- context_packs: ${Array.isArray(contextPacks) ? contextPacks.join(", ") : contextPacks}`,
    ].join("\n");

    // TODO: Discord webhook 활성화
    // await sendDiscordMessage(process.env.DISCORD_WEBHOOK_URL, discordMessage);

    // TODO: Obsidian 세션 로그 append (bucky_chat_server 경유)
    // await appendToObsidianLog("05_Logs/session-log.md", obsidianLog);

    return { ok: true, discordMessage, obsidianLog };
  },
});
