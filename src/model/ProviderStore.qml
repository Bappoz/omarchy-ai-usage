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
  property var enabledProviders: ({ "claude": true, "codex": true, "antigravity": true, "cursor": true })
  property bool officialRefreshPending: false
  property double lastOfficialRefreshMs: 0
  readonly property int officialRefreshCooldownMs: 15000
  readonly property bool ready: true
  readonly property bool loading: claudeRunner.loading || codexRunner.loading
                                      || antigravityRunner.loading || cursorRunner.loading
  readonly property var snapshots: {
    var result = []
    if (claudeRunner.enabled) result.push(claudeRunner.snapshot)
    if (codexRunner.enabled) result.push(codexRunner.snapshot)
    if (antigravityRunner.enabled) result.push(antigravityRunner.snapshot)
    if (cursorRunner.enabled) result.push(cursorRunner.snapshot)
    return result
  }

  function isEnabled(providerId) {
    var providers = root.enabledProviders || ({})
    return providers[providerId] !== false
  }

  function refresh(providerId) {
    if (root.previewMode) return
    if (providerId === "claude" || providerId === "codex") root.requestOfficialRefresh()
    if (providerId === "claude") claudeRunner.refresh()
    else if (providerId === "codex") codexRunner.refresh()
    else if (providerId === "antigravity") antigravityRunner.refresh()
    else if (providerId === "cursor") cursorRunner.refresh()
  }

  function refreshAll() {
    if (root.previewMode) return
    if ((claudeRunner.enabled || codexRunner.enabled) && root.enabledProviders) root.requestOfficialRefresh()
    if (claudeRunner.enabled) claudeRunner.refresh()
    if (codexRunner.enabled) codexRunner.refresh()
    if (antigravityRunner.enabled) antigravityRunner.refresh()
    if (cursorRunner.enabled) cursorRunner.refresh()
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

  property ProviderRunner antigravityRunner: ProviderRunner {
    providerId: "antigravity"
    displayName: "Antigravity"
    helperFile: "orca_usage_provider.py"
    helperArguments: ["--provider", "antigravity"]
    enabled: !root.previewMode && root.isEnabled("antigravity")
    pollingIntervalSeconds: root.pollingIntervalSeconds
  }

  property ProviderRunner cursorRunner: ProviderRunner {
    providerId: "cursor"
    displayName: "Cursor"
    helperFile: "orca_usage_provider.py"
    helperArguments: ["--provider", "cursor"]
    enabled: !root.previewMode && root.isEnabled("cursor")
    pollingIntervalSeconds: root.pollingIntervalSeconds
  }

}
