import QtQuick
import QtQuick.Layouts
import "Usage.js" as Usage

Column {
  id: root

  property var preferences: ({})
  property real uiScale: 1
  signal preferenceChanged(string key, var value)

  width: parent ? parent.width : 200
  spacing: 5 * uiScale

  function title(value) {
    var text = String(value || "")
    return text.length > 0 ? text.charAt(0).toUpperCase() + text.slice(1) : ""
  }

  function nextIn(values, current) {
    var index = values.indexOf(current)
    return values[(index + 1 + values.length) % values.length]
  }

  function openMode() {
    if (preferences.autoHide === false) return "Always"
    return preferences.expandBehavior === "click" ? "Click" : "Hover"
  }

  function rows() {
    var p = preferences || ({})
    var providers = p.enabledProviders || ({})
    var colors = p.providerColors || ({})
    function colorValue(providerId) {
      var color = Usage.validAccent(colors[providerId])
      return color === "auto" ? "Auto" : color.toUpperCase()
    }
    return [
      { key: "providerClaude", label: "Claude", value: providers.claude === false ? "Off" : "On" },
      { key: "providerCodex", label: "Codex", value: providers.codex === false ? "Off" : "On" },
      { key: "providerAntigravity", label: "Antigravity quota", value: providers.antigravity === false ? "Off" : "On" },
      { key: "providerCursor", label: "Cursor quota", value: providers.cursor === false ? "Off" : "On" },
      { key: "colorClaude", label: "Claude color", value: colorValue("claude"), swatch: Usage.validAccent(colors.claude) },
      { key: "colorCodex", label: "Codex color", value: colorValue("codex"), swatch: Usage.validAccent(colors.codex) },
      { key: "colorAntigravity", label: "Antigravity color", value: colorValue("antigravity"), swatch: Usage.validAccent(colors.antigravity) },
      { key: "colorCursor", label: "Cursor color", value: colorValue("cursor"), swatch: Usage.validAccent(colors.cursor) },
      { key: "edge", label: "Screen edge", value: title(p.edge || "right") },
      { key: "offset", label: "Position", value: Math.round(Number(p.offset === undefined ? 0.5 : p.offset) * 100) + "%" },
      { key: "monitor", label: "Display", value: p.monitor === "all" ? "All" : (p.monitor === "focused" ? "Focused" : String(p.monitor || "Focused")) },
      { key: "size", label: "Size", value: title(p.size || "medium") },
      { key: "openMode", label: "Open", value: openMode() },
      { key: "pollingInterval", label: "Refresh", value: Math.round(Number(p.pollingInterval || 900) / 60) + " min" },
      { key: "showProviderLabel", label: "Provider label", value: p.showProviderLabel === true ? "On" : "Off" },
      { key: "showResetTimer", label: "Reset time", value: p.showResetTimer === false ? "Off" : "On" },
      { key: "accentColor", label: "Accent color", value: Usage.validAccent(p.accentColor) === "auto" ? "Auto" : Usage.validAccent(p.accentColor).toUpperCase(), swatch: Usage.validAccent(p.accentColor) },
      { key: "showInsights", label: "Insights panel", value: p.showInsights === false ? "Off" : "On" },
      { key: "animations", label: "Motion", value: p.animations === false ? "Off" : "On" }
    ]
  }

  function activate(key) {
    var p = preferences || ({})
    if (key.indexOf("provider") === 0) {
      var providerId = key === "providerClaude" ? "claude"
        : (key === "providerCodex" ? "codex"
        : (key === "providerAntigravity" ? "antigravity"
        : "cursor"))
      var current = p.enabledProviders || ({})
      var currentlyEnabled = current[providerId] !== false
      var enabledCount = 0
      var providerIds = ["claude", "codex", "antigravity", "cursor"]
      for (var i = 0; i < providerIds.length; i++) {
        if (current[providerIds[i]] !== false) enabledCount++
      }
      if (currentlyEnabled && enabledCount <= 1) return
      var next = ({})
      for (i = 0; i < providerIds.length; i++) next[providerIds[i]] = current[providerIds[i]] !== false
      next[providerId] = !currentlyEnabled
      preferenceChanged("enabledProviders", next)
    }
    else if (key.indexOf("color") === 0) {
      var colorProvider = key === "colorClaude" ? "claude"
        : (key === "colorCodex" ? "codex"
        : (key === "colorAntigravity" ? "antigravity" : "cursor"))
      var nextColors = ({})
      var currentColors = p.providerColors || ({})
      var colorProviders = ["claude", "codex", "antigravity", "cursor"]
      for (var j = 0; j < colorProviders.length; j++) {
        var name = colorProviders[j]
        nextColors[name] = Usage.validAccent(currentColors[name])
      }
      nextColors[colorProvider] = nextIn(Usage.PRESETS, Usage.validAccent(nextColors[colorProvider]))
      preferenceChanged("providerColors", nextColors)
    }
    else if (key === "edge") preferenceChanged(key, nextIn(["right", "bottom", "left", "top"], p.edge))
    else if (key === "offset") preferenceChanged(key, nextIn([0.25, 0.5, 0.75], Number(p.offset)))
    else if (key === "monitor") preferenceChanged(key, p.monitor === "all" ? "focused" : "all")
    else if (key === "size") preferenceChanged(key, nextIn(["small", "medium", "large"], p.size))
    else if (key === "openMode") {
      if (p.autoHide === false) {
        preferenceChanged("autoHide", true)
        preferenceChanged("expandBehavior", "hover")
      } else if (p.expandBehavior === "hover") {
        preferenceChanged("expandBehavior", "click")
      } else {
        preferenceChanged("autoHide", false)
      }
    }
    else if (key === "accentColor") preferenceChanged(key, nextIn(Usage.PRESETS, Usage.validAccent(p.accentColor)))
    else if (key === "pollingInterval") preferenceChanged(key, nextIn([300, 900, 1800, 3600], Number(p.pollingInterval)))
    else preferenceChanged(key, p[key] === false)
  }

  Repeater {
    model: root.rows()

    delegate: Rectangle {
      id: row
      required property var modelData
      width: root.width
      height: 27 * root.uiScale
      radius: 8 * root.uiScale
      color: rowMouse.containsMouse ? "#1d1d1d" : "transparent"

      RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 8 * root.uiScale
        anchors.rightMargin: 8 * root.uiScale
        spacing: 8 * root.uiScale

        Text {
          Layout.fillWidth: true
          text: String(row.modelData.label)
          textFormat: Text.PlainText
          color: "#d8d8d8"
          font.family: "sans-serif"
          font.pixelSize: 10 * root.uiScale
        }

        Rectangle {
          visible: row.modelData.swatch !== undefined
          Layout.preferredWidth: 9 * root.uiScale
          Layout.preferredHeight: 9 * root.uiScale
          radius: width / 2
          color: row.modelData.swatch === "auto" || row.modelData.swatch === undefined
            ? "transparent"
            : row.modelData.swatch
          border.width: row.modelData.swatch === "auto" ? 1 : 0
          border.color: "#808080"
          Behavior on color { ColorAnimation { duration: 200 } }
        }

        Text {
          text: String(row.modelData.value)
          textFormat: Text.PlainText
          color: "#808080"
          font.family: "sans-serif"
          font.pixelSize: 10 * root.uiScale
        }
      }

      MouseArea {
        id: rowMouse
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.activate(String(row.modelData.key))
      }

      Accessible.role: Accessible.Button
      Accessible.name: String(modelData.label) + ": " + String(modelData.value)
      Accessible.onPressAction: root.activate(String(modelData.key))
    }
  }
}
