const fs = require('fs')
const http = require('http')
const os = require('os')
const path = require('path')
const crypto = require('crypto')
const { execFileSync } = require('child_process')

function loadEnvFile() {
  const envFile = path.join(__dirname, '.env')
  if (!fs.existsSync(envFile)) return
  const lines = fs.readFileSync(envFile, 'utf8').split(/\r?\n/)
  for (const line of lines) {
    if (!line || line.trim().startsWith('#') || !line.includes('=')) continue
    const [name, ...rest] = line.split('=')
    if (!process.env[name.trim()]) process.env[name.trim()] = rest.join('=').trim()
  }
}

loadEnvFile()

const PORT = Number(process.env.PORT || 3100)
const SHARED_DIR = process.env.AGENT_ROOM_SHARED_DIR || 'G:\\내 드라이브\\JH-SHARED'
const OBSIDIAN_VAULT_DIR = process.env.OBSIDIAN_VAULT_DIR || 'G:\\내 드라이브\\OBSIDIAN-SECOND'
const SYSTEM_DIR = path.join(SHARED_DIR, '00_SYSTEM')
const AGENT_ROOM_DIR = path.join(SHARED_DIR, '01_AGENT_ROOM')
const LOGS_DIR = path.join(SHARED_DIR, '03_LOGS')
const LOG_FILE = path.join(AGENT_ROOM_DIR, 'agent-room-messages.jsonl')
const LEGACY_LOG_FILE = path.join(SHARED_DIR, 'agent-room-messages.jsonl')
const SYNC_STATE_FILE = path.join(LOGS_DIR, 'sync-state.jsonl')
const PUBLIC_DIR = path.join(__dirname, 'public')

const syncTargets = [
  { label: '동기화 프로토콜', file: path.join(SYSTEM_DIR, 'sync-protocol.md') },
  { label: 'JH-SHARED 시스템 브리핑', file: path.join(SYSTEM_DIR, 'jh-system.md') },
  { label: 'JH-SHARED 경로 명세', file: path.join(SYSTEM_DIR, 'paths.md') },
  { label: 'Codex 마스터 상태', file: 'G:\\내 드라이브\\codex\\CODEX_MASTER_STATUS.md' },
  { label: 'Codex 운영 규칙', file: 'G:\\내 드라이브\\codex\\CODEX_OPERATING_RULES.md' },
  { label: 'Obsidian Vault 인덱스', file: path.join(OBSIDIAN_VAULT_DIR, 'wiki', 'index.md') },
  { label: 'Obsidian Vault 로그', file: path.join(OBSIDIAN_VAULT_DIR, 'wiki', 'log.md') },
]

const starterMessages = [
  ['user', 'direction', 'JH 통합 구축 시스템 기준으로 Claude와 Codex가 같은 맥락을 보고 역할을 분담한다.', '2026-04-29T20:16:00.000+09:00'],
  ['claude', 'implementation', 'GitHub는 코드, Google Drive는 자료, Obsidian Vault는 지식 허브로 분리해 작업한다.', '2026-04-29T20:18:00.000+09:00'],
  ['codex', 'review', 'Codex는 Claude 구현물을 자동 수정하지 않고 독립 검수 결과를 사용자에게 직접 보고한다.', '2026-04-29T20:19:00.000+09:00'],
]

function ensureStore() {
  fs.mkdirSync(SYSTEM_DIR, { recursive: true })
  fs.mkdirSync(AGENT_ROOM_DIR, { recursive: true })
  fs.mkdirSync(LOGS_DIR, { recursive: true })

  if (!fs.existsSync(LOG_FILE) && fs.existsSync(LEGACY_LOG_FILE)) {
    fs.copyFileSync(LEGACY_LOG_FILE, LOG_FILE)
  }

  if (!fs.existsSync(LOG_FILE)) {
    for (const [speaker, kind, body, createdAt] of starterMessages) {
      appendMessage({ speaker, kind, body, createdAt })
    }
  }
}

function appendJsonLine(file, payload) {
  fs.appendFileSync(file, JSON.stringify(payload) + '\n', 'utf8')
}

function normalizeTarget(speaker, target) {
  if (speaker !== 'user') return 'room'
  return ['room', 'claude', 'codex'].includes(target) ? target : 'room'
}

