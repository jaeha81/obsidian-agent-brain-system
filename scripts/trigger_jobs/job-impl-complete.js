/**
 * Trigger.dev Job: 구현완료 알림 + Codex 핸드오프
 * Hook 템플릿: ObsidianVault/08_Content/hook-library/hook-impl-complete.md
 *
 * 트리거: Claude Code 완료 보고 키워드 감지 또는 수동 POST
 * 호스팅 결정 전 stub — SaaS / Docker 모두 동일 코드 사용 가능
 */

import { task } from "@trigger.dev/sdk/v3";

export const implCompleteNotifyTask = task({
  id: "impl-complete-notify",
  run: async (payload) => {
    const {
      taskTitle,
      filesModified = [],
      commitHashShort,
      sessionId,
      timestamp = new Date().toISOString(),
    } = payload;

    const filesList = Array.isArray(filesModified)
      ? filesModified.map((f) => `  - ${f}`).join("\n")
      : filesModified;

    // --- Discord 구현완료 알림 ---
    const completionMessage = [
      `✅ **[구현완료]** ${taskTitle}`,
      `📁 파일: ${Array.isArray(filesModified) ? filesModified.join(", ") : filesModified}`,
      `🔍 다음 단계: Codex 검수 대기`,
      `⏱ ${timestamp} | 세션: ${sessionId ?? "unknown"}`,
    ].join("\n");

    // --- Codex 핸드오프 메시지 (#jh-태스크보드) ---
    const codexHandoff = [
      `🔍 **Codex 검수 요청**`,
      `작업: ${taskTitle}`,
      `커밋: ${commitHashShort ?? "N/A"}`,
      `변경 파일:\n${filesList}`,
      ``,
      `검수 포인트:`,
      `- 타입 안전성`,
      `- 보안 취약점`,
      `- AI-Slop 패턴`,
    ].join("\n");

    // TODO: Discord webhook 활성화
    // await sendDiscordMessage(process.env.DISCORD_WEBHOOK_URL, completionMessage);
    // await sendDiscordMessage(process.env.DISCORD_TASKBOARD_WEBHOOK, codexHandoff);

    return { ok: true, completionMessage, codexHandoff };
  },
});
