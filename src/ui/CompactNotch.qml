import QtQuick
import "../model/Activity.js" as Activity

Item {
  id: root

  property string edge: "right"
  property var providers: []
  property bool unfolded: false
  property int activeIndex: -1
  property bool previewMode: false
  property real uiScale: 1
  property bool animationsEnabled: true
  property bool settingsOpen: false
  property string accentColor: "auto"
  property var providerColors: ({})
  property var sessions: []
  property string busyIndicator: "arc"
  property real dragStart: 0
  property real dragDistance: 0
  property real dragPrevious: 0

  signal surfaceHovered(bool hovered)
  signal providerHovered(int index, bool hovered)
  signal providerActivated(int index)
  signal bodyActivated()
  signal settingsRequested()
  signal contextRequested()
  signal offsetDragged(real delta)

  readonly property bool verticalEdge: edge === "left" || edge === "right"
  readonly property real designScale: (44 / 117) * uiScale
  readonly property real bodyDepthSide: 186 * designScale
  readonly property real ringDiameter: 117 * designScale
  readonly property real ringLabelGap: 26.9 * designScale
  readonly property real percentLineHeight: 18 * uiScale
  readonly property real cellExtent: ringDiameter + ringLabelGap + percentLineHeight
  readonly property real cellAlong: verticalEdge ? cellExtent : ringDiameter
  readonly property real cellSpacing: 83.5 * designScale
  readonly property real padTop: 69.5 * designScale
  readonly property real padBottom: 50.1 * designScale
  readonly property real padStart: verticalEdge ? padTop : (padTop + padBottom) / 2
  readonly property real padEnd: verticalEdge ? padBottom : (padTop + padBottom) / 2
  readonly property real curl: 103 * designScale
  readonly property real fullDepth: verticalEdge
    ? bodyDepthSide
    : 2 * ((bodyDepthSide - ringDiameter) / 2) + cellExtent
  readonly property real bodyLength: providers.length > 0
    ? padStart + providers.length * cellAlong + (providers.length - 1) * cellSpacing + padEnd
    : padStart + padEnd
  readonly property real fullLength: bodyLength + 2 * curl
  readonly property real pillDepth: 26 * designScale
  readonly property real pillLength: 210 * designScale

  property real openProgress: unfolded ? 1 : 0
  readonly property real easedProgress: Math.max(0, Math.min(1, openProgress))
  readonly property real drawnDepth: pillDepth + (fullDepth - pillDepth) * easedProgress
  readonly property real drawnLength: pillLength + (fullLength - pillLength) * easedProgress

  readonly property real orbReach: 152 * designScale / 2
  readonly property real orbCenterX: edge === "right" ? fullDepth - curl : (edge === "left" ? curl : fullLength)
  readonly property real orbCenterY: verticalEdge ? fullLength : (edge === "top" ? curl : fullDepth - curl)
  readonly property rect orbInputRect: Qt.rect(orbCenterX - orbReach, orbCenterY - orbReach, orbReach * 2, orbReach * 2)
  readonly property bool orbVisible: orb.visible
  readonly property bool orbSettling: orb.wake > 0.001
  implicitWidth: verticalEdge ? fullDepth : fullLength + orbReach
  implicitHeight: verticalEdge ? fullLength + orbReach : fullDepth

  readonly property real surfaceX: verticalEdge
    ? (edge === "right" ? width - drawnDepth : 0)
    : (fullLength - drawnLength) / 2
  readonly property real surfaceY: verticalEdge
    ? (fullLength - drawnLength) / 2
    : (edge === "bottom" ? height - drawnDepth : 0)
  readonly property real surfaceWidth: verticalEdge ? drawnDepth : drawnLength
  readonly property real surfaceHeight: verticalEdge ? drawnLength : drawnDepth
  readonly property real hotDepth: 90 * designScale

  readonly property real inputX: verticalEdge
    ? (edge === "right" ? Math.max(0, width - Math.max(drawnDepth, hotDepth)) : 0)
    : surfaceX
  readonly property real inputY: verticalEdge
    ? surfaceY
    : (edge === "bottom" ? Math.max(0, height - Math.max(drawnDepth, hotDepth)) : 0)
  readonly property real inputWidth: verticalEdge ? Math.max(drawnDepth, hotDepth) : drawnLength
  readonly property real inputHeight: verticalEdge ? drawnLength : Math.max(drawnDepth, hotDepth)

  function providerCenter(index) {
    return root.curl + root.padStart + root.ringDiameter / 2
      + index * (root.cellAlong + root.cellSpacing)
  }

  Behavior on openProgress {
    enabled: root.animationsEnabled
    SpringAnimation { spring: 3.8; damping: 0.38; epsilon: 0.001 }
  }

  EdgeNotchSurface {
    id: surface
    x: root.surfaceX
    y: root.surfaceY
    width: root.surfaceWidth
    height: root.surfaceHeight
    edge: root.edge
    uiScale: root.uiScale
  }

  MouseArea {
    id: bodyMouse
    x: root.inputX
    y: root.inputY
    width: root.inputWidth
    height: root.inputHeight
    hoverEnabled: true
    acceptedButtons: Qt.LeftButton | Qt.RightButton
    preventStealing: true
    cursorShape: root.unfolded ? Qt.ArrowCursor : Qt.PointingHandCursor
    onContainsMouseChanged: root.surfaceHovered(containsMouse)
    onPressed: function(mouse) {
      var scene = mapToItem(null, mouse.x, mouse.y)
      root.dragStart = root.verticalEdge ? scene.y : scene.x
      root.dragPrevious = root.dragStart
      root.dragDistance = 0
    }
    onPositionChanged: function(mouse) {
      if (pressed && (mouse.modifiers & Qt.AltModifier)) {
        var scene = mapToItem(null, mouse.x, mouse.y)
        var position = root.verticalEdge ? scene.y : scene.x
        root.dragDistance = position - root.dragStart
        if (Math.abs(root.dragDistance) > 3) root.offsetDragged(position - root.dragPrevious)
        root.dragPrevious = position
      }
    }
    onClicked: function(mouse) {
      if (Math.abs(root.dragDistance) > 3) return
      if (mouse.button === Qt.RightButton) root.contextRequested()
      else root.bodyActivated()
    }
  }

  Repeater {
    model: root.providers

    delegate: Item {
      id: cell

      required property var modelData
      required property int index
      // Rings wait for the silhouette to finish unfolding (openProgress is eased,
      // so 0.995 is visually complete); folding hides them immediately.
      property real reveal: root.unfolded && root.openProgress >= 0.995 ? 1 : 0
      readonly property real outwardX: root.edge === "right" ? 1 : (root.edge === "left" ? -1 : 0)
      readonly property real outwardY: root.edge === "bottom" ? 1 : (root.edge === "top" ? -1 : 0)

      x: root.verticalEdge ? 0 : root.providerCenter(index) - root.ringDiameter / 2
      y: root.verticalEdge ? root.providerCenter(index) - root.ringDiameter / 2 : 0
      width: root.verticalEdge ? root.fullDepth : root.ringDiameter
      height: root.verticalEdge ? root.cellExtent : root.fullDepth
      opacity: reveal
      enabled: reveal > 0.85
      z: 2

      transform: Translate {
        x: (1 - cell.reveal) * cell.outwardX * 10
        y: (1 - cell.reveal) * cell.outwardY * 10
      }

      Behavior on reveal {
        SequentialAnimation {
          PauseAnimation { duration: root.animationsEnabled && root.unfolded ? Math.min(cell.index * 45, 180) : 0 }
          NumberAnimation {
            duration: root.animationsEnabled ? (root.unfolded ? 360 : 150) : 0
            easing.type: Easing.OutCubic
          }
        }
      }

      Column {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        spacing: root.ringLabelGap

        UsageRing {
          anchors.horizontalCenter: parent.horizontalCenter
          width: root.ringDiameter
          height: width
          providerId: String(cell.modelData.id || "codex")
          usedPercent: cell.modelData.usedPercent
          stale: Boolean(cell.modelData.stale)
          animationsEnabled: root.animationsEnabled
          active: cell.reveal > 0.01
          hovered: cellMouse.containsMouse
          pressed: cellMouse.pressed
          uiScale: root.uiScale
          accentColor: root.accentColor
          providerColor: String((root.providerColors || ({}))[String(cell.modelData.id || "")] || "auto")
          accessibleName: String(cell.modelData.displayName || "Provider") + " usage"
          activityState: Activity.summary(root.sessions, String(cell.modelData.id)).state
          busyIndicator: root.busyIndicator
        }

        Text {
          anchors.horizontalCenter: parent.horizontalCenter
          width: root.ringDiameter + 18 * root.uiScale
          height: root.percentLineHeight
          horizontalAlignment: Text.AlignHCenter
          verticalAlignment: Text.AlignVCenter
          text: typeof cell.modelData.usedPercent === "number" ? Math.round(cell.modelData.usedPercent) + "%" : "—"
          textFormat: Text.PlainText
          color: "#ffffff"
          opacity: cell.modelData.stale ? 0.45 : 1
          font.family: "sans-serif"
          font.pixelSize: (27 / 0.714) * root.designScale
          font.weight: Font.DemiBold
          font.letterSpacing: -0.15
        }
      }

      MouseArea {
        id: cellMouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        enabled: cell.enabled
        onContainsMouseChanged: root.providerHovered(cell.index, containsMouse)
        acceptedButtons: Qt.LeftButton | Qt.RightButton
        onClicked: function(mouse) {
          if (mouse.button === Qt.RightButton) root.contextRequested()
          else root.providerActivated(cell.index)
        }
      }

      Accessible.role: Accessible.Button
      Accessible.name: String(modelData.displayName || "Provider")
      Accessible.description: typeof modelData.usedPercent === "number"
        ? Math.round(modelData.usedPercent) + " percent used"
        : "Usage unavailable"
      Accessible.onPressAction: root.providerActivated(index)
    }
  }

  SettingsOrb {
    id: orb
    x: root.orbCenterX - width / 2
    y: root.orbCenterY - height / 2
    z: 3
    edge: root.edge
    uiScale: root.uiScale
    animationsEnabled: root.animationsEnabled
    revealed: root.unfolded && root.openProgress >= 0.995
    selected: root.settingsOpen
    onHoverChanged: function(value) { root.surfaceHovered(value) }
    onActivated: root.settingsRequested()
  }
}