function normalizeStatus(speaker, status) {
  if (speaker !== 'user') return 'logged'
  return ['todo', 'working', 'review', 'done'].includes(status) ? status : 'todo'
}

function appendMessage({ speaker, kind, body, target = 'room', status = 'todo', createdAt = new Date().toISOString() }) {
  const message = {
    id: crypto.randomUUID(),
    speaker,
    kind,
    target: normalizeTarget(speaker, target),
    status: normalizeStatus(speaker, status),
    body,
    createdAt,
  }
  appendJsonLine(LOG_FILE, message)
  return message
}

function readJsonLines(file) {
  if (!fs.existsSync(file)) return []
  const raw = fs.readFileSync(file, 'utf8').trim()
  if (!raw) return []
  return raw
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line))
}

function readMessages() {
  ensureStore()
  return readJsonLines(LOG_FILE).sort((a, b) => new Date(a.createdAt) - new Date(b.createdAt))
}

function writeJsonLines(file, rows) {
  const data = rows.map((row) => JSON.stringify(row)).join('\n')
  fs.writeFileSync(file, data ? `${data}\n` : '', 'utf8')
}

function updateMessageStatus(id, status) {
  const rows = readJsonLines(LOG_FILE)
  const index = rows.findIndex((row) => row.id === id)
  if (index === -1) return false
  if (rows[index].speaker !== 'user') return false
  rows[index].status = normalizeStatus('user', status)
  writeJsonLines(LOG_FILE, rows)
  return true
}

function statusSnapshot() {
  return syncTargets.map((target) => {
    try {
      const stat = fs.statSync(target.file)
      return { label: target.label, exists: true, updatedAt: stat.mtime.toISOString() }
    } catch {
      return { label: target.label, exists: false, updatedAt: null }
    }
  })
}

