.pragma library

var AUTO = "auto"
var PRESETS = ["auto", "#00ff88", "#7c9cff", "#38bdf8", "#c084fc", "#ff5d8f", "#ffb347", "#ffffff"]

function validAccent(value) {
  var text = String(value || "").trim().toLowerCase()
  return /^#[0-9a-f]{6}$/.test(text) ? text : AUTO
}

// "auto" keeps the CodeNotch green/yellow/orange scale; any hex replaces it.
function usageColor(used, accent) {
  if (used === null || used === undefined) return "#808080"
  var custom = validAccent(accent)
  if (custom !== AUTO) return custom
  return used < 50 ? "#00ff88" : (used < 70 ? "#f2ff00" : "#ff3f00")
}

function usedPercent(window) {
  if (window && typeof window.usedPercent === "number" && isFinite(window.usedPercent)) {
    return Math.max(0, Math.min(100, window.usedPercent))
  }
  if (window && typeof window.remainingPercent === "number" && isFinite(window.remainingPercent)) {
    return Math.max(0, Math.min(100, 100 - window.remainingPercent))
  }
  return null
}

// Fraction of the window already elapsed, or null when the contract carries no
// reset time or duration (DERIVED/MANUAL windows may omit them).
function elapsedFraction(window, nowMs) {
  if (!window || !window.resetAt || !(window.durationMinutes > 0)) return null
  var reset = new Date(String(window.resetAt)).getTime()
  if (isNaN(reset)) return null
  var total = window.durationMinutes * 60000
  return Math.max(0, Math.min(1, 1 - (reset - nowMs) / total))
}

function formatSpan(minutes) {
  var m = Math.max(1, Math.round(minutes))
  if (m < 60) return m + " min"
  if (m < 24 * 60) {
    var rest = m % 60
    return Math.floor(m / 60) + "h" + (rest > 0 ? " " + rest + " min" : "")
  }
  var days = Math.floor(m / (24 * 60))
  var hours = Math.round((m % (24 * 60)) / 60)
  return days + "d" + (hours > 0 ? " " + hours + "h" : "")
}

// Linear burn-rate projection. Needs 3% of the window elapsed to avoid
// extrapolating from noise. Returns { tone, text } or null.
function pace(window, nowMs) {
  var used = usedPercent(window)
  var elapsed = elapsedFraction(window, nowMs)
  if (used === null || elapsed === null) return null
  if (used >= 100) return { tone: "over", text: "Limit reached" }
  if (elapsed < 0.03 || used <= 0) return { tone: "ok", text: "Not enough usage to project" }

  var elapsedMinutes = elapsed * window.durationMinutes
  var minutesToLimit = (100 - used) / (used / elapsedMinutes)
  var minutesToReset = (1 - elapsed) * window.durationMinutes
  // 3% margin so an exactly-on-pace burn does not flicker between verdicts.
  if (minutesToLimit < minutesToReset * 0.97) {
    return { tone: "over", text: "At this pace the limit hits in ~" + formatSpan(minutesToLimit) }
  }
  return { tone: used / 100 > elapsed + 0.1 ? "warn" : "ok", text: "On pace to last until reset" }
}
