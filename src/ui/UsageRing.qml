import QtQuick
import QtQuick.Shapes
import "Usage.js" as Usage

Item {
  id: root

  property string providerId: "codex"
  property var usedPercent: null
  property bool stale: false
  property bool animationsEnabled: true
  // False while hidden: the ring rests empty and sweeps in when revealed.
  property bool active: true
  property bool hovered: false
  property bool pressed: false
  property real uiScale: 1
  property string accentColor: "auto"
  property string providerColor: "auto"
  property string accessibleName: "Usage"

  readonly property bool hasReading: typeof usedPercent === "number" && isFinite(usedPercent)
  readonly property real safeUsed: hasReading ? Math.max(0, Math.min(100, usedPercent)) : 0
  readonly property real targetFraction: active ? safeUsed / 100 : 0
  property real animatedFraction: 0

  readonly property real designScale: (44 / 117) * uiScale
  readonly property real trackStroke: 15.5 * designScale
  readonly property real progressStroke: 8 * designScale
  readonly property real ringRadius: Math.max(1, (Math.min(width, height) - trackStroke) / 2)
  readonly property color trackColor: "#303030"
  property color progressColor: Usage.usageColor(safeUsed, accentColor, providerColor)

  Accessible.role: Accessible.ProgressBar
  Accessible.name: root.accessibleName
  Accessible.description: root.hasReading
    ? Math.round(root.safeUsed) + " percent used"
    : "Usage unavailable"

  onTargetFractionChanged: animatedFraction = targetFraction
  Component.onCompleted: animatedFraction = targetFraction

  // Spring with light overshoot (Sileo-style); the sweep is clamped to 0..1.
  Behavior on animatedFraction {
    enabled: root.animationsEnabled
    SpringAnimation { spring: 2.4; damping: 0.28; epsilon: 0.0005 }
  }

  Behavior on progressColor {
    ColorAnimation { duration: root.animationsEnabled ? 400 : 0 }
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
    scale: root.pressed ? 0.88 : (root.hovered ? 1.14 : 1)
    Behavior on scale {
      enabled: root.animationsEnabled
      SpringAnimation { spring: 4; damping: 0.35; epsilon: 0.001 }
    }
  }
}
