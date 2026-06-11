const messagesEl = document.querySelector('#messages')
const targetsEl = document.querySelector('#targets')
const form = document.querySelector('#message-form')
const kindEl = document.querySelector('#kind')
const bodyEl = document.querySelector('#body')
const errorEl = document.querySelector('#error')
const refreshEl = document.querySelector('#refresh')
const quickSyncEl = document.querySelector('#quick-sync')
const quickUpdateEl = document.querySelector('#quick-update')
const exportLogEl = document.querySelector('#export-log')
const autoRefreshEl = document.querySelector('#auto-refresh')
const storageEl = document.querySelector('#storage')
const syncStateEl = document.querySelector('#sync-state')
const agentEnabledEl = document.querySelector('#agent-enabled')
const searchEl = document.querySelector('#search')
const detailEl = document.querySelector('#detail')
const targetSummaryEl = document.querySelector('#target-summary')
const statusSummaryEl = document.querySelector('#status-summary')
const queueRoomEl = document.querySelector('#queue-room')
const queueClaudeEl = document.querySelector('#queue-claude')
const queueCodexEl = document.querySelector('#queue-codex')
const queueCountRoomEl = document.querySelector('#queue-count-room')
const queueCountClaudeEl = document.querySelector('#queue-count-claude')
const queueCountCodexEl = document.querySelector('#queue-count-codex')
const targetButtons = Array.from(document.querySelectorAll('[data-target]'))
const templateButtons = Array.from(document.querySelectorAll('[data-template]'))
const statusButtons = Array.from(document.querySelectorAll('[data-status]'))
const filterButtons = Array.from(document.querySelectorAll('[data-filter]'))

const labels = {
  user: '사용자',
  claude: 'Claude',
  codex: 'Codex',
  direction: '지시',
  implementation: '구현',
  review: '검수',
  sync: '동기화',
  room: '공유 지시',
}

const statusLabels = {
  todo: '대기',
  working: '진행중',
  review: '검수중',
  done: '완료',
}

let currentMessages = []
let currentFilter = 'all'
let refreshTimer = null
let activeMessageId = null
let currentTarget = 'room'

const templates = {
  'claude-start': {
    target: 'claude',
    kind: 'direction',
    body: '작업 목적:\n대상 저장소/폴더:\n수정 예정 파일:\n기대 결과:\n작업 시작 전 잠금 확인:',
  },
  'codex-review': {
    target: 'codex',
    kind: 'review',
    body: '검수 대상 작업:\n검수 범위:\n확인할 파일/커밋:\n보고 형식:',
  },
  'shared-plan': {
    target: 'room',
    kind: 'direction',
    body: '공유 작업 계획:\n1.\n2.\n3.\n역할 분담:\nClaude:\nCodex:',
  },
}

function formatTimestamp(value) {
  return new Intl.DateTimeFormat('ko-KR', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  }).format(new Date(value))
}

function setError(message) {
  errorEl.hidden = !message
  errorEl.textContent = message || ''
}

function updateTargetUI() {
  for (const button of targetButtons) {
    button.classList.toggle('active', button.dataset.target === currentTarget)
  }
  targetSummaryEl.textContent = `현재 지시 대상: ${labels[currentTarget]}`
}

function updateStatusUI(message) {
  const activeStatus = message && message.speaker === 'user' ? (message.status || 'todo') : null
  for (const button of statusButtons) {
    button.classList.toggle('active', button.dataset.status === activeStatus)
    button.disabled = !activeStatus
  }
  statusSummaryEl.textContent = activeStatus
    ? `현재 상태: ${statusLabels[activeStatus]}`
    : '사용자 지시를 선택하면 상태를 변경할 수 있습니다.'
}

function visibleMessages() {
  const query = searchEl.value.trim().toLowerCase()
  return currentMessages.filter((message) => {
    const speakerMatches = currentFilter === 'all' || message.speaker === currentFilter
    if (!speakerMatches) return false
    if (!query) return true
    return [
      labels[message.speaker],
      labels[message.kind],
      message.body,
      formatTimestamp(message.createdAt),
    ].join(' ').toLowerCase().includes(query)
  })
}

