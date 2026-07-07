#!/usr/bin/env bash
# oci_provision.sh — Bucky second-brain RUNTIME provisioning for Oracle A1
# Target: aarch64 Ubuntu 24.04 (verified: ubuntu@161.33.204.158 = instance #2)
#
# IDEMPOTENT: safe to re-run. Each step checks-before-installing.
# SCOPE = runtimes only. Deliberately NOT here (each is a separate gated step):
#   - secrets            -> /etc/ai-os/.env created by hand on server (chmod 600), never in git
#   - interactive login  -> `claude login` / `codex login` run manually (device-code flow)
#   - code deploy        -> git clone / rsync of scripts/ (asset-classification excludes)
#   - systemd units      -> bucky-bot / bucky-chat / gbrain enable --now
#   - OCI resize 4/24 & #1 termination -> OCI SDK + explicit approval, AFTER cutover verify
#
# Usage:
#   ./oci_provision.sh            # run all steps
#   ./oci_provision.sh doctor     # only print component status
#   ./oci_provision.sh apt node claude codex bun gbrain ollama dirs   # run selected steps
#   DRY_RUN=1 ./oci_provision.sh  # print what would run, change nothing
set -euo pipefail

# ---- config (override via env) -------------------------------------------
NODE_MAJOR="${NODE_MAJOR:-22}"
CLAUDE_NPM_PKG="${CLAUDE_NPM_PKG:-@anthropic-ai/claude-code}"
CODEX_NPM_PKG="${CODEX_NPM_PKG:-@openai/codex}"   # TODO: confirm exact pkg; override if wrong
GBRAIN_PKG="${GBRAIN_PKG:-github:garrytan/gbrain}"
EMBED_MODEL="${EMBED_MODEL:-nomic-embed-text}"
AI_OS_ROOT="${AI_OS_ROOT:-/opt/ai-os}"
AI_OS_ETC="${AI_OS_ETC:-/etc/ai-os}"
DRY_RUN="${DRY_RUN:-0}"

