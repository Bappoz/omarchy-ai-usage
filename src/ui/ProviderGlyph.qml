import QtQuick
import QtQuick.Effects

Item {
  id: root

  property string providerId: "codex"
  property real opticalScale: providerId === "codex" ? 0.94
    : (providerId === "claude" ? 0.97 : 1.0)

  function glyphSource() {
    if (root.providerId === "claude") return Qt.resolvedUrl("../assets/glyphs/claude.svg")
    if (root.providerId === "perplexity") return Qt.resolvedUrl("../assets/glyphs/perplexity.svg")
    return Qt.resolvedUrl("../assets/glyphs/codex.svg")
  }

  Image {
    id: glyphImage
    anchors.centerIn: parent
    width: parent.width * root.opticalScale
    height: parent.height * root.opticalScale
    source: root.glyphSource()
    sourceSize.width: Math.max(64, Math.round(width * 4))
    sourceSize.height: Math.max(64, Math.round(height * 4))
    fillMode: Image.PreserveAspectFit
    smooth: true
    mipmap: true
    visible: root.providerId !== "claude"
    layer.enabled: root.providerId === "claude"
  }

  MultiEffect {
    anchors.fill: glyphImage
    source: glyphImage
    visible: root.providerId === "claude"
    colorization: 1.0
    colorizationColor: "#D97757"
  }
}
