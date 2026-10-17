import { useEffect, useState } from "react"

export type HourCycle = "12h" | "24h"

export type TimePrefs = {
  hourCycle: HourCycle
  // IANA zone the user actually works in -- deliberately NOT read from the OS/
  // browser, since that can be wrong (e.g. a PC set to one country's timezone
  // while the person is physically working from another).
  myTimezone: string
  showUtc: boolean
}

const STORAGE_KEY = "allino.timePrefs"
const TIME_PREFS_EVENT = "allino:timeprefs-changed"

// Used only for the SSR render pass and before the post-mount restore effect
// runs -- never read localStorage/Intl during the initial render (hydration
// mismatch), same convention as mode/filters restoration in page.tsx.
const SSR_DEFAULT_PREFS: TimePrefs = { hourCycle: "24h", myTimezone: "UTC", showUtc: false }

function detectBrowserTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone || "UTC"
  } catch {
    return "UTC"
  }
}

export function defaultTimePrefs(): TimePrefs {
  return { hourCycle: "24h", myTimezone: detectBrowserTimezone(), showUtc: false }
}

export function loadTimePrefs(): TimePrefs {
  if (typeof window === "undefined") return SSR_DEFAULT_PREFS
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return defaultTimePrefs()
    const parsed = JSON.parse(raw) as Partial<TimePrefs>
    return {
      hourCycle: parsed.hourCycle === "12h" ? "12h" : "24h",
      myTimezone:
        typeof parsed.myTimezone === "string" && parsed.myTimezone ? parsed.myTimezone : detectBrowserTimezone(),
      showUtc: Boolean(parsed.showUtc),
    }
  } catch {
    return defaultTimePrefs()
  }
}

export function saveTimePrefs(prefs: TimePrefs): void {
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs))
  window.dispatchEvent(new Event(TIME_PREFS_EVENT))
}

export function listSupportedTimezones(): string[] {
  const withSupportedValuesOf = Intl as unknown as { supportedValuesOf?: (key: string) => string[] }
  if (typeof withSupportedValuesOf.supportedValuesOf === "function") {
    try {
      return withSupportedValuesOf.supportedValuesOf("timeZone")
    } catch {
      // fall through to the small fallback list below
    }
  }
  return Array.from(new Set([detectBrowserTimezone(), "UTC"]))
}

// Reads the persisted preference, restoring after mount (SSR-safe) and staying
// in sync with Settings -- both cross-tab ("storage") and same-tab (custom
// event, since ThreadPanel/ChannelTranscript don't remount when Settings mode
// is left, so "storage" alone would miss same-session changes).
export function useTimePrefs(): TimePrefs {
  const [prefs, setPrefs] = useState<TimePrefs>(SSR_DEFAULT_PREFS)

  useEffect(() => {
    setPrefs(loadTimePrefs())
    function reload() {
      setPrefs(loadTimePrefs())
    }
    window.addEventListener(TIME_PREFS_EVENT, reload)
    window.addEventListener("storage", reload)
    return () => {
      window.removeEventListener(TIME_PREFS_EVENT, reload)
      window.removeEventListener("storage", reload)
    }
  }, [])

  return prefs
}

// SQLite's CURRENT_TIMESTAMP columns (audit_logs.created_at etc.) come back as
// "YYYY-MM-DD HH:MM:SS" -- UTC, but with no zone marker, which `new Date()`
// would read as the browser's LOCAL time. Treat that shape as UTC.
export function parseServerTimestamp(value: string): Date {
  const naive = /^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}(\.\d+)?$/.test(value)
  return new Date(naive ? `${value.replace(" ", "T")}Z` : value)
}

function clockAt(iso: string, timeZone: string, hourCycle: HourCycle): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return "--:--"
  return d.toLocaleTimeString("en-GB", { timeZone, hour: "2-digit", minute: "2-digit", hour12: hourCycle === "12h" })
}

// Rocket.Chat only reports the DM counterpart's utcOffset as a plain number of
// hours (no IANA zone), so instead of fighting Etc/GMT's inverted sign
// convention we shift the instant ourselves and print the shifted wall-clock
// value as if it were UTC.
function clockAtOffset(iso: string, offsetHours: number, hourCycle: HourCycle): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return "--:--"
  const shifted = new Date(d.getTime() + offsetHours * 3600_000)
  return shifted.toLocaleTimeString("en-GB", { timeZone: "UTC", hour: "2-digit", minute: "2-digit", hour12: hourCycle === "12h" })
}

function dateAt(iso: string, timeZone: string): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return ""
  return d.toLocaleDateString("en-GB", { timeZone, day: "2-digit", month: "short" })
}

// Compact "03 Jul, 14:32" for tight spaces (e.g. a related-messages list row) --
// honors the format/timezone prefs but skips the "you/them/UTC" cluster.
export function formatShort(iso: string, prefs: TimePrefs): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  return `${dateAt(iso, prefs.myTimezone)}, ${clockAt(iso, prefs.myTimezone, prefs.hourCycle)}`
}

// Builds the compact "03 Jul · 14:32 you · 08:32 them · 12:32 UTC" cluster used
// everywhere an absolute timestamp is shown. counterpartOffsetHours is only
// ever known for Rocket.Chat DMs (see the /rocketchat/dm-timezone endpoint) --
// omitted (and the "them" clock skipped) everywhere else.
export function formatClockCluster(iso: string, prefs: TimePrefs, counterpartOffsetHours?: number | null): string {
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso

  const clocks: { label: string; text: string }[] = [{ label: "you", text: clockAt(iso, prefs.myTimezone, prefs.hourCycle) }]
  if (typeof counterpartOffsetHours === "number") {
    clocks.push({ label: "them", text: clockAtOffset(iso, counterpartOffsetHours, prefs.hourCycle) })
  }
  if (prefs.showUtc) {
    clocks.push({ label: "UTC", text: clockAt(iso, "UTC", prefs.hourCycle) })
  }

  const multi = clocks.length > 1
  const clockStr = clocks.map((c) => (multi ? `${c.text} ${c.label}` : c.text)).join(" · ")
  return `${dateAt(iso, prefs.myTimezone)} · ${clockStr}`
}
