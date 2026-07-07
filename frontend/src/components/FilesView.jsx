import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { FilesCard, SummaryCard, CompareCard } from './Cards.jsx'
import { IconRefresh } from './icons.jsx'

export default function FilesView({ notify }) {
  const [q, setQ] = useState('')
  const [type, setType] = useState('')
  const [latest, setLatest] = useState(false)
  const [hits, setHits] = useState([])
  const [panel, setPanel] = useState(null)          // {kind:'summary'|'compare', card}
  const [sel, setSel] = useState([])                // compare selection (paths)
  const [mode, setMode] = useState('medium')
  const [busy, setBusy] = useState(false)

  const run = async (query = q) => {
    setBusy(true)
    try {
      const r = await api.search(query, { type: type || undefined, latest })
      setHits(r.hits)
    } catch (e) { notify(`Search failed: ${e.message}`, 'err') }
    setBusy(false)
  }

  useEffect(() => { run('') }, [])   // browse on first open

  const summarize = async (path) => {
    setBusy(true)
    try {
      const r = await api.summarize(path, mode)
      const card = r.cards?.[0]
      if (card) setPanel({ kind: 'summary', card })
      else notify(r.reply, 'err')     // blocked-content refusal, shown honestly
    } catch (e) { notify(e.message, 'err') }
    setBusy(false)
  }

  const pickCompare = async (path) => {
    const next = sel.includes(path) ? sel.filter((p) => p !== path) : [...sel, path].slice(-2)
    setSel(next)
    if (next.length === 2) {
      setBusy(true)
      try {
        const r = await api.compare(next[0], next[1])
        const card = r.cards?.[0]
        if (card) setPanel({ kind: 'compare', card })
        else notify(r.reply, 'err')
      } catch (e) { notify(e.message, 'err') }
      setBusy(false)
    }
  }

  return (
    <div className="view">
      <div className="view-head">
        <h1>Files</h1>
        <p>Search is confined to your approved folders. Blocked documents are listed by name only.</p>
      </div>

      <div className="filters-bar">
        <input type="text" value={q} placeholder="Search by keyword — try “vendor risks” or “sop”"
               onChange={(e) => setQ(e.target.value)}
               onKeyDown={(e) => e.key === 'Enter' && run()} />
        <select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">any type</option>
          {['md', 'txt', 'csv', 'pdf', 'docx'].map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <label className="check">
          <input type="checkbox" checked={latest} onChange={(e) => setLatest(e.target.checked)} />
          prefer latest
        </label>
        <select value={mode} onChange={(e) => setMode(e.target.value)} title="Summary length">
          <option value="short">short</option>
          <option value="medium">medium</option>
          <option value="detailed">detailed</option>
        </select>
        <button className="btn btn-ghost" onClick={() => run()} disabled={busy}>
          <IconRefresh style={{ width: 14 }} /> Search
        </button>
      </div>

      {sel.length > 0 && (
        <div className="compare-bar">
          <span>Compare: <b>{sel.map((p) => p.split('/').pop()).join('  ↔  ')}</b>
            {sel.length === 1 ? ' — pick one more file' : ''}</span>
          <button className="btn btn-ghost btn-sm" style={{ marginLeft: 'auto' }}
                  onClick={() => setSel([])}>clear</button>
        </div>
      )}

      {hits.length > 0
        ? <FilesCard card={{ items: hits }} onSummarize={summarize}
                     onPickCompare={pickCompare} compareSel={sel} />
        : <div className="empty"><div className="big">Nothing here yet.</div>
            Search your approved workspace above.</div>}

      {panel?.kind === 'summary' && <SummaryCard card={panel.card} />}
      {panel?.kind === 'compare' && <CompareCard card={panel.card} />}
    </div>
  )
}
