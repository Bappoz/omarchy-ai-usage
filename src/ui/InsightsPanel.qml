import QtQuick
import QtQuick.Layouts
import QtQuick.Shapes
import "Usage.js" as Usage

Item {
  id: root

  property string providerId: "claude"
  property string providerName: "Claude"
  property var insights: null
  property bool failed: false
  property bool previewMode: false
  property real uiScale: 1
  property bool animationsEnabled: true
  property string accentColor: "auto"
  property bool shown: false
  property real nowMs: Date.now()
  signal panelHovered(bool hovered)

  readonly property real designScale: (44 / 117) * uiScale
  readonly property real bodyWidth: 600 * designScale
  readonly property real corner: 49.5 * designScale
  readonly property real padding: 32 * designScale
  readonly property real sectionGap: 17 * designScale
  readonly property real chartHeight: 46 * uiScale
  readonly property color accent: Usage.chartColor(providerId, accentColor)

  readonly property var totals: insights && insights.totals ? insights.totals : ({})
  readonly property bool hasData: insights !== null && insights !== undefined
    && insights.available === true && Number(totals.last7dTokens) > 0
  readonly property var current: insights && insights.currentModel ? insights.currentModel : null
  readonly property bool recentlyActive: current !== null
    && root.nowMs - new Date(String(current.lastSeen)).getTime() < 15 * 60000
  readonly property var series: {
    var out = []
    var hourly = insights && Array.isArray(insights.hourly) ? insights.hourly : []
    for (var i = 0; i < hourly.length; i++) out.push(hourly[i].tokens)
    return out
  }
  readonly property var curve: Usage.smoothPath(series, content.width, chartHeight)
  readonly property var models: Usage.collapseModels(insights ? insights.models : [], 4)

  // 0..1 clock driving the staggered section entrance; `draw` drives the chart.
  property real enter: 0
  property real draw: 0
  property int hoverIndex: -1

  function reveal(index) {
    return Math.max(0, Math.min(1, (root.enter - index * 0.13) / 0.4))
  }

  function shade(index) {
    return Qt.rgba(root.accent.r, root.accent.g, root.accent.b, Math.max(0.22, 1 - index * 0.24))
  }

  function replay() {
    root.hoverIndex = -1
    enterAnimation.restart()
    chartAnimation.restart()
  }

  function message() {
    if (root.failed) return "Activity could not be read."
    if (!root.insights) return "Reading activity…"
    if (root.insights.available !== true) return "No local " + root.providerName + " session logs found."
    return "No activity in the last 7 days."
  }

  implicitWidth: bodyWidth
  implicitHeight: content.implicitHeight + 2 * padding

  onShownChanged: {
    if (shown) replay()
    else { enter = 0; draw = 0 }
  }
  onProviderIdChanged: if (shown) replay()
  onHasDataChanged: if (shown && hasData) replay()

  Timer {
    interval: 30000
    repeat: true
    running: root.shown
    onTriggered: root.nowMs = Date.now()
  }

  NumberAnimation {
    id: enterAnimation
    target: root
    property: "enter"
    from: 0
    to: 1
    duration: root.animationsEnabled ? 900 : 0
  }

  SequentialAnimation {
    id: chartAnimation
    PauseAnimation { duration: root.animationsEnabled ? 200 : 0 }
    NumberAnimation {
      target: root
      property: "draw"
      from: 0
      to: 1
      duration: root.animationsEnabled ? 900 : 0
      easing.type: Easing.OutCubic
    }
  }

  Rectangle {
    anchors.fill: parent
    radius: root.corner
    color: "#000000"
  }

  MouseArea {
    anchors.fill: parent
    hoverEnabled: true
    acceptedButtons: Qt.NoButton
    onContainsMouseChanged: root.panelHovered(containsMouse)
  }

  Column {
    id: content
    x: root.padding
    y: root.padding
    width: root.bodyWidth - 2 * root.padding
    spacing: 0

    // Header: title + current model chip
    RowLayout {
      width: parent.width
      spacing: 8 * root.uiScale
      opacity: root.reveal(0)
      transform: Translate { y: (1 - parent.opacity) * 6 * root.uiScale }

      Text {
        Layout.fillWidth: true
        text: "Activity"
        textFormat: Text.PlainText
        color: "#ffffff"
        font.family: "sans-serif"
        font.pixelSize: 14 * root.uiScale
        font.weight: Font.DemiBold
        font.letterSpacing: -0.15
      }

      Rectangle {
        visible: root.current !== null
        Layout.preferredHeight: 16 * root.uiScale
        Layout.preferredWidth: chipRow.implicitWidth + 12 * root.uiScale
        radius: height / 2
        color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.16)
        Behavior on color { ColorAnimation { duration: root.animationsEnabled ? 250 : 0 } }

        Row {
          id: chipRow
          anchors.centerIn: parent
          spacing: 4 * root.uiScale

          Rectangle {
            visible: root.recentlyActive
            anchors.verticalCenter: parent.verticalCenter
            width: 5 * root.uiScale
            height: width
            radius: width / 2
            color: root.accent
            SequentialAnimation on opacity {
              running: root.shown && root.recentlyActive && root.animationsEnabled
              loops: Animation.Infinite
              NumberAnimation { to: 0.35; duration: 900; easing.type: Easing.InOutSine }
              NumberAnimation { to: 1; duration: 900; easing.type: Easing.InOutSine }
            }
          }

          Text {
            anchors.verticalCenter: parent.verticalCenter
            text: {
              if (!root.current) return ""
              var label = Usage.modelLabel(root.current.name)
              if (root.current.effort) label += " · " + root.current.effort
              if (!root.recentlyActive) label += " · " + Usage.agoLabel(root.current.lastSeen, root.nowMs)
              return label
            }
            textFormat: Text.PlainText
            color: root.accent
            font.family: "sans-serif"
            font.pixelSize: 8 * root.uiScale
            font.weight: Font.DemiBold
          }
        }
      }
    }

    Item { width: 1; height: root.sectionGap }

    Text {
      visible: !root.hasData
      width: parent.width
      text: root.message()
      textFormat: Text.PlainText
      wrapMode: Text.Wrap
      color: "#808080"
      font.family: "sans-serif"
      font.pixelSize: 10 * root.uiScale
      opacity: root.reveal(1)
    }

    // Chart
    Column {
      visible: root.hasData
      width: parent.width
      spacing: 6 * root.uiScale
      opacity: root.reveal(1)
      transform: Translate { y: (1 - parent.opacity) * 6 * root.uiScale }

      RowLayout {
        width: parent.width

        Text {
          Layout.fillWidth: true
          text: "Tokens · 24h"
          textFormat: Text.PlainText
          color: "#808080"
          font.family: "sans-serif"
          font.pixelSize: 9 * root.uiScale
        }

        Text {
          text: root.hoverIndex >= 0 && root.hoverIndex < root.series.length
            ? Usage.hourLabel(root.insights.hourly[root.hoverIndex].start) + "  "
              + Usage.compactNumber(root.series[root.hoverIndex])
            : Usage.compactNumber(root.totals.last24hTokens)
          textFormat: Text.PlainText
          color: "#ffffff"
          font.family: "sans-serif"
          font.pixelSize: 9 * root.uiScale
          font.weight: Font.DemiBold
        }
      }

      Item {
        id: chart
        width: parent.width
        height: root.chartHeight

        Rectangle {
          anchors.bottom: parent.bottom
          width: parent.width
          height: 1
          color: "#2d2d2d"
        }

        Item {
          width: chart.width * root.draw
          height: chart.height
          clip: true

          Shape {
            width: chart.width
            height: chart.height
            preferredRendererType: Shape.CurveRenderer

            ShapePath {
              strokeWidth: -1
              fillGradient: LinearGradient {
                y1: 0
                y2: chart.height
                GradientStop { position: 0; color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0.34) }
                GradientStop { position: 1; color: Qt.rgba(root.accent.r, root.accent.g, root.accent.b, 0) }
              }
              PathSvg { path: root.curve.area }
            }

            ShapePath {
              strokeWidth: 1.6 * root.uiScale
              strokeColor: root.accent
              fillColor: "transparent"
              capStyle: ShapePath.RoundCap
              joinStyle: ShapePath.RoundJoin
              PathSvg { path: root.curve.line }
            }
          }
        }

        // Latest reading, with a soft pulse.
        Rectangle {
          readonly property var point: root.curve.points.length > 0
            ? root.curve.points[root.curve.points.length - 1]
            : null
          visible: point !== null && root.draw > 0.98
          x: point ? point.x - width / 2 : 0
          y: point ? point.y - height / 2 : 0
          width: 5 * root.uiScale
          height: width
          radius: width / 2
          color: root.accent

          Rectangle {
            anchors.centerIn: parent
            width: parent.width
            height: width
            radius: width / 2
            color: "transparent"
            border.width: 1
            border.color: root.accent
            NumberAnimation on scale {
              running: root.shown && root.animationsEnabled && parent.visible
              loops: Animation.Infinite
              from: 1
              to: 3
              duration: 1600
              easing.type: Easing.OutCubic
            }
            NumberAnimation on opacity {
              running: root.shown && root.animationsEnabled && parent.visible
              loops: Animation.Infinite
              from: 0.55
              to: 0
              duration: 1600
              easing.type: Easing.OutCubic
            }
          }
        }

        // Hover crosshair
        Rectangle {
          readonly property var point: root.hoverIndex >= 0 && root.hoverIndex < root.curve.points.length
            ? root.curve.points[root.hoverIndex]
            : null
          visible: point !== null
          x: point ? point.x - width / 2 : 0
          width: 1
          height: chart.height
          color: "#ffffff"
          opacity: 0.22
        }

        Rectangle {
          readonly property var point: root.hoverIndex >= 0 && root.hoverIndex < root.curve.points.length
            ? root.curve.points[root.hoverIndex]
            : null
          visible: point !== null
          x: point ? point.x - width / 2 : 0
          y: point ? point.y - height / 2 : 0
          width: 5 * root.uiScale
          height: width
          radius: width / 2
          color: "#ffffff"
        }

        MouseArea {
          anchors.fill: parent
          hoverEnabled: true
          acceptedButtons: Qt.NoButton
          onPositionChanged: function(mouse) {
            var count = root.series.length
            root.hoverIndex = count < 2
              ? -1
              : Math.max(0, Math.min(count - 1, Math.round(mouse.x / width * (count - 1))))
          }
          onExited: root.hoverIndex = -1
        }
      }
    }

    Item { visible: root.hasData; width: 1; height: root.sectionGap }

    // Stat tiles
    RowLayout {
      visible: root.hasData
      width: parent.width
      spacing: 6 * root.uiScale
      opacity: root.reveal(2)
      transform: Translate { y: (1 - parent.opacity) * 6 * root.uiScale }

      Repeater {
        model: [
          { "label": "Tokens 24h", "value": Usage.compactNumber(root.totals.last24hTokens) },
          { "label": "Requests 24h", "value": Usage.compactNumber(root.totals.last24hRequests) },
          { "label": "Tokens 7d", "value": Usage.compactNumber(root.totals.last7dTokens) }
        ]

        delegate: Rectangle {
          required property var modelData
          Layout.fillWidth: true
          Layout.preferredHeight: 34 * root.uiScale
          radius: 8 * root.uiScale
          color: "#141414"

          Column {
            anchors.centerIn: parent
            spacing: 1 * root.uiScale

            Text {
              anchors.horizontalCenter: parent.horizontalCenter
              text: modelData.value
              textFormat: Text.PlainText
              color: "#ffffff"
              font.family: "sans-serif"
              font.pixelSize: 12 * root.uiScale
              font.weight: Font.DemiBold
              font.letterSpacing: -0.1
            }

            Text {
              anchors.horizontalCenter: parent.horizontalCenter
              text: modelData.label
              textFormat: Text.PlainText
              color: "#808080"
              font.family: "sans-serif"
              font.pixelSize: 7 * root.uiScale
            }
          }
        }
      }
    }

    Item { visible: root.hasData; width: 1; height: root.sectionGap }

    // Per-model share
    Column {
      visible: root.hasData && root.models.length > 0
      width: parent.width
      spacing: 7 * root.uiScale
      opacity: root.reveal(3)
      transform: Translate { y: (1 - parent.opacity) * 6 * root.uiScale }

      RowLayout {
        width: parent.width

        Text {
          Layout.fillWidth: true
          text: "By model"
          textFormat: Text.PlainText
          color: "#808080"
          font.family: "sans-serif"
          font.pixelSize: 9 * root.uiScale
        }

        Text {
          text: "7 days"
          textFormat: Text.PlainText
          color: "#808080"
          font.family: "sans-serif"
          font.pixelSize: 9 * root.uiScale
        }
      }

      Row {
        id: shareBar
        width: parent.width
        height: 6 * root.uiScale
        spacing: 2 * root.uiScale

        Repeater {
          model: root.models

          delegate: Rectangle {
            required property var modelData
            required property int index
            width: Math.max(3 * root.uiScale,
              (shareBar.width - shareBar.spacing * (root.models.length - 1)) * modelData.share)
              * root.reveal(3)
            height: shareBar.height
            radius: height / 2
            color: root.shade(index)
          }
        }
      }

      Column {
        width: parent.width
        spacing: 4 * root.uiScale

        Repeater {
          model: root.models

          delegate: RowLayout {
            required property var modelData
            required property int index
            width: parent.width
            spacing: 6 * root.uiScale

            Rectangle {
              Layout.preferredWidth: 6 * root.uiScale
              Layout.preferredHeight: 6 * root.uiScale
              radius: width / 2
              color: root.shade(index)
            }

            Text {
              Layout.fillWidth: true
              text: modelData.name === "other" ? "Other" : Usage.modelLabel(modelData.name)
              textFormat: Text.PlainText
              elide: Text.ElideRight
              color: "#ffffff"
              font.family: "sans-serif"
              font.pixelSize: 10 * root.uiScale
            }

            Text {
              text: Usage.compactNumber(modelData.tokens)
              textFormat: Text.PlainText
              color: "#808080"
              font.family: "sans-serif"
              font.pixelSize: 9 * root.uiScale
            }

            Text {
              Layout.preferredWidth: 28 * root.uiScale
              horizontalAlignment: Text.AlignRight
              text: Math.round(modelData.share * 100) + "%"
              textFormat: Text.PlainText
              color: "#ffffff"
              font.family: "sans-serif"
              font.pixelSize: 10 * root.uiScale
              font.weight: Font.DemiBold
            }
          }
        }
      }
    }

    Item { visible: root.hasData; width: 1; height: 9 * root.uiScale }

    Text {
      visible: root.hasData
      width: parent.width
      text: root.previewMode ? "PREVIEW · synthetic data" : "Fresh tokens · cache reads excluded"
      textFormat: Text.PlainText
      color: "#555555"
      font.family: "sans-serif"
      font.pixelSize: 7.5 * root.uiScale
      opacity: root.reveal(3)
    }
  }
}
