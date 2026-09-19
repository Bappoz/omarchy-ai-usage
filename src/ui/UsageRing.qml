import QtQuick
import QtQuick.Shapes

Item {
  id: root

  property string providerId: "codex"
  property var usedPercent: null
  property bool stale: false
  property bool animationsEnabled: true
  property real uiScale: 1
  property string accessibleName: "Usage"

  readonly property bool hasReading: typeof usedPercent === "number" && isFinite(usedPercent)
  readonly property real safeUsed: hasReading ? Math.max(0, Math.min(100, usedPercent)) : 0
  readonly property real targetFraction: safeUsed / 100
  property real animatedFraction: 0

  readonly property real designScale: (44 / 117) * uiScale
  readonly property real trackStroke: 15.5 * designScale
  readonly property real progressStroke: 8 * designScale
  readonly property real ringRadius: Math.max(1, (Math.min(width, height) - trackStroke) / 2)
  readonly property color trackColor: "#303030"
  readonly property color progressColor: safeUsed < 50
    ? "#00ff88"
    : (safeUsed < 70 ? "#f2ff00" : "#ff3f00")

  Accessible.role: Accessible.ProgressBar
  Accessible.name: root.accessibleName
  Accessible.description: root.hasReading
    ? Math.round(root.safeUsed) + " percent used"
    : "Usage unavailable"

  onTargetFractionChanged: animatedFraction = targetFraction
  Component.onCompleted: animatedFraction = targetFraction

  Behavior on animatedFraction {
    NumberAnimation {
      duration: root.animationsEnabled ? 900 : 0
      easing.type: Easing.OutCubic
    }
  }

  Shape {
    anchors.fill: parent
    opacity: root.stale ? 0.45 : 1
    preferredRendererType: Shape.CurveRenderer

    ShapePath {
      strokeWidth: root.trackStroke
      strokeColor: root.trackColor
      fillColor: "transparent"
      capStyle: ShapePath.RoundCap

      PathAngleArc {
        centerX: root.width / 2
        centerY: root.height / 2
        radiusX: root.ringRadius
        radiusY: root.ringRadius
        startAngle: -90
        sweepAngle: 359.9
      }
    }

    ShapePath {
      strokeWidth: root.progressStroke
      strokeColor: root.hasReading && root.animatedFraction > 0
        ? root.progressColor
        : "transparent"
      fillColor: "transparent"
      capStyle: ShapePath.RoundCap

      PathAngleArc {
        centerX: root.width / 2
        centerY: root.height / 2
        radiusX: root.ringRadius
        radiusY: root.ringRadius
        startAngle: -90
        sweepAngle: 359.9 * Math.max(0, Math.min(1, root.animatedFraction))
      }
    }
  }

  ProviderGlyph {
    anchors.centerIn: parent
    width: 46 * root.designScale
    height: width
    providerId: root.providerId
    opacity: root.stale ? 0.45 : (root.safeUsed >= 100 ? 0.35 : 1)
  }
}
