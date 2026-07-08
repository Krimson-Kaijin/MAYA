import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { listVoices, ttsAvailable, speak } from '../voice.js'

export default function SettingsView({ notify, sources, onSettingsChanged }) {
  const [s, setS] = useState(null)
  const [voices, setVoices] = useState([])

  useEffect(() => {
    api.settingsGet().then(setS)
    const t = setTimeout(() => setVoices(listVoices()), 300)  // voices load async
    return () => clearTimeout(t)
  }, [])

  const save = async (patch) => {
    const next = await api.settingsPut(patch)
    setS(next)
    onSettingsChanged?.(next)
    notify('Saved.', 'ok')
  }

  if (!s) return <div className="view"><div className="empty">Loading…</div></div>

  return (
    <div className="view" style={{ maxWidth: 780 }}>
      <div className="view-head">
        <h1>Settings</h1>
        <p>Personality, voice, and the sources MAYA is allowed to see.</p>
      </div>

      <div className="eyebrow" style={{ marginBottom: 4 }}>Personality</div>
      <div className="setting-row">
        <div>
          <div className="s-label">Wit level</div>
          <div className="s-help">How playful MAYA is allowed to be. Humor is always disabled
            around sensitive or blocked content, whatever you pick here.</div>
        </div>
        <div className="seg">
          {['off', 'subtle', 'classic'].map((v) => (
            <button key={v} className={s.wit_level === v ? 'on' : ''}
                    onClick={() => save({ wit_level: v })}>{v}</button>
          ))}
        </div>
      </div>

      <div className="eyebrow" style={{ margin: '22px 0 4px' }}>Voice</div>
      <div className="setting-row">
        <div>
          <div className="s-label">Speaking rate — {Number(s.tts_rate).toFixed(2)}×</div>
          <div className="s-help">Applied to spoken replies (browser speech synthesis).</div>
        </div>
        <input type="range" min="0.6" max="1.6" step="0.05" defaultValue={s.tts_rate}
               style={{ width: 180, accentColor: 'var(--gold)' }}
               onMouseUp={(e) => save({ tts_rate: parseFloat(e.target.value) })}
               onTouchEnd={(e) => save({ tts_rate: parseFloat(e.target.value) })} />
      </div>
      <div className="setting-row">
        <div>
          <div className="s-label">Voice</div>
          <div className="s-help">
            {ttsAvailable
              ? 'Ranked by quality — “natural” voices are neural/cloud rendered and sound far ' +
                'less robotic. On Windows, Edge offers the best en-IN voices (Neerja, Swara).'
              : 'Speech synthesis is not available in this browser.'}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <select value={s.voice_hint || 'en-IN'} onChange={(e) => save({ voice_hint: e.target.value })}
                  style={{ maxWidth: 260 }}>
            <option value="en-IN">Auto — best available (en-IN)</option>
            {voices.slice(0, 12).map((v) => (
              <option key={v.name} value={v.name}>
                {v.natural ? '✦ ' : ''}{v.name} · {v.lang}
              </option>
            ))}
          </select>
          <button className="btn btn-ghost btn-sm" disabled={!ttsAvailable}
                  onClick={() => speak(
                    'Namaskaram! I am MAYA. Shall we get your day in order? I promise to be gentle about the inbox.',
                    { rate: s.tts_rate, voiceHint: s.voice_hint })}>
            Test
          </button>
        </div>
      </div>

      <div className="eyebrow" style={{ margin: '22px 0 4px' }}>Engines & sources (read-only)</div>
      <div className="setting-row">
        <div>
          <div className="s-label">Summarizer: {s.summarizer}</div>
          <div className="s-help">Local extractive engine — deterministic, offline, selects the
            document's own sentences. An LLM can be plugged in via nlp/summarizer.py (not configured).</div>
        </div>
        <span className="badge safe">local</span>
      </div>
      <div className="setting-row">
        <div>
          <div className="s-label">Email connector: {sources?.email?.provider}</div>
          <div className="s-help">{sources?.email?.note}</div>
        </div>
        <span className="badge mock">{sources?.email?.status}</span>
      </div>
      <div className="setting-row">
        <div>
          <div className="s-label">Approved folders</div>
          <div className="s-help">
            Edit config/settings.yaml to change — MAYA never reads outside this list.
            {sources?.folders?.map((f) => (
              <div key={f.path} style={{ fontFamily: 'var(--font-mono)', fontSize: 11, marginTop: 4 }}>
                {f.path}
              </div>
            ))}
          </div>
        </div>
        <span className="badge safe">allowlist</span>
      </div>
      <div className="setting-row" style={{ borderBottom: 'none' }}>
        <div>
          <div className="s-label">Wake phrases</div>
          <div className="s-help">{sources?.voice?.wake_phrases?.map((w) => `“${w}”`).join(', ')}</div>
        </div>
      </div>
    </div>
  )
}
