import QtQuick
import Quickshell
import Quickshell.Wayland

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
  readonly property bool forcedOpen: Quickshell.env("OMARCHY_AI_USAGE_EXPANDED") === "1"
  readonly property bool horizontalEdge: edge === "top" || edge === "bottom"
  readonly property real contentGap: 28 * (44 / 117) * sizeScale
  readonly property real screenWidth: targetScreen ? targetScreen.width : 0
  readonly property real screenHeight: targetScreen ? targetScreen.height : 0
  readonly property var providers: previewMode ? previewProviders() : liveProviders()
  readonly property bool autoHide: preferences.autoHide !== false
  readonly property string expandBehavior: String(preferences.expandBehavior || "hover")
  readonly property real sizeScale: preferences.size === "small" ? 0.85
    : (preferences.size === "large" ? 1.2 : 1)
  readonly property bool motionEnabled: preferences.animations !== false
    && Quickshell.env("OMARCHY_REDUCED_MOTION") !== "1"
  readonly property bool hoverExpansion: autoHide && expandBehavior === "hover"
  readonly property bool unfolded: !autoHide || forcedOpen || heldOpen || settingsOpen
    || (hoverExpansion && (hoveringSurface || hoveringProvider || hoveringCard || hoveredIndex >= 0))
  readonly property bool showCard: settingsOpen
    || (hoveredIndex >= 0 && hoveredIndex < providers.length && unfolded)
  readonly property var activeProvider: showCard && hoveredIndex >= 0 && hoveredIndex < providers.length
    ? providers[hoveredIndex]
    : null

  signal refreshRequested(string providerId)
  signal preferenceChanged(string key, var value)

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

  function previewProviders() {
    var claude = {
      "schemaVersion": 1,
      "providerId": "claude",
      "displayName": "Claude",
      "status": "ACTIVE",
      "windows": [
        { "id": "session", "name": "Current session", "usedPercent": 73, "remainingPercent": 27, "resetCopy": "Resets in 51 min" },
        { "id": "models", "name": "All models", "usedPercent": 7, "remainingPercent": 93, "resetCopy": "Resets Thu 12:00 AM" }
      ],
      "message": null
    }
    var codex = {
      "schemaVersion": 1,
      "providerId": "codex",
      "displayName": "Codex",
      "status": "ACTIVE",
      "windows": [
        { "id": "five-hour", "name": "5-hour limit", "usedPercent": 21, "remainingPercent": 79, "resetCopy": "Resets in 3h 12 min" },
        { "id": "weekly", "name": "Weekly", "usedPercent": 34, "remainingPercent": 66, "resetCopy": "Resets Mon 9:00 AM" }
      ],
      "message": null
    }
    var perplexity = {
      "schemaVersion": 1,
      "providerId": "perplexity",
      "displayName": "Perplexity",
      "status": "ACTIVE",
      "windows": [
        { "id": "queries", "name": "Pro searches", "usedPercent": 52, "remainingPercent": 48, "resetCopy": "Resets tomorrow" }
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
      x: expandedCard.x
      y: expandedCard.y
      width: root.showCard || expandedCard.opacity > 0 ? expandedCard.width : 0
      height: root.showCard || expandedCard.opacity > 0 ? expandedCard.height : 0
      radius: Math.round(expandedCard.cardCorner)
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
  WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

  Timer {
    id: hoverGrace
    interval: 250
    repeat: false
    onTriggered: {
      if (root.hoveringSurface || root.hoveringProvider || root.hoveringCard) return
      if (root.settingsOpen) {
        root.settingsOpen = false
        root.heldOpen = false
      }
      root.hoveredIndex = -1
    }
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
    showProviderLabel: root.preferences.showProviderLabel === true
    showPercentage: root.preferences.showPercentage !== false

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
      if (!root.previewMode && index >= 0 && index < root.providers.length) {
        root.refreshRequested(String(root.providers[index].id || ""))
      }
    }
    onBodyActivated: {
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
    scale: root.showCard ? 1 : 0.985
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
    settingsOpen: root.settingsOpen
    preferences: root.preferences
    onSettingsRequested: {
      root.settingsOpen = !root.settingsOpen
      if (root.settingsOpen) {
        root.heldOpen = false
        if (root.hoveredIndex < 0 && root.providers.length > 0) root.hoveredIndex = 0
      }
    }
    onPreferenceChanged: function(key, value) { root.preferenceChanged(key, value) }
    onCardHovered: function(hovered) {
      root.hoveringCard = hovered
      if (hovered) hoverGrace.stop()
      else root.scheduleClose()
    }

    Behavior on x {
      NumberAnimation { duration: root.motionEnabled ? 500 : 0; easing.type: Easing.OutCubic }
    }
    Behavior on y {
      NumberAnimation { duration: root.motionEnabled ? 500 : 0; easing.type: Easing.OutCubic }
    }
    Behavior on opacity {
      NumberAnimation { duration: root.motionEnabled ? 180 : 0; easing.type: Easing.OutCubic }
    }
    Behavior on scale {
      NumberAnimation { duration: root.motionEnabled ? 180 : 0; easing.type: Easing.OutCubic }
    }
  }

  Component.onCompleted: {
    if (root.forcedOpen && root.providers.length > 0) root.hoveredIndex = 0
  }
}
