import QtQuick
import Quickshell.Io

QtObject {
  id: root

  // Fixed table: no user-controlled strings reach a command line. The desktop
  // entries are the installed apps; the web app is the fallback when absent.
  readonly property var apps: ({
    "claude": { "desktop": "com.anthropic.Claude", "url": "https://claude.ai" },
    "codex": { "desktop": "chatgpt", "url": "https://chatgpt.com/codex" }
  })
  property string pendingUrl: ""

  function canOpen(providerId) { return root.apps[providerId] !== undefined }

  function open(providerId) {
    var app = root.apps[providerId]
    if (!app || primary.running || fallback.running) return false
    root.pendingUrl = app.url
    primary.command = ["gtk-launch", app.desktop]
    primary.running = true
    return true
  }

  property Process primary: Process {
    running: false
    onExited: function(exitCode) {
      if (exitCode === 0) return
      fallback.command = ["omarchy-launch-webapp", root.pendingUrl]
      fallback.running = true
    }
  }

  property Process fallback: Process { running: false }
}
