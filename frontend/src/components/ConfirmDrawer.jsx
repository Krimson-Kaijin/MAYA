import React from 'react'
import { IconShieldAlert } from './icons.jsx'

// The action confirmation drawer: shows the EXACT operation before anything
// executes. Nothing with side effects happens until "Approve" (or a spoken
// "confirm") — cancel and the file system stays untouched.
export default function ConfirmDrawer({ action, onResolve, busy }) {
  if (!action) return null
  return (
    <>
      <div className="drawer-scrim" onClick={() => !busy && onResolve(false)} />
      <div className="drawer" role="alertdialog" aria-label="Confirm action">
        <div className="d-head">
          <IconShieldAlert />
          <h3>MAYA needs your confirmation</h3>
        </div>
        <div className="d-desc">{action.description}</div>
        <div className="d-exact">
          {action.action_type}({JSON.stringify(action.params, null, 1).replace(/\n\s*/g, ' ')})
        </div>
        <div className="d-foot">
          <span className="d-expiry">
            expires in {Math.max(1, Math.round((action.expires_in ?? 180) / 60))} min ·
            you can also say “confirm” or “cancel”
          </span>
          <button className="btn btn-ghost" disabled={busy} onClick={() => onResolve(false)}>Cancel</button>
          <button className="btn btn-gold" disabled={busy} onClick={() => onResolve(true)}>Approve</button>
        </div>
      </div>
    </>
  )
}
