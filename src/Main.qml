import QtQuick
import Quickshell
import Quickshell.Hyprland
import "model"
import "ui"

Item {
  id: root

  // Injected by the Omarchy service host. The current runtime needs no
  // privileged host methods, but declaring the facade keeps the contract clear.
  property var shell: null
  property var manifest: null
  readonly property var preferenceValues: preferenceStore.values || ({})

  readonly property string edge: normalizeEdge(environmentOr(
    "OMARCHY_AI_USAGE_EDGE", root.preferenceValues.edge
  ))
  readonly property real edgeOffset: normalizeOffset(environmentOr(
    "OMARCHY_AI_USAGE_OFFSET", root.preferenceValues.offset
  ))
  readonly property string screenSelection: normalizeScreenSelection(environmentOr(
    "OMARCHY_AI_USAGE_SCREEN", root.preferenceValues.monitor
  ))

  function environmentOr(name, fallback) {
    var value = String(Quickshell.env(name) || "").trim()
    return value === "" ? fallback : value
  }

  function normalizeEdge(value) {
    var candidate = String(value || "").trim().toLowerCase()
    return ["top", "right", "bottom", "left"].indexOf(candidate) >= 0
      ? candidate
      : "right"
  }

  function normalizeOffset(value) {
    if (String(value || "").trim() === "") return 0.5
    var candidate = Number(value)
    return isFinite(candidate) ? Math.max(0, Math.min(1, candidate)) : 0.5
  }

  function normalizeScreenSelection(value) {
    var candidate = String(value || "").trim()
    return candidate === "" ? "focused" : candidate
  }

  function focusedScreen(screens) {
    if (!screens || screens.length === 0) return null
    var focused = Hyprland.focusedMonitor
    var focusedName = focused ? String(focused.name || "") : ""
    for (var i = 0; i < screens.length; i++) {
      if (String(screens[i].name || "") === focusedName) return screens[i]
    }
    return screens[0]
  }

  readonly property var selectedScreens: {
    var screens = Quickshell.screens || []
    var focused = root.focusedScreen(screens)
    if (root.screenSelection === "all") {
      var everyScreen = []
      for (var i = 0; i < screens.length; i++) everyScreen.push(screens[i])
      return everyScreen
    }

    if (root.screenSelection !== "focused") {
      for (var j = 0; j < screens.length; j++) {
        if (String(screens[j].name || "") === root.screenSelection) return [screens[j]]
      }
    }
    return focused ? [focused] : []
  }

  ProviderStore {
    id: providerStore
    pollingIntervalSeconds: root.preferenceValues.pollingInterval || 900
    enabledProviders: root.preferenceValues.enabledProviders || ({ "claude": true, "codex": true })
  }

  Preferences {
    id: preferenceStore
    shell: root.shell
    manifest: root.manifest
  }

  Variants {
    model: root.selectedScreens

    EdgeWindow {
      required property var modelData

      targetScreen: modelData
      edge: root.edge
      edgeOffset: root.edgeOffset
      preferences: root.preferenceValues
      snapshots: providerStore.snapshots
      providerReady: providerStore.ready
      loading: providerStore.loading
      previewMode: providerStore.previewMode
      onRefreshRequested: function(providerId) { providerStore.refresh(providerId) }
      onPreferenceChanged: function(key, value) { preferenceStore.update(key, value) }
    }
  }
}
