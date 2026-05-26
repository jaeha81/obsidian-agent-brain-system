const { ItemView, MarkdownRenderer, Notice, Plugin, PluginSettingTab, Setting, setIcon } = require("obsidian");
const childProcess = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const BUCKY_NAME = "\uBC84\uD0A4";
const BUCKY_CHAT_VIEW = "bucky-chat-view";
const HOME_PROJECT_MARKER = "D:\\ai\uD504\uB85C\uC81D\uD2B8";
const LOCAL_PROJECT_MARKER = "C:\\ai\uD504\uB85C\uC81D\uD2B8";
const OFFICE_USERNAME = "\uC124\uACC4" + "4";

const DEFAULT_SETTINGS = {
  autoStart: true,
  autoOpenChat: true,
  pythonCommand: "python",
  statusNotePath: "00_System/BUCKY_STATUS.md",
  chatTranscriptPath: "10_AgentBus/chat/BUCKY_CHAT.md",
  chatBridgeScript: "scripts/bucky_chat_once.py",
  chatTimeoutSeconds: 900,
  startupDelayMs: 2500,
  chatModel: "sonnet",    // sonnet | opus | haiku
  toolMode: "safe",       // safe (no tools) | auto (dangerously-skip-permissions)
  scripts: [
    "scripts/raw_import_watcher.py",
    "scripts/codex_review_runner.py",
    "scripts/agent_dispatcher.py",
  ],
};

class BuckyAgentPlugin extends Plugin {
  async onload() {
    this.settings = Object.assign({}, DEFAULT_SETTINGS, await this.loadData());
    this.rootPath = this.getRootPath();
    this.vaultPath = this.getVaultPath();
    this.agentVaultPath = this.getAgentVaultPath();
    this.pc = this.detectPc();
    this.lastStartResult = { started: [], alreadyRunning: [], missing: [] };
    this.chatMessages = [];
    this._discordRefreshTimer = null;
    this.statusBar = this.addStatusBarItem();
    this.statusBar.addClass("bucky-agent-status");

    this.registerView(BUCKY_CHAT_VIEW, leaf => new BuckyChatView(leaf, this));

    // Discord → PC 채팅 실시간 동기화: BUCKY_CHAT.md 변경 감지
    this.registerEvent(this.app.vault.on("modify", async (file) => {
      const transcriptPath = this.settings.chatTranscriptPath || DEFAULT_SETTINGS.chatTranscriptPath;
      if (file.path !== transcriptPath) return;
      if (this._discordRefreshTimer) window.clearTimeout(this._discordRefreshTimer);
      this._discordRefreshTimer = window.setTimeout(async () => {
        await this.loadChatHistoryFromTranscript();
        const leaves = this.app.workspace.getLeavesOfType(BUCKY_CHAT_VIEW);
        for (const leaf of leaves) {
          if (leaf.view && leaf.view.renderMessages) leaf.view.renderMessages();
        }
      }, 500);
    }));

    this.addRibbonIcon("message-circle", "Bucky Chat", async () => {
      await this.activateChatView();
    });

    this.addRibbonIcon("bot", "Bucky Agent status", async () => {
      await this.refreshStatus(true);
    });

    this.addCommand({
      id: "bucky-open-chat",
      name: "Bucky: open chat",
      callback: async () => this.activateChatView(),
    });

    this.addCommand({
      id: "bucky-start",
      name: "Bucky: start agent line",
      callback: async () => this.startBucky(true),
    });

    this.addCommand({
      id: "bucky-refresh-status",
      name: "Bucky: refresh status",
      callback: async () => this.refreshStatus(true),
    });

    this.addCommand({
      id: "bucky-open-status-note",
      name: "Bucky: open status note",
      callback: async () => this.openStatusNote(),
    });

    this.addCommand({
      id: "bucky-focus-chat",
      name: "Bucky: focus/unfocus chat input",
      hotkeys: [{ modifiers: ["Ctrl"], key: "Escape" }],
      callback: async () => {
        const leaf = this.app.workspace.getLeavesOfType(BUCKY_CHAT_VIEW)[0];
        if (!leaf) { await this.activateChatView(); return; }
        const view = leaf.view;
        if (view && view.inputEl) {
          if (document.activeElement === view.inputEl) {
            view.inputEl.blur();
          } else {
            this.app.workspace.setActiveLeaf(leaf, { focus: true });
            view.inputEl.focus();
          }
        }
      },
    });

    this.addSettingTab(new BuckySettingTab(this.app, this));
    await this.refreshStatus(false);

    if (this.settings.autoStart) {
      this.startTimer = window.setTimeout(() => {
        this.startBucky(false);
      }, this.settings.startupDelayMs);
    }

    if (this.settings.autoOpenChat) {
      this.app.workspace.onLayoutReady(() => {
        this.chatTimer = window.setTimeout(() => {
          this.activateChatView();
        }, this.settings.startupDelayMs + 800);
        this.chatFocusTimer = window.setTimeout(() => {
          this.activateChatView();
        }, this.settings.startupDelayMs + 5000);
      });
    }

    this.refreshTimer = window.setInterval(() => {
      this.refreshStatus(false);
    }, 60000);
  }

