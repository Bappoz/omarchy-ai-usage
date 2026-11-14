import QtQuick
import Quickshell
import Quickshell.Io
import "../ui/Usage.js" as Usage
import "Activity.js" as Activity

QtObject {
  id: root

  property var shell: null
  property var manifest: null
  readonly property string pluginId: manifest && manifest.id
    ? String(manifest.id)
    : "ai-usage.notch"
  readonly property string configPath: (Quickshell.env("HOME") || "")
    + "/.config/omarchy/shell.json"
  property var values: defaults()
  property bool loaded: false

  function defaults() {
    return {
      "settingsVersion": 1,
      "edge": "right",
      "offset": 0.5,
      "monitor": "focused",
      "size": "medium",
      "autoHide": true,
      "expandBehavior": "hover",
      "pollingInterval": 900,
      "showProviderLabel": false,
      "showPercentage": true,
      "showResetTimer": true,
      "animations": true,
      "accentColor": "auto",
      "showInsights": true,
      "showSessions": true,
      "peekOnEvent": true,
      "peekDuration": 5,
      "sessionSounds": true,
      "sessionNotifications": false,
      "finishedSound": "complete",
      "waitingSound": "bell",
      "quotaAlerts": true,
      "mutedAlerts": {},
      "busyIndicator": "arc",
      "resetTimeStyle": "remaining",
      "providerOrder": ["claude", "codex", "antigravity", "cursor"],
      "edgeOffsets": {},
      "enabledProviders": { "claude": true, "codex": true, "antigravity": true, "cursor": true },
      "providerColors": { "claude": "auto", "codex": "auto", "antigravity": "auto", "cursor": "auto" }
    }
  }

  function plainObject(value) {
    return value && typeof value === "object" && !Array.isArray(value)
  }

  function clamp(value, minimum, maximum, fallback) {
    var number = Number(value)
    if (!isFinite(number)) number = fallback
    return Math.max(minimum, Math.min(maximum, number))
  }

  function sanitize(source) {
    var raw = plainObject(source) ? source : ({})
    var base = defaults()
    var edges = ["top", "right", "bottom", "left"]
    var sizes = ["small", "medium", "large"]
    var behaviors = ["hover", "click"]
    var providers = plainObject(raw.enabledProviders) ? raw.enabledProviders : ({})
    var providerColors = plainObject(raw.providerColors) ? raw.providerColors : ({})
    var muted = plainObject(raw.mutedAlerts) ? raw.mutedAlerts : ({})
    var offsets = plainObject(raw.edgeOffsets) ? raw.edgeOffsets : ({})
    var edge = String(raw.edge || "").toLowerCase()
    var size = String(raw.size || "").toLowerCase()
    var behavior = String(raw.expandBehavior || "").toLowerCase()

    return {
      "settingsVersion": 1,
      "edge": edges.indexOf(edge) >= 0 ? edge : base.edge,
      "offset": clamp(raw.offset, 0, 1, base.offset),
      "monitor": String(raw.monitor || base.monitor).trim() || base.monitor,
      "size": sizes.indexOf(size) >= 0 ? size : base.size,
      "autoHide": raw.autoHide === undefined ? base.autoHide : raw.autoHide === true,
      "expandBehavior": behaviors.indexOf(behavior) >= 0 ? behavior : base.expandBehavior,
      "pollingInterval": Math.round(clamp(raw.pollingInterval, 60, 3600, base.pollingInterval)),
      "showProviderLabel": raw.showProviderLabel === true,
      "showPercentage": raw.showPercentage !== false,
      "showResetTimer": raw.showResetTimer === undefined ? base.showResetTimer : raw.showResetTimer === true,
      "animations": raw.animations === undefined ? base.animations : raw.animations === true,
      "accentColor": Usage.validAccent(raw.accentColor),
      "providerColors": {
        "claude": providerColors.claude === undefined ? base.providerColors.claude : Usage.validAccent(providerColors.claude),
        "codex": providerColors.codex === undefined ? base.providerColors.codex : Usage.validAccent(providerColors.codex),
        "antigravity": providerColors.antigravity === undefined ? base.providerColors.antigravity : Usage.validAccent(providerColors.antigravity),
        "cursor": providerColors.cursor === undefined ? base.providerColors.cursor : Usage.validAccent(providerColors.cursor)
      },
      "showInsights": raw.showInsights === undefined ? base.showInsights : raw.showInsights === true,
      "showSessions": raw.showSessions !== false,
      "peekOnEvent": raw.peekOnEvent !== false,
      "peekDuration": [3, 5, 10].indexOf(raw.peekDuration) >= 0 ? raw.peekDuration : 5,
      "sessionSounds": raw.sessionSounds !== false,
      "sessionNotifications": raw.sessionNotifications === true,
      "finishedSound": ["complete", "bell", "message"].indexOf(raw.finishedSound) >= 0 ? raw.finishedSound : "complete",
      "waitingSound": ["complete", "bell", "message"].indexOf(raw.waitingSound) >= 0 ? raw.waitingSound : "bell",
      "quotaAlerts": raw.quotaAlerts !== false,
      "mutedAlerts": { "claude": muted.claude === true, "codex": muted.codex === true,
        "antigravity": muted.antigravity === true, "cursor": muted.cursor === true },
      "busyIndicator": raw.busyIndicator === "breath" ? "breath" : "arc",
      "resetTimeStyle": raw.resetTimeStyle === "date" ? "date" : "remaining",
      "providerOrder": Activity.providerOrder(raw.providerOrder),
      "edgeOffsets": { "top": clamp(offsets.top, 0, 1, 0.5), "right": clamp(offsets.right, 0, 1, 0.5),
        "bottom": clamp(offsets.bottom, 0, 1, 0.5), "left": clamp(offsets.left, 0, 1, 0.5) },
      "enabledProviders": {
        "claude": providers.claude === false
          ? false
          : (!plainObject(providers.claude) || providers.claude.enabled !== false),
        "codex": providers.codex === false
          ? false
          : (!plainObject(providers.codex) || providers.codex.enabled !== false),
        "antigravity": providers.antigravity === false
          ? false
          : (!plainObject(providers.antigravity) || providers.antigravity.enabled !== false),
        "cursor": providers.cursor === false
          ? false
          : (!plainObject(providers.cursor) || providers.cursor.enabled !== false)
      }
    }
  }

  function pluginSettings(config) {
    if (!plainObject(config) || !Array.isArray(config.plugins)) return ({})
    for (var i = 0; i < config.plugins.length; i++) {
      var entry = config.plugins[i]
      if (plainObject(entry) && String(entry.id || "") === root.pluginId) return entry
    }
    return ({})
  }

  function applyText(text) {
    try {
      var config = JSON.parse(String(text || ""))
      root.values = root.sanitize(root.pluginSettings(config))
    } catch (error) {
      root.values = root.defaults()
    }
    root.loaded = true
  }

  function update(key, value) {
    var next = ({})
    var current = root.values || root.defaults()
    for (var name in current) next[name] = current[name]
    next[key] = value
    if (key === "enabledProviders") {
      var order = Activity.providerOrder(current.providerOrder)
      order.slice().forEach(function(id) {
        if (current.enabledProviders[id] === false && value[id] !== false) {
          order.splice(order.indexOf(id), 1)
          order.push(id)
        }
      })
      next.providerOrder = order
    }
    if (key === "edge") {
      var offsets = ({})
      for (var edge in current.edgeOffsets) offsets[edge] = current.edgeOffsets[edge]
      offsets[current.edge] = current.offset
      next.offset = offsets[value] === undefined ? 0.5 : offsets[value]
      next.edgeOffsets = offsets
    }
    if (key === "offset") {
      var positions = ({})
      for (var side in current.edgeOffsets) positions[side] = current.edgeOffsets[side]
      positions[current.edge] = value
      next.edgeOffsets = positions
    }
    next = root.sanitize(next)
    root.values = next

    // The scoped plugin facade writes only this plugin's inline entry in
    // shell.json. The FileView below remains the source of truth afterwards.
    if (root.shell && typeof root.shell.updateEntryInline === "function") {
      root.shell.updateEntryInline(root.pluginId, next)
    }
  }

  property FileView configFile: FileView {
    path: root.configPath
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.applyText(text())
    onLoadFailed: {
      root.values = root.defaults()
      root.loaded = true
    }
  }

  Component.onCompleted: configFile.reload()
}
