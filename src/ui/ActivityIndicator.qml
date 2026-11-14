import QtQuick
import QtQuick.Shapes

Item {
  id: root
  property string activityState: "idle"
  property string style: "arc"
  property color brandColor: "#ffffff"
  property bool animationsEnabled: true
  property bool active: true
  property real phase: 0
  readonly property bool busy: activityState === "busy"
  readonly property bool waiting: activityState === "waiting"
  readonly property bool breathing: busy && style === "breath"
  readonly property color tint: waiting ? "#ffb340" : (activityState === "success" ? "#00ff88" : "#ffffff")
  visible: active && (busy || waiting || activityState === "success")

  NumberAnimation on phase {
    from: 0; to: 360; duration: 1800; loops: Animation.Infinite
    running: root.visible && root.busy && !root.breathing && root.animationsEnabled
  }

  Rectangle {
    anchors.centerIn: parent
    width: parent.width * 0.75
    height: width
    radius: width / 2
    visible: root.breathing
    color: root.brandColor
    opacity: 0.3
    SequentialAnimation on opacity {
      running: root.visible && root.breathing && root.animationsEnabled
      loops: Animation.Infinite
      NumberAnimation { from: 0.12; to: 0.4; duration: 900; easing.type: Easing.InOutSine }
      NumberAnimation { from: 0.4; to: 0.12; duration: 900; easing.type: Easing.InOutSine }
    }
  }

  Shape {
    anchors.fill: parent
    visible: !root.breathing
    rotation: root.busy ? root.phase : 0
    preferredRendererType: Shape.CurveRenderer
    opacity: 1
    ShapePath {
      strokeWidth: Math.max(1, root.width / 38)
      strokeColor: root.tint
      fillColor: "transparent"
      capStyle: ShapePath.RoundCap
      PathAngleArc {
        centerX: root.width / 2; centerY: root.height / 2
        radiusX: root.width * 0.34; radiusY: root.height * 0.34
        startAngle: -90; sweepAngle: root.busy ? 90 : 359.9
      }
    }
    SequentialAnimation on opacity {
      running: root.visible && root.waiting && root.animationsEnabled
      loops: Animation.Infinite
      NumberAnimation { from: 1; to: 0.3; duration: 850; easing.type: Easing.InOutSine }
      NumberAnimation { from: 0.3; to: 1; duration: 850; easing.type: Easing.InOutSine }
    }
  }
}
