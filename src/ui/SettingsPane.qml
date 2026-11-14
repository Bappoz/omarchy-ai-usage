import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as Controls
import Quickshell
import "Usage.js" as Usage
import "../model/Activity.js" as Activity

Column {
  id: root

  property var preferences: ({})
  property real uiScale: 1
  property bool animationsEnabled: true
  property string category: "General"
  signal preferenceChanged(string key, var value)
  signal soundPreviewRequested(string sound)

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
      { key: "showPercentage", label: "Percentage", value: p.showPercentage === false ? "Off" : "On" },
      { key: "showResetTimer", label: "Reset time", value: p.showResetTimer === false ? "Off" : "On" },
      { key: "resetTimeStyle", label: "Reset display", value: p.resetTimeStyle === "date" ? "Reset date" : "Time remaining" },
      { key: "accentColor", label: "Accent color", value: Usage.validAccent(p.accentColor) === "auto" ? "Auto" : Usage.validAccent(p.accentColor).toUpperCase(), swatch: Usage.validAccent(p.accentColor) },
      { key: "showInsights", label: "Insights panel", value: p.showInsights === false ? "Off" : "On" },
      { key: "showSessions", label: "Live sessions", value: p.showSessions === false ? "Off" : "On" },
      { key: "busyIndicator", label: "Working indicator", value: p.busyIndicator === "breath" ? "Breathing disc" : "Spinning arc" },
      { key: "peekOnEvent", label: "Peek on completion / waiting", value: p.peekOnEvent === false ? "Off" : "On" },
      { key: "peekDuration", label: "Peek duration", value: Number(p.peekDuration || 5) + " sec" },
      { key: "sessionSounds", label: "Session sounds", value: p.sessionSounds === false ? "Off" : "On" },
      { key: "finishedSound", label: "Finished sound", value: title(p.finishedSound || "complete") },
      { key: "waitingSound", label: "Waiting sound", value: title(p.waitingSound || "bell") },
      { key: "sessionNotifications", label: "Session notifications", value: p.sessionNotifications === true ? "On" : "Off" },
      { key: "quotaAlerts", label: "80% / 100% alerts", value: p.quotaAlerts === false ? "Off" : "On" },
      { key: "muteClaude", label: "Claude alerts", value: (p.mutedAlerts || {}).claude === true ? "Muted" : "On" },
      { key: "muteCodex", label: "Codex alerts", value: (p.mutedAlerts || {}).codex === true ? "Muted" : "On" },
      { key: "muteAntigravity", label: "Antigravity alerts", value: (p.mutedAlerts || {}).antigravity === true ? "Muted" : "On" },
      { key: "muteCursor", label: "Cursor alerts", value: (p.mutedAlerts || {}).cursor === true ? "Muted" : "On" },
      { key: "animations", label: "Motion", value: p.animations === false ? "Off" : "On" }
    ]
  }

  function activate(key) {
    var p = preferences || ({})
    if (key.indexOf("mute") === 0) {
      var muted = ({})
      for (var m in (p.mutedAlerts || {})) muted[m] = p.mutedAlerts[m]
      var id = key.slice(4).toLowerCase()
      muted[id] = muted[id] !== true
      preferenceChanged("mutedAlerts", muted)
    }
    else if (key.indexOf("provider") === 0) {
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
    else if (key === "monitor") {
      var displays = ["focused", "all"]
      for (var d = 0; d < Quickshell.screens.length; d++) displays.push(String(Quickshell.screens[d].name))
      preferenceChanged(key, nextIn(displays, p.monitor))
    }
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
    else if (key === "resetTimeStyle") preferenceChanged(key, p.resetTimeStyle === "date" ? "remaining" : "date")
    else if (key === "busyIndicator") preferenceChanged(key, p.busyIndicator === "breath" ? "arc" : "breath")
    else if (key === "peekDuration") preferenceChanged(key, nextIn([3, 5, 10], Number(p.peekDuration || 5)))
    else if (key === "finishedSound" || key === "waitingSound") preferenceChanged(key, nextIn(["complete", "bell", "message"], p[key]))
    else if (key === "pollingInterval") preferenceChanged(key, nextIn([300, 900, 1800, 3600], Number(p.pollingInterval)))
    else preferenceChanged(key, p[key] === false)
  }

  function rowCategory(key) {
    if (key.indexOf("provider") === 0 || key.indexOf("color") === 0) return "Accounts"
    if (key.indexOf("mute") === 0 || ["quotaAlerts", "sessionNotifications", "sessionSounds", "finishedSound", "waitingSound"].indexOf(key) >= 0) return "Alerts"
    if (["showSessions", "showInsights", "peekOnEvent", "peekDuration", "busyIndicator"].indexOf(key) >= 0) return "Activity"
    return "General"
  }

  Row {
    width: parent.width
    Repeater {
      model: ["General", "Accounts", "Activity", "Alerts"]
      delegate: Rectangle {
        required property string modelData
        width: root.width / 4; height: 28 * root.uiScale; radius: 7 * root.uiScale
        color: root.category === modelData ? "#2d2d2d" : "transparent"
        Text {
          anchors.centerIn: parent; text: parent.modelData
          font.pixelSize: 9 * root.uiScale; color: root.category === parent.modelData ? "#ffffff" : "#808080"
        }
        MouseArea {
          anchors.fill: parent; cursorShape: Qt.PointingHandCursor
          onClicked: root.category = parent.modelData
        }
        Accessible.role: Accessible.PageTab
        Accessible.name: modelData
        Accessible.onPressAction: root.category = modelData
      }
    }
  }

  Repeater {
    model: root.rows().filter(function(row) { return root.rowCategory(row.key) === root.category })

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
          Behavior on color { ColorAnimation { duration: root.animationsEnabled ? 200 : 0 } }
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

  Controls.Slider {
    id: positionSlider
    visible: root.category === "General"
    width: parent.width
    from: 0; to: 1; value: Number(root.preferences.offset === undefined ? 0.5 : root.preferences.offset)
    onMoved: root.preferenceChanged("offset", value)
    Accessible.name: "Position along screen edge"
    background: Rectangle {
      x: positionSlider.leftPadding
      y: positionSlider.topPadding + (positionSlider.availableHeight - height) / 2
      width: positionSlider.availableWidth; height: 3 * root.uiScale; radius: height / 2
      color: "#303030"
      Rectangle { width: parent.width * positionSlider.visualPosition; height: parent.height; radius: height / 2; color: "#ffffff" }
    }
    handle: Rectangle {
      x: positionSlider.leftPadding + positionSlider.visualPosition * (positionSlider.availableWidth - width)
      y: positionSlider.topPadding + (positionSlider.availableHeight - height) / 2
      width: 12 * root.uiScale; height: width; radius: width / 2; color: "#ffffff"
    }
  }

  RowLayout {
    visible: root.category === "General"
    width: parent.width
    spacing: 6 * root.uiScale
    Controls.TextField {
      id: customColor
      Layout.fillWidth: true
      placeholderText: "Accent #RRGGBB"
      maximumLength: 7
      color: "#ffffff"
      placeholderTextColor: "#808080"
      font.pixelSize: 10 * root.uiScale
      background: Rectangle { radius: 6; color: "#202020" }
      validator: RegularExpressionValidator { regularExpression: /#[0-9a-fA-F]{6}/ }
      onAccepted: if (acceptableInput) root.preferenceChanged("accentColor", text)
      Accessible.name: "Custom accent hex color"
    }
    NotchButton {
      uiScale: root.uiScale
      text: "Apply"
      enabled: customColor.acceptableInput
      onClicked: root.preferenceChanged("accentColor", customColor.text)
      Accessible.name: "Apply custom accent color"
    }
  }

  Column {
    width: parent.width
    visible: root.category === "Accounts"
    spacing: 4 * root.uiScale
    Text { text: "Ring order"; color: "#808080"; font.pixelSize: 10 * root.uiScale }
    Repeater {
      model: Activity.providerOrder(root.preferences.providerOrder)
      delegate: RowLayout {
        id: orderRow
        required property string modelData
        required property int index
        width: root.width
        Text {
          Layout.fillWidth: true; text: root.title(orderRow.modelData); color: "#ffffff"; font.pixelSize: 10 * root.uiScale
        }
        Repeater {
          model: [-1, 1]
          delegate: NotchButton {
            uiScale: root.uiScale
            required property int modelData
            text: modelData < 0 ? "↑" : "↓"
            implicitWidth: 28 * root.uiScale
            implicitHeight: 26 * root.uiScale
            enabled: orderRow.index + modelData >= 0 && orderRow.index + modelData < 4
            onClicked: {
              var order = Activity.providerOrder(root.preferences.providerOrder)
              var other = orderRow.index + modelData
              var held = order[orderRow.index]
              order[orderRow.index] = order[other]
              order[other] = held
              root.preferenceChanged("providerOrder", order)
            }
            Accessible.name: "Move " + orderRow.modelData + (modelData < 0 ? " earlier" : " later")
          }
        }
      }
    }
  }

  RowLayout {
    visible: root.category === "Alerts"
    width: parent.width
    NotchButton {
      uiScale: root.uiScale
      Layout.fillWidth: true; text: "Test finished"
      onClicked: root.soundPreviewRequested(String(root.preferences.finishedSound || "complete"))
    }
    NotchButton {
      uiScale: root.uiScale
      Layout.fillWidth: true; text: "Test waiting"
      onClicked: root.soundPreviewRequested(String(root.preferences.waitingSound || "bell"))
    }
  }

  Text {
    width: parent.width; topPadding: 6 * root.uiScale; wrapMode: Text.Wrap
    text: root.category === "General" ? "Alt-drag the body to reposition. Right-click for Keep open and Refresh now."
      : (root.category === "Accounts" ? "Changes apply immediately. At least one provider stays enabled."
      : (root.category === "Activity" ? "Session metadata is read locally. Turn off Live sessions to stop monitoring."
      : "Alerts are sent once per crossing. Sound and peek can be disabled independently."))
    color: "#808080"; font.pixelSize: 9 * root.uiScale; textFormat: Text.PlainText
  }
}
