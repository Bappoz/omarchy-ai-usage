import QtQuick
import Quickshell

QtObject {
  id: root

  readonly property string stateHome: Quickshell.env("XDG_STATE_HOME")
                                      || (Quickshell.env("HOME") + "/.local/state")
  readonly property string agentUsageDir: stateHome + "/omarchy/agents/usage"

  property bool previewMode: Quickshell.env("OMARCHY_AI_USAGE_PREVIEW") === "1"
  property int pollingIntervalSeconds: 900
  property var enabledProviders: ({ "claude": true, "codex": true })
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
    if (providerId === "claude") claudeRunner.refresh()
    else if (providerId === "codex") codexRunner.refresh()
  }

  function refreshAll() {
    if (root.previewMode) return
    if (claudeRunner.enabled) claudeRunner.refresh()
    if (codexRunner.enabled) codexRunner.refresh()
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
