/**
 * Trigger.dev Job: 세션종료 알림 + Handoff 메모 생성
 * Hook 템플릿: ObsidianVault/08_Content/hook-library/hook-session-end.md
 *
 * 트리거: Claude Code PostSession 훅 또는 /goal clear
 * 호스팅 결정 전 stub — SaaS / Docker 모두 동일 코드 사용 가능
 */

import { task } from "@trigger.dev/sdk/v3";

export const sessionEndNotifyTask = task({
  id: "session-end-notify",
  run: async (payload) => {
    const {
      sessionId,
      completedTasks = [],
      pendingTasks = [],
      sessionNote = "",
      durationMin,
      nextPriorities = [],
      timestamp = new Date().toISOString(),
    } = payload;

    const dateStr = timestamp.slice(0, 10);
    const completedStr = Array.isArray(completedTasks)
      ? completedTasks.join(", ")
      : completedTasks;
    const pendingStr = Array.isArray(pendingTasks)
      ? pendingTasks.join(", ")
      : pendingTasks;

    // --- Discord 알림 ---
    const discordMessage = [
      `🔴 **[세션종료]** Claude Code 비활성화`,
      `✅ 완료: ${completedStr || "없음"}`,
      `⏳ 미완료: ${pendingStr || "없음"}`,
      `💾 메모: ${sessionNote || "(없음)"}`,
      `⏱ ${durationMin ?? "?"}분 | ${timestamp}`,
    ].join("\n");

    // --- Handoff 메모 ---
    const handoffMemo = [
      `이전 세션 메모: memory/project_session_${dateStr}.md`,
      `완료: ${sessionNote}`,
      `다음 우선순위:`,
      ...nextPriorities.map((p, i) => `${i + 1}. ${p}`),
    ].join("\n");

    // TODO: Discord webhook 활성화
    // await sendDiscordMessage(process.env.DISCORD_WEBHOOK_URL, discordMessage);

    // TODO: HANDOFF_LOG 기록
    // await appendToObsidianLog("00_System/HANDOFF_LOG.md", handoffMemo);

    return { ok: true, discordMessage, handoffMemo };
  },
});
