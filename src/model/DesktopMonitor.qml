import QtQuick
import Quickshell.Hyprland
import Quickshell.Io

// Tracks Hyprland fullscreen and active-window geometry via compositor events
// (zero idle polling) so the notch can fold away during fullscreen apps/videos
// or overlapping windows, inspired by CodeNotch's FullScreenDetector.
QtObject {
  id: root

  property bool enabled: false
  property bool activeFullscreen: false
  property string activeMonitorName: ""
  property var activeWindowBounds: null // { x, y, width, height }
  property bool queryPending: false

  function scheduleCheck() {
    if (!root.enabled) {
      root.activeFullscreen = false
      root.activeMonitorName = ""
      root.activeWindowBounds = null
      return
    }
    debounce.restart()
  }

  function runCheck() {
    if (!root.enabled) return
    if (queryProcess.running) {
      root.queryPending = true
      return
    }
    queryProcess.command = ["hyprctl", "activewindow", "-j"]
    queryProcess.running = true
  }

  function applyOutput(text) {
    try {
      var win = JSON.parse(String(text || "{}"))
      if (!win || typeof win !== "object" || !win.address || win.mapped === false) {
        root.activeFullscreen = false
        root.activeWindowBounds = null
        return
      }
      var mon = Hyprland.focusedMonitor
      root.activeMonitorName = mon ? String(mon.name || "") : ""
      // In Hyprland, fullscreen === 2 (or boolean true on older builds) is true
      // fullscreen; 1 is maximize. Only true fullscreen triggers onFullscreen.
      var fs = win.fullscreen === true || win.fullscreen === 2 || win.fullscreenClient === 2
      root.activeFullscreen = fs
      if (Array.isArray(win.at) && win.at.length >= 2 && Array.isArray(win.size) && win.size.length >= 2) {
        var x = Number(win.at[0]), y = Number(win.at[1])
        var w = Number(win.size[0]), h = Number(win.size[1])
        if (isFinite(x) && isFinite(y) && isFinite(w) && isFinite(h) && w >= 20 && h >= 20) {
          root.activeWindowBounds = { "x": x, "y": y, "width": w, "height": h }
        } else {
          root.activeWindowBounds = null
        }
      } else {
        root.activeWindowBounds = null
      }
    } catch (error) {
      root.activeFullscreen = false
      root.activeWindowBounds = null
    }
  }

  onEnabledChanged: scheduleCheck()

  property Connections hyprEvents: Connections {
    target: Hyprland
    function onRawEvent(event) {
      if (!root.enabled || !event) return
      var name = String(event.name || "")
      if (name === "fullscreen" || name === "activewindow" || name === "activewindowv2"
          || name === "workspace" || name === "workspacev2" || name === "focusedmon"
          || name === "movewindow" || name === "movewindowv2"
          || name === "openwindow" || name === "closewindow" || name === "changefloatingmode") {
        root.scheduleCheck()
      }
    }
  }

  property Timer debounce: Timer {
    interval: 80
    repeat: false
    onTriggered: root.runCheck()
  }

  property Process queryProcess: Process {
    running: false
    stdout: StdioCollector { id: queryOutput; waitForEnd: true }
    stderr: StdioCollector { waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode === 0) root.applyOutput(queryOutput.text)
      if (root.queryPending) {
        root.queryPending = false
        debounce.restart()
      }
    }
  }

  Component.onCompleted: scheduleCheck()
}
