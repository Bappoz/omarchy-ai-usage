.pragma library

// Pure transition logic shared by the store and behavioral tests.
function validSession(s) {
  return s && /^[a-f0-9]{24}$/.test(String(s.id))
    && ["claude", "codex"].indexOf(s.providerId) >= 0
    && ["busy", "waiting", "success", "idle", "unknown"].indexOf(s.state) >= 0
    && typeof s.name === "string" && s.name.length <= 80
    && typeof s.detail === "string" && s.detail.length <= 80
    && (s.pid === null || (Number.isInteger(s.pid) && s.pid > 0))
    && (s.started === null || /^[0-9]+$/.test(String(s.started)))
}

function absorb(previous, sessions) {
  var next = ({})
  var events = []
  for (var i = 0; i < sessions.length; i++) {
    var s = sessions[i]
    var key = s.providerId + ":" + s.id
    next[key] = s.state
    // No launch announcements, no events for vanished sessions, no completion
    // inferred from missing metadata or from a question being answered.
    if (previous && previous[key] === "busy") {
      if (s.state === "waiting") events.push({ session: s, reason: "blocked" })
      else if (s.state === "success" || s.state === "idle") events.push({ session: s, reason: "finished" })
    }
  }
  return { previous: next, events: events }
}

function summary(sessions, providerId) {
  var found = sessions.filter(function(s) { return s.providerId === providerId })
  var state = "idle"
  if (found.some(function(s) { return s.state === "waiting" })) state = "waiting"
  else if (found.some(function(s) { return s.state === "busy" })) state = "busy"
  else if (found.some(function(s) { return s.state === "success" })) state = "success"
  return { state: state, sessions: found }
}

// Thresholds latch for the whole window. A fluctuation below 80 does not
// rearm them. Only an observed reset boundary advancing can start a new cycle.
function quotaCrossings(previous, snapshot, nowMs) {
  if (!snapshot || ["ACTIVE", "RATE_LIMITED"].indexOf(snapshot.status) < 0 || snapshot.stale) {
    return { previous: previous, thresholds: [] }
  }
  var windows = Array.isArray(snapshot.windows) ? snapshot.windows : []
  var window = windows.filter(function(w) { return w.id === snapshot.headlineWindowId })[0]
  if (!window || typeof window.usedPercent !== "number" || !isFinite(window.usedPercent)) {
    return { previous: previous, thresholds: [] }
  }
  var reset = Date.parse(String(window.resetAt || ""))
  var newCycle = previous && previous.windowId === window.id
    && isFinite(reset) && isFinite(previous.reset) && reset > previous.reset
    && nowMs >= previous.reset
  var next = previous && previous.windowId === window.id && !newCycle
    ? { windowId: previous.windowId, reset: previous.reset, high: previous.high }
    : { windowId: window.id, reset: reset, high: 0 }
  var crossed = []
  var used = Math.max(0, Math.min(100, window.usedPercent))
  var seeded = previous && previous.windowId === window.id
  if (seeded && next.high < 80 && used >= 80) crossed.push(80)
  if (seeded && next.high < 100 && used >= 100) crossed.push(100)
  next.high = Math.max(next.high, used)
  return { previous: next, thresholds: crossed }
}

function resetCopy(window, nowMs, style) {
  if (!window) return ""
  var reset = Date.parse(String(window.resetAt || ""))
  if (!isFinite(reset)) return String(window.resetCopy || "")
  var seconds = Math.max(0, Math.ceil((reset - nowMs) / 1000))
  if (seconds === 0) return "Reset due"
  if (style === "date" && seconds >= 3600) return "Resets " + new Date(reset).toLocaleString()
  if (seconds < 60) return "Resets in " + seconds + "s"
  var minutes = Math.ceil(seconds / 60)
  if (minutes < 60) return "Resets in " + minutes + " min"
  var hours = Math.floor(minutes / 60)
  if (hours < 24) return "Resets in " + hours + "h " + minutes % 60 + " min"
  return "Resets in " + Math.floor(hours / 24) + "d " + hours % 24 + "h"
}

function providerOrder(value) {
  var known = ["claude", "codex", "antigravity", "cursor"]
  var result = []
  if (Array.isArray(value)) value.forEach(function(id) {
    if (known.indexOf(id) >= 0 && result.indexOf(id) < 0) result.push(id)
  })
  known.forEach(function(id) { if (result.indexOf(id) < 0) result.push(id) })
  return result
}
