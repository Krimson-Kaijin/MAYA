// Browser voice layer: Web Speech API for STT, speechSynthesis for TTS.
// PRIVACY: audio is processed by the browser's speech stack; MAYA's backend
// only ever receives the final text transcript. No audio is uploaded to it.

const SR = typeof window !== 'undefined'
  ? (window.SpeechRecognition || window.webkitSpeechRecognition)
  : null

export const sttAvailable = !!SR
export const ttsAvailable = typeof window !== 'undefined' && 'speechSynthesis' in window

export const WAKE_RE = /^\s*(hey |ok )?maya\b/i

// ---- speech to text ----------------------------------------------------------
export function listen({ continuous = false, onInterim, onFinal, onEnd, lang = 'en-IN' }) {
  if (!SR) return null
  const rec = new SR()
  rec.lang = lang
  rec.continuous = continuous
  rec.interimResults = true
  let stopped = false

  rec.onresult = (ev) => {
    let interim = ''
    for (let i = ev.resultIndex; i < ev.results.length; i++) {
      const r = ev.results[i]
      if (r.isFinal) onFinal?.(r[0].transcript.trim())
      else interim += r[0].transcript
    }
    if (interim) onInterim?.(interim.trim())
  }
  rec.onend = () => {
    if (continuous && !stopped) {
      try { rec.start() } catch { onEnd?.() }   // keep wake-mode alive
    } else onEnd?.()
  }
  rec.onerror = () => { if (!continuous) { stopped = true; onEnd?.() } }

  try { rec.start() } catch { return null }
  return () => { stopped = true; try { rec.stop() } catch { /* already stopped */ } }
}

// ---- text to speech ----------------------------------------------------------
let voiceCache = []
function loadVoices() {
  if (!ttsAvailable) return []
  voiceCache = window.speechSynthesis.getVoices()
  return voiceCache
}
if (ttsAvailable) {
  loadVoices()
  window.speechSynthesis.onvoiceschanged = loadVoices
}

export function pickVoice(hint = 'en-IN') {
  const voices = voiceCache.length ? voiceCache : loadVoices()
  if (!voices.length) return null
  const female = (v) => /female|woman|heera|swara|neerja|kalpana|veena/i.test(v.name)
  return (
    voices.find((v) => v.lang === hint && female(v)) ||
    voices.find((v) => v.lang === hint) ||
    voices.find((v) => v.lang?.startsWith('en') && female(v)) ||
    voices.find((v) => v.lang?.startsWith('en')) ||
    voices[0]
  )
}

export function speak(text, { rate = 1.0, voiceHint = 'en-IN', onStart, onEnd } = {}) {
  if (!ttsAvailable || !text) { onEnd?.(); return }
  window.speechSynthesis.cancel()
  const u = new SpeechSynthesisUtterance(text.replace(/\*\*|__|[•`#]/g, ''))
  const v = pickVoice(voiceHint)
  if (v) u.voice = v
  u.rate = rate
  u.pitch = 1.02
  u.onstart = () => onStart?.()
  u.onend = () => onEnd?.()
  u.onerror = () => onEnd?.()
  window.speechSynthesis.speak(u)
}

// Interruption handling: anything that starts the mic calls this first.
export function stopSpeaking() {
  if (ttsAvailable) window.speechSynthesis.cancel()
}

export function listVoices() {
  return (voiceCache.length ? voiceCache : loadVoices())
    .filter((v) => v.lang?.startsWith('en') || v.lang?.startsWith('te'))
    .map((v) => ({ name: v.name, lang: v.lang }))
}
