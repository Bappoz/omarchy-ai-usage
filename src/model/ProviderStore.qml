import QtQuick
import Quickshell
import Quickshell.Io

QtObject {
  id: root

  readonly property string stateHome: Quickshell.env("XDG_STATE_HOME")
                                      || (Quickshell.env("HOME") + "/.local/state")
  readonly property string agentUsageDir: stateHome + "/omarchy/agents/usage"

  property bool previewMode: Quickshell.env("OMARCHY_AI_USAGE_PREVIEW") === "1"
  property int pollingIntervalSeconds: 900
  property var enabledProviders: ({ "claude": true, "codex": true })
  property bool officialRefreshPending: false
  property double lastOfficialRefreshMs: 0
  readonly property int officialRefreshCooldownMs: 15000
  readonly property bool ready: true
  readonly property bool loading: claudeRunner.loading || codexRunner.loading
  readonly property var snapshots: {
    var result = []
    if (claudeRunner.enabled) result.push(claudeRunner.snapshot)
    if (codexRunner.enabled) result.push(codexRunner.snapshot)
    return result
  }

  function isEnabled(providerId) {
    var providers = root.enabledProviders || ({})
    return providers[providerId] !== false
  }

  function refresh(providerId) {
    if (root.previewMode) return
    root.requestOfficialRefresh()
    if (providerId === "claude") claudeRunner.refresh()
    else if (providerId === "codex") codexRunner.refresh()
  }

  function refreshAll() {
    if (root.previewMode) return
    root.requestOfficialRefresh()
    if (claudeRunner.enabled) claudeRunner.refresh()
    if (codexRunner.enabled) codexRunner.refresh()
  }

  function requestOfficialRefresh() {
    var elapsed = Date.now() - root.lastOfficialRefreshMs
    if (officialRefreshProcess.running) {
      root.officialRefreshPending = true
      return
    }
    if (elapsed >= 0 && elapsed < root.officialRefreshCooldownMs) return
    root.lastOfficialRefreshMs = Date.now()
    officialRefreshProcess.command = ["omarchy-shell", "omarchy.agents", "refresh"]
    officialRefreshProcess.running = true
  }

  property Process officialRefreshProcess: Process {
    running: false
    stdout: StdioCollector { waitForEnd: true }
    stderr: StdioCollector { waitForEnd: true }
    onExited: {
      if (root.officialRefreshPending) {
        root.officialRefreshPending = false
        officialRefreshCooldown.restart()
      }
    }
  }

  property Timer officialRefreshCooldown: Timer {
    interval: root.officialRefreshCooldownMs
    repeat: false
    onTriggered: root.requestOfficialRefresh()
  }

  property ProviderRunner claudeRunner: ProviderRunner {
    providerId: "claude"
    displayName: "Claude"
    helperFile: "omarchy_agent_provider.py"
    helperArguments: ["--provider", "claude"]
    watchedFilePath: root.agentUsageDir + "/claude.json"
    enabled: !root.previewMode && root.isEnabled("claude")
    pollingIntervalSeconds: root.pollingIntervalSeconds
  }

  property ProviderRunner codexRunner: ProviderRunner {
    providerId: "codex"
    displayName: "Codex"
    helperFile: "omarchy_agent_provider.py"
    helperArguments: ["--provider", "codex"]
    watchedFilePath: root.agentUsageDir + "/codex.json"
    enabled: !root.previewMode && root.isEnabled("codex")
    pollingIntervalSeconds: root.pollingIntervalSeconds
  }
}
