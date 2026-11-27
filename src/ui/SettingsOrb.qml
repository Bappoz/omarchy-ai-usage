import QtQuick
import QtQuick.Shapes
import "NotchGeometry.js" as Geometry

Item {
  id: root
  property string edge: "right"
  property real uiScale: 1
  property real surfaceOpacity: 1.0
  property bool animationsEnabled: true
  property bool revealed: false
  property bool selected: false
  property bool hovered: false
  property real wake: hovered || selected ? 1 : 0
  property real separation: revealed ? 1 : 0
  property int spins: 0
  readonly property real unit: 44 / 117 * uiScale
  readonly property real flare: 103 * unit
  readonly property real stroke: 18 * unit
  readonly property real clearance: 39 * unit
  readonly property real discDiameter: 124 * unit
  readonly property real hotZone: 152 * unit
  width: hotZone
  height: hotZone
  visible: separation > 0.001
  enabled: revealed
  signal activated()
  signal hoverChanged(bool value)

  Behavior on wake {
    NumberAnimation { duration: root.animationsEnabled ? (root.wake > 0 ? 360 : 500) : 0; easing.type: Easing.InOutCubic }
  }
  // Absorb back into the notch with NotchMotion.merge (ease-in 200ms) so the
  // orb finishes entering the black before the silhouette begins folding shut.
  Behavior on separation {
    NumberAnimation {
      duration: root.animationsEnabled ? (root.revealed ? 440 : 200) : 0
      easing.type: root.revealed ? Easing.OutCubic : Easing.InCubic
    }
  }

  // A round-ended line grows from the arc's middle into the disc itself.
  // There is no separate disc crossfade, and leaving reverses the same morph.
  function pathData() {
    var p = Math.max(0, Math.min(1, wake))
    var half = Math.max(0.0001, (1 - p) / 2)
    var slide = (1 - separation) * (clearance + stroke)
    var shift = 1 - Math.min(1, (1 - p) / 0.55)
    var mid = Geometry.FLARE[32]
    var mx = flare * mid.v - Math.sin(mid.heading) * clearance
    var my = flare * mid.u - flare + Math.cos(mid.heading) * clearance
    var result = ""
    for (var i = 0; i <= 48; i++) {
      var share = 0.5 - half + (2 * half * i / 48)
      var index = Math.min(63, Math.floor(share * 64))
      var blend = share * 64 - index
      var a = Geometry.FLARE[index], b = Geometry.FLARE[index + 1]
      var q = {u: a.u + (b.u - a.u) * blend, v: a.v + (b.v - a.v) * blend,
        heading: a.heading + (b.heading - a.heading) * blend}
      var u = flare * q.v - Math.sin(q.heading) * clearance - mx * shift
      var v = flare * q.u - flare + Math.cos(q.heading) * clearance - my * shift
      u += slide / Math.sqrt(2)
      v -= slide / Math.sqrt(2)
      var mapped = Geometry.point(edge, u, v, 0)
      result += (i === 0 ? "M " : " L ") + Number(width / 2 + Number(mapped.x)).toFixed(4) + " " + Number(height / 2 + Number(mapped.y)).toFixed(4)
    }
    return result
  }

  Shape {
    anchors.fill: parent
    preferredRendererType: Shape.CurveRenderer
    ShapePath {
      strokeColor: root.surfaceOpacity >= 0.999 ? "#000000" : Qt.rgba(0, 0, 0, Math.max(0.5, Math.min(1, root.surfaceOpacity)))
      strokeWidth: (root.stroke + (root.discDiameter - root.stroke) * root.wake) * root.separation
      fillColor: "transparent"
      capStyle: ShapePath.RoundCap
      joinStyle: ShapePath.RoundJoin
      PathSvg { path: root.pathData() }
    }
  }
  Image {
    anchors.centerIn: parent
    width: 56 * root.unit; height: width
    source: "../assets/icons/gear.svg"
    opacity: root.wake
    scale: (0.5 + root.wake / 2) * (orbMouse.pressed ? 0.84 : 1)
    rotation: -60 * (1 - root.wake) + root.spins * 360
    Behavior on rotation { enabled: root.animationsEnabled; SpringAnimation { spring: 3.5; damping: 0.4; epsilon: 0.1 } }
  }
  MouseArea {
    id: orbMouse
    anchors.fill: parent
    hoverEnabled: true
    cursorShape: Qt.PointingHandCursor
    onContainsMouseChanged: { root.hovered = containsMouse; root.hoverChanged(containsMouse) }
    onClicked: { root.spins++; root.activated() }
  }
  Accessible.role: Accessible.Button
  Accessible.name: root.selected ? "Close preferences" : "Open preferences"
  Accessible.onPressAction: { root.spins++; root.activated() }
}
