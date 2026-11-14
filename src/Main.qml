import QtQuick
import Quickshell
import Quickshell.Hyprland
import "model"
import "ui"
import "model/Activity.js" as Activity

Item {
  id: root

  // Injected by the Omarchy service host. The current runtime needs no
  // privileged host methods, but declaring the facade keeps the contract clear.
  property var shell: null
  property var manifest: null
  readonly property var preferenceValues: preferenceStore.values || ({})
  property var quotaHistory: ({})
  property var latestEvent: null

  function sessionEvent(event) {
    root.latestEvent = { session: event.session, reason: event.reason, at: Date.now() }
    var p = root.preferenceValues
    var sound = p.sessionSounds === false ? "" : (event.reason === "blocked" ? p.waitingSound : p.finishedSound)
    desktopFeedback.send(event.session.providerId, event.reason, p.sessionNotifications === true, sound)
    providerStore.refresh(event.session.providerId)
  }

  function checkQuotaAlerts() {
    if (providerStore.previewMode) return
    var history = ({})
    var p = root.preferenceValues
    providerStore.snapshots.forEach(function(snapshot) {
      var id = snapshot.providerId
      var next = Activity.quotaCrossings(root.quotaHistory[id], snapshot, Date.now())
      history[id] = next.previous
      if (p.quotaAlerts !== false && (!p.mutedAlerts || p.mutedAlerts[id] !== true)
          && next.thresholds.length) {
        desktopFeedback.send(id, String(next.thresholds[next.thresholds.length - 1]), true, "")
      }
    })
    root.quotaHistory = history
  }

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
    enabledProviders: root.preferenceValues.enabledProviders || ({ "claude": true, "codex": true, "antigravity": true, "cursor": true })
    activeProviderIds: {
      var result = []
      sessionStore.sessions.forEach(function(s) {
        if (s.state === "busy" && result.indexOf(s.providerId) < 0) result.push(s.providerId)
      })
      return result
    }
    onSnapshotsChanged: Qt.callLater(root.checkQuotaAlerts)
  }

  SessionStore {
    id: sessionStore
    enabled: root.preferenceValues.showSessions !== false
    previewMode: providerStore.previewMode
    enabledProviders: providerStore.enabledProviders
    onEventOccurred: function(event) { root.sessionEvent(event) }
  }

  DesktopFeedback { id: desktopFeedback }

  InsightsStore {
    id: insightsStore
    previewMode: providerStore.previewMode
  }

  AppLauncher { id: appLauncher }

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
      insights: insightsStore.docs
      insightFailures: insightsStore.failures
      openableApps: appLauncher.apps
      sessions: sessionStore.sessions
      sessionsFailed: sessionStore.failed
      latestEvent: root.latestEvent
      onSessionFocusRequested: function(session) { sessionStore.focus(session) }
      onSoundPreviewRequested: function(sound) { desktopFeedback.send("claude", "preview", false, sound) }
      onInsightsRequested: function(providerId) { insightsStore.refresh(providerId) }
      onAppRequested: function(providerId) { appLauncher.open(providerId) }
      onRefreshRequested: function(providerId) { providerStore.refresh(providerId) }
      onPreferenceChanged: function(key, value) { preferenceStore.update(key, value) }
    }
  }
}
