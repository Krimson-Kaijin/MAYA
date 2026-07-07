import React from 'react'
import { IconFolder, IconMail, IconShield } from './icons.jsx'

const tick = (ts) => {
  try { return new Date(ts).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) }
  catch { return '' }
}

// "Today at a glance" + approved sources + live activity feed.
export default function RightRail({ glance, sources, feed }) {
  return (
    <aside className="rail">
      <div className="rail-block">
        <div className="eyebrow">Today at a glance</div>
        <div className="stat-row">
          <div className="stat rose"><div className="v">{glance?.urgent ?? '–'}</div><div className="k">urgent</div></div>
          <div className="stat teal"><div className="v">{glance?.actions ?? '–'}</div><div className="k">actions</div></div>
          <div className="stat"><div className="v">{glance?.meetings ?? '–'}</div><div className="k">meetings</div></div>
        </div>
        {glance?.top && <div className="mock-note" style={{ padding: 0 }}>Next: {glance.top}</div>}
      </div>

      <div className="rail-block">
        <div className="eyebrow">Approved sources</div>
        {sources?.folders?.map((f) => (
          <div className="source-row" key={f.path}>
            <IconFolder /><span className="path" title={f.path}>{f.path.split('/').slice(-2).join('/')}</span>
            <span className="badge safe">allowed</span>
          </div>
        ))}
        <div className="source-row">
          <IconMail /><span className="path">{sources?.email?.labels?.join(', ') || 'INBOX'}</span>
          <span className="badge mock">{sources?.email?.status || 'mock'}</span>
        </div>
        <div className="source-row">
          <IconShield />
          <span className="path" style={{ fontFamily: 'var(--font-body)' }}>
            {sources?.denied_patterns?.length || 0} deny patterns enforced
          </span>
        </div>
      </div>

      <div className="rail-block">
        <div className="eyebrow">Activity</div>
        {(feed || []).slice(0, 9).map((e) => (
          <div className="feed-item" key={e.id}>
            <span className="tick">{tick(e.ts)}</span>
            <span className="ev">
              <b>{e.event}</b>{' '}
              {e.outcome !== 'ok'
                ? <span className="outcome-shielded">({e.outcome})</span>
                : (e.target ? `· ${e.target}` : '')}
            </span>
          </div>
        ))}
        {(!feed || feed.length === 0) && <div className="mock-note" style={{ padding: 0 }}>No activity yet.</div>}
      </div>
    </aside>
  )
}
