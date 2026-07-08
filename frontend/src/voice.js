// Browser voice layer: Web Speech API for STT, speechSynthesis for TTS.
// PRIVACY: audio is processed by the browser's speech stack; MAYA's backend
// only ever receives the final text transcript. No audio is uploaded to it.
//
// TTS refinement: voices are quality-ranked (neural/natural cloud voices first,
// Indian-English preferred), and speech is delivered sentence-by-sentence with
// gentle rate/pitch variation so MAYA breathes instead of droning.

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

// Quality heuristic: neural/natural > cloud > named Indian voices > plain local.
function scoreVoice(v, hint = 'en-IN') {
  let s = 0
  if (v.lang === hint) s += 40
  else if (v.lang?.replace('_', '-').startsWith('en-IN')) s += 34
  else if (v.lang?.startsWith('en')) s += 12
  if (/natural|neural/i.test(v.name)) s += 30            // Edge "Online (Natural)" voices
  if (!v.localService) s += 12                           // cloud voices sound richer
  if (/neerja|swara|aditi|raveena|heera|kalpana|veena|priya/i.test(v.name)) s += 18
  if (/google/i.test(v.name)) s += 10                    // Chrome's better set
  if (/female|woman/i.test(v.name)) s += 5
  if (/espeak|compact/i.test(v.name)) s -= 25            // the truly robotic ones
  return s
}

export function pickVoice(hint = 'en-IN') {
  const voices = voiceCache.length ? voiceCache : loadVoices()
  if (!voices.length) return null
  // An exact voice name (chosen in Settings) always wins.
  const byName = voices.find((v) => v.name === hint)
  if (byName) return byName
  return [...voices].sort((a, b) => scoreVoice(b, hint) - scoreVoice(a, hint))[0]
}

// Make text read aloud like speech, not markup.
function humanize(text) {
  return text
    .replace(/\*\*|__|[`#*]/g, '')
    .replace(/✦|•|·/g, ',')
    .replace(/\s+—\s+/g, ', ')          // em-dashes become breaths
    .replace(/"|“|”/g, '')
    .replace(/\((.*?)\)/g, ', $1,')     // parentheticals get spoken pauses
    .replace(/\bSOP\b/g, 'S O P')
    .replace(/\.(md|txt|csv|pdf|docx)\b/gi, ' file')
    .replace(/\s{2,}/g, ' ')
    .trim()
}

function splitSentences(text) {
  return text.split(/(?<=[.!?])\s+/).map((s) => s.trim()).filter(Boolean)
}

let speakSession = 0   // bumped by cancel/interrupt so stale queues die

export function speak(text, { rate = 1.0, voiceHint = 'en-IN', onStart, onEnd } = {}) {
  if (!ttsAvailable || !text) { onEnd?.(); return }
  window.speechSynthesis.cancel()
  const session = ++speakSession
  const voice = pickVoice(voiceHint)
  const sentences = splitSentences(humanize(text))
  if (!sentences.length) { onEnd?.(); return }

  let started = false
  sentences.forEach((sentence, i) => {
    const u = new SpeechSynthesisUtterance(sentence)
    if (voice) u.voice = voice
    // Gentle prosody: questions lift, closings settle, middles vary slightly.
    const isQuestion = /\?$/.test(sentence)
    const isLast = i === sentences.length - 1
    u.rate = rate * (0.985 + (i % 3) * 0.015)
    u.pitch = 1.04 + (isQuestion ? 0.06 : 0) - (isLast ? 0.03 : 0) + ((i % 2) * 0.015)
    u.volume = 1
    u.onstart = () => {
      if (session !== speakSession) return
      if (!started) { started = true; onStart?.() }
    }
    if (isLast) {
      u.onend = () => { if (session === speakSession) onEnd?.() }
      u.onerror = () => { if (session === speakSession) onEnd?.() }
    }
    window.speechSynthesis.speak(u)
  })
}

// Interruption handling: anything that starts the mic calls this first.
export function stopSpeaking() {
  speakSession++
  if (ttsAvailable) window.speechSynthesis.cancel()
}

// For the Settings picker: English/Telugu voices, best first, quality-tagged.
export function listVoices(hint = 'en-IN') {
  return (voiceCache.length ? voiceCache : loadVoices())
    .filter((v) => v.lang?.startsWith('en') || v.lang?.startsWith('te'))
    .map((v) => ({
      name: v.name,
      lang: v.lang,
      score: scoreVoice(v, hint),
      natural: /natural|neural/i.test(v.name) || !v.localService,
    }))
    .sort((a, b) => b.score - a.score)
}
