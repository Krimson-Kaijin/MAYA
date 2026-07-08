// Hand-drawn inline icon set (stroke style, 24 viewBox) — no icon library.
import React from 'react'

const I = ({ children, ...p }) => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
       strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...p}>
    {children}
  </svg>
)

export const IconSpark = (p) => (
  <I {...p}><path d="M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z" /></I>
)
export const IconFolder = (p) => (
  <I {...p}><path d="M3 7a2 2 0 012-2h4l2 2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2z" /></I>
)
export const IconMail = (p) => (
  <I {...p}><rect x="3" y="5" width="18" height="14" rx="2" /><path d="M3 7l9 6 9-6" /></I>
)
export const IconBrain = (p) => (
  <I {...p}><path d="M12 4a3 3 0 00-3 3v9a3 3 0 003 3m0-15a3 3 0 013 3v9a3 3 0 01-3 3m0-15v15" />
    <path d="M9 8H7a2 2 0 000 4h2m6-4h2a2 2 0 010 4h-2" /></I>
)
export const IconScroll = (p) => (
  <I {...p}><path d="M6 4h12v13a3 3 0 01-3 3H6a2 2 0 01-2-2V6a2 2 0 012-2z" /><path d="M9 9h6M9 13h4" /></I>
)
export const IconGear = (p) => (
  <I {...p}><circle cx="12" cy="12" r="3" />
    <path d="M12 2v3m0 14v3M4.9 4.9l2.1 2.1m10 10l2.1 2.1M2 12h3m14 0h3M4.9 19.1l2.1-2.1m10-10l2.1-2.1" /></I>
)
export const IconShield = (p) => (
  <I {...p}><path d="M12 3l7 3v5c0 4.5-3 8.2-7 10-4-1.8-7-5.5-7-10V6z" /><path d="M9.5 12l1.8 1.8 3.4-3.6" /></I>
)
export const IconShieldAlert = (p) => (
  <I {...p}><path d="M12 3l7 3v5c0 4.5-3 8.2-7 10-4-1.8-7-5.5-7-10V6z" /><path d="M12 8.5V12m0 3.2v.1" /></I>
)
export const IconMic = (p) => (
  <I {...p}><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0014 0M12 18v3" /></I>
)
export const IconSend = (p) => (
  <I {...p}><path d="M21 3L10 14M21 3l-7 18-3-8-8-3z" /></I>
)
export const IconLock = (p) => (
  <I {...p}><rect x="5" y="11" width="14" height="9" rx="2" /><path d="M8 11V7a4 4 0 018 0v4" /></I>
)
export const IconTrash = (p) => (
  <I {...p}><path d="M4 7h16M9 7V5a1 1 0 011-1h4a1 1 0 011 1v2m3 0l-1 13a1 1 0 01-1 1H8a1 1 0 01-1-1L6 7" /></I>
)
export const IconClock = (p) => (
  <I {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></I>
)
export const IconCompare = (p) => (
  <I {...p}><path d="M10 4H6a2 2 0 00-2 2v12a2 2 0 002 2h4m4-16h4a2 2 0 012 2v12a2 2 0 01-2 2h-4M12 2v20" /></I>
)
export const IconWand = (p) => (
  <I {...p}><path d="M15 4l1 2 2 1-2 1-1 2-1-2-2-1 2-1zM4 20L14 10m4 4l1 1.6 1.6 1-1.6 1-1 1.6-1-1.6-1.6-1 1.6-1z" /></I>
)
export const IconRefresh = (p) => (
  <I {...p}><path d="M20 12a8 8 0 11-2.3-5.6M20 4v4h-4" /></I>
)
export const IconCheck = (p) => (
  <I {...p}><path d="M4 12.5l5 5L20 6.5" /></I>
)
export const IconX = (p) => (
  <I {...p}><path d="M6 6l12 12M18 6L6 18" /></I>
)
export const IconEye = (p) => (
  <I {...p}><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6-10-6-10-6z" /><circle cx="12" cy="12" r="2.6" /></I>
)