  onunload() {
    if (this.startTimer) window.clearTimeout(this.startTimer);
    if (this.chatTimer) window.clearTimeout(this.chatTimer);
    if (this.chatFocusTimer) window.clearTimeout(this.chatFocusTimer);
    if (this.refreshTimer) window.clearInterval(this.refreshTimer);
    this.app.workspace.detachLeavesOfType(BUCKY_CHAT_VIEW);
    const views = this.app.workspace.getLeavesOfType(BUCKY_CHAT_VIEW).map(l => l.view);
    for (const v of views) { if (v.elapsedTimer) window.clearInterval(v.elapsedTimer); }
  }

  getVaultPath() {
    const adapter = this.app.vault.adapter;
    return adapter && adapter.basePath ? adapter.basePath : "";
  }

  getRootPath() {
    const vaultPath = this.getVaultPath();
    if (!vaultPath) return "";

    const candidates = [vaultPath, path.dirname(vaultPath)];
    for (const candidate of candidates) {
      if (fs.existsSync(path.join(candidate, "scripts", "agent_dispatcher.py"))) {
        return candidate;
      }
    }

    return path.dirname(vaultPath);
  }

  getAgentVaultPath() {
    if (this.vaultPath && path.basename(this.vaultPath) === "ObsidianVault") {
      return this.vaultPath;
    }
    const nestedVault = path.join(this.rootPath, "ObsidianVault");
    return fs.existsSync(nestedVault) ? nestedVault : this.vaultPath;
  }

  detectPc() {
    const username = os.userInfo().username || "";
    const hostname = os.hostname() || "";
    const markers = {
      homeProject: fs.existsSync(HOME_PROJECT_MARKER),
      localProject: fs.existsSync(LOCAL_PROJECT_MARKER),
      googleDriveRoot: this.rootPath && fs.existsSync(this.rootPath),
    };

    let label = "Unknown PC";
    if (markers.homeProject) label = "\uC9D1 PC";
    else if (username.toLowerCase() === "info") label = "\uB178\uD2B8\uBD81";
    else if (username === OFFICE_USERNAME) label = "\uC0AC\uBB34\uC2E4 PC";
    else if (markers.localProject) label = "\uB85C\uCEEC Windows PC";

    return {
      label,
      username,
      hostname,
      rootPath: this.rootPath,
      vaultPath: this.vaultPath,
      agentVaultPath: this.agentVaultPath,
      markers,
    };
  }

  async activateChatView() {
    try {
      let leaf = this.app.workspace.getLeavesOfType(BUCKY_CHAT_VIEW)[0];
      if (!leaf) {
        leaf = this.app.workspace.getRightLeaf(false) || this.app.workspace.getLeaf(true);
        await leaf.setViewState({ type: BUCKY_CHAT_VIEW, active: true });
      }
      this.app.workspace.setActiveLeaf(leaf, { focus: true });
      this.app.workspace.revealLeaf(leaf);
    } catch (error) {
      console.error("Bucky chat open failed", error);
      new Notice(`Bucky chat open failed: ${error.message || error}`);
    }
  }

  addChatMessage(role, text) {
    const message = {
      role,
      text,
      time: new Date().toISOString(),
    };
    this.chatMessages.push(message);
    return message;
  }

