const assert = require("assert");
const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const pluginDirs = [
  path.join(root, ".obsidian", "plugins", "bucky-agent"),
  path.join(root, "ObsidianVault", ".obsidian", "plugins", "bucky-agent"),
];

const requiredScripts = [
  "scripts/raw_import_watcher.py",
  "scripts/codex_review_runner.py",
  "scripts/agent_dispatcher.py",
];

for (const dir of pluginDirs) {
  const label = path.relative(root, dir);
  const mainPath = path.join(dir, "main.js");
  const dataPath = path.join(dir, "data.json");

  assert.ok(fs.existsSync(mainPath), `${label}: missing main.js`);
  assert.ok(fs.existsSync(dataPath), `${label}: missing data.json`);

  const main = fs.readFileSync(mainPath, "utf8");
  const data = JSON.parse(fs.readFileSync(dataPath, "utf8"));

  assert.equal(data.autoStart, true, `${label}: autoStart must be enabled`);
  assert.equal(data.autoOpenChat, true, `${label}: autoOpenChat must be enabled`);
  assert.deepEqual(data.scripts, requiredScripts, `${label}: should only auto-start core local agent scripts`);

  assert.match(main, /async activateAgentLine\(/, `${label}: missing startup orchestrator`);
  assert.match(main, /startupRetryCount/, `${label}: missing startup retry setting`);
  assert.match(main, /onLayoutReady\(\(\) => \{\s*this\.activateAgentLine\(false\)/s, `${label}: startup should wait for layout readiness`);
  assert.match(main, /Bucky chat bridge not found/, `${label}: chat bridge error should stay explicit`);
  assert.match(main, /async tryHandleObsidianCommand\(/, `${label}: missing Obsidian control command router`);
  assert.match(main, /async runObsidianCommand\(/, `${label}: missing Obsidian control executor`);
  for (const command of ["/open", "/new", "/append", "/search", "/today", "/agentbus"]) {
    assert.ok(main.includes(`case "${command}"`), `${label}: missing ${command} command`);
  }
  for (const forbidden of ["/delete", "/move", "/rename", "/discord"]) {
    assert.ok(main.includes(`case "${forbidden}"`), `${label}: missing guarded ${forbidden} command`);
  }
  assert.match(main, /await this\.plugin\.tryHandleObsidianCommand\(prompt\)/, `${label}: chat submit must route Obsidian commands before Claude bridge`);
}

console.log("Bucky agent autostart verification passed");
