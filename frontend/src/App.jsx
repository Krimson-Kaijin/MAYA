import React, { useCallback, useEffect, useRef, useState } from 'react'
import { api } from './api.js'
import { listen, speak, stopSpeaking, WAKE_RE, sttAvailable } from './voice.js'
import Sidebar from './components/Sidebar.jsx'
import CommandCenter from './components/CommandCenter.jsx'
import RightRail from './components/RightRail.jsx'
import ConfirmDrawer from './components/ConfirmDrawer.jsx'
import FilesView from './components/FilesView.jsx'
import InboxView from './components/InboxView.jsx'
import MemoryView from './components/MemoryView.jsx'
import AuditView from './components/AuditView.jsx'
import SettingsView from './components/SettingsView.jsx'

const SESSION = `ui-${Math.random().toString(36).slice(2, 9)}`

export default function App() {
  const [view, setView] = useState('command')
  const [messages, setMessages] = useState([])
  const [mayaState, setMayaState] = useState('idle')      // idle|listening|thinking|speaking
  const [thinking, setThinking] = useState(false)
  const [interim, setInterim] = useState('')
  const [pending, setPending] = useState(null)
  const [drawerBusy, setDrawerBusy] = useState(false)
  const [toast, setToast] = useState(null)
  const [meta, setMeta] = useState(null)
  const [sources, setSources] = useState(null)
  const [glance, setGlance] = useState(null)
  const [feed, setFeed] = useState([])
  const [settings, setSettings] = useState({ tts_rate: 1.0, voice_hint: 'en-IN' })
  const [speakOn, setSpeakOn] = useState(false)
  const [wakeOn, setWakeOn] = useState(false)
  const [micLive, setMicLive] = useState(false)

  const stopListenRef = useRef(null)
  const wakeStopRef = useRef(null)
  const settingsRef = useRef(settings)
  settingsRef.current = settings

  const notify = useCallback((text, kind = 'ok') => {
    setToast({ text, kind })
    setTimeout(() => setToast(null), 4200)
  }, [])

  const refreshFeed = useCallback(async () => {
    try {
      const [a, s] = await Promise.all([api.audit(12), api.sources()])
      setFeed(a.entries)
      setSources(s)
    } catch { /* backend not up yet */ }
  }, [])

  // Boot: meta, settings, sources, a quiet briefing for the glance panel.
  useEffect(() => {
    (async () => {
      try {
        const [m, st] = await Promise.all([api.meta(), api.settingsGet()])
        setMeta(m); setSettings(st)
        await refreshFeed()
        const b = await api.briefing(SESSION)
        const card = b.cards?.find((c) => c.type === 'briefing')
        if (card) {
          setGlance({
            urgent: card.urgent?.length ?? 0,
            actions: (card.action_emails?.length ?? 0) + (card.doc_tasks?.items?.length ?? 0),
            meetings: card.meetings?.length ?? 0,
            top: card.suggestions?.[0],
            shielded: card.shielded_count ?? 0,
          })
        }
        await refreshFeed()
      } catch (e) {
        notify(`Backend unreachable: ${e.message}`, 'err')
      }
    })()
  }, [refreshFeed, notify])

  // ---- core send pipeline ----------------------------------------------------
  const send = useCallback(async (text, mode = 'chat') => {
    stopSpeaking()
    setMessages((ms) => [...ms, { role: 'user', text, mode }])
    setThinking(true); setMayaState('thinking'); setView('command')
    try {
      const r = await api.chat(text, mode, SESSION)
      setThinking(false)
      setMessages((ms) => [...ms, {
        role: 'maya', text: r.reply, cards: r.cards,
        accessed: r.accessed, privacy: r.privacy,
      }])
      if (r.pending_action && r.pending_action.status === 'pending') setPending(r.pending_action)
      else if (r.intent === 'confirm') setPending(null)
      refreshFeed()
      if ((speakOn || mode === 'voice') && r.speak) {
        setMayaState('speaking')
        speak(r.speak, {
          rate: settingsRef.current.tts_rate,
          voiceHint: settingsRef.current.voice_hint,
          onEnd: () => setMayaState('idle'),
        })
      } else setMayaState('idle')
    } catch (e) {
      setThinking(false); setMayaState('idle')
      notify(`That didn't reach MAYA: ${e.message}`, 'err')
    }
  }, [notify, refreshFeed, speakOn])

  // ---- push-to-talk -----------------------------------------------------------
  const onMic = useCallback(() => {
    if (micLive) { stopListenRef.current?.(); return }
    stopSpeaking()                                  // interruption handling
    setMayaState('listening'); setMicLive(true); setInterim('')
    const stop = listen({
      onInterim: setInterim,
      onFinal: (t) => { setInterim(''); send(t, 'voice') },
      onEnd: () => { setMicLive(false); setInterim(''); setMayaState((s) => (s === 'listening' ? 'idle' : s)) },
    })
    if (!stop) { setMicLive(false); setMayaState('idle'); notify('Voice input unavailable in this browser.', 'err') }
    stopListenRef.current = stop
  }, [micLive, send, notify])

  // ---- wake-phrase mode --------------------------------------------------------
  const toggleWake = useCallback(() => {
    if (!sttAvailable) { notify('Wake phrase needs Chrome/Edge speech recognition.', 'err'); return }
    if (wakeOn) { wakeStopRef.current?.(); wakeStopRef.current = null; setWakeOn(false); return }
    const stop = listen({
      continuous: true,
      onFinal: (t) => {
        if (WAKE_RE.test(t)) { stopSpeaking(); send(t, 'voice') }
      },
      onEnd: () => setWakeOn(false),
    })
    if (stop) { wakeStopRef.current = stop; setWakeOn(true); notify('Wake mode on — say “Maya, …”', 'ok') }
  }, [wakeOn, send, notify])

  // ---- confirmation drawer -------------------------------------------------------
  const resolvePending = useCallback(async (approve) => {
    if (!pending) return
    setDrawerBusy(true)
    try {
      const out = await api.confirm(pending.id, approve)
      const a = out.action || {}
      const line = out.status === 'executed'
        ? `Done — ${a.description}. ${a.result || ''}`
        : out.status === 'failed' ? `That failed: ${out.error}`
        : 'Cancelled — nothing was changed.'
      setMessages((ms) => [...ms, { role: 'maya', text: line }])
      notify(line, out.status === 'executed' ? 'ok' : out.status === 'failed' ? 'err' : 'ok')
      refreshFeed()
    } catch (e) { notify(e.message, 'err') }
    setPending(null); setDrawerBusy(false)
  }, [pending, notify, refreshFeed])

  // Card-level handlers reachable from chat cards.
  const handlers = {
    onSummarize: async (path) => {
      const r = await api.summarize(path, 'medium')
      setMessages((ms) => [...ms, { role: 'maya', text: r.reply, cards: r.cards, accessed: r.accessed }])
    },
    onSendDraft: async (draft) => {
      const out = await api.sendDraft(draft)
      if (out.status === 'pending') setPending(out.action)
    },
    onDraftReply: (item) => send(`draft a reply to ${item.sender_name}`),
  }

  return (
    <div className="shell">
      <div className="aurora" aria-hidden="true"><i className="a1" /><i className="a2" /><i className="a3" /></div>
      <Sidebar view={view} onNavigate={setView}
               shielded={glance?.shielded ?? 0} sources={sources} />

      <div className="main">
        <div className="stage view-shell" key={view}>
          {view === 'command' && (
            <CommandCenter
              messages={messages} mayaState={mayaState} thinking={thinking}
              tagline={meta?.tagline} interim={interim}
              onSend={send} onMic={onMic} micLive={micLive}
              wakeOn={wakeOn} onToggleWake={toggleWake}
              speakOn={speakOn} onToggleSpeak={() => { setSpeakOn(!speakOn); if (speakOn) stopSpeaking() }}
              handlers={handlers}
            />
          )}
          {view === 'files' && <FilesView notify={notify} />}
          {view === 'inbox' && <InboxView notify={notify} onPending={setPending} />}
          {view === 'memory' && <MemoryView notify={notify} />}
          {view === 'audit' && <AuditView />}
          {view === 'settings' && (
            <SettingsView notify={notify} sources={sources} onSettingsChanged={setSettings} />
          )}
        </div>
        {view === 'command' && <RightRail glance={glance} sources={sources} feed={feed} />}
      </div>

      <ConfirmDrawer action={pending} onResolve={resolvePending} busy={drawerBusy} />
      {toast && <div className={`toast ${toast.kind}`}>{toast.text}</div>}
    </div>
  )
}
