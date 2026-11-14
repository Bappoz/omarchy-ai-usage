import QtQuick
import Quickshell.Io
import "Activity.js" as Activity

QtObject {
  id: root
  property bool enabled: true
  property bool previewMode: false
  property var enabledProviders: ({})
  property var sessions: []
  property var previous: null
  property bool failed: false
  property bool ready: false
  readonly property string helperPath: String(Qt.resolvedUrl("../../helpers/session_provider.py")).replace(/^file:\/\//, "")
  readonly property string providerList: ["claude", "codex"].filter(function(id) {
    return root.enabledProviders[id] !== false
  }).join(",")
  signal eventOccurred(var event)

  function applyText(text) {
    try {
      var doc = JSON.parse(text)
      if (doc.schemaVersion !== 1 || !Array.isArray(doc.sessions) || doc.sessions.length > 128
          || !doc.sessions.every(Activity.validSession)) throw new Error("Invalid session data")
      var next = Activity.absorb(root.previous, doc.sessions)
      root.previous = next.previous
      root.sessions = doc.sessions
      root.failed = false
      next.events.forEach(function(event) { root.eventOccurred(event) })
    } catch (error) {
      // A broken read must not announce every old session as completed.
      root.sessions = []
      root.previous = null
      root.failed = true
    }
  }

  function restart() {
    if (!root.ready) return
    root.previous = null
    root.sessions = []
    if (watcher.running) watcher.running = false
    retry.restart()
  }

  function focus(session) {
    if (!session || !session.pid || !session.started || focusProcess.running) return
    focusProcess.command = ["python3", root.helperPath, "--focus", String(session.pid), "--started", String(session.started)]
    focusProcess.running = true
  }

  onEnabledChanged: restart()
  onProviderListChanged: restart()
  onPreviewModeChanged: restart()

  property Timer retry: Timer {
    interval: 1000
    onTriggered: if (root.enabled && !root.previewMode && root.providerList) watcher.running = true
  }
  property Process watcher: Process {
    command: ["python3", root.helperPath, "--watch", "--providers", root.providerList]
    stdout: SplitParser { onRead: function(data) { root.applyText(data) } }
    stderr: StdioCollector { waitForEnd: true }
    onExited: {
      root.sessions = []
      root.previous = null
      if (root.enabled && !root.previewMode) { root.failed = true; retry.restart() }
    }
  }
  property Process focusProcess: Process {
    stdout: StdioCollector { waitForEnd: true }
    stderr: StdioCollector { waitForEnd: true }
  }
  Component.onCompleted: { root.ready = true; retry.start() }
}
