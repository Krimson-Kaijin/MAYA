import React, { useEffect, useRef, useState } from 'react'
import Orb from './Orb.jsx'
import NeuralMap from './NeuralMap.jsx'
import CardRenderer from './Cards.jsx'
import { IconMic, IconSend } from './icons.jsx'
import { sttAvailable } from '../voice.js'

function Message({ m, handlers }) {
  return (
    <div className={`msg ${m.role}`}>
      <span className="who">
        {m.role === 'user' ? (m.mode === 'voice' ? 'you · voice' : 'you') : 'maya'}
      </span>
      {m.text && <div className="bubble">{m.text}</div>}
      {m.cards?.map((c, i) => <CardRenderer key={i} card={c} handlers={handlers} />)}
      {m.accessed?.length > 0 && (
        <div className="accessed">
          <span className="chip">accessed:</span>
          {m.accessed.map((a, i) => (
            <span className="chip" key={i}><b>{a.kind}</b> {a.label}{a.note ? ` — ${a.note}` : ''}</span>
          ))}
        </div>
      )}
    </div>
  )
}

const SUGGESTIONS = [
  ['What should I prioritize today?', 'gold'],
  ['Summarize today’s important emails', 'iris'],
  ['Find the latest logistics SOP', 'teal'],
  ['Compare the logistics SOP v2 and v3', 'rose'],
]

function Greeting() {
  const now = new Date()
  const hour = now.getHours()
  const word = hour < 12 ? 'Good morning.' : hour < 17 ? 'Good afternoon.' : 'Good evening.'
  const date = now.toLocaleDateString('en-IN', {
    weekday: 'long', day: 'numeric', month: 'long',
  })
  return (
    <div className="hero hero-compact">
      <div className="hero-date">{date}</div>
      <h2 className="hero-greeting">{word}</h2>
    </div>
  )
}

export default function CommandCenter({
  messages, mayaState, tagline, interim, onSend, onMic, micLive,
  wakeOn, onToggleWake, speakOn, onToggleSpeak, handlers, thinking,
  neuralStats, onDive,
}) {
  const [text, setText] = useState('')
  const streamRef = useRef(null)
  const idle = messages.length === 0 && !thinking

  useEffect(() => {
    const el = streamRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [messages, thinking])

  const submit = () => {
    const t = text.trim()
    if (!t) return
    setText('')
    onSend(t, 'chat')
  }

  return (
    <div className="command-wrap">
      <div className="chat-col">
        {idle ? (
          <>
            <Greeting />
            <NeuralMap orbState={mayaState} tagline={tagline} interim={interim}
                       stats={neuralStats} onDive={onDive} />
            <div className="hero-pills hero-pills-row">
              {SUGGESTIONS.map(([s, accent]) => (
                <button key={s} className="pill" data-accent={accent}
                        onClick={() => onSend(s, 'chat')}>
                  <span className="p-dot" /> {s}
                </button>
              ))}
            </div>
          </>
        ) : (
          <>
            <Orb state={mayaState} tagline={tagline} interim={interim} />
            <div className="chat-stream" ref={streamRef}>
              {messages.map((m, i) => <Message key={i} m={m} handlers={handlers} />)}
              {thinking && (
                <div className="msg maya">
                  <span className="who">maya</span>
                  <div className="bubble"><span className="thinking-dots"><i /><i /><i /></span></div>
                </div>
              )}
            </div>
          </>
        )}

        <div className="composer">
          <div className="composer-row">
            <button
              className={`mic-btn ${micLive ? 'live' : ''}`}
              onClick={onMic}
              disabled={!sttAvailable}
              title={sttAvailable
                ? (micLive ? 'Stop listening' : 'Push to talk')
                : 'Voice input needs Chrome/Edge (Web Speech API)'}
            >
              <IconMic />
            </button>
            <input
              value={text}
              placeholder='Type a command — or say “Maya, …”'
              onChange={(e) => setText(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && submit()}
            />
            <button className="btn btn-gold" onClick={submit}><IconSend style={{ width: 15 }} /></button>
          </div>
          <div className="hint">
            <span className={`toggle ${wakeOn ? 'on' : ''}`} onClick={onToggleWake}
                  title={sttAvailable ? 'Continuously listen for “Maya, …”' : 'Needs Chrome/Edge'}>
              <span className="dot" /> wake phrase {wakeOn ? 'on' : 'off'}
            </span>
            <span className={`toggle ${speakOn ? 'on' : ''}`} onClick={onToggleSpeak}>
              <span className="dot" /> spoken replies {speakOn ? 'on' : 'off'}
            </span>
            <span style={{ marginLeft: 'auto' }}>
              audio stays in your browser — the backend only sees text
            </span>
          </div>
        </div>
      </div>
    </div>
  )
}
