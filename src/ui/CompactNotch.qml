import QtQuick

Item {
  id: root

  property string edge: "right"
  property var providers: []
  property bool unfolded: false
  property int activeIndex: -1
  property bool previewMode: false
  property real uiScale: 1
  property bool animationsEnabled: true
  property bool showProviderLabel: false
  property bool showPercentage: true

  signal surfaceHovered(bool hovered)
  signal providerHovered(int index, bool hovered)
  signal providerActivated(int index)
  signal bodyActivated()

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

  implicitWidth: verticalEdge ? fullDepth : fullLength
  implicitHeight: verticalEdge ? fullLength : fullDepth

  readonly property real surfaceX: verticalEdge
    ? (edge === "right" ? width - drawnDepth : 0)
    : (width - drawnLength) / 2
  readonly property real surfaceY: verticalEdge
    ? (height - drawnLength) / 2
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
    NumberAnimation {
      duration: root.animationsEnabled ? (root.unfolded ? 420 : 220) : 0
      easing.type: root.unfolded ? Easing.OutCubic : Easing.InCubic
    }
  }

  EdgeNotchSurface {
    id: surface
    x: root.surfaceX
    y: root.surfaceY
    width: root.surfaceWidth
    height: root.surfaceHeight
    edge: root.edge
  }

  MouseArea {
    id: bodyMouse
    x: root.inputX
    y: root.inputY
    width: root.inputWidth
    height: root.inputHeight
    hoverEnabled: true
    cursorShape: root.unfolded ? Qt.ArrowCursor : Qt.PointingHandCursor
    onContainsMouseChanged: root.surfaceHovered(containsMouse)
    onClicked: root.bodyActivated()
  }

  Repeater {
    model: root.providers

    delegate: Item {
      id: cell

      required property var modelData
      required property int index
      property real reveal: root.unfolded ? 1 : 0
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
          uiScale: root.uiScale
          accessibleName: String(cell.modelData.displayName || "Provider") + " usage"
        }

        Text {
          anchors.horizontalCenter: parent.horizontalCenter
          width: root.ringDiameter + 18 * root.uiScale
          height: root.percentLineHeight
          horizontalAlignment: Text.AlignHCenter
          verticalAlignment: Text.AlignVCenter
          visible: root.showProviderLabel || root.showPercentage
          text: {
            var label = root.showProviderLabel ? String(cell.modelData.displayName || "Provider") : ""
            var percent = ""
            if (root.showPercentage) {
              percent = typeof cell.modelData.usedPercent === "number" && isFinite(cell.modelData.usedPercent)
                ? Math.round(Math.max(0, Math.min(100, cell.modelData.usedPercent))) + "%"
                : "—"
            }
            return label && percent ? label + " " + percent : (label || percent)
          }
          textFormat: Text.PlainText
          color: "#ffffff"
          opacity: cell.modelData.stale ? 0.45 : 1
          font.family: "sans-serif"
          font.pixelSize: 14 * root.uiScale
          font.weight: Font.DemiBold
          font.letterSpacing: -0.15
        }
      }

      MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        enabled: cell.enabled
        onContainsMouseChanged: root.providerHovered(cell.index, containsMouse)
        onClicked: root.providerActivated(cell.index)
      }

      Accessible.role: Accessible.Button
      Accessible.name: String(modelData.displayName || "Provider")
      Accessible.description: typeof modelData.usedPercent === "number"
        ? Math.round(modelData.usedPercent) + " percent used"
        : "Usage unavailable"
      Accessible.onPressAction: root.providerActivated(index)
    }
  }
}
