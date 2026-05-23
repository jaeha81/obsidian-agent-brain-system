const { Notice, Plugin, PluginSettingTab, Setting } = require("obsidian");
const childProcess = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");

const BUCKY_NAME = "\uBC84\uD0A4";
const HOME_PROJECT_MARKER = "D:\\ai\uD504\uB85C\uC81D\uD2B8";
const LOCAL_PROJECT_MARKER = "C:\\ai\uD504\uB85C\uC81D\uD2B8";
const OFFICE_USERNAME = "\uC124\uACC4" + "4";

const DEFAULT_SETTINGS = {
  autoStart: true,
  pythonCommand: "python",
  statusNotePath: "00_System/BUCKY_STATUS.md",
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
    this.pc = this.detectPc();
    this.lastStartResult = { started: [], alreadyRunning: [], missing: [] };
    this.statusBar = this.addStatusBarItem();
    this.statusBar.addClass("bucky-agent-status");

    this.addRibbonIcon("bot", "Bucky Agent status", async () => {
      await this.refreshStatus(true);
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

    this.addSettingTab(new BuckySettingTab(this.app, this));
    await this.refreshStatus(false);

    if (this.settings.autoStart) {
      this.startTimer = window.setTimeout(() => {
        this.startBucky(false);
      }, this.settings.startupDelayMs);
    }

    this.refreshTimer = window.setInterval(() => {
      this.refreshStatus(false);
    }, 60000);
  }

  onunload() {
    if (this.startTimer) window.clearTimeout(this.startTimer);
    if (this.refreshTimer) window.clearInterval(this.refreshTimer);
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
      markers,
    };
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
        VAULT_PATH: this.vaultPath,
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
      `| Auto Start | ${this.settings.autoStart ? "on" : "off"} |`,
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
      "- Agent runtime uses the existing Claude CLI subscription route.",
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
  }
}

module.exports = BuckyAgentPlugin;
