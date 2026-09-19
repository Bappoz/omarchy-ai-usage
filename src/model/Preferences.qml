import QtQuick
import Quickshell
import Quickshell.Io

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
      "enabledProviders": { "claude": true, "codex": true }
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
      "showPercentage": raw.showPercentage === undefined ? base.showPercentage : raw.showPercentage === true,
      "showResetTimer": raw.showResetTimer === undefined ? base.showResetTimer : raw.showResetTimer === true,
      "animations": raw.animations === undefined ? base.animations : raw.animations === true,
      "enabledProviders": {
        "claude": providers.claude === false
          ? false
          : (!plainObject(providers.claude) || providers.claude.enabled !== false),
        "codex": providers.codex === false
          ? false
          : (!plainObject(providers.codex) || providers.codex.enabled !== false)
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