function gitValue(args) {
  try {
    return execFileSync('git', args, { cwd: __dirname, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim()
  } catch {
    return null
  }
}

function currentPcSnapshot(reason) {
  const targets = statusSnapshot()
  const previous = readJsonLines(SYNC_STATE_FILE).at(-1) || null
  const current = {
    id: crypto.randomUUID(),
    reason,
    createdAt: new Date().toISOString(),
    hostname: os.hostname(),
    username: os.userInfo().username,
    platform: os.platform(),
    projectRoot: __dirname,
    gitBranch: gitValue(['branch', '--show-current']),
    gitCommit: gitValue(['rev-parse', '--short', 'HEAD']),
    gitStatus: gitValue(['status', '--short']) || '',
    targetsOk: targets.filter((target) => target.exists).length,
    targetsTotal: targets.length,
    previous: previous ? {
      hostname: previous.hostname,
      username: previous.username,
      createdAt: previous.createdAt,
      gitCommit: previous.gitCommit,
    } : null,
  }
  appendJsonLine(SYNC_STATE_FILE, current)
  return current
}

function syncSummary(snapshot) {
  const pc = `${snapshot.hostname}/${snapshot.username}`
  const previous = snapshot.previous
    ? `이전 기록: ${snapshot.previous.hostname}/${snapshot.previous.username} (${snapshot.previous.gitCommit || 'no-git'})`
    : '이전 기록 없음'
  const dirty = snapshot.gitStatus ? '로컬 변경 있음' : '로컬 변경 없음'
  return `동기화 스냅샷 기록: ${pc}, 기준 파일 ${snapshot.targetsOk}/${snapshot.targetsTotal} 확인, ${dirty}, 현재 커밋 ${snapshot.gitCommit || 'unknown'}. ${previous}.`
}

function safePayload() {
  return {
    messages: readMessages(),
    syncTargets: statusSnapshot(),
    storage: 'JH-SHARED / 01_AGENT_ROOM / agent-room-messages.jsonl',
    syncState: 'JH-SHARED / 03_LOGS / sync-state.jsonl',
    agentPostingEnabled: Boolean(process.env.ADMIN_SECRET),
  }
}

function readBody(req) {
  return new Promise((resolve, reject) => {
    let body = ''
    req.on('data', (chunk) => {
      body += chunk
      if (body.length > 100_000) {
        reject(new Error('request body too large'))
        req.destroy()
      }
    })
    req.on('end', () => resolve(body))
    req.on('error', reject)
  })
}

function sendJson(res, status, payload) {
  res.writeHead(status, { 'Content-Type': 'application/json; charset=utf-8' })
  res.end(JSON.stringify(payload))
}

function sendFile(res, filePath) {
  const ext = path.extname(filePath)
  const type = ext === '.css' ? 'text/css; charset=utf-8' : ext === '.js' ? 'text/javascript; charset=utf-8' : 'text/html; charset=utf-8'
  fs.readFile(filePath, (error, data) => {
    if (error) {
      res.writeHead(404)
      res.end('Not found')
      return
    }
    res.writeHead(200, {
      'Content-Type': type,
      'Cache-Control': 'no-cache, must-revalidate',
    })
    res.end(data)
  })
}

function isSyncOrUpdate(kind, body) {
  return kind === 'sync' || body.includes('동기화') || body.includes('업데이트') || body.toLowerCase().includes('update')
}

async function handleMessagePost(req, res) {
  try {
    const input = JSON.parse(await readBody(req))
    const speaker = input.speaker || 'user'
    const kind = input.kind || 'direction'
    const target = typeof input.target === 'string' ? input.target.trim() : 'room'
    const body = typeof input.body === 'string' ? input.body.trim() : ''

    if (!body) return sendJson(res, 400, { error: 'body is required' })
    if (!['direction', 'implementation', 'review', 'sync'].includes(kind)) return sendJson(res, 400, { error: 'invalid kind' })
    if (!['user', 'claude', 'codex'].includes(speaker)) return sendJson(res, 400, { error: 'invalid speaker' })

    if (speaker !== 'user') {
      const secret = req.headers['x-admin-secret']
      if (!process.env.ADMIN_SECRET || secret !== process.env.ADMIN_SECRET) {
        return sendJson(res, 401, { error: 'Unauthorized' })
      }
    }

    appendMessage({ speaker, kind, target, body })

    if (isSyncOrUpdate(kind, body)) {
      const snapshot = currentPcSnapshot(kind === 'sync' ? 'sync' : 'update')
      appendMessage({ speaker: 'claude', kind: 'implementation', body: '동기화 요청 접수. 전역 지침 전체가 아니라 JH-SHARED/00_SYSTEM의 최소 기준 파일부터 확인합니다.' })
      appendMessage({ speaker: 'codex', kind: 'review', body: syncSummary(snapshot) })
    }

    sendJson(res, 201, safePayload())
  } catch (error) {
    sendJson(res, 400, { error: error.message || 'Invalid request' })
  }
}

async function handleStatusPost(req, res) {
  try {
    const input = JSON.parse(await readBody(req))
    const id = typeof input.id === 'string' ? input.id.trim() : ''
    const status = typeof input.status === 'string' ? input.status.trim() : ''

    if (!id) return sendJson(res, 400, { error: 'id is required' })
    if (!['todo', 'working', 'review', 'done'].includes(status)) return sendJson(res, 400, { error: 'invalid status' })
    if (!updateMessageStatus(id, status)) return sendJson(res, 404, { error: 'message not found' })

    sendJson(res, 200, safePayload())
  } catch (error) {
    sendJson(res, 400, { error: error.message || 'Invalid request' })
  }
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`)

  if (url.pathname === '/api/messages' && req.method === 'GET') return sendJson(res, 200, safePayload())
  if (url.pathname === '/api/messages' && req.method === 'POST') return void handleMessagePost(req, res)
  if (url.pathname === '/api/messages/status' && req.method === 'POST') return void handleStatusPost(req, res)
  if (url.pathname === '/api/status' && req.method === 'GET') return sendJson(res, 200, safePayload())

  const filePath = url.pathname === '/' ? path.join(PUBLIC_DIR, 'index.html') : path.normalize(path.join(PUBLIC_DIR, url.pathname))
  if (!filePath.startsWith(PUBLIC_DIR)) {
    res.writeHead(403)
    res.end('Forbidden')
    return
  }
  sendFile(res, filePath)
})

ensureStore()
server.listen(PORT, () => {
  console.log(`JH Agent Room running at http://localhost:${PORT}`)
})