# ---- helpers -------------------------------------------------------------
c_g=$'\e[32m'; c_y=$'\e[33m'; c_r=$'\e[31m'; c_b=$'\e[36m'; c_0=$'\e[0m'
log()  { printf '%s[*]%s %s\n' "$c_b" "$c_0" "$*"; }
ok()   { printf '%s[ok]%s %s\n' "$c_g" "$c_0" "$*"; }
warn() { printf '%s[!]%s %s\n' "$c_y" "$c_0" "$*" >&2; }
die()  { printf '%s[x]%s %s\n' "$c_r" "$c_0" "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }
run()  { if [ "$DRY_RUN" = "1" ]; then printf '   would run: %s\n' "$*"; else eval "$*"; fi; }

need_root_helper() { have sudo || die "sudo not found — run as a user with sudo"; }

# ---- preflight -----------------------------------------------------------
preflight() {
  local arch; arch="$(uname -m)"
  [ "$arch" = "aarch64" ] || warn "arch is '$arch', expected aarch64 (ARM). Continuing anyway."
  . /etc/os-release 2>/dev/null || true
  log "Host: $(whoami)@$(hostname) | ${PRETTY_NAME:-unknown} | $arch | $(nproc) vCPU"
  need_root_helper
}

# ---- steps ---------------------------------------------------------------
step_apt() {
  log "apt base packages"
  run "sudo apt-get update -y"
  run "sudo apt-get install -y python3-pip python3-venv git ffmpeg build-essential curl unzip jq ca-certificates"
  ok "apt base packages present"
}

step_node() {
  if have node && [ "$(node -v | sed 's/v\([0-9]*\).*/\1/')" -ge "$NODE_MAJOR" ] 2>/dev/null; then
    ok "node $(node -v) already >= $NODE_MAJOR — skip"; return
  fi
  log "installing Node $NODE_MAJOR (NodeSource, arm64)"
  run "curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | sudo -E bash -"
  run "sudo apt-get install -y nodejs"
  have node && ok "node $(node -v) / npm $(npm -v)" || warn "node still missing after install"
}

step_claude() {
  if have claude; then ok "claude CLI present ($(claude --version 2>/dev/null | head -1))"; return; fi
  have npm || die "npm required for claude CLI — run step_node first"
  log "installing Claude CLI ($CLAUDE_NPM_PKG)"
  run "sudo npm install -g $CLAUDE_NPM_PKG"
  warn "MANUAL: run 'claude login' (subscription/device-code) — NOT automated here"
}

step_codex() {
  if have codex; then ok "codex CLI present"; return; fi
  have npm || die "npm required for codex CLI — run step_node first"
  log "installing Codex CLI ($CODEX_NPM_PKG)"
  run "sudo npm install -g $CODEX_NPM_PKG" || warn "codex install failed — verify package name ($CODEX_NPM_PKG)"
  warn "MANUAL: run 'codex login' — NOT automated here"
}

step_bun() {
  if have bun || [ -x "$HOME/.bun/bin/bun" ]; then
    export PATH="$HOME/.bun/bin:$PATH"; ok "bun present ($(bun --version 2>/dev/null))"; return
  fi
  log "installing Bun (arm64)"
  run "curl -fsSL https://bun.sh/install | bash"
  export PATH="$HOME/.bun/bin:$PATH"
  # persist PATH for future shells (idempotent append)
  if ! grep -q '.bun/bin' "$HOME/.bashrc" 2>/dev/null; then
    run "printf '\nexport PATH=\"\$HOME/.bun/bin:\$PATH\"\n' >> \"$HOME/.bashrc\""
  fi
  have bun && ok "bun $(bun --version)" || warn "bun still missing"
}

step_gbrain() {
  export PATH="$HOME/.bun/bin:$PATH"
  if have gbrain; then ok "gbrain present ($(gbrain --version 2>/dev/null | head -1)) — skip (update: bun install -g $GBRAIN_PKG)"; return; fi
  have bun || die "bun required for gbrain — run step_bun first"
  log "installing gbrain ($GBRAIN_PKG)"
  run "bun install -g $GBRAIN_PKG"
  have gbrain && ok "gbrain installed" || warn "gbrain still missing"
  warn "NEXT (separate step): gbrain init --pglite ; gbrain serve --http --port 8787 --enable-dcr ; gbrain auth create mcp-claude"
}

step_ollama() {
  if have ollama; then ok "ollama present ($(ollama --version 2>/dev/null | head -1))"; else
    log "installing Ollama (arm64; sets up systemd ollama.service)"
    run "curl -fsSL https://ollama.com/install.sh | sh"
  fi
  # ensure service is up before pulling
  if [ "$DRY_RUN" != "1" ]; then
    have ollama || { warn "ollama missing after install"; return; }
    systemctl is-active --quiet ollama 2>/dev/null || run "sudo systemctl enable --now ollama || ollama serve &"
    sleep 2
    if ollama list 2>/dev/null | grep -q "$EMBED_MODEL"; then
      ok "embed model '$EMBED_MODEL' already pulled"
    else
      log "pulling embed model '$EMBED_MODEL'"
      run "ollama pull $EMBED_MODEL"
    fi
  else
    run "ollama pull $EMBED_MODEL"
  fi
}

step_dirs() {
  log "scaffolding $AI_OS_ROOT (code) + $AI_OS_ETC (secrets, 700)"
  run "sudo mkdir -p $AI_OS_ROOT && sudo chown \"$(whoami)\":\"$(whoami)\" $AI_OS_ROOT"
  run "sudo mkdir -p $AI_OS_ETC && sudo chmod 700 $AI_OS_ETC"
  # env TEMPLATE only — placeholders, no real secrets ever committed or written here
  if [ "$DRY_RUN" != "1" ] && [ ! -f "$AI_OS_ETC/.env.example" ]; then
    sudo tee "$AI_OS_ETC/.env.example" >/dev/null <<'ENVEOF'
# Fill real values on-server only. chmod 600. NEVER commit or route via Google Drive.
DISCORD_BOT_TOKEN=
DISCORD_CHANNEL_IDS=
GBRAIN_TOKEN=
ANTHROPIC_... =   # via `claude login`, not raw key if using subscription
ENVEOF
    sudo chmod 600 "$AI_OS_ETC/.env.example"
  fi
  ok "dirs ready ($AI_OS_ROOT owned by $(whoami); $AI_OS_ETC 700)"
}

# ---- doctor --------------------------------------------------------------
doctor() {
  export PATH="$HOME/.bun/bin:$PATH"
  log "component status"
  for b in python3 git node npm bun claude codex gbrain ollama ffmpeg; do
    if have "$b"; then printf '  %s%-8s%s %s\n' "$c_g" "$b" "$c_0" "$(command -v "$b")";
    else printf '  %s%-8s%s MISSING\n' "$c_r" "$b" "$c_0"; fi
  done
  have ollama && { ollama list 2>/dev/null | grep -q "$EMBED_MODEL" && ok "embed '$EMBED_MODEL' pulled" || warn "embed '$EMBED_MODEL' NOT pulled"; }
  [ -d "$AI_OS_ROOT" ] && ok "$AI_OS_ROOT exists" || warn "$AI_OS_ROOT absent"
  [ -d "$AI_OS_ETC" ]  && ok "$AI_OS_ETC exists"  || warn "$AI_OS_ETC absent"
  have claude && warn "claude login status: run 'claude login' if not authenticated"
}

# ---- dispatch ------------------------------------------------------------
main() {
  preflight
  local steps=("$@")
  if [ "${#steps[@]}" -eq 0 ]; then
    steps=(apt node claude codex bun gbrain ollama dirs doctor)
  fi
  for s in "${steps[@]}"; do
    case "$s" in
      apt) step_apt ;; node) step_node ;; claude) step_claude ;; codex) step_codex ;;
      bun) step_bun ;; gbrain) step_gbrain ;; ollama) step_ollama ;; dirs) step_dirs ;;
      doctor) doctor ;;
      *) warn "unknown step: $s" ;;
    esac
  done
  ok "oci_provision.sh finished (steps: ${steps[*]})"
}
main "$@"
