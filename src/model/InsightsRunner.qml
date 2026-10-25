import QtQuick
import Quickshell.Io
import "../ui/Usage.js" as Usage

QtObject {
  id: root

  required property string providerId
  property var doc: null
  property bool loading: false
  property bool failed: false
  property bool refreshPending: false
  property double lastStartMs: 0
  readonly property int cooldownMs: 15000
  readonly property string helperPath: String(
    Qt.resolvedUrl("../../helpers/insights_provider.py")
  ).replace(/^file:\/\//, "")

  function refresh() {
    if (insightsProcess.running) {
      root.refreshPending = true
      return
    }
    if (Date.now() - root.lastStartMs < root.cooldownMs) return
    root.lastStartMs = Date.now()
    root.loading = true
    insightsProcess.command = ["python3", root.helperPath, "--provider", root.providerId]
    insightsProcess.running = true
  }

  function applyText(text) {
    try {
      var parsed = JSON.parse(String(text || ""))
      if (!Usage.isInsights(parsed, root.providerId)) throw new Error("invalid insights")
      root.doc = parsed
      root.failed = false
    } catch (error) {
      // Keep the last good document; only flag failure when there is none.
      root.failed = root.doc === null
    }
    root.loading = false
  }

  property Process insightsProcess: Process {
    running: false
    stdout: StdioCollector { id: insightsOutput; waitForEnd: true }
    stderr: StdioCollector { waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode === 0) {
        root.applyText(insightsOutput.text)
      } else {
        root.failed = root.doc === null
        root.loading = false
      }
      if (root.refreshPending) {
        root.refreshPending = false
        Qt.callLater(root.refresh)
      }
    }
  }
}
