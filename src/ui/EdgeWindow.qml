import QtQuick
import Quickshell
import Quickshell.Wayland
import "../model/Activity.js" as Activity

PanelWindow {
  id: root

  property var targetScreen: null
  property string edge: "right"
  property real edgeOffset: 0.5
  property var snapshots: []
  property bool providerReady: false
  property bool loading: false
  property bool previewMode: false
  property var preferences: ({})
  property bool heldOpen: false
  property bool hoveringSurface: false
  property bool hoveringProvider: false
  property bool hoveringCard: false
  property int hoveredIndex: -1
  property bool settingsOpen: false
  property bool contextOpen: false
  property var sessions: []
  property bool sessionsFailed: false
  property var latestEvent: null
  property var peekEvent: null
  property bool desktopFullscreen: false
  property string desktopMonitorName: ""
  property var desktopWindowBounds: null
  readonly property bool peekActive: peekTimer.running
  readonly property var displaySessions: previewMode ? [
    { id: "aaaaaaaaaaaaaaaaaaaaaaaa", providerId: "claude", name: "Build workspace", detail: "Terminal · example", state: "busy", pid: null, started: null },
    { id: "bbbbbbbbbbbbbbbbbbbbbbbb", providerId: "codex", name: "Review changes", detail: "Codex · example", state: "waiting", waitingFor: "Permission or input required", pid: null, started: null }
  ] : sessions
  property var insights: ({})
  property var insightFailures: ({})
  property var openableApps: ({})
  property bool hoveringPanel: false
  property bool insightsArmed: false
  property var panelProvider: null
  readonly property bool forcedOpen: Quickshell.env("OMARCHY_AI_USAGE_EXPANDED") === "1"
  readonly property bool horizontalEdge: edge === "top" || edge === "bottom"
  readonly property real contentGap: 28 * (44 / 117) * sizeScale
  readonly property real screenWidth: targetScreen ? targetScreen.width : 0
  readonly property real screenHeight: targetScreen ? targetScreen.height : 0
  readonly property var providers: {
    var list = previewMode ? previewProviders() : liveProviders()
    var order = Activity.providerOrder(preferences.providerOrder)
    return list.sort(function(a, b) { return order.indexOf(a.id) - order.indexOf(b.id) })
  }
  readonly property bool autoHide: preferences.autoHide !== false
  readonly property string autoHideMode: String(preferences.autoHideMode || "onFullscreen")
  readonly property real surfaceOpacity: preferences.surfaceOpacity === undefined ? 1.0 : Number(preferences.surfaceOpacity)
  readonly property string colorTransitionStyle: String(preferences.colorTransitionStyle || "hardStep")
  readonly property string expandBehavior: String(preferences.expandBehavior || "hover")
  readonly property real sizeScale: preferences.size === "small" ? 0.85
    : (preferences.size === "large" ? 1.2 : 1)
  readonly property bool motionEnabled: preferences.animations !== false
    && Quickshell.env("OMARCHY_REDUCED_MOTION") !== "1"
  readonly property bool hoverExpansion: autoHide && expandBehavior === "hover"
  readonly property bool screenMatchesDesktop: targetScreen !== null
    && (desktopMonitorName === "" || String(targetScreen.name || "") === desktopMonitorName)
  readonly property bool desktopSuppressed: !previewMode && !forcedOpen && !heldOpen
    && !settingsOpen && !contextOpen && !peekActive
    && !hoveringSurface && !hoveringProvider && !hoveringCard && !hoveringPanel
    && screenMatchesDesktop
    && ((autoHideMode === "onFullscreen" && desktopFullscreen)
        || (autoHideMode === "onOverlap" && (desktopFullscreen || windowOverlapsNotch())))
  readonly property bool unfolded: (!autoHide && !desktopSuppressed) || forcedOpen || heldOpen || settingsOpen || contextOpen || peekActive || notch.orbSettling
    || (hoverExpansion && (hoveringSurface || hoveringProvider || hoveringCard || hoveringPanel || hoveredIndex >= 0))
  readonly property bool showCard: settingsOpen || contextOpen
    || (hoveredIndex >= 0 && hoveredIndex < providers.length && unfolded)
  readonly property var activeProvider: showCard && hoveredIndex >= 0 && hoveredIndex < providers.length
    ? providers[hoveredIndex]
    : null
  readonly property bool insightsEnabled: preferences.showInsights !== false
  readonly property bool showInsights: insightsEnabled && showCard && !settingsOpen
    && !contextOpen && !peekActive && insightsArmed && activeProvider !== null

  signal refreshRequested(string providerId)
  signal insightsRequested(string providerId)
  signal appRequested(string providerId)
  signal preferenceChanged(string key, var value)
  signal sessionFocusRequested(var session)
  signal soundPreviewRequested(string sound)

  function openSettings() {
    contextOpen = false
    settingsOpen = !settingsOpen
    if (settingsOpen && hoveredIndex < 0 && providers.length) hoveredIndex = 0
  }

  function windowOverlapsNotch() {
    var b = root.desktopWindowBounds
    if (!b || !root.targetScreen) return false
    var sx = Number(root.targetScreen.x || 0)
    var sy = Number(root.targetScreen.y || 0)
    var nx = sx + notch.x + notch.surfaceX
    var ny = sy + notch.y + notch.surfaceY
    var nw = notch.surfaceWidth
    var nh = notch.surfaceHeight
    return b.x < nx + nw && b.x + b.width > nx && b.y < ny + nh && b.y + b.height > ny
  }

  onLatestEventChanged: {
    if (!latestEvent || preferences.peekOnEvent === false || settingsOpen || heldOpen) return
    if (Date.now() - latestEvent.at > Number(preferences.peekDuration || 5) * 1000) return
    for (var i = 0; i < providers.length; i++) {
      if (providers[i].id === latestEvent.session.providerId) {
        peekEvent = latestEvent
        hoveredIndex = i
        peekTimer.restart()
        break
      }
    }
  }

  // Keep selection attached to the same account when its order changes.
  property string selectedProviderId: ""
  onHoveredIndexChanged: {
    selectedProviderId = hoveredIndex >= 0 && hoveredIndex < providers.length ? providers[hoveredIndex].id : ""
  }
  onProvidersChanged: {
    if (!selectedProviderId) return
    var index = providers.findIndex(function(p) { return p.id === root.selectedProviderId })
    if (index < 0) { settingsOpen = false; contextOpen = false }
    hoveredIndex = index
  }

  function headlineWindow(value) {
    if (!value || !Array.isArray(value.windows)) return null
    var targetId = String(value.headlineWindowId || "")
    for (var i = 0; i < value.windows.length; i++) {
      var candidate = value.windows[i]
      if (candidate && String(candidate.id || "") === targetId) return candidate
    }
    return value.windows.length > 0 ? value.windows[0] : null
  }

  function windowUsed(window) {
    if (window && typeof window.usedPercent === "number" && isFinite(window.usedPercent)) {
      return Math.max(0, Math.min(100, window.usedPercent))
    }
    if (window && typeof window.remainingPercent === "number" && isFinite(window.remainingPercent)) {
      return Math.max(0, Math.min(100, 100 - window.remainingPercent))
    }
    return null
  }

  function liveProviders() {
    var result = []
    var currentSnapshots = Array.isArray(root.snapshots) ? root.snapshots : []
    for (var i = 0; i < currentSnapshots.length; i++) {
      var current = currentSnapshots[i]
      if (!current) continue
      var status = String(current.status || "UNAVAILABLE")
      result.push({
        "id": String(current.providerId || ""),
        "displayName": String(current.displayName || current.providerId || "AI"),
        "usedPercent": root.windowUsed(root.headlineWindow(current)),
        "stale": status === "STALE" || status === "ERROR" || status === "UNAVAILABLE",
        "snapshot": current
      })
    }
    return result
  }

  function previewReset(minutes) {
    return new Date(Date.now() + minutes * 60000).toISOString()
  }

  function previewProviders() {
    var claude = {
      "schemaVersion": 1,
      "providerId": "claude",
      "displayName": "Claude",
      "status": "ACTIVE",
      "windows": [
        { "id": "session", "name": "Current session", "usedPercent": 73, "remainingPercent": 27, "resetCopy": "Resets in 51 min", "resetAt": previewReset(51), "durationMinutes": 300 },
        { "id": "models", "name": "All models", "usedPercent": 7, "remainingPercent": 93, "resetCopy": "Resets Thu 12:00 AM", "resetAt": previewReset(4300), "durationMinutes": 10080 }
      ],
      "message": null
    }
    var codex = {
      "schemaVersion": 1,
      "providerId": "codex",
      "displayName": "Codex",
      "status": "ACTIVE",
      "windows": [
        { "id": "five-hour", "name": "5-hour limit", "usedPercent": 21, "remainingPercent": 79, "resetCopy": "Resets in 3h 12 min", "resetAt": previewReset(192), "durationMinutes": 300 },
        { "id": "weekly", "name": "Weekly", "usedPercent": 34, "remainingPercent": 66, "resetCopy": "Resets Mon 9:00 AM", "resetAt": previewReset(6000), "durationMinutes": 10080 }
      ],
      "message": null
    }
    var perplexity = {
      "schemaVersion": 1,
      "providerId": "perplexity",
      "displayName": "Perplexity",
      "status": "ACTIVE",
      "windows": [
        { "id": "queries", "name": "Pro searches", "usedPercent": 52, "remainingPercent": 48, "resetCopy": "Resets tomorrow", "resetAt": previewReset(1200), "durationMinutes": 1440 }
      ],
      "message": null
    }
    return [
      { "id": "claude", "displayName": "Claude", "usedPercent": 73, "stale": false, "snapshot": claude },
      { "id": "codex", "displayName": "Codex", "usedPercent": 21, "stale": false, "snapshot": codex },
      { "id": "perplexity", "displayName": "Perplexity", "usedPercent": 52, "stale": false, "snapshot": perplexity }
    ]
  }

  function scheduleClose() {
    if (!root.autoHide || root.forcedOpen) return
    if (!root.settingsOpen && (!root.hoverExpansion || root.heldOpen)) return
    hoverGrace.restart()
  }

  function cardTargetX() {
    var ringX = root.horizontalEdge
      ? notch.x + notch.providerCenter(root.hoveredIndex)
      : notch.x + notch.fullDepth / 2
    if (root.edge === "left") return notch.x + notch.width + root.contentGap
    if (root.edge === "right") return notch.x - root.contentGap - expandedCard.width
    return Math.max(0, Math.min(root.screenWidth - expandedCard.width, ringX - expandedCard.width / 2))
  }

  function cardTargetY() {
    var ringY = root.horizontalEdge
      ? notch.y + (notch.fullDepth - notch.cellExtent) / 2 + notch.ringDiameter / 2
      : notch.y + notch.providerCenter(root.hoveredIndex)
    if (root.edge === "top") return notch.y + notch.height + root.contentGap
    if (root.edge === "bottom") return notch.y - root.contentGap - expandedCard.height
    return Math.max(0, Math.min(root.screenHeight - expandedCard.height, ringY - expandedCard.height / 2))
  }

  function panelTargetX() {
    var gap = root.contentGap
    if (root.edge === "right") return Math.max(0, expandedCard.x - gap - insightsPanel.width)
    if (root.edge === "left") {
      return Math.min(Math.max(0, root.screenWidth - insightsPanel.width),
                      expandedCard.x + expandedCard.width + gap)
    }
    return Math.max(0, Math.min(root.screenWidth - insightsPanel.width, expandedCard.x))
  }

  function panelTargetY() {
    var gap = root.contentGap
    if (root.edge === "top") return expandedCard.y + expandedCard.height + gap
    if (root.edge === "bottom") return Math.max(0, expandedCard.y - gap - insightsPanel.height)
    var centered = expandedCard.y + (expandedCard.height - insightsPanel.height) / 2
    return Math.max(0, Math.min(root.screenHeight - insightsPanel.height, centered))
  }

  function requestInsights() {
    if (root.previewMode || !root.activeProvider) return
    root.insightsRequested(String(root.activeProvider.id || ""))
  }

  function bridgeRect() {
    if (!root.showCard) return Qt.rect(0, 0, 0, 0)
    var ringX = root.horizontalEdge
      ? notch.x + notch.providerCenter(root.hoveredIndex)
      : notch.x + notch.fullDepth / 2
    var ringY = root.horizontalEdge
      ? notch.y + (notch.fullDepth - notch.cellExtent) / 2 + notch.ringDiameter / 2
      : notch.y + notch.providerCenter(root.hoveredIndex)
    if (root.edge === "right") {
      return Qt.rect(expandedCard.x + expandedCard.width, ringY - expandedCard.tailHeight / 2,
                     Math.max(0, notch.x - expandedCard.x - expandedCard.width), expandedCard.tailHeight)
    }
    if (root.edge === "left") {
      return Qt.rect(notch.x + notch.width, ringY - expandedCard.tailHeight / 2,
                     Math.max(0, expandedCard.x - notch.x - notch.width), expandedCard.tailHeight)
    }
    if (root.edge === "top") {
      return Qt.rect(ringX - expandedCard.tailHeight / 2, notch.y + notch.height,
                     expandedCard.tailHeight, Math.max(0, expandedCard.y - notch.y - notch.height))
    }
    return Qt.rect(ringX - expandedCard.tailHeight / 2, expandedCard.y + expandedCard.height,
                   expandedCard.tailHeight, Math.max(0, notch.y - expandedCard.y - expandedCard.height))
  }

  screen: targetScreen
  visible: targetScreen !== null && providerReady
  color: "transparent"
  exclusionMode: ExclusionMode.Ignore
  surfaceFormat.opaque: false

  anchors {
    top: true
    bottom: true
    left: true
    right: true
  }

  mask: Region {
    Region {
      x: notch.x + notch.inputX
      y: notch.y + notch.inputY
      width: notch.inputWidth
      height: notch.inputHeight
      radius: Math.round(Math.min(width, height) / 2)
    }
    Region {
      x: notch.x + notch.orbInputRect.x
      y: notch.y + notch.orbInputRect.y
      width: notch.orbVisible ? notch.orbInputRect.width : 0
      height: notch.orbVisible ? notch.orbInputRect.height : 0
      radius: Math.round(width / 2)
    }
    Region {
      x: expandedCard.x
      y: expandedCard.y
      width: root.showCard || expandedCard.opacity > 0 ? expandedCard.width : 0
      height: root.showCard || expandedCard.opacity > 0 ? expandedCard.height : 0
      radius: Math.round(expandedCard.cardCorner)
    }
    Region {
      x: insightsPanel.x
      y: insightsPanel.y
      width: root.showInsights || insightsPanel.opacity > 0 ? insightsPanel.width : 0
      height: root.showInsights || insightsPanel.opacity > 0 ? insightsPanel.height : 0
      radius: Math.round(insightsPanel.corner)
    }
    Region {
      x: root.bridgeRect().x
      y: root.bridgeRect().y
      width: root.bridgeRect().width
      height: root.bridgeRect().height
    }
  }

  WlrLayershell.namespace: "ai-usage-notch"
  WlrLayershell.layer: WlrLayer.Overlay
  WlrLayershell.keyboardFocus: root.settingsOpen ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.None

  Timer {
    id: peekTimer
    interval: Number(root.preferences.peekDuration || 5) * 1000
    onTriggered: {
      root.peekEvent = null
      if (!root.hoveringSurface && !root.hoveringProvider && !root.hoveringCard && !root.heldOpen) root.hoveredIndex = -1
    }
  }

  Timer {
    id: hoverGrace
    interval: 250
    repeat: false
    onTriggered: {
      if (root.hoveringSurface || root.hoveringProvider || root.hoveringCard || root.hoveringPanel) return
      if (root.peekActive) return
      if (root.settingsOpen) {
        root.settingsOpen = false
        root.heldOpen = false
      }
      root.hoveredIndex = -1
      root.contextOpen = false
    }
  }

  // The panel waits a beat after the card so the two read as one cascade.
  Timer {
    id: insightsArm
    interval: 320
    repeat: false
    running: root.showCard && root.insightsEnabled && !root.settingsOpen && !root.insightsArmed
    onTriggered: root.insightsArmed = true
  }

  Timer {
    id: insightsRefresh
    interval: 60000
    repeat: true
    running: root.showInsights && !root.previewMode
    onTriggered: root.requestInsights()
  }

  onShowCardChanged: if (!showCard) insightsArmed = false
  onSettingsOpenChanged: if (settingsOpen) insightsArmed = false
  onShowInsightsChanged: if (showInsights) requestInsights()
  onActiveProviderChanged: {
    if (activeProvider) panelProvider = activeProvider
    if (showInsights) requestInsights()
  }

  Timer {
    id: visibleRefresh
    interval: 30000
    repeat: true
    running: root.showCard && !root.previewMode && root.activeProvider !== null
    onTriggered: root.refreshRequested(String(root.activeProvider.id || ""))
  }

  CompactNotch {
    id: notch
    x: root.horizontalEdge
      ? Math.round(root.edgeOffset * Math.max(0, root.screenWidth - width))
      : (root.edge === "right" ? root.screenWidth - width : 0)
    y: !root.horizontalEdge
      ? Math.round(root.edgeOffset * Math.max(0, root.screenHeight - height))
      : (root.edge === "bottom" ? root.screenHeight - height : 0)
    width: implicitWidth
    height: implicitHeight
    z: 2
    edge: root.edge
    providers: root.providers
    unfolded: root.unfolded
    activeIndex: root.hoveredIndex
    previewMode: root.previewMode
    uiScale: root.sizeScale
    animationsEnabled: root.motionEnabled
    settingsOpen: root.settingsOpen
    accentColor: String(root.preferences.accentColor || "auto")
    providerColors: root.preferences.providerColors || ({})
    colorTransitionStyle: root.colorTransitionStyle
    surfaceOpacity: root.surfaceOpacity
    suppressed: root.desktopSuppressed
    sessions: root.preferences.showSessions === false ? [] : root.displaySessions
    busyIndicator: String(root.preferences.busyIndicator || "arc")
    onSettingsRequested: root.openSettings()
    onContextRequested: {
      root.contextOpen = !root.contextOpen
      root.settingsOpen = false
      if (root.hoveredIndex < 0 && root.providers.length) root.hoveredIndex = 0
    }
    onOffsetDragged: function(delta) {
      var available = root.horizontalEdge ? root.screenWidth - notch.width : root.screenHeight - notch.height
      if (available > 0) root.preferenceChanged("offset", Math.max(0, Math.min(1, root.edgeOffset + delta / available)))
    }

    onSurfaceHovered: function(hovered) {
      root.hoveringSurface = hovered
      if (hovered) hoverGrace.stop()
      else root.scheduleClose()
    }
    onProviderHovered: function(index, hovered) {
      root.hoveringProvider = hovered
      if (hovered) {
        var shouldRefresh = root.hoveredIndex !== index || !root.showCard
        hoverGrace.stop()
        root.hoveredIndex = index
        if (shouldRefresh && !root.previewMode && index >= 0 && index < root.providers.length) {
          root.refreshRequested(String(root.providers[index].id || ""))
        }
      } else {
        root.scheduleClose()
      }
    }
    onProviderActivated: function(index) {
      if (index >= 0 && index < root.providers.length) {
        if (root.peekActive && root.peekEvent && root.peekEvent.session.pid) {
          root.sessionFocusRequested(root.peekEvent.session)
          peekTimer.stop()
        } else root.refreshRequested(String(root.providers[index].id || ""))
      }
    }
    onBodyActivated: {
      if (root.peekActive && root.peekEvent && root.peekEvent.session.pid) {
        root.sessionFocusRequested(root.peekEvent.session)
        peekTimer.stop()
        return
      }
      root.heldOpen = !root.heldOpen
      if (root.heldOpen && root.hoveredIndex < 0 && root.providers.length > 0) root.hoveredIndex = 0
      if (!root.heldOpen) root.settingsOpen = false
    }
  }

  ExpandedCard {
    id: expandedCard
    x: root.cardTargetX()
    y: root.cardTargetY()
    width: implicitWidth
    height: implicitHeight
    visible: root.showCard || opacity > 0
    opacity: root.showCard ? 1 : 0
    scale: root.showCard ? 1 : 0.92
    transformOrigin: root.edge === "right" ? Item.Right
      : (root.edge === "left" ? Item.Left : (root.edge === "top" ? Item.Top : Item.Bottom))
    edge: root.edge
    tailCenter: root.horizontalEdge
      ? notch.x + notch.providerCenter(root.hoveredIndex) - x
      : notch.y + notch.providerCenter(root.hoveredIndex) - y
    snapshot: root.activeProvider ? root.activeProvider.snapshot : null
    providerId: root.activeProvider ? String(root.activeProvider.id || "codex") : "codex"
    loading: root.loading
    previewMode: root.previewMode
    uiScale: root.sizeScale
    animationsEnabled: root.motionEnabled
    showResetTimer: root.preferences.showResetTimer !== false
    accentColor: String(root.preferences.accentColor || "auto")
    providerColors: root.preferences.providerColors || ({})
    colorTransitionStyle: root.colorTransitionStyle
    surfaceOpacity: root.surfaceOpacity
    settingsOpen: root.settingsOpen
    contextOpen: root.contextOpen
    heldOpen: root.heldOpen
    sessions: root.preferences.showSessions === false ? [] : Activity.summary(root.displaySessions, root.activeProvider ? root.activeProvider.id : "").sessions
    sessionsFailed: root.sessionsFailed
    sessionMonitoring: root.preferences.showSessions !== false
    maxBodyHeight: Math.max(120, root.screenHeight - 2 * root.contentGap - (root.horizontalEdge ? notch.height + expandedCard.tailLength : 0))
    preferences: root.preferences
    canOpenApp: root.activeProvider !== null && root.openableApps[String(root.activeProvider.id)] !== undefined
    onAppRequested: root.appRequested(String(root.activeProvider ? root.activeProvider.id : ""))
    onPreferenceChanged: function(key, value) { root.preferenceChanged(key, value) }
    onSoundPreviewRequested: function(sound) { root.soundPreviewRequested(sound) }
    onSessionFocusRequested: function(session) { root.sessionFocusRequested(session) }
    onRefreshRequested: {
      if (root.activeProvider) root.refreshRequested(root.activeProvider.id)
      root.contextOpen = false
    }
    onPinRequested: { root.heldOpen = !root.heldOpen; root.contextOpen = false }
    onCardHovered: function(hovered) {
      root.hoveringCard = hovered
      if (hovered) hoverGrace.stop()
      else root.scheduleClose()
    }

    Behavior on x {
      enabled: root.motionEnabled
      SpringAnimation { spring: 3.6; damping: 0.52; epsilon: 0.1 }
    }
    Behavior on y {
      enabled: root.motionEnabled
      SpringAnimation { spring: 3.6; damping: 0.52; epsilon: 0.1 }
    }
    Behavior on opacity {
      NumberAnimation { duration: root.motionEnabled ? 180 : 0; easing.type: Easing.OutCubic }
    }
    Behavior on scale {
      enabled: root.motionEnabled
      SpringAnimation { spring: 4.0; damping: 0.38; epsilon: 0.001 }
    }
  }

  InsightsPanel {
    id: insightsPanel
    x: root.panelTargetX()
    y: root.panelTargetY()
    width: implicitWidth
    height: implicitHeight
    visible: root.showInsights || opacity > 0
    opacity: root.showInsights ? 1 : 0
    scale: root.showInsights ? 1 : 0.9
    transformOrigin: root.edge === "right" ? Item.Right
      : (root.edge === "left" ? Item.Left : (root.edge === "top" ? Item.Top : Item.Bottom))
    shown: root.showInsights
    sessions: root.preferences.showSessions === false ? [] : Activity.summary(root.displaySessions, root.panelProvider ? root.panelProvider.id : "").sessions
    providerId: root.panelProvider ? String(root.panelProvider.id || "") : "claude"
    providerName: root.panelProvider ? String(root.panelProvider.displayName || "") : ""
    insights: root.panelProvider ? (root.insights[String(root.panelProvider.id)] || null) : null
    failed: root.panelProvider ? root.insightFailures[String(root.panelProvider.id)] === true : false
    previewMode: root.previewMode
    uiScale: root.sizeScale
    animationsEnabled: root.motionEnabled
    accentColor: String(root.preferences.accentColor || "auto")
    providerColors: root.preferences.providerColors || ({})
    surfaceOpacity: root.surfaceOpacity
    onPanelHovered: function(hovered) {
      root.hoveringPanel = hovered
      if (hovered) hoverGrace.stop()
      else root.scheduleClose()
    }

    Behavior on x {
      enabled: root.motionEnabled
      SpringAnimation { spring: 3.6; damping: 0.52; epsilon: 0.1 }
    }
    Behavior on y {
      enabled: root.motionEnabled
      SpringAnimation { spring: 3.6; damping: 0.52; epsilon: 0.1 }
    }
    Behavior on opacity {
      NumberAnimation { duration: root.motionEnabled ? 200 : 0; easing.type: Easing.OutCubic }
    }
    Behavior on scale {
      enabled: root.motionEnabled
      SpringAnimation { spring: 3.6; damping: 0.36; epsilon: 0.001 }
    }
  }

  Component.onCompleted: {
    if (root.forcedOpen && root.providers.length > 0) root.hoveredIndex = 0
  }
}
