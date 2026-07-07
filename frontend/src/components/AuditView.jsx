import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { IconRefresh } from './icons.jsx'

const FILTERS = [
  ['', 'everything'], ['files', 'files'], ['email', 'email'],
  ['action', 'actions'], ['memory', 'memory'], ['command', 'commands'],
]

export default function AuditView() {
  const [entries, setEntries] = useState([])
  const [filter, setFilter] = useState('')

  const load = async (f = filter) => {
    const r = await api.audit(120, f || undefined)
    setEntries(r.entries)
  }
  useEffect(() => { load() }, [filter])

  return (
    <div className="view">
      <div className="view-head" style={{ display: 'flex', alignItems: 'flex-end', gap: 14 }}>
        <div style={{ flex: 1 }}>
          <h1>Audit trail</h1>
          <p>Every access, classification block, memory write and gated action — append-only.
             Targets and categories are logged; sensitive content itself never is.</p>
        </div>
        <div className="seg">
          {FILTERS.map(([v, label]) => (
            <button key={v} className={filter === v ? 'on' : ''} onClick={() => setFilter(v)}>{label}</button>
          ))}
        </div>
        <button className="btn btn-ghost" onClick={() => load()}><IconRefresh style={{ width: 14 }} /></button>
      </div>

      <div className="card" style={{ padding: '8px 6px' }}>
        {entries.map((e) => (
          <div className="audit-row" key={e.id}>
            <span className="ts">{new Date(e.ts).toLocaleString('en-IN', {
              day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', second: '2-digit' })}</span>
            <span className="ev" style={{
              color: e.event.startsWith('action') ? 'var(--gold-bright)'
                : e.event.includes('shielded') || e.outcome === 'refused' ? 'var(--rose)'
                : e.event.startsWith('memory') ? 'var(--violet)' : 'var(--teal)' }}>
              {e.event}
            </span>
            <span className="detail" title={`${e.target} ${e.detail}`}>
              {e.target && <b style={{ color: 'var(--ink)' }}>{e.target}</b>} {e.detail}
            </span>
            <span className={`badge ${e.outcome === 'ok' ? 'safe' : e.outcome === 'shielded' || e.outcome === 'refused' ? 'blocked' : 'neutral'}`}>
              {e.outcome}
            </span>
          </div>
        ))}
        {entries.length === 0 && <div className="empty" style={{ border: 'none' }}>No entries for this filter.</div>}
      </div>
    </div>
  )
}
