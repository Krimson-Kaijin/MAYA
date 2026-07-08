import React, { useState } from 'react'
import { IconLock, IconWand, IconCompare, IconSend, IconSpark } from './icons.jsx'
import { DistributionBar, DuoBar, bucketColor } from './Charts.jsx'

const fmtDate = (iso) => {
  try {
    return new Date(iso).toLocaleString('en-IN', {
      day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit',
    })
  } catch { return iso }
}

export function SensitivityBadge({ level }) {
  if (!level || level === 'SAFE') return <span className="badge safe">safe</span>
  if (level === 'SENSITIVE') return <span className="badge sensitive">sensitive</span>
  return <span className="badge blocked">blocked</span>
}

/* ------------------------------------------------------------------ files -- */
export function FilesCard({ card, onSummarize, onPickCompare, compareSel = [] }) {
  return (
    <div className="card" data-accent="teal">
      <div className="card-title"><IconSpark style={{ width: 15 }} /> Files found</div>
      <div style={{ marginTop: 8 }}>
        {card.items.map((f) => (
          <div key={f.path}
               className={`file-row ${f.shielded ? 'shielded' : ''} ${compareSel.includes(f.path) ? 'selected' : ''}`}>
            <div className="ficon">{f.shielded ? <IconLock style={{ width: 15 }} /> : f.ext.replace('.', '').toUpperCase()}</div>
            <div className="fmeta">
              <div className="fname">{f.name}</div>
              <div className="fsnippet">
                {f.shielded
                  ? `Shielded (${f.categories.join(', ') || 'financial'}) — listed by name only, content not indexed.`
                  : (f.snippet || f.folder)}
              </div>
            </div>
            <div className="facts">
              <SensitivityBadge level={f.sensitivity} />
              {!f.shielded && onSummarize && (
                <button className="btn btn-ghost btn-sm" onClick={() => onSummarize(f.path)}>Summarize</button>
              )}
              {!f.shielded && onPickCompare && (
                <button className="btn btn-ghost btn-sm" title="Select for comparison"
                        onClick={() => onPickCompare(f.path)}><IconCompare style={{ width: 13 }} /></button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/* ---------------------------------------------------------------- summary -- */
export function SummaryCard({ card }) {
  const { summary, tasks } = card
  const has = (k) => tasks && tasks[k] && tasks[k].length > 0
  return (
    <div className="card" data-accent="gold">
      <div className="card-title">
        <IconWand style={{ width: 15 }} />
        {card.file}
        <SensitivityBadge level={card.sensitivity} />
        <span className="badge neutral">{card.mode}</span>
      </div>
      <div className="card-sub">
        {summary.headline} · {summary.original_words} words distilled · engine: {summary.engine}
      </div>
      <div className="summary-bullets">
        {summary.bullets.map((b, i) => <div className="b" key={i}>{b}</div>)}
      </div>
      {(has('action_items') || has('risks') || has('deadlines') || has('entities')) && (
        <div className="tasks-grid">
          {has('action_items') && (
            <div className="tcol">
              <div className="eyebrow">Action items</div>
              <ul>{tasks.action_items.slice(0, 6).map((t, i) => <li key={i}>{t}</li>)}</ul>
            </div>
          )}
          {has('risks') && (
            <div className="tcol">
              <div className="eyebrow">Risks</div>
              <ul>{tasks.risks.slice(0, 4).map((t, i) => <li className="risk" key={i}>{t}</li>)}</ul>
            </div>
          )}
          {has('deadlines') && (
            <div className="tcol">
              <div className="eyebrow">Deadlines spotted</div>
              <ul>{tasks.deadlines.slice(0, 6).map((t, i) => <li key={i}>{t}</li>)}</ul>
            </div>
          )}
          {has('entities') && (
            <div className="tcol">
              <div className="eyebrow">Key entities</div>
              <div className="term-chips">
                {tasks.entities.slice(0, 6).map((e, i) => <span className="chip" key={i}>{e}</span>)}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ tasks -- */
export function TasksCard({ card }) {
  return (
    <div className="card" data-accent="coral">
      <div className="card-title">Action items — {card.file}</div>
      <div className="tasks-grid" style={{ gridTemplateColumns: '1fr' }}>
        <div className="tcol">
          <ul>{card.action_items.map((t, i) => <li key={i}>{t}</li>)}</ul>
        </div>
        {card.deadlines?.length > 0 && (
          <div className="tcol">
            <div className="eyebrow">Deadlines</div>
            <ul>{card.deadlines.map((t, i) => <li key={i}>{t}</li>)}</ul>
          </div>
        )}
      </div>
    </div>
  )
}

/* ----------------------------------------------------------------- digest -- */
const BUCKET_LABELS = [
  ['urgent', 'Urgent'],
  ['action', 'Needs action'],
  ['meetings', 'Meetings & appointments'],
  ['follow_ups', 'Follow-ups'],
  ['noise', 'Low-priority noise'],
]

export function DigestCard({ card, onDraftReply }) {
  const shielded = card.buckets.shielded || []
  return (
    <div className="card" data-accent="iris">
      <div className="card-title">
        Inbox digest <span className="badge mock">mock data</span>
      </div>
      <div className="card-sub">{card.source_note} · generated {fmtDate(card.generated_at)}</div>

      <DistributionBar counts={card.counts} />

      {BUCKET_LABELS.map(([key, label]) => {
        const items = card.buckets[key] || []
        if (!items.length) return null
        return (
          <div className="digest-bucket" key={key}>
            <div className="eyebrow">
              <i className="bdot" style={{ background: bucketColor(key) }} />
              {label} <span className="count">— {items.length}</span>
            </div>
            {items.map((it) => (
              <div key={it.id} className={`email-row ${key === 'urgent' ? 'urgent-item' : ''}`}>
                <div className="avatar">{(it.sender_name || '?')[0]}</div>
                <div className="emeta">
                  <div className="esub">{it.subject} {it.vip && <span className="badge neutral">vip</span>}
                    {it.sensitivity === 'SENSITIVE' && <SensitivityBadge level="SENSITIVE" />}</div>
                  <div className="eline">{it.sender_name} · {it.one_line}</div>
                  <div className="ewhy">why: {it.why.join('; ')}</div>
                </div>
                {onDraftReply && key !== 'noise' && (
                  <button className="btn btn-ghost btn-sm" onClick={() => onDraftReply(it)}>Draft reply</button>
                )}
              </div>
            ))}
          </div>
        )
      })}

      {shielded.length > 0 && (
        <div className="shield-panel">
          <IconLock />
          <div className="t">
            <b>{shielded.length} message{shielded.length === 1 ? '' : 's'} shielded by your privacy policy.</b>{' '}
            MAYA classified them at category level and did not read, summarize, or store their content.
            <div className="cats">
              {[...new Set(shielded.flatMap((s) => s.categories))].map((c) => (
                <span className="badge blocked" key={c}>{c.replace('_', ' ')}</span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

/* --------------------------------------------------------------- briefing -- */
export function BriefingCard({ card }) {
  return (
    <div className="card" data-accent="sunrise">
      <div className="card-title">Today’s briefing</div>
      {card.suggestions?.length > 0 && (
        <div style={{ marginTop: 10 }}>
          <div className="eyebrow" style={{ marginBottom: 9 }}>Suggested next actions</div>
          <ol className="suggestion-list">
            {card.suggestions.map((s, i) => (
              <li key={i}><span className="n">{String(i + 1).padStart(2, '0')}</span> {s}</li>
            ))}
          </ol>
        </div>
      )}
      <div className="brief-grid">
        {card.urgent?.length > 0 && (
          <div className="brief-block">
            <div className="eyebrow">Urgent email</div>
            {card.urgent.map((it) => (
              <div className="mini-file" key={it.id}><b>{it.subject}</b><span>{it.sender_name}</span></div>
            ))}
          </div>
        )}
        {card.meetings?.length > 0 && (
          <div className="brief-block">
            <div className="eyebrow">Meetings</div>
            {card.meetings.map((it) => (
              <div className="mini-file" key={it.id}>
                <b>{it.subject}</b>
                {it.sensitivity === 'SENSITIVE' && <SensitivityBadge level="SENSITIVE" />}
              </div>
            ))}
          </div>
        )}
        {card.doc_tasks?.items?.length > 0 && (
          <div className="brief-block">
            <div className="eyebrow">From {card.doc_tasks.file}</div>
            <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 6 }}>
              {card.doc_tasks.items.map((t, i) => (
                <li key={i} style={{ fontSize: 12.5, color: 'var(--ink-dim)' }}>· {t}</li>
              ))}
            </ul>
          </div>
        )}
        <div className="brief-block">
          <div className="eyebrow">Recent files</div>
          {card.recent_files?.map((f) => (
            <div className="mini-file" key={f.path}>
              <b>{f.name}</b><SensitivityBadge level={f.sensitivity} />
            </div>
          ))}
        </div>
        {card.reminders?.length > 0 && (
          <div className="brief-block">
            <div className="eyebrow">Reminders</div>
            {card.reminders.map((r) => (
              <div className="mini-file" key={r.id}><b>{r.value}</b></div>
            ))}
          </div>
        )}
      </div>
      {card.shielded_count > 0 && (
        <div className="card-sub" style={{ marginTop: 12 }}>
          {card.shielded_count} email(s) stayed shielded while building this briefing.
        </div>
      )}
    </div>
  )
}

/* ---------------------------------------------------------------- compare -- */
export function CompareCard({ card }) {
  const col = (side) => (
    <div className="compare-col">
      <h4>{side.name}</h4>
      <div className="card-sub">{side.words} words · deadlines: {side.deadlines?.join(', ') || '—'}</div>
      <div className="summary-bullets">
        {side.summary.bullets.map((b, i) => <div className="b" key={i}>{b}</div>)}
      </div>
      {side.action_items?.length > 0 && (
        <>
          <div className="eyebrow" style={{ margin: '10px 0 6px' }}>Action items</div>
          <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 5 }}>
            {side.action_items.slice(0, 4).map((t, i) => (
              <li key={i} style={{ fontSize: 12, color: 'var(--ink-dim)' }}>· {t}</li>
            ))}
          </ul>
        </>
      )}
    </div>
  )
  return (
    <div className="card" data-accent="duo">
      <div className="card-title"><IconCompare style={{ width: 15 }} /> Comparison</div>
      {card.version_note && <div className="version-note">✦ {card.version_note}</div>}
      <DuoBar unit=" words" rows={[
        { label: card.a.name, value: card.a.words, color: 'var(--chart-action)' },
        { label: card.b.name, value: card.b.words, color: 'var(--chart-meetings)' },
      ]} />
      <div className="compare-grid">{col(card.a)}{col(card.b)}</div>
      <div style={{ marginTop: 14 }}>
        {card.shared_topics?.length > 0 && (
          <>
            <div className="eyebrow">Shared ground</div>
            <div className="term-chips">
              {card.shared_topics.map((t) => <span className="chip" key={t}>{t}</span>)}
            </div>
          </>
        )}
        <div className="compare-grid" style={{ marginTop: 10 }}>
          <div>
            <div className="eyebrow">Distinct to {card.a.name}</div>
            <div className="term-chips">
              {card.only_in_a.map((t) => <span className="chip" key={t} style={{ borderColor: 'rgba(217,164,65,.35)', color: 'var(--gold-bright)', background: 'rgba(217,164,65,.08)' }}>{t}</span>)}
            </div>
          </div>
          <div>
            <div className="eyebrow">Distinct to {card.b.name}</div>
            <div className="term-chips">
              {card.only_in_b.map((t) => <span className="chip" key={t} style={{ borderColor: 'rgba(139,124,246,.4)', color: '#b3a8fa', background: 'rgba(139,124,246,.08)' }}>{t}</span>)}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ draft -- */
export function DraftCard({ card, onSend }) {
  const [body, setBody] = useState(card.body)
  return (
    <div className="card" data-accent="iris">
      <div className="card-title"><IconSend style={{ width: 15 }} /> Draft reply
        <span className="badge neutral">draft — not sent</span></div>
      <div className="card-sub">{card.note}</div>
      <div className="draft-field"><label>To</label><div className="val">{card.to}</div></div>
      <div className="draft-field"><label>Subject</label><div className="val">{card.subject}</div></div>
      <div className="draft-field">
        <label>Body — editable</label>
        <textarea className="val" style={{ width: '100%', minHeight: 130, resize: 'vertical' }}
                  value={body} onChange={(e) => setBody(e.target.value)} />
      </div>
      {onSend && (
        <div style={{ marginTop: 12, display: 'flex', gap: 10 }}>
          <button className="btn btn-gold btn-sm"
                  onClick={() => onSend({ to: card.to, subject: card.subject, body })}>
            Send (asks confirmation)
          </button>
        </div>
      )}
    </div>
  )
}

/* ----------------------------------------------------------------- memory -- */
export function MemoryCard({ card }) {
  return (
    <div className="card" data-accent="mint">
      <div className="card-title">Memory {!card.enabled && <span className="badge blocked">off</span>}</div>
      {card.items.length === 0
        ? <div className="card-sub" style={{ marginTop: 8 }}>Empty — MAYA only stores what you explicitly ask her to.</div>
        : card.items.map((m) => (
          <div className="mini-file" key={m.id}>
            <b>{m.value}</b><span className="badge neutral">{m.source}</span>
          </div>
        ))}
    </div>
  )
}

/* --------------------------------------------------------------- dispatch -- */
export default function CardRenderer({ card, handlers = {} }) {
  switch (card.type) {
    case 'files': return <FilesCard card={card} {...handlers} />
    case 'summary': return <SummaryCard card={card} />
    case 'tasks': return <TasksCard card={card} />
    case 'digest': return <DigestCard card={card} onDraftReply={handlers.onDraftReply} />
    case 'briefing': return <BriefingCard card={card} />
    case 'compare': return <CompareCard card={card} />
    case 'draft': return <DraftCard card={card} onSend={handlers.onSendDraft} />
    case 'memory': return <MemoryCard card={card} />
    default: return null
  }
}
