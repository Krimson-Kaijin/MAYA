import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { IconTrash, IconBrain } from './icons.jsx'

export default function MemoryView({ notify }) {
  const [items, setItems] = useState([])
  const [enabled, setEnabled] = useState(true)
  const [value, setValue] = useState('')

  const load = async () => {
    const r = await api.memoryList()
    setItems(r.items); setEnabled(r.enabled)
  }
  useEffect(() => { load() }, [])

  const add = async () => {
    if (!value.trim()) return
    const out = await api.memoryAdd(value.trim())
    if (out.stored) { setValue(''); notify('Remembered — encrypted at rest.', 'ok') }
    else if (out.reason === 'blocked_content')
      notify(`Refused: that looks like ${out.categories?.join(', ')} content. MAYA doesn't memorize it.`, 'err')
    else notify('Memory is switched off.', 'err')
    load()
  }

  const toggle = async () => {
    const r = await api.memoryToggle(!enabled)
    setEnabled(r.enabled)
    notify(r.enabled ? 'Memory on.' : 'Memory off — nothing new will be stored.', 'ok')
  }

  return (
    <div className="view" style={{ maxWidth: 760 }}>
      <div className="view-head">
        <h1>Memory</h1>
        <p>Only what you explicitly asked MAYA to remember. Fernet-encrypted on disk,
           reviewable, deletable — and refuses financial/credential material outright.</p>
      </div>

      <div className="setting-row" style={{ borderTop: '1px solid var(--hairline)' }}>
        <div>
          <div className="s-label">Memory {enabled ? 'enabled' : 'disabled'}</div>
          <div className="s-help">Turn off to make MAYA fully stateless between sessions.</div>
        </div>
        <label className="switch">
          <input type="checkbox" checked={enabled} onChange={toggle} />
          <span className="track" />
        </label>
      </div>

      <div className="filters-bar" style={{ margin: '18px 0 14px' }}>
        <input type="text" value={value} placeholder='e.g. "I prefer short summaries before 10am"'
               onChange={(e) => setValue(e.target.value)}
               onKeyDown={(e) => e.key === 'Enter' && add()} disabled={!enabled} />
        <button className="btn btn-gold" onClick={add} disabled={!enabled}>Remember</button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        {items.map((m) => (
          <div className="mem-row" key={m.id}>
            <IconBrain style={{ width: 15, color: 'var(--teal)', flexShrink: 0, marginTop: 2 }} />
            <div style={{ flex: 1 }}>
              <div className="val">{m.value}</div>
              <div className="meta">{m.source} · {new Date(m.created_at).toLocaleString('en-IN')}</div>
            </div>
            <button className="btn btn-rose btn-sm" onClick={async () => { await api.memoryDelete(m.id); load() }}>
              <IconTrash style={{ width: 13 }} />
            </button>
          </div>
        ))}
        {items.length === 0 && (
          <div className="empty"><div className="big">Nothing memorized.</div>
            MAYA stores preferences only when you explicitly ask.</div>
        )}
      </div>
    </div>
  )
}
