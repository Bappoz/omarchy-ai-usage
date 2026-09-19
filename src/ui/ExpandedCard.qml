import QtQuick
import QtQuick.Layouts
import QtQuick.Shapes

Item {
  id: root

  property string edge: "right"
  property real tailCenter: 0
  property var snapshot: null
  property string providerId: "codex"
  property bool loading: false
  property bool previewMode: false
  property real uiScale: 1
  property bool animationsEnabled: true
  property bool showResetTimer: true
  property bool settingsOpen: false
  property var preferences: ({})
  signal cardHovered(bool hovered)
  signal settingsRequested()
  signal preferenceChanged(string key, var value)

  readonly property bool horizontalEdge: edge === "top" || edge === "bottom"
  readonly property real designScale: (44 / 117) * uiScale
  readonly property real bodyWidth: 600 * designScale
  readonly property real cardCorner: 49.5 * designScale
  readonly property real cardPadding: 32 * designScale
  readonly property real tailLength: 75 * designScale
  readonly property real tailHeight: 87 * designScale
  readonly property real barHeight: 10.5 * designScale
  readonly property real headerGap: 17 * designScale
  readonly property real headerToBlock: 21 * designScale
  readonly property real labelToBar: 16.8 * designScale
  readonly property real barToUsed: 17.8 * designScale
  readonly property real blockSpacing: 20 * designScale
  readonly property real bodyHeight: content.implicitHeight + 2 * cardPadding
  readonly property real bodyX: edge === "left" ? tailLength : 0
  readonly property real bodyY: edge === "top" ? tailLength : 0
  readonly property var windows: snapshot && Array.isArray(snapshot.windows)
    ? snapshot.windows
    : []
  readonly property string status: snapshot
    ? String(snapshot.status || "UNAVAILABLE")
    : "UNAVAILABLE"
  readonly property string providerName: snapshot
    ? String(snapshot.displayName || "Codex")
    : "Codex"

  implicitWidth: horizontalEdge ? bodyWidth : bodyWidth + tailLength
  implicitHeight: horizontalEdge ? bodyHeight + tailLength : bodyHeight

  function statusLabel() {
    if (root.loading && root.status === "LOADING") return "Reading usage"
    if (root.status === "ACTIVE") return "Active"
    if (root.status === "STALE") return "Last known reading"
    if (root.status === "NEEDS_AUTH") return "Sign in required"
    if (root.status === "RATE_LIMITED") return "Limit reached"
    if (root.status === "ERROR") return "Refresh failed"
    if (root.status === "LOADING") return "Reading usage"
    if (root.status === "UNAVAILABLE") return "Usage unavailable"
    return "Usage unavailable"
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

  function usageColor(used) {
    if (used === null) return "#808080"
    return used < 50 ? "#00ff88" : (used < 70 ? "#f2ff00" : "#ff3f00")
  }

  function formatReset(window) {
    if (!root.showResetTimer) return ""
    if (window && window.resetCopy) return String(window.resetCopy)
    var value = window ? window.resetAt : null
    if (value === null || value === undefined || String(value) === "") return ""
    var parsed = new Date(String(value))
    if (isNaN(parsed.getTime())) return ""
    var minutes = Math.max(0, Math.round((parsed.getTime() - Date.now()) / 60000))
    if (minutes < 60) return "Resets in " + minutes + " min"
    if (minutes < 24 * 60) {
      var hours = Math.floor(minutes / 60)
      var rest = minutes % 60
      return "Resets in " + hours + "h" + (rest > 0 ? " " + rest + " min" : "")
    }
    return "Resets " + Qt.formatDateTime(parsed, "ddd h:mm AP")
  }

  function tailPath() {
    var w = tail.width
    var h = tail.height
    if (root.edge === "right") {
      return "M 0 0 C 0 " + (h * 0.25) + " " + (w * 0.58) + " " + (h * 0.38)
        + " " + w + " " + (h / 2)
        + " C " + (w * 0.58) + " " + (h * 0.62) + " 0 " + (h * 0.75) + " 0 " + h + " Z"
    }
    if (root.edge === "left") {
      return "M " + w + " 0 C " + w + " " + (h * 0.25) + " " + (w * 0.42) + " " + (h * 0.38)
        + " 0 " + (h / 2)
        + " C " + (w * 0.42) + " " + (h * 0.62) + " " + w + " " + (h * 0.75) + " " + w + " " + h + " Z"
    }
    if (root.edge === "top") {
      return "M 0 " + h + " C " + (w * 0.25) + " " + h + " " + (w * 0.38) + " " + (h * 0.42)
        + " " + (w / 2) + " 0"
        + " C " + (w * 0.62) + " " + (h * 0.42) + " " + (w * 0.75) + " " + h + " " + w + " " + h + " Z"
    }
    return "M 0 0 C " + (w * 0.25) + " 0 " + (w * 0.38) + " " + (h * 0.58)
      + " " + (w / 2) + " " + h
      + " C " + (w * 0.62) + " " + (h * 0.58) + " " + (w * 0.75) + " 0 " + w + " 0 Z"
  }

  Shape {
    id: tail
    x: root.edge === "left" ? 0
      : (root.edge === "right"
        ? root.bodyWidth - 1
        : Math.max(root.cardCorner, Math.min(root.bodyWidth - width - root.cardCorner, root.tailCenter - width / 2)))
    y: root.edge === "top" ? 0
      : (root.edge === "bottom"
        ? root.bodyHeight - 1
        : Math.max(root.cardCorner, Math.min(root.bodyHeight - height - root.cardCorner, root.tailCenter - height / 2)))
    width: root.horizontalEdge ? root.tailHeight : root.tailLength + 1
    height: root.horizontalEdge ? root.tailLength + 1 : root.tailHeight
    preferredRendererType: Shape.CurveRenderer

    ShapePath {
      strokeWidth: -1
      fillColor: "#000000"
      PathSvg { path: root.tailPath() }
    }
  }

  Rectangle {
    x: root.bodyX
    y: root.bodyY
    width: root.bodyWidth
    height: root.bodyHeight
    radius: root.cardCorner
    color: "#000000"
  }

  Column {
    id: content
    x: root.bodyX + root.cardPadding
    y: root.bodyY + root.cardPadding
    width: root.bodyWidth - 2 * root.cardPadding
    spacing: 0

    RowLayout {
      width: parent.width
      spacing: root.headerGap

      ProviderGlyph {
        Layout.preferredWidth: 46 * root.designScale
        Layout.preferredHeight: 46 * root.designScale
        providerId: root.providerId
      }

      Text {
        Layout.fillWidth: true
        text: root.providerName + " Usage"
        textFormat: Text.PlainText
        color: "#ffffff"
        elide: Text.ElideRight
        font.family: "sans-serif"
        font.pixelSize: 14 * root.uiScale
        font.weight: Font.DemiBold
        font.letterSpacing: -0.15
      }

      Rectangle {
        Layout.preferredWidth: 24 * root.uiScale
        Layout.preferredHeight: 24 * root.uiScale
        radius: 8 * root.uiScale
        color: settingsMouse.containsMouse || root.settingsOpen ? "#202020" : "transparent"

        Image {
          anchors.centerIn: parent
          width: 14 * root.uiScale
          height: 14 * root.uiScale
          source: "../assets/icons/settings.svg"
          sourceSize.width: Math.round(width * 2)
          sourceSize.height: Math.round(height * 2)
          opacity: settingsMouse.containsMouse || root.settingsOpen ? 1 : 0.62
          rotation: root.settingsOpen ? 90 : 0
          Behavior on rotation {
            NumberAnimation { duration: root.animationsEnabled ? 180 : 0; easing.type: Easing.OutCubic }
          }
          Behavior on opacity {
            NumberAnimation { duration: root.animationsEnabled ? 120 : 0 }
          }
        }

        MouseArea {
          id: settingsMouse
          anchors.fill: parent
          hoverEnabled: true
          cursorShape: Qt.PointingHandCursor
          onClicked: root.settingsRequested()
        }

        Accessible.role: Accessible.Button
        Accessible.name: root.settingsOpen ? "Close preferences" : "Open preferences"
        Accessible.onPressAction: root.settingsRequested()
      }

      Text {
        visible: root.previewMode
        text: "PREVIEW"
        textFormat: Text.PlainText
        color: "#808080"
        font.family: "sans-serif"
        font.pixelSize: 8 * root.uiScale
        font.weight: Font.DemiBold
        font.letterSpacing: 0.6
      }
    }

    Item { width: 1; height: root.headerToBlock }

    Text {
      visible: !root.settingsOpen && root.windows.length === 0
      width: parent.width
      text: root.snapshot && root.snapshot.message
        ? String(root.snapshot.message)
        : root.statusLabel()
      textFormat: Text.PlainText
      wrapMode: Text.Wrap
      color: "#808080"
      font.family: "sans-serif"
      font.pixelSize: 10 * root.uiScale
    }

    Repeater {
      model: root.settingsOpen ? [] : root.windows

      delegate: Column {
        id: limitRow

        required property var modelData
        required property int index
        readonly property var used: root.usedPercent(modelData)
        width: content.width
        spacing: 0

        RowLayout {
          width: parent.width
          spacing: 8

          Text {
            Layout.fillWidth: true
            text: String(limitRow.modelData.name || "Usage limit")
            textFormat: Text.PlainText
            elide: Text.ElideRight
            color: "#ffffff"
            font.family: "sans-serif"
            font.pixelSize: 10 * root.uiScale
          }

          Text {
            text: root.formatReset(limitRow.modelData)
            textFormat: Text.PlainText
            color: "#808080"
            font.family: "sans-serif"
            font.pixelSize: 10 * root.uiScale
          }
        }

        Item { width: 1; height: root.labelToBar }

        Rectangle {
          width: parent.width
          height: root.barHeight
          radius: height / 2
          color: "#2d2d2d"

          Rectangle {
            width: limitRow.used === null
              ? 0
              : Math.min(parent.width, Math.max(root.barHeight, parent.width * limitRow.used / 100))
            height: parent.height
            radius: height / 2
            color: root.usageColor(limitRow.used)

            Behavior on width {
              NumberAnimation { duration: root.animationsEnabled ? 900 : 0; easing.type: Easing.OutCubic }
            }
          }
        }

        Item { width: 1; height: root.barToUsed }

        Text {
          text: limitRow.used === null ? "Usage unavailable" : Math.round(limitRow.used) + "% Used"
          textFormat: Text.PlainText
          color: "#ffffff"
          font.family: "sans-serif"
          font.pixelSize: 10 * root.uiScale
        }

        Item {
          width: 1
          height: limitRow.index < root.windows.length - 1 ? root.blockSpacing : 0
        }
      }
    }

    SettingsPane {
      visible: root.settingsOpen
      width: parent.width
      preferences: root.preferences
      uiScale: root.uiScale
      onPreferenceChanged: function(key, value) { root.preferenceChanged(key, value) }
    }
  }

  MouseArea {
    id: cardMouse
    anchors.fill: parent
    hoverEnabled: true
    acceptedButtons: Qt.NoButton
    onContainsMouseChanged: root.cardHovered(containsMouse)
  }
}
