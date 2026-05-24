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
    this.statusBar = this.addStatusBarItem();
    this.statusBar.addClass("bucky-agent-status");

    this.registerView(BUCKY_CHAT_VIEW, leaf => new BuckyChatView(leaf, this));

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

  async sendChat(userText) {
    const reply = await this.runChatBridge(userText);
    await this.appendChatTranscript(userText, reply);
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
      const child = childProcess.spawn(
        this.settings.pythonCommand,
        [bridgePath, "--timeout", String(timeoutSeconds)],
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
    const existing = await adapter.exists(transcriptPath)
      ? await adapter.read(transcriptPath)
      : header;
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

      const running = this.isScriptRunning(path.basename(relativeScript));
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
    if (process.platform !== "win32") return false;

    const command = [
      "$script = " + JSON.stringify(scriptName) + ";",
      "$items = Get-CimInstance Win32_Process | Where-Object {",
      "  $_.CommandLine -and",
      "  $_.CommandLine -like \"*$script*\" -and",
      "  $_.Name -notmatch \"^(powershell|pwsh)(\\.exe)?$\"",
      "};",
      "@($items).Count",
    ].join(" ");

    try {
      const result = childProcess.spawnSync("powershell.exe", [
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        command,
      ], {
        encoding: "utf8",
        windowsHide: true,
        timeout: 5000,
      });
      return Number(String(result.stdout || "").trim()) > 0;
    } catch (error) {
      return false;
    }
  }

  async getRuntimeStatus() {
    const scripts = {};
    for (const relativeScript of this.settings.scripts) {
      scripts[relativeScript] = this.isScriptRunning(path.basename(relativeScript));
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
    this.render();
  }

  render() {
    const root = this.contentEl || this.containerEl.children[1] || this.containerEl;
    root.empty();
    root.classList.add("bucky-chat-view");

    const titlebar = root.createDiv({ cls: "bucky-code-titlebar" });
    titlebar.createDiv({ cls: "bucky-code-title", text: "Untitled" });
    const titleActions = titlebar.createDiv({ cls: "bucky-code-actions" });
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
    });

    const brand = root.createDiv({ cls: "bucky-code-brand" });
    brand.createEl("span", { cls: "bucky-code-spark" });
    brand.createEl("span", { text: "Bucky Code" });

    const stage = root.createDiv({ cls: "bucky-code-stage" });
    this.messagesEl = stage.createDiv({ cls: "bucky-chat-messages" });
    this.renderMessages();

    const composerWrap = root.createDiv({ cls: "bucky-composer-wrap" });
    composerWrap.createDiv({
      cls: "bucky-terminal-tip",
      text: "Prefer the Terminal experience? Switch back in Settings.",
    });
    const form = composerWrap.createEl("form", { cls: "bucky-chat-form" });
    const inputRow = form.createDiv({ cls: "bucky-input-row" });
    this.inputEl = inputRow.createEl("textarea", {
      cls: "bucky-chat-input",
      attr: {
        rows: "1",
        placeholder: "ctrl esc to focus or unfocus Bucky",
      },
    });
    const micEl = inputRow.createDiv({ cls: "bucky-mic" });
    setIcon(micEl, "mic");
    const controls = form.createDiv({ cls: "bucky-composer-controls" });
    const leftControls = controls.createDiv({ cls: "bucky-composer-left" });
    const plusButton = leftControls.createEl("button", {
      cls: "bucky-tool-button",
      attr: { type: "button", title: "Attach current file", "aria-label": "Attach current file" },
    });
    setIcon(plusButton, "plus");
    plusButton.addEventListener("click", () => this.attachActiveFile());
    const fileButton = leftControls.createEl("button", {
      cls: "bucky-tool-button",
      attr: { type: "button", title: "Current file", "aria-label": "Current file" },
    });
    setIcon(fileButton, "file");
    fileButton.addEventListener("click", () => this.attachActiveFile());
    this.attachEl = leftControls.createDiv({ cls: "bucky-attachment", text: "no file" });
    const rightControls = controls.createDiv({ cls: "bucky-composer-right" });
    rightControls.createDiv({ cls: "bucky-edit-mode", text: "Ask before edits" });
    this.statusEl = rightControls.createDiv({ cls: "bucky-chat-status", text: "ready" });
    this.sendButton = rightControls.createEl("button", {
      cls: "bucky-send-button",
      attr: { title: "Send", "aria-label": "Send" },
    });
    setIcon(this.sendButton, "arrow-up");
    form.addEventListener("submit", event => {
      event.preventDefault();
      this.handleSubmit();
    });
    this.inputEl.addEventListener("keydown", event => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        this.handleSubmit();
      }
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

    for (const message of this.plugin.chatMessages) {
      const item = this.messagesEl.createDiv({
        cls: `bucky-chat-message bucky-chat-${message.role}`,
      });
      item.createDiv({ cls: "bucky-chat-role", text: message.role });
      const body = item.createDiv({ cls: "bucky-chat-body" });
      if (message.role === "bucky") {
        MarkdownRenderer.renderMarkdown(message.text, body, "", this);
      } else {
        body.setText(message.text);
      }
    }
    this.messagesEl.scrollTop = this.messagesEl.scrollHeight;
  }

  refreshAttachmentLabel() {
    if (!this.attachEl) return;
    const file = this.app.workspace.getActiveFile();
    this.attachEl.setText(file ? file.path : "no file");
  }

  attachActiveFile() {
    this.refreshAttachmentLabel();
    const file = this.app.workspace.getActiveFile();
    new Notice(file ? `Bucky attached: ${file.path}` : "No active file");
  }

  async buildIdePrompt(prompt) {
    const file = this.app.workspace.getActiveFile();
    let fileContext = "";
    if (file) {
      try {
        const content = await this.app.vault.cachedRead(file);
        fileContext = [
          "## Active Obsidian File",
          `Path: ${file.path}`,
          "",
          "```markdown",
          content.slice(0, 12000),
          "```",
        ].join("\n");
      } catch (error) {
        fileContext = `## Active Obsidian File\nPath: ${file.path}\nRead failed: ${error.message || error}`;
      }
    }
    return [
      "# Bucky Code IDE Chat",
      "",
      "Mode: Ask before edits. Do not edit files without explicit user approval.",
      "Environment: Obsidian pane styled after Claude Code/Codex IDE chat.",
      "",
      fileContext,
      "",
      "## User Message",
      "",
      prompt,
    ].join("\n");
  }

  setBusy(value) {
    this.busy = value;
    if (this.sendButton) this.sendButton.disabled = value;
    if (this.inputEl) this.inputEl.disabled = value;
    if (this.statusEl) this.statusEl.setText(value ? "thinking" : "ready");
  }

  async handleSubmit() {
    if (this.busy || !this.inputEl) return;
    const prompt = this.inputEl.value.trim();
    if (!prompt) return;

    this.inputEl.value = "";
    this.plugin.addChatMessage("user", prompt);
    this.renderMessages();
    this.setBusy(true);

    try {
      const idePrompt = await this.buildIdePrompt(prompt);
      const reply = await this.plugin.sendChat(idePrompt);
      this.plugin.addChatMessage("bucky", reply);
    } catch (error) {
      this.plugin.addChatMessage("error", String(error.message || error));
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
