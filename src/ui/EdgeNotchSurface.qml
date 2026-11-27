import QtQuick
import QtQuick.Shapes
import "NotchGeometry.js" as Geometry

// The canonical right-edge outline and its measurements are adapted from
// CodeNotch's MIT-licensed SideNotchShape at revision ec1a7e3. The shape is
// transformed onto every edge here so there is only one source of geometry.
Item {
  id: root

  property string edge: "right"
  property real uiScale: 1
  property real surfaceOpacity: 1.0
  property bool animationsEnabled: true

  readonly property real designScale: (44 / 117) * uiScale
  readonly property real wantedCurl: 103 * designScale
  readonly property real wantedCorner: 78.8 * designScale

  function point(u, v, depth) {
    if (root.edge === "left") return Qt.point(depth - u, v)
    if (root.edge === "top") return Qt.point(v, depth - u)
    if (root.edge === "bottom") return Qt.point(v, u)
    return Qt.point(u, v)
  }

  function pair(point) {
    return point.x.toFixed(3) + " " + point.y.toFixed(3)
  }

  function pathData() {
    var depth = Math.max(1, root.edge === "left" || root.edge === "right" ? root.width : root.height)
    var length = Math.max(1, root.edge === "left" || root.edge === "right" ? root.height : root.width)
    var wanted = Math.max(0, Math.min(root.wantedCorner, depth / 2))
    var curl = Math.max(0, Math.min(root.wantedCurl, length / 2, depth - wanted))
    var corner = Math.max(0, Math.min(wanted, (length - 2 * curl) / 2))
    var bodyBottom = length - curl
    var k = 0.5522847498

    var start = root.point(depth, 0, depth)
    var flareTopEnd = root.point(depth - curl, curl, depth)
    var cornerTopStart = root.point(corner, curl, depth)
    var cornerTop1 = root.point(corner - k * corner, curl, depth)
    var cornerTop2 = root.point(0, curl + corner - k * corner, depth)
    var cornerTopEnd = root.point(0, curl + corner, depth)
    var cornerBottomStart = root.point(0, bodyBottom - corner, depth)
    var cornerBottom1 = root.point(0, bodyBottom - corner + k * corner, depth)
    var cornerBottom2 = root.point(corner - k * corner, bodyBottom, depth)
    var cornerBottomEnd = root.point(corner, bodyBottom, depth)
    var flareBottomStart = root.point(depth - curl, bodyBottom, depth)
    var topFlare = ""
    var bottomFlare = ""
    for (var i = 1; i < Geometry.FLARE.length; i++) {
      var q = Geometry.FLARE[i]
      topFlare += " L " + root.pair(root.point(depth - curl * q.u, curl * q.v, depth))
      bottomFlare += " L " + root.pair(root.point(depth - curl + curl * q.v, bodyBottom + curl * q.u, depth))
    }

    return "M " + root.pair(start)
      + topFlare
      + " L " + root.pair(cornerTopStart)
      + " C " + root.pair(cornerTop1) + " " + root.pair(cornerTop2) + " " + root.pair(cornerTopEnd)
      + " L " + root.pair(cornerBottomStart)
      + " C " + root.pair(cornerBottom1) + " " + root.pair(cornerBottom2) + " " + root.pair(cornerBottomEnd)
      + " L " + root.pair(flareBottomStart)
      + bottomFlare
      + " Z"
  }

  Shape {
    anchors.fill: parent
    preferredRendererType: Shape.CurveRenderer

    ShapePath {
      strokeWidth: -1
      fillColor: root.surfaceOpacity >= 0.999 ? "#000000" : Qt.rgba(0, 0, 0, Math.max(0.5, Math.min(1, root.surfaceOpacity)))
      Behavior on fillColor { ColorAnimation { duration: root.animationsEnabled ? 220 : 0 } }
      PathSvg { path: root.pathData() }
    }
  }
}
