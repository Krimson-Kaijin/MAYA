// Thin client for MAYA's local API. Same-origin in production build;
// the vite dev server proxies /api to 127.0.0.1:8930.

async function req(method, url, body) {
  const res = await fetch(url, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!res.ok) {
    const detail = await res.text().catch(() => '')
    throw new Error(`${res.status} ${detail}`)
  }
  return res.json()
}

export const api = {
  meta: () => req('GET', '/api/meta'),
  chat: (text, mode = 'chat', session_id = 'ui') =>
    req('POST', '/api/chat', { text, mode, session_id }),
  briefing: (session_id = 'ui') => req('GET', `/api/briefing?session_id=${session_id}`),
  digest: (session_id = 'ui') => req('GET', `/api/emails/digest?session_id=${session_id}`),
  search: (q, { type, folder, latest } = {}) => {
    const p = new URLSearchParams({ q: q || '' })
    if (type) p.set('type', type)
    if (folder) p.set('folder', folder)
    if (latest) p.set('latest', 'true')
    return req('GET', `/api/files/search?${p}`)
  },
  summarize: (path, mode = 'medium') => req('POST', '/api/files/summarize', { path, mode }),
  compare: (a, b) => req('POST', '/api/files/compare', { a, b }),
  rebuild: () => req('POST', '/api/index/rebuild'),
  pending: () => req('GET', '/api/actions/pending'),
  confirm: (id, approve) => req('POST', `/api/actions/${id}/confirm`, { approve }),
  sendDraft: (draft) => req('POST', '/api/emails/send_draft', draft),
  memoryList: () => req('GET', '/api/memory'),
  memoryAdd: (value) => req('POST', '/api/memory', { value }),
  memoryDelete: (id) => req('DELETE', `/api/memory/${id}`),
  memoryToggle: (enabled) => req('POST', '/api/memory/enabled', { enabled }),
  audit: (limit = 60, event) =>
    req('GET', `/api/audit?limit=${limit}${event ? `&event=${event}` : ''}`),
  sources: () => req('GET', '/api/sources'),
  settingsGet: () => req('GET', '/api/settings'),
  settingsPut: (patch) => req('PUT', '/api/settings', patch),
}