function selectMessage(message) {
  activeMessageId = message ? message.id : null
  if (!message) {
    detailEl.className = 'detail-card empty'
    detailEl.innerHTML = '<strong>선택된 메시지 없음</strong><p>메시지를 선택하면 전체 작업 내용과 지시 대상을 확인할 수 있습니다.</p>'
    return
  }

  const targetLabel = message.speaker === 'user' ? labels[message.target || 'room'] : '채팅방 기록'
  const statusLabel = message.speaker === 'user' ? statusLabels[message.status || 'todo'] : '기록'
  detailEl.className = `detail-card ${message.speaker}`
  detailEl.innerHTML = `
    <div class="detail-head">
      <span><span class="badge">${labels[message.speaker]}</span> · ${labels[message.kind]}</span>
      <time datetime="${message.createdAt}">${formatTimestamp(message.createdAt)}</time>
    </div>
    <p class="detail-target">대상: ${targetLabel}</p>
    <p class="detail-status">상태: ${statusLabel}</p>
    <pre></pre>
  `
  detailEl.querySelector('pre').textContent = message.body
  updateStatusUI(message)
}

function renderMessages(messages) {
  currentMessages = messages
  messagesEl.innerHTML = ''
  const counts = { user: 0, claude: 0, codex: 0 }

  for (const message of messages) {
    counts[message.speaker] += 1
  }

  const shownMessages = visibleMessages()
  if (!activeMessageId && shownMessages.length > 0) {
    activeMessageId = shownMessages[shownMessages.length - 1].id
  }

  for (const message of shownMessages) {
    const item = document.createElement('article')
    item.className = `message ${message.speaker}${message.id === activeMessageId ? ' active' : ''}`
    item.tabIndex = 0
    const targetLabel = message.speaker === 'user' ? labels[message.target || 'room'] : labels[message.speaker]
    const statusLabel = message.speaker === 'user' ? statusLabels[message.status || 'todo'] : null
    item.innerHTML = `
      <div class="message-head">
        <span><span class="badge">${labels[message.speaker]}</span> · ${labels[message.kind]}</span>
        <time datetime="${message.createdAt}">${formatTimestamp(message.createdAt)}</time>
      </div>
      <div class="message-meta">${targetLabel}${statusLabel ? ` · ${statusLabel}` : ''}</div>
      <p></p>
    `
    item.querySelector('p').textContent = message.body
    item.addEventListener('click', () => {
      selectMessage(message)
      renderMessages(currentMessages)
    })
    item.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault()
        selectMessage(message)
        renderMessages(currentMessages)
      }
    })
    messagesEl.appendChild(item)
  }

  const selectedMessage = currentMessages.find((message) => message.id === activeMessageId)
  selectMessage(selectedMessage || shownMessages.at(-1) || null)

  if (shownMessages.length === 0) {
    const empty = document.createElement('div')
    empty.className = 'empty-state'
    empty.textContent = '표시할 메시지가 없습니다.'
    messagesEl.appendChild(empty)
  }

  document.querySelector('#count-user').textContent = counts.user
  document.querySelector('#count-claude').textContent = counts.claude
  document.querySelector('#count-codex').textContent = counts.codex
  messagesEl.scrollTop = messagesEl.scrollHeight
}

function renderTargets(targets) {
  targetsEl.innerHTML = ''
  for (const target of targets) {
    const item = document.createElement('div')
    item.className = `target ${target.exists ? 'ok' : 'missing'}`
    item.innerHTML = `
      <div>
        <strong>${target.label}</strong>
        <p>${target.updatedAt ? new Date(target.updatedAt).toLocaleString('ko-KR') : '확인되지 않음'}</p>
      </div>
      <span class="state">${target.exists ? '확인' : '없음'}</span>
    `
    targetsEl.appendChild(item)
  }
}

function renderQueueList(container, countEl, messages) {
  container.innerHTML = ''
  countEl.textContent = String(messages.length)

  if (messages.length === 0) {
    const empty = document.createElement('div')
    empty.className = 'queue-empty'
    empty.textContent = '대기 중인 지시 없음'
    container.appendChild(empty)
    return
  }

  for (const message of messages.slice(-4).reverse()) {
    const item = document.createElement('button')
    item.type = 'button'
    item.className = 'queue-item'
    item.innerHTML = `
      <span class="queue-time">${formatTimestamp(message.createdAt)} · ${statusLabels[message.status || 'todo']}</span>
      <span class="queue-text"></span>
    `
    item.querySelector('.queue-text').textContent = message.body
    item.addEventListener('click', () => {
      activeMessageId = message.id
      currentFilter = 'user'
      for (const button of filterButtons) button.classList.toggle('active', button.dataset.filter === 'user')
      selectMessage(message)
      renderMessages(currentMessages)
    })
    container.appendChild(item)
  }
}