  async loadChatHistoryFromTranscript() {
    const transcriptPath = this.settings.chatTranscriptPath || DEFAULT_SETTINGS.chatTranscriptPath;
    const adapter = this.app.vault.adapter;
    if (!(await adapter.exists(transcriptPath))) return;
    try {
      const raw = await adapter.read(transcriptPath);
      const blocks = raw.split(/\n(## \d{4}-\d{2}-\d{2}T[^\n]+)\n/);
      const entries = [];
      for (let i = 1; i < blocks.length; i += 2) {
        const content = blocks[i + 1] || "";
        const userMatch = content.match(/### User\n\n([\s\S]*?)(?=\n### Bucky|\n## |\s*$)/);
        const buckyMatch = content.match(/### Bucky\n\n([\s\S]*?)(?=\n## |\s*$)/);
        const userText = userMatch ? userMatch[1].trim() : null;
        const buckyText = buckyMatch ? buckyMatch[1].trim() : null;
        // Skip corrupted entries (recursive prompts or empty)
        if (!userText || userText.length > 2000 || userText.includes("# Bucky Code IDE Chat")) continue;
        entries.push({ role: "user", text: userText, time: blocks[i] });
        if (buckyText) entries.push({ role: "bucky", text: buckyText, time: blocks[i] });
      }
      this.chatMessages = entries.slice(-20);
    } catch (e) {
      console.error("Bucky: failed to load chat history", e);
    }
  }

  async sendChat(idePrompt, originalPrompt) {
    const reply = await this.runChatBridge(idePrompt);
    await this.appendChatTranscript(originalPrompt || idePrompt, reply);
    return reply;
  }

  runChatBridge(userText) {
    return new Promise((resolve, reject) => {
      const bridgePath = path.join(this.rootPath, this.settings.chatBridgeScript);
      if (!fs.existsSync(bridgePath)) {
        reject(new Error(`Bucky chat bridge not found: ${bridgePath}`));
        return;
      }

      const timeoutSeconds = Number(this.settings.chatTimeoutSeconds || 900);
      const model = this.settings.chatModel || DEFAULT_SETTINGS.chatModel;
      const toolMode = this.settings.toolMode || DEFAULT_SETTINGS.toolMode;
      const child = childProcess.spawn(
        this.settings.pythonCommand,
        [bridgePath, "--timeout", String(timeoutSeconds), "--model", model, "--tool-mode", toolMode],
        {
          cwd: this.rootPath,
          stdio: ["pipe", "pipe", "pipe"],
          windowsHide: true,
          env: Object.assign({}, process.env, {
            PYTHONIOENCODING: "utf-8",
            VAULT_PATH: this.agentVaultPath,
            BUCKY_AGENT: "1",
          }),
        }
      );

      let stdout = "";
      let stderr = "";
      const timer = window.setTimeout(() => {
        child.kill();
        reject(new Error(`Bucky chat timed out after ${timeoutSeconds}s`));
      }, (timeoutSeconds + 5) * 1000);

      child.stdout.on("data", chunk => {
        stdout += chunk.toString("utf8");
      });
      child.stderr.on("data", chunk => {
        stderr += chunk.toString("utf8");
      });
      child.on("error", error => {
        window.clearTimeout(timer);
        reject(error);
      });
      child.on("close", code => {
        window.clearTimeout(timer);
        if (code === 0) {
          resolve(stdout.trim() || "(empty response)");
        } else {
          reject(new Error((stderr || stdout || `Bucky exited with code ${code}`).trim()));
        }
      });

      child.stdin.write(userText, "utf8");
      child.stdin.end();
    });
  }

  async appendChatTranscript(userText, replyText) {
    const now = new Date().toISOString();
    const transcriptPath = this.settings.chatTranscriptPath || DEFAULT_SETTINGS.chatTranscriptPath;
    const header = [
      "---",
      "type: bucky-chat",
      "agent: Bucky",
      "---",
      "",
      "# Bucky Chat",
      "",
    ].join("\n");
    const entry = [
      `## ${now}`,
      "",
      "### User",
      "",
      userText.trim(),
      "",
      "### Bucky",
      "",
      replyText.trim(),
      "",
    ].join("\n");

    await this.ensureParentFolder(transcriptPath);
    const adapter = this.app.vault.adapter;
    let existing = (await adapter.exists(transcriptPath))
      ? await adapter.read(transcriptPath)
      : header;

    // Truncate: keep last 50 entries to prevent unbounded growth
    const tsPattern = /\n## \d{4}-\d{2}-\d{2}T/g;
    const matches = [...existing.matchAll(tsPattern)];
    if (matches.length > 50) {
      existing = header.trim() + existing.slice(matches[matches.length - 50].index);
    }

    await adapter.write(transcriptPath, `${existing.trim()}\n\n${entry}`);
  }

  async startBucky(showNotice) {
    if (!this.rootPath || !fs.existsSync(this.rootPath)) {
      new Notice("Bucky: root path not found");
      return;
    }

    const started = [];
    const alreadyRunning = [];
    const missing = [];

    for (const relativeScript of this.settings.scripts) {
      const scriptPath = path.join(this.rootPath, relativeScript);
      if (!fs.existsSync(scriptPath)) {
        missing.push(relativeScript);
        continue;
      }

      const running = await this.isScriptRunning(path.basename(relativeScript));
      if (running) {
        alreadyRunning.push(relativeScript);
        continue;
      }

      this.spawnPython(scriptPath);
      started.push(relativeScript);
    }

    this.lastStartResult = { started, alreadyRunning, missing };
    await this.writeStatusNote({ started, alreadyRunning, missing });
    await this.refreshStatus(false);

    if (showNotice) {
      new Notice(`Bucky: ${started.length} started, ${alreadyRunning.length} already running`);
    }
  }

  spawnPython(scriptPath) {
    const child = childProcess.spawn(this.settings.pythonCommand, [scriptPath], {
      cwd: this.rootPath,
      detached: true,
      stdio: "ignore",
      windowsHide: true,
      env: Object.assign({}, process.env, {
        VAULT_PATH: this.agentVaultPath,
        BUCKY_AGENT: "1",
      }),
    });
    child.unref();
  }

  isScriptRunning(scriptName) {
    return new Promise(resolve => {
      if (process.platform !== "win32") { resolve(false); return; }

      const command = [
        "$script = " + JSON.stringify(scriptName) + ";",
        "$items = Get-CimInstance Win32_Process | Where-Object {",
        "  $_.CommandLine -and",
        "  $_.CommandLine -like \"*$script*\" -and",
        "  $_.Name -notmatch \"^(powershell|pwsh)(\\.exe)?$\"",
        "};",
        "@($items).Count",
      ].join(" ");

      const child = childProcess.spawn("powershell.exe", [
        "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command,
      ], { windowsHide: true });

      let stdout = "";
      const timer = window.setTimeout(() => { child.kill(); resolve(false); }, 5000);
      child.stdout.on("data", chunk => { stdout += chunk.toString("utf8"); });
      child.on("close", () => { window.clearTimeout(timer); resolve(Number(stdout.trim()) > 0); });
      child.on("error", () => { window.clearTimeout(timer); resolve(false); });
    });
  }

  async getRuntimeStatus() {
    const scripts = {};
    for (const relativeScript of this.settings.scripts) {
      scripts[relativeScript] = await this.isScriptRunning(path.basename(relativeScript));
    }
    return scripts;
  }

  async refreshStatus(showNotice) {
    this.vaultPath = this.getVaultPath();
    this.rootPath = this.getRootPath();
    this.agentVaultPath = this.getAgentVaultPath();
    this.pc = this.detectPc();
    const scripts = await this.getRuntimeStatus();
    const runningCount = Object.values(scripts).filter(Boolean).length;
    const total = Object.keys(scripts).length;
    this.statusBar.setText(`${BUCKY_NAME} ${runningCount}/${total} | ${this.pc.label}`);
    await this.writeStatusNote({ scripts });

    if (showNotice) {
      new Notice(`Bucky: ${runningCount}/${total} running on ${this.pc.label}`);
    }
  }

  async ensureParentFolder(filePath) {
    const adapter = this.app.vault.adapter;
    const parent = filePath.split("/").slice(0, -1).join("/");
    if (!parent) return;

    let current = "";
    for (const part of parent.split("/")) {
      current = current ? `${current}/${part}` : part;
      if (!(await adapter.exists(current))) {
        await adapter.mkdir(current);
      }
    }
  }

  async writeStatusNote(extra) {
    const scripts = extra.scripts || await this.getRuntimeStatus();
    const lastStartResult = {
      started: extra.started || this.lastStartResult.started || [],
      alreadyRunning: extra.alreadyRunning || this.lastStartResult.alreadyRunning || [],
      missing: extra.missing || this.lastStartResult.missing || [],
    };
    const now = new Date().toISOString();
    const lines = [
      "---",
      "type: bucky-status",
      `updated: ${now}`,
      `pc: ${this.pc.label}`,
      `hostname: ${this.pc.hostname}`,
      `username: ${this.pc.username}`,
      `agent: ${BUCKY_NAME}`,
      "runtime: claude_cli",
      "---",
      "",
      `# ${BUCKY_NAME} Status`,
      "",
      "| Item | Value |",
      "|---|---|",
      `| PC | ${this.pc.label} |`,
      `| Hostname | ${this.pc.hostname} |`,
      `| Username | ${this.pc.username} |`,
      `| Root | ${this.rootPath} |`,
      `| Vault | ${this.vaultPath} |`,
      `| Agent Vault | ${this.agentVaultPath} |`,
      `| Auto Start | ${this.settings.autoStart ? "on" : "off"} |`,
      `| Chat | ${this.settings.autoOpenChat ? "open" : "manual"} |`,
      "",
      "## Runtime",
      "",
      "| Script | Running |",
      "|---|---|",
      ...Object.entries(scripts).map(([script, running]) => `| ${script} | ${running ? "yes" : "no"} |`),
      "",
      "## Last Start Result",
      "",
      `- started: ${lastStartResult.started.join(", ") || "none"}`,
      `- already_running: ${lastStartResult.alreadyRunning.join(", ") || "none"}`,
      `- missing: ${lastStartResult.missing.join(", ") || "none"}`,
      "",
      "## Rules",
      "",
      "- Obsidian desktop loads the bucky-agent plugin.",
      "- Plugin detects local PC and starts Bucky scripts when autoStart is on.",
      "- Duplicate process check prevents launching the same script twice.",
      "- Bucky Chat calls the Claude CLI subscription route through scripts/bucky_chat_once.py.",
      "",
      "## Plugin Stack (2026-05-26)",
      "",
      "**원칙**: Plugin으로 해결 가능한 기능은 직접 개발하지 않는다.",
      "",
      "| 카테고리 | 플러그인 | 상태 |",
      "|---------|---------|------|",
      "| 자동화 | QuickAdd, Templater, Tasks, Shell Commands | ✅ 활성 |",
      "| 데이터 | Dataview, Smart Connections | ✅ 활성 |",
      "| UI | Meta Bind, Buttons, Kanban | ✅ 신규 |",
      "| 검색 | Omnisearch | ✅ 활성 |",
      "| 연동 | Local REST API, Git, Claudian | ✅ 활성 |",
      "",
      "커스텀 필수: Discord 봇 · Claude API · 비동기 병렬 · 음성인식 · AI 패턴학습",
      "상세: `00_System/plugin-stack/PLUGIN_STACK.md`",
    ];

    await this.ensureParentFolder(this.settings.statusNotePath);
    await this.app.vault.adapter.write(this.settings.statusNotePath, lines.join("\n"));
  }

  async openStatusNote() {
    await this.writeStatusNote({});
    const file = this.app.vault.getAbstractFileByPath(this.settings.statusNotePath);
    if (file) await this.app.workspace.getLeaf(false).openFile(file);
  }

  async saveSettings() {
    await this.saveData(this.settings);
  }
}

class BuckyChatView extends ItemView {
  constructor(leaf, plugin) {
    super(leaf);
    this.plugin = plugin;
    this.busy = false;
  }

  getViewType() {
    return BUCKY_CHAT_VIEW;
  }

  getDisplayText() {
    return "Bucky Chat";
  }

  getIcon() {
    return "message-circle";
  }

  async onOpen() {
    if (!this.plugin.chatMessages.length) {
      await this.plugin.loadChatHistoryFromTranscript();
    }
    this.render();
  }

  render() {
    const root = this.contentEl || this.containerEl.children[1] || this.containerEl;
    root.empty();
    root.classList.add("bucky-chat-view");

    // ── Titlebar ──────────────────────────────────────────────────────────
    const titlebar = root.createDiv({ cls: "bucky-code-titlebar" });
    titlebar.createDiv({ cls: "bucky-code-title", text: "Bucky Code" });
    const titleActions = titlebar.createDiv({ cls: "bucky-code-actions" });

    // Model selector
    const modelSel = titleActions.createEl("select", { cls: "bucky-model-select" });
    [
      { value: "sonnet", label: "Sonnet 4.6" },
      { value: "opus",   label: "Opus 4.7" },
      { value: "haiku",  label: "Haiku 4.5" },
    ].forEach(({ value, label }) => {
      const opt = modelSel.createEl("option", { value, text: label });
      if ((this.plugin.settings.chatModel || "sonnet") === value) opt.selected = true;
    });
    modelSel.addEventListener("change", async () => {
      this.plugin.settings.chatModel = modelSel.value;
      await this.plugin.saveSettings();
    });

    // Tool mode toggle
    const toolMode = this.plugin.settings.toolMode || "safe";
    this.toolBtn = titleActions.createEl("button", {
      cls: "bucky-icon-button bucky-tool-mode-btn",
      attr: { title: toolMode === "safe" ? "Safe mode (no tools)" : "Auto mode (tools enabled)", "aria-label": "Tool mode" },
      text: toolMode === "safe" ? "🔒" : "⚡",
    });
    this.toolBtn.addEventListener("click", async () => {
      const next = (this.plugin.settings.toolMode === "safe") ? "auto" : "safe";
      this.plugin.settings.toolMode = next;
      await this.plugin.saveSettings();
      this.toolBtn.textContent = next === "safe" ? "🔒" : "⚡";
      this.toolBtn.setAttribute("title", next === "safe" ? "Safe mode (no tools)" : "Auto mode (tools enabled)");
      new Notice(`Bucky: ${next === "safe" ? "Safe mode (채팅 전용)" : "Auto mode (툴 사용 가능)"}`);
    });

    // History & New chat
    const historyButton = titleActions.createEl("button", {
      cls: "bucky-icon-button",
      attr: { title: "History", "aria-label": "History" },
    });
    setIcon(historyButton, "clock");
    historyButton.addEventListener("click", () => this.openTranscript());

    const newButton = titleActions.createEl("button", {
      cls: "bucky-icon-button",
      attr: { title: "New chat", "aria-label": "New chat" },
    });
    setIcon(newButton, "plus-circle");
    newButton.addEventListener("click", () => {
      this.plugin.chatMessages = [];
      this.renderMessages();
      new Notice("Bucky: 새 대화 시작");
    });

    // ── Messages ─────────────────────────────────────────────────────────
    const stage = root.createDiv({ cls: "bucky-code-stage" });
    this.messagesEl = stage.createDiv({ cls: "bucky-chat-messages" });
    this.renderMessages();

    // ── Composer ─────────────────────────────────────────────────────────
    const composerWrap = root.createDiv({ cls: "bucky-composer-wrap" });
    const form = composerWrap.createEl("form", { cls: "bucky-chat-form" });
    const inputRow = form.createDiv({ cls: "bucky-input-row" });
    this.inputEl = inputRow.createEl("textarea", {
      cls: "bucky-chat-input",
      attr: { rows: "1", placeholder: "메시지 입력 (Enter 전송, Shift+Enter 줄바꿈)" },
    });

    const controls = form.createDiv({ cls: "bucky-composer-controls" });
    const leftControls = controls.createDiv({ cls: "bucky-composer-left" });

    // Attach file button
    const attachBtn = leftControls.createEl("button", {
      cls: "bucky-tool-button",
      attr: { type: "button", title: "현재 파일 첨부", "aria-label": "파일 첨부" },
    });
    setIcon(attachBtn, "paperclip");
    attachBtn.addEventListener("click", () => this.attachActiveFile());
    this.attachEl = leftControls.createDiv({ cls: "bucky-attachment", text: "파일 없음" });

    // Clear attachment button
    const clearAttachBtn = leftControls.createEl("button", {
      cls: "bucky-tool-button",
      attr: { type: "button", title: "첨부 해제", "aria-label": "첨부 해제" },
    });
    setIcon(clearAttachBtn, "x");
    clearAttachBtn.addEventListener("click", () => {
      this.attachedFile = null;
      this.refreshAttachmentLabel();
    });

    const rightControls = controls.createDiv({ cls: "bucky-composer-right" });
    this.statusEl = rightControls.createDiv({ cls: "bucky-chat-status", text: "ready" });
    this.sendButton = rightControls.createEl("button", {
      cls: "bucky-send-button",
      attr: { title: "전송", "aria-label": "전송" },
    });
    setIcon(this.sendButton, "arrow-up");

    form.addEventListener("submit", e => { e.preventDefault(); this.handleSubmit(); });
    this.inputEl.addEventListener("keydown", e => {
      if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); this.handleSubmit(); }
    });
    this.inputEl.addEventListener("input", () => {
      this.inputEl.style.height = "auto";
      this.inputEl.style.height = Math.min(this.inputEl.scrollHeight, 200) + "px";
    });
    this.refreshAttachmentLabel();
  }

  renderMessages() {
    if (!this.messagesEl) return;
    this.messagesEl.empty();
    if (!this.plugin.chatMessages.length) {
      const empty = this.messagesEl.createDiv({ cls: "bucky-chat-empty" });
      empty.createDiv({ cls: "bucky-empty-mark", text: "B" });
      empty.createDiv({ cls: "bucky-empty-line", text: "// TODO: Everything. Let's start." });
      return;
    }

    const renders = [];
    for (const message of this.plugin.chatMessages) {
      const item = this.messagesEl.createDiv({
        cls: `bucky-chat-message bucky-chat-${message.role}`,
      });
      const header = item.createDiv({ cls: "bucky-chat-header" });
      header.createDiv({ cls: "bucky-chat-role", text: message.role === "bucky" ? "버키" : message.role === "user" ? "나" : message.role });
      // Copy button for every message
      const copyBtn = header.createEl("button", {
        cls: "bucky-copy-btn",
        attr: { title: "복사", "aria-label": "복사" },
      });
      setIcon(copyBtn, "copy");
      copyBtn.addEventListener("click", () => {
        navigator.clipboard.writeText(message.text).then(() => {
          setIcon(copyBtn, "check");
          window.setTimeout(() => setIcon(copyBtn, "copy"), 1500);
        });
      });
      const body = item.createDiv({ cls: "bucky-chat-body" });
      if (message.role === "bucky") {
        if (message.text === "...") {
          body.createDiv({ cls: "bucky-thinking-dots", text: "..." });
        } else {
          renders.push(
            MarkdownRenderer.renderMarkdown(message.text, body, "", this)
              .catch(() => { body.setText(message.text); })
          );
        }
      } else {
        body.setText(message.text);
      }
    }
    Promise.all(renders).then(() => {
      if (this.messagesEl) this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
    });
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  refreshAttachmentLabel() {
    if (!this.attachEl) return;
    this.attachEl.setText(this.attachedFile ? path.basename(this.attachedFile.path) : "파일 없음");
  }

  attachActiveFile() {
    const file = this.app.workspace.getActiveFile();
    if (file) {
      const transcriptPath = this.plugin.settings.chatTranscriptPath || DEFAULT_SETTINGS.chatTranscriptPath;
      if (file.path === transcriptPath) {
        new Notice("Bucky: 채팅 기록 파일은 첨부할 수 없습니다");
        return;
      }
      this.attachedFile = file;
      new Notice(`첨부: ${file.name}`);
    } else {
      this.attachedFile = null;
      new Notice("열린 파일 없음");
    }
    this.refreshAttachmentLabel();
  }

  async buildIdePrompt(prompt, attachFile) {
    // chatMessages has current user msg already appended; exclude it from history
    const historyRaw = this.plugin.chatMessages.slice(0, -1).slice(-16);
    let historyContext = "";
    if (historyRaw.length > 0) {
      const lines = ["## Conversation History", ""];
      for (const msg of historyRaw) {
        if (msg.role === "user") {
          lines.push("### User", "", msg.text.trim(), "");
        } else if (msg.role === "bucky") {
          lines.push("### Bucky", "", msg.text.trim(), "");
        }
      }
      historyContext = lines.join("\n");
    }

    let fileContext = "";
    if (attachFile) {
      try {
        const content = await this.app.vault.cachedRead(attachFile);
        fileContext = [
          "## Attached File",
          `Path: ${attachFile.path}`,
          "",
          "```markdown",
          content.slice(0, 8000),
          "```",
        ].join("\n");
      } catch (error) {
        fileContext = `## Attached File\nPath: ${attachFile.path}\nRead failed: ${error.message || error}`;
      }
    }

    const parts = [
      "# Bucky Code IDE Chat",
      "",
      "Mode: Ask before edits. Do not edit files without explicit user approval.",
    ];
    if (historyContext) parts.push("", historyContext);
    if (fileContext) parts.push("", fileContext);
    parts.push("", "## User Message", "", prompt);
    return parts.join("\n");
  }

  setBusy(value) {
    this.busy = value;
    if (this.sendButton) this.sendButton.disabled = value;
    if (this.inputEl) this.inputEl.disabled = value;
    if (!value) {
      if (this.elapsedTimer) { window.clearInterval(this.elapsedTimer); this.elapsedTimer = null; }
      if (this.statusEl) this.statusEl.setText("ready");
    } else {
      const start = Date.now();
      if (this.statusEl) this.statusEl.setText("thinking 0s");
      this.elapsedTimer = window.setInterval(() => {
        const s = Math.round((Date.now() - start) / 1000);
        if (this.statusEl) this.statusEl.setText(`thinking ${s}s`);
      }, 1000);
    }
  }

  async handleSubmit() {
    if (this.busy || !this.inputEl) return;
    const prompt = this.inputEl.value.trim();
    if (!prompt) return;

    this.inputEl.value = "";
    this.plugin.addChatMessage("user", prompt);
    this.renderMessages();
    this.setBusy(true);

    const attachFile = this.attachedFile || null;
    this.attachedFile = null;
    this.refreshAttachmentLabel();

    const thinkingMsg = this.plugin.addChatMessage("bucky", "...");
    this.renderMessages();

    try {
      const idePrompt = await this.buildIdePrompt(prompt, attachFile);
      const reply = await this.plugin.sendChat(idePrompt, prompt);
      thinkingMsg.text = reply;
      thinkingMsg.role = "bucky";
    } catch (error) {
      thinkingMsg.text = String(error.message || error);
      thinkingMsg.role = "error";
      new Notice("Bucky chat failed");
    } finally {
      this.setBusy(false);
      this.renderMessages();
      if (this.inputEl) this.inputEl.focus();
    }
  }

  async openTranscript() {
    const file = this.app.vault.getAbstractFileByPath(this.plugin.settings.chatTranscriptPath);
    if (file) {
      await this.app.workspace.getLeaf(false).openFile(file);
    } else {
      new Notice("No Bucky transcript yet");
    }
  }
}

class BuckySettingTab extends PluginSettingTab {
  constructor(app, plugin) {
    super(app, plugin);
    this.plugin = plugin;
  }

  display() {
    const { containerEl } = this;
    containerEl.empty();
    containerEl.createEl("h2", { text: "Bucky Agent" });

    new Setting(containerEl)
      .setName("Auto start")
      .setDesc("Start the Bucky agent line when Obsidian loads.")
      .addToggle(toggle => toggle
        .setValue(this.plugin.settings.autoStart)
        .onChange(async value => {
          this.plugin.settings.autoStart = value;
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName("Auto open chat")
      .setDesc("Open the Bucky chat pane when Obsidian loads.")
      .addToggle(toggle => toggle
        .setValue(this.plugin.settings.autoOpenChat)
        .onChange(async value => {
          this.plugin.settings.autoOpenChat = value;
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName("Python command")
      .setDesc("Command used to launch Bucky scripts.")
      .addText(text => text
        .setValue(this.plugin.settings.pythonCommand)
        .onChange(async value => {
          this.plugin.settings.pythonCommand = value || "python";
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName("Status note")
      .setDesc("Vault-relative note path for Bucky runtime status.")
      .addText(text => text
        .setValue(this.plugin.settings.statusNotePath)
        .onChange(async value => {
          this.plugin.settings.statusNotePath = value || DEFAULT_SETTINGS.statusNotePath;
          await this.plugin.saveSettings();
        }));

    new Setting(containerEl)
      .setName("Chat transcript")
      .setDesc("Vault-relative note path for Bucky chat history.")
      .addText(text => text
        .setValue(this.plugin.settings.chatTranscriptPath)
        .onChange(async value => {
          this.plugin.settings.chatTranscriptPath = value || DEFAULT_SETTINGS.chatTranscriptPath;
          await this.plugin.saveSettings();
        }));
  }
}

module.exports = BuckyAgentPlugin;
