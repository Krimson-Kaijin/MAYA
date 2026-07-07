import React from 'react'

const STATUS = {
  idle: { line: null, sub: 'at your service' },
  listening: { line: 'Listening…', sub: 'speak naturally' },
  thinking: { line: 'Thinking…', sub: 'reading so you don’t have to' },
  speaking: { line: 'Speaking…', sub: 'tap the mic to interrupt' },
}

export default function Orb({ state = 'idle', tagline, interim }) {
  const s = STATUS[state] || STATUS.idle
  return (
    <div className="orb-stack">
      <div className={`orb ${state}`} role="status" aria-label={`MAYA is ${state}`}>
        <div className="ring" />
        <div className="ring inner" />
        <div className="core">
          <span className="glyph">మ</span>
        </div>
      </div>
      <div className="orb-status">
        <span className={`line ${state !== 'idle' ? 'active' : ''}`}>
          {state === 'listening' && interim ? `“${interim}”` : (s.line || tagline || '—')}
        </span>
        {state === 'listening' ? (
          <div className="waveform" aria-hidden="true">
            {Array.from({ length: 14 }).map((_, i) => (
              <span key={i} style={{ animationDelay: `${(i % 7) * 0.09}s`,
                                     animationDuration: `${0.8 + (i % 5) * 0.12}s` }} />
            ))}
          </div>
        ) : (
          <span className="sub">{s.sub}</span>
        )}
      </div>
    </div>
  )
}
