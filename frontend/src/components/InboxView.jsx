import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { DigestCard, DraftCard } from './Cards.jsx'
import { IconRefresh } from './icons.jsx'

export default function InboxView({ notify, onPending }) {
  const [digest, setDigest] = useState(null)
  const [reply, setReply] = useState(null)
  const [busy, setBusy] = useState(false)

  const load = async () => {
    setBusy(true)
    try {
      const r = await api.digest()
      setDigest(r.cards?.find((c) => c.type === 'digest') || null)
    } catch (e) { notify(e.message, 'err') }
    setBusy(false)
  }
  useEffect(() => { load() }, [])

  const draftReply = async (item) => {
    setBusy(true)
    try {
      const r = await api.chat(`draft a reply to ${item.sender_name}`)
      const card = r.cards?.find((c) => c.type === 'draft')
      if (card) setReply(card)
      else notify(r.reply, 'err')
    } catch (e) { notify(e.message, 'err') }
    setBusy(false)
  }

  const sendDraft = async (draft) => {
    try {
      const out = await api.sendDraft(draft)
      if (out.status === 'pending') onPending(out.action)
      else notify(`Unexpected: ${out.status}`, 'err')
    } catch (e) { notify(e.message, 'err') }
  }

  return (
    <div className="view">
      <div className="view-head" style={{ display: 'flex', alignItems: 'flex-end', gap: 14 }}>
        <div style={{ flex: 1 }}>
          <h1>Inbox</h1>
          <p>Mock sample data — a real connector would use the official Gmail API with
             read-only scope on approved labels. Blocked categories never render here.</p>
        </div>
        <button className="btn btn-ghost" onClick={load} disabled={busy}>
          <IconRefresh style={{ width: 14 }} /> Refresh digest
        </button>
      </div>
      {digest
        ? <DigestCard card={digest} onDraftReply={draftReply} />
        : <div className="empty"><div className="big">Building digest…</div></div>}
      {reply && <DraftCard card={reply} onSend={sendDraft} />}
    </div>
  )
}
