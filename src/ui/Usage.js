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

var PROVIDER_TINTS = { claude: "#d97757", codex: "#74aa9c" }

// Charts and model shares take the custom accent when set, otherwise the
// provider's own tint (the usage-threshold scale only makes sense for quotas).
function chartColor(providerId, accent) {
  var custom = validAccent(accent)
  if (custom !== AUTO) return custom
  return PROVIDER_TINTS[providerId] || "#00ff88"
}

function compactNumber(value) {
  var n = Number(value)
  if (!isFinite(n) || n < 0) return "—"
  var units = ["", "K", "M", "B"], i = 0
  while (n >= 999.5 && i < units.length - 1) { n /= 1000; i++ }
  var text = i === 0 || n >= 10 ? String(Math.round(n)) : String(Math.round(n * 10) / 10)
  return text + units[i]
}

// "claude-sonnet-5-5" -> "Sonnet 5.5", "gpt-6-luna" -> "GPT-6 Luna".
function modelLabel(name) {
  var parts = String(name || "").split("-").filter(function(part) { return part.length > 0 })
  if (parts[0] === "claude") parts.shift()
  while (parts.length > 1 && /^\d{8}$/.test(parts[parts.length - 1])) parts.pop()
  var out = []
  for (var i = 0; i < parts.length; i++) {
    var part = parts[i]
    if (/^\d{1,2}$/.test(part)) {
      var version = part
      while (i + 1 < parts.length && /^\d{1,2}$/.test(parts[i + 1])) { version += "." + parts[i + 1]; i++ }
      out.push(version)
    } else {
      out.push(part === "gpt" ? "GPT" : part.charAt(0).toUpperCase() + part.slice(1))
    }
  }
  var label = out.join(" ")
  return label.indexOf("GPT ") === 0 ? "GPT-" + label.slice(4) : (label || "Unknown")
}

function fmt(n) { return Math.round(n * 100) / 100 }

// Smooth (Catmull-Rom -> cubic Bezier) area/line paths for a sparkline. Control
// points are clamped to the plot so the curve never dips under the baseline.
function smoothPath(values, width, height) {
  var count = values.length
  if (count < 2 || !(width > 0) || !(height > 0)) return { line: "", area: "", points: [] }
  var max = 1
  for (var i = 0; i < count; i++) max = Math.max(max, Number(values[i]) || 0)
  var top = 3, bottom = height - 1.5
  var points = []
  for (i = 0; i < count; i++) {
    points.push({ x: width * i / (count - 1), y: bottom - ((Number(values[i]) || 0) / max) * (bottom - top) })
  }
  function clampY(y) { return Math.max(top, Math.min(bottom, y)) }
  var line = "M " + fmt(points[0].x) + " " + fmt(points[0].y)
  for (i = 0; i < count - 1; i++) {
    var p0 = points[Math.max(0, i - 1)], p1 = points[i], p2 = points[i + 1]
    var p3 = points[Math.min(count - 1, i + 2)]
    line += " C " + fmt(p1.x + (p2.x - p0.x) / 6) + " " + fmt(clampY(p1.y + (p2.y - p0.y) / 6))
      + " " + fmt(p2.x - (p3.x - p1.x) / 6) + " " + fmt(clampY(p2.y - (p3.y - p1.y) / 6))
      + " " + fmt(p2.x) + " " + fmt(p2.y)
  }
  return {
    line: line,
    area: line + " L " + fmt(width) + " " + fmt(height) + " L 0 " + fmt(height) + " Z",
    points: points
  }
}

function hourLabel(isoStart) {
  var date = new Date(String(isoStart))
  if (isNaN(date.getTime())) return ""
  var hours = date.getHours()
  return (hours < 10 ? "0" : "") + hours + ":00"
}

// Validates a helper document before the UI trusts it.
function isInsights(value, providerId) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false
  if (value.schemaVersion !== 1 || String(value.providerId || "") !== providerId) return false
  if (!Array.isArray(value.hourly) || value.hourly.length !== 24) return false
  for (var i = 0; i < value.hourly.length; i++) {
    var bucket = value.hourly[i]
    if (!bucket || typeof bucket.tokens !== "number" || !isFinite(bucket.tokens) || bucket.tokens < 0) return false
  }
  if (!Array.isArray(value.models) || value.models.length > 12) return false
  for (i = 0; i < value.models.length; i++) {
    var model = value.models[i]
    if (!model || typeof model.name !== "string" || typeof model.tokens !== "number"
        || typeof model.share !== "number") return false
  }
  return Boolean(value.totals) && typeof value.totals === "object"
}

function agoLabel(iso, nowMs) {
  var at = new Date(String(iso)).getTime()
  if (isNaN(at)) return ""
  var minutes = Math.max(0, (nowMs - at) / 60000)
  if (minutes < 2) return "now"
  if (minutes < 60) return Math.round(minutes) + "m ago"
  if (minutes < 24 * 60) return Math.round(minutes / 60) + "h ago"
  return Math.round(minutes / (24 * 60)) + "d ago"
}

// Keeps the list readable: the first max-1 models plus one merged "Other".
function collapseModels(models, max) {
  var list = Array.isArray(models) ? models : []
  if (list.length <= max) return list
  var kept = list.slice(0, max - 1), tokens = 0, share = 0
  for (var i = max - 1; i < list.length; i++) {
    tokens += Number(list[i].tokens) || 0
    share += Number(list[i].share) || 0
  }
  kept.push({ name: "other", tokens: tokens, share: share })
  return kept
}
