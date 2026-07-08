// The Neural Atlas — MAYA's idle home. Every section of the app is a neuron
// wired to the core orb by living synapses: pulses travel the wires, nodes
// float on their own depth plane, and the whole field tilts gently with the
// pointer (parallax). Click a neuron to dive into that section.
//
// Deliberately legible: every node carries an icon, a plain-English label,
// and a live stat — spatial navigation, zero guesswork. The sidebar still
// works; this is the fast, delightful path.
import React, { useEffect, useRef, useState } from 'react'
import Orb from './Orb.jsx'
import { IconFolder, IconMail, IconSpark, IconBrain, IconScroll, IconGear } from './icons.jsx'

const NODES = [
  { id: 'files',    label: 'Files',    icon: IconFolder, accent: 'teal',  x: 16, y: 24 },
  { id: 'inbox',    label: 'Inbox',    icon: IconMail,   accent: 'iris',  x: 84, y: 24 },
  { id: 'briefing', label: 'Briefing', icon: IconSpark,  accent: 'gold',  x: 8,  y: 62 },
  { id: 'memory',   label: 'Memory',   icon: IconBrain,  accent: 'mint',  x: 92, y: 62 },
  { id: 'audit',    label: 'Audit',    icon: IconScroll, accent: 'coral', x: 26, y: 90 },
  { id: 'settings', label: 'Settings', icon: IconGear,   accent: 'rose',  x: 74, y: 90 },
]

const ACCENT_HEX = {
  teal: '#22c8b7', iris: '#a08dff', gold: '#f2b84b',
  mint: '#52d8a2', coral: '#ff8663', rose: '#ff5d8f',
}

const CX = 50, CY = 46            // the orb's home in map coordinates (%)
const VW = 1000, VH = 640         // svg viewBox

function synapsePath(x, y) {
  const x1 = CX * 10, y1 = CY * 6.4
  const x2 = x * 10, y2 = y * 6.4
  // control point: midpoint eased toward the vertical of the core → soft arc
  const mx = (x1 + x2) / 2 + (x1 - x2) * 0.18
  const my = (y1 + y2) / 2 + 26
  return `M ${x1} ${y1} Q ${mx} ${my} ${x2} ${y2}`
}

export default function NeuralMap({ orbState, tagline, interim, stats = {}, onDive }) {
  const mapRef = useRef(null)
  const raf = useRef(0)
  const [diving, setDiving] = useState(null)
  const [reduced] = useState(() =>
    typeof window !== 'undefined' &&
    window.matchMedia?.('(prefers-reduced-motion: reduce)')?.matches)

  // Pointer parallax: three depth planes read --px/--py from the container.
  useEffect(() => {
    const el = mapRef.current
    if (!el || reduced) return undefined
    const onMove = (e) => {
      cancelAnimationFrame(raf.current)
      raf.current = requestAnimationFrame(() => {
        const r = el.getBoundingClientRect()
        const px = ((e.clientX - r.left) / r.width - 0.5) * 2   // -1 … 1
        const py = ((e.clientY - r.top) / r.height - 0.5) * 2
        el.style.setProperty('--px', px.toFixed(3))
        el.style.setProperty('--py', py.toFixed(3))
      })
    }
    const onLeave = () => { el.style.setProperty('--px', 0); el.style.setProperty('--py', 0) }
    el.addEventListener('mousemove', onMove)
    el.addEventListener('mouseleave', onLeave)
    return () => {
      cancelAnimationFrame(raf.current)
      el.removeEventListener('mousemove', onMove)
      el.removeEventListener('mouseleave', onLeave)
    }
  }, [reduced])

  const dive = (id) => {
    if (diving) return
    setDiving(id)
    setTimeout(() => onDive(id), 380)   // let the zoom read before switching
  }

  return (
    <div className={`neural-map ${diving ? 'diving' : ''}`} ref={mapRef}>
      {/* depth plane 1 — synapses */}
      <svg className="np-wires" viewBox={`0 0 ${VW} ${VH}`} preserveAspectRatio="none" aria-hidden="true">
        {NODES.map((n, i) => {
          const d = synapsePath(n.x, n.y)
          const hex = ACCENT_HEX[n.accent]
          return (
            <g key={n.id} className={diving && diving !== n.id ? 'wire-dim' : ''}>
              <path d={d} className="synapse" style={{ stroke: hex }} />
              <path d={d} className="synapse-flow" style={{ stroke: hex }} />
              {!reduced && (
                /* begin=0 keeps the dot on its path from the first frame; the
                   differing durations desynchronize the pulses over time */
                <circle r="3.2" className="pulse" style={{ fill: hex }}>
                  <animateMotion dur={`${4.2 + i * 0.7}s`} begin="0s"
                                 repeatCount="indefinite" path={d} />
                </circle>
              )}
            </g>
          )
        })}
      </svg>

      {/* depth plane 2 — the core */}
      <div className="np-core">
        <Orb state={orbState} tagline={tagline} interim={interim} />
      </div>

      {/* depth plane 3 — neurons */}
      <div className="np-nodes">
        {NODES.map((n, i) => {
          const Icon = n.icon
          return (
            <button
              key={n.id}
              className={`neuron ${diving === n.id ? 'dive-target' : ''} ${diving && diving !== n.id ? 'dive-away' : ''}`}
              data-accent={n.accent}
              style={{ left: `${n.x}%`, top: `${n.y}%`, animationDelay: `${i * 0.55}s`,
                       animationDuration: `${5.6 + (i % 3) * 1.3}s` }}
              onClick={() => dive(n.id)}
              aria-label={`Open ${n.label}`}
            >
              <span className="n-ring" aria-hidden="true" />
              <span className="n-body">
                <Icon />
                <span className="n-label">{n.label}</span>
                <span className="n-stat">{stats[n.id] || '—'}</span>
              </span>
            </button>
          )
        })}
      </div>

      <div className="np-caption">Your workspace, mapped — click a node to dive in</div>
    </div>
  )
}