function renderQueues(messages) {
  const userMessages = messages.filter((message) => message.speaker === 'user' && (message.status || 'todo') !== 'done')
  renderQueueList(queueRoomEl, queueCountRoomEl, userMessages.filter((message) => (message.target || 'room') === 'room'))
  renderQueueList(queueClaudeEl, queueCountClaudeEl, userMessages.filter((message) => message.target === 'claude'))
  renderQueueList(queueCodexEl, queueCountCodexEl, userMessages.filter((message) => message.target === 'codex'))
}

function renderPayload(payload) {
  renderMessages(payload.messages)
  renderQueues(payload.messages)
  renderTargets(payload.syncTargets)
  storageEl.textContent = `저장소: ${payload.storage}`
  syncStateEl.textContent = `동기화 기록: ${payload.syncState || 'JH-SHARED / 03_LOGS / sync-state.jsonl'}`
  agentEnabledEl.textContent = payload.agentPostingEnabled ? 'Claude/Codex 등록: 활성화됨' : 'Claude/Codex 등록: .env의 ADMIN_SECRET 필요'
}

async function loadRoom() {
  setError('')
  const response = await fetch('/api/messages', { cache: 'no-store' })
  if (!response.ok) throw new Error('채팅방 데이터를 불러오지 못했습니다.')
  renderPayload(await response.json())
}

async function postUserMessage(kind, body) {
  const response = await fetch('/api/messages', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ speaker: 'user', kind, target: currentTarget, body }),
  })
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.error || '메시지를 저장하지 못했습니다.')
  renderPayload(payload)
}

async function updateMessageStatus(id, status) {
  const response = await fetch('/api/messages/status', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ id, status }),
  })
  const payload = await response.json()
  if (!response.ok) throw new Error(payload.error || '상태를 저장하지 못했습니다.')
  renderPayload(payload)
}

function scheduleAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer)
  refreshTimer = null
  if (autoRefreshEl.checked) {
    refreshTimer = setInterval(() => {
      loadRoom().catch((error) => setError(error.message))
    }, 5000)
  }
}

function exportLog() {
  const blob = new Blob([JSON.stringify(currentMessages, null, 2)], { type: 'application/json;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  const stamp = new Date().toISOString().replace(/[:.]/g, '-')
  link.href = url
  link.download = `jh-agent-room-${stamp}.json`
  document.body.appendChild(link)
  link.click()
  link.remove()
  URL.revokeObjectURL(url)
}

form.addEventListener('submit', async (event) => {
  event.preventDefault()
  const body = bodyEl.value.trim()
  if (!body) return

  try {
    setError('')
    await postUserMessage(kindEl.value, body)
    bodyEl.value = ''
  } catch (error) {
    setError(error.message)
  }
})

bodyEl.addEventListener('keydown', (event) => {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
    form.requestSubmit()
  }
})

for (const button of templateButtons) {
  button.addEventListener('click', () => {
    const template = templates[button.dataset.template]
    if (!template) return
    currentTarget = template.target
    kindEl.value = template.kind
    bodyEl.value = template.body
    updateTargetUI()
    bodyEl.focus()
  })
}

refreshEl.addEventListener('click', () => {
  loadRoom().catch((error) => setError(error.message))
})

quickSyncEl.addEventListener('click', () => {
  postUserMessage('sync', '동기화').catch((error) => setError(error.message))
})

quickUpdateEl.addEventListener('click', () => {
  postUserMessage('direction', '업데이트').catch((error) => setError(error.message))
})

exportLogEl.addEventListener('click', exportLog)
autoRefreshEl.addEventListener('change', scheduleAutoRefresh)
searchEl.addEventListener('input', () => renderMessages(currentMessages))

for (const button of targetButtons) {
  button.addEventListener('click', () => {
    currentTarget = button.dataset.target
    updateTargetUI()
  })
}

for (const button of statusButtons) {
  button.addEventListener('click', async () => {
    const selectedMessage = currentMessages.find((message) => message.id === activeMessageId)
    if (!selectedMessage || selectedMessage.speaker !== 'user') return
    try {
      setError('')
      await updateMessageStatus(selectedMessage.id, button.dataset.status)
    } catch (error) {
      setError(error.message)
    }
  })
}

for (const button of filterButtons) {
  button.addEventListener('click', () => {
    currentFilter = button.dataset.filter
    for (const item of filterButtons) item.classList.toggle('active', item === button)
    renderMessages(currentMessages)
  })
}

updateTargetUI()
updateStatusUI(null)
loadRoom().then(scheduleAutoRefresh).catch((error) => setError(error.message))
