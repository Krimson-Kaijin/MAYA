// Tiny, honest charts — no library. Colors are the validated chart palette
// from base.css (dataviz six-checks, dark surface): fixed bucket order,
// 2px surface gaps between segments, legend so identity is never color-alone,
// hatch texture on "shielded" as secondary encoding.
import React from 'react'

export const BUCKET_META = [
  ['urgent', 'Urgent', 'var(--chart-urgent)'],
  ['action', 'Action', 'var(--chart-action)'],
  ['meetings', 'Meetings', 'var(--chart-meetings)'],
  ['follow_ups', 'Follow-ups', 'var(--chart-followups)'],
  ['noise', 'Noise', 'var(--chart-noise)'],
  ['shielded', 'Shielded', 'var(--chart-shielded)'],
]

export const bucketColor = (key) =>
  (BUCKET_META.find(([k]) => k === key) || [])[2] || 'var(--ink-faint)'

/** One slim segmented bar: how today's inbox splits across buckets. */
export function DistributionBar({ counts }) {
  const present = BUCKET_META.filter(([k]) => (counts[k] || 0) > 0)
  const total = present.reduce((s, [k]) => s + counts[k], 0)
  if (!total) return null
  return (
    <div className="segbar-wrap" role="img"
         aria-label={present.map(([k, label]) => `${label} ${counts[k]}`).join(', ')}>
      <div className="segbar">
        {present.map(([k, label, color]) => (
          <i key={k}
             className={k === 'shielded' ? 'hatch' : ''}
             style={{ flexGrow: counts[k], background: k === 'shielded' ? undefined : color }}
             title={`${label}: ${counts[k]}`} />
        ))}
      </div>
      <div className="seglegend">
        {present.map(([k, label, color]) => (
          <span className="lg" key={k}>
            <i className="swatch" style={{
              background: color,
              backgroundImage: k === 'shielded'
                ? 'repeating-linear-gradient(45deg, rgba(10,6,20,.55) 0 2px, transparent 2px 4px)'
                : undefined,
            }} />
            {label} <b>{counts[k]}</b>
          </span>
        ))}
      </div>
    </div>
  )
}

/** Two magnitudes on one shared scale (e.g. document sizes in a comparison). */
export function DuoBar({ rows, unit = '' }) {
  const max = Math.max(...rows.map((r) => r.value), 1)
  return (
    <div className="duobar">
      {rows.map((r) => (
        <div className="db-row" key={r.label}>
          <span className="db-label" title={r.label}>{r.label}</span>
          <span className="db-track">
            <span className="db-fill"
                  style={{ width: `${(r.value / max) * 100}%`, background: r.color }} />
          </span>
          <span className="db-val">{r.value.toLocaleString('en-IN')}{unit}</span>
        </div>
      ))}
    </div>
  )
}
