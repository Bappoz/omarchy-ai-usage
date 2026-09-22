import QtQuick
import Quickshell
import Quickshell.Io

QtObject {
  id: root

  required property string providerId
  required property string displayName
  required property string helperFile
  property var helperArguments: []
  property string watchedFilePath: ""
  property bool enabled: true
  property int pollingIntervalSeconds: 900
  property var snapshot: loadingSnapshot()
  property bool loading: true
  property int consecutiveFailures: 0
  property bool refreshPending: false
  readonly property string helperPath: String(
    Qt.resolvedUrl("../../helpers/" + helperFile)
  ).replace(/^file:\/\//, "")

  function emptySnapshot(status, message) {
    return {
      "schemaVersion": 1, "providerId": root.providerId, "displayName": root.displayName,
      "account": null, "status": status, "lastUpdated": null, "stale": false,
      "headlineWindowId": null, "windows": [], "message": message
    }
  }

  function loadingSnapshot() { return emptySnapshot("LOADING", "Reading " + root.displayName + " limits…") }
  function failedSnapshot() { return emptySnapshot("ERROR", root.displayName + " usage could not be refreshed.") }
  function isNumber(value) { return typeof value === "number" && isFinite(value) }

  function isSnapshot(value) {
    if (!value || typeof value !== "object" || Array.isArray(value)) return false
    if (value.schemaVersion !== 1 || String(value.providerId || "") !== root.providerId) return false
    if (typeof value.displayName !== "string" || value.displayName.length === 0) return false
    var states = ["ACTIVE", "LOADING", "STALE", "NEEDS_AUTH", "RATE_LIMITED", "ERROR", "UNAVAILABLE"]
    if (states.indexOf(String(value.status || "")) < 0) return false
    if (!Array.isArray(value.windows) || value.windows.length > 32) return false
    if (typeof value.stale !== "boolean") return false
    var ids = ({})
    for (var i = 0; i < value.windows.length; i++) {
      var window = value.windows[i]
      if (!window || typeof window !== "object" || Array.isArray(window)) return false
      if (typeof window.id !== "string" || window.id.length === 0 || ids[window.id]) return false
      if (typeof window.name !== "string" || window.name.length === 0) return false
      ids[window.id] = true
      var remaining = window.remainingPercent
      var used = window.usedPercent
      if (remaining !== null && (!isNumber(remaining) || remaining < 0 || remaining > 100)) return false
      if (used !== null && (!isNumber(used) || used < 0 || used > 100)) return false
    }
    var headline = value.headlineWindowId
    return headline === null || Boolean(ids[String(headline)])
  }

  function applyText(text) {
    try {
      var parsed = JSON.parse(String(text || ""))
      if (!isSnapshot(parsed)) throw new Error("invalid provider snapshot")
      root.snapshot = parsed
    } catch (error) {
      root.snapshot = failedSnapshot()
    }
    root.loading = false
  }

  function refresh() {
    if (!root.enabled) {
      pollTimer.stop()
      root.snapshot = emptySnapshot("UNAVAILABLE", root.displayName + " is disabled in preferences.")
      root.loading = false
      return
    }
    if (providerProcess.running) {
      root.refreshPending = true
      return
    }
    pollTimer.stop()
    root.loading = true
    providerProcess.command = ["python3", root.helperPath].concat(root.helperArguments || [])
    providerProcess.running = true
  }

  function earliestResetDelaySeconds(value) {
    if (!value || !Array.isArray(value.windows)) return 0
    var best = 0
    for (var i = 0; i < value.windows.length; i++) {
      var resetAt = value.windows[i] ? value.windows[i].resetAt : null
      if (!resetAt) continue
      var seconds = Math.ceil((new Date(String(resetAt)).getTime() - Date.now()) / 1000)
      if (isFinite(seconds) && seconds > 0 && (best === 0 || seconds < best)) best = seconds
    }
    return best
  }

  function scheduleNext() {
    if (!root.enabled) return
    var status = String(root.snapshot ? root.snapshot.status : "ERROR")
    var seconds = Math.max(60, Math.min(3600, Number(root.pollingIntervalSeconds) || 900))
    if (status === "ERROR" || status === "UNAVAILABLE" || status === "STALE") {
      root.consecutiveFailures = Math.min(7, root.consecutiveFailures + 1)
      seconds = Math.max(30, Math.min(seconds, 30 * Math.pow(2, root.consecutiveFailures - 1)))
    } else {
      root.consecutiveFailures = 0
    }
    if (status === "NEEDS_AUTH") seconds = Math.max(seconds, 3600)
    if (status === "RATE_LIMITED") {
      var resetDelay = root.earliestResetDelaySeconds(root.snapshot)
      if (resetDelay > 0) seconds = Math.max(seconds, Math.min(21600, resetDelay + 5))
    }
    pollTimer.interval = Math.round(seconds * 1000)
    pollTimer.restart()
  }

  onEnabledChanged: {
    if (enabled) refresh()
    else {
      pollTimer.stop()
      snapshot = emptySnapshot("UNAVAILABLE", root.displayName + " is disabled in preferences.")
      loading = false
    }
  }
  onPollingIntervalSecondsChanged: if (!loading && enabled) scheduleNext()
  Component.onCompleted: refresh()

  property Process providerProcess: Process {
    running: false
    stdout: StdioCollector { id: providerOutput; waitForEnd: true }
    stderr: StdioCollector { waitForEnd: true }
    onExited: function(exitCode) {
      if (exitCode !== 0) {
        root.snapshot = root.failedSnapshot()
        root.loading = false
      } else {
        root.applyText(providerOutput.text)
      }
      if (root.refreshPending) {
        root.refreshPending = false
        Qt.callLater(root.refresh)
      } else {
        root.scheduleNext()
      }
    }
  }

  property Timer pollTimer: Timer {
    interval: 900000
    repeat: false
    onTriggered: root.refresh()
  }

  property FileView providerRecordWatcher: FileView {
    path: root.watchedFilePath
    watchChanges: root.watchedFilePath !== ""
    printErrors: false
    onFileChanged: root.refresh()
  }
}
