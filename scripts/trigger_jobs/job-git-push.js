/**
 * Trigger.dev Job: git-push 알림
 * Hook 템플릿: ObsidianVault/08_Content/hook-library/hook-git-push.md
 *
 * 트리거: GitHub webhook onPush 또는 Claude Code PostToolUse:Bash 훅
 * 호스팅 결정 전 stub — SaaS / Docker 모두 동일 코드 사용 가능
 */

import { task } from "@trigger.dev/sdk/v3";

export const gitPushNotifyTask = task({
  id: "git-push-notify",
  run: async (payload) => {
    const {
      branch = "master",
      remote = "origin",
      commitHashShort,
      commitMessage,
      commitCount = 1,
      filesChanged,
      timestamp = new Date().toISOString(),
    } = payload;

    // --- Discord 알림 메시지 구성 ---
    const discordMessage = [
      `🚀 **[git push]** ${branch} → ${remote}`,
      `📦 ${commitCount}개 커밋 | ${filesChanged ?? "?"}개 파일`,
      `🔗 ${commitHashShort}: ${commitMessage}`,
      `⏱ ${timestamp}`,
    ].join("\n");

    // --- Discord Webhook 전송 ---
    // TODO: DISCORD_WEBHOOK_URL 환경변수 등록 후 활성화
    // const webhookUrl = process.env.DISCORD_WEBHOOK_URL;
    // await fetch(webhookUrl, {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify({ content: discordMessage }),
    // });

    // --- Obsidian 로그 append (bucky_chat_server /tablet-intake 경유) ---
    // TODO: BUCKY_SERVER_URL 환경변수 등록 후 활성화
    // const serverUrl = process.env.BUCKY_SERVER_URL ?? "http://localhost:8765";
    // await fetch(`${serverUrl}/tablet-intake`, {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify({
    //     vault_path: "05_Logs",
    //     chunks: [{
    //       timestamp,
    //       text: `git push: ${branch} ${commitHashShort} — ${commitMessage}`,
    //       source: "trigger-git-push",
    //     }],
    //   }),
    // });

    return { ok: true, message: discordMessage };
  },
});
