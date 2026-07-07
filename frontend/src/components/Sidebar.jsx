import React from 'react'
import { IconSpark, IconFolder, IconMail, IconBrain, IconScroll, IconGear,
         IconShield, IconShieldAlert } from './icons.jsx'

const NAV = [
  { id: 'command', label: 'Command', icon: IconSpark },
  { id: 'files', label: 'Files', icon: IconFolder },
  { id: 'inbox', label: 'Inbox', icon: IconMail },
  { id: 'memory', label: 'Memory', icon: IconBrain },
  { id: 'audit', label: 'Audit trail', icon: IconScroll },
  { id: 'settings', label: 'Settings', icon: IconGear },
]

export default function Sidebar({ view, onNavigate, shielded, sources }) {
  return (
    <aside className="sidebar">
      <div className="wordmark">
        <div className="name">MAYA</div>
        <div className="expansion">Modular Assistant<br />for Your Actions</div>
      </div>

      <nav className="nav">
        {NAV.map(({ id, label, icon: Icon }) => (
          <button key={id} className={`nav-item ${view === id ? 'active' : ''}`}
                  onClick={() => onNavigate(id)}>
            <Icon /> {label}
          </button>
        ))}
      </nav>

      <div className="sidebar-foot">
        <div className="divider-orn">✦</div>
        <div className={`shield-pill ${shielded > 0 ? 'alert' : ''}`}
             title="MAYA's privacy shield: blocked content is never read, summarized, or stored.">
          {shielded > 0 ? <IconShieldAlert /> : <IconShield />}
          <span>
            {shielded > 0
              ? <><b>{shielded}</b> item{shielded === 1 ? '' : 's'} shielded today</>
              : <>Privacy shield <b>active</b></>}
          </span>
        </div>
        <div className="mock-note">
          <b>Prototype notice:</b> email is <b>mock sample data</b>; summaries are local
          &amp; extractive. Nothing leaves this machine.
        </div>
        {sources && (
          <div className="mock-note">{sources.indexed_files} files indexed from approved folders.</div>
        )}
      </div>
    </aside>
  )
}
