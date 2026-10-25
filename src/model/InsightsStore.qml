import QtQuick

QtObject {
  id: root

  property bool previewMode: false

  readonly property var docs: root.previewMode
    ? root.previewDocs()
    : ({ "claude": claudeRunner.doc, "codex": codexRunner.doc })
  readonly property var failures: root.previewMode
    ? ({})
    : ({ "claude": claudeRunner.failed, "codex": codexRunner.failed })

  function refresh(providerId) {
    if (root.previewMode) return
    if (providerId === "claude") claudeRunner.refresh()
    else if (providerId === "codex") codexRunner.refresh()
  }

  // Synthetic shapes for the opt-in preview only; never used as a live fallback.
  function previewDocs() {
    var hour = new Date()
    hour.setMinutes(0, 0, 0)
    function document(providerId, series, models, current, effort) {
      var hourly = []
      var total = 0
      for (var i = 0; i < series.length; i++) {
        total += series[i]
        hourly.push({
          "start": new Date(hour.getTime() - (series.length - 1 - i) * 3600000).toISOString(),
          "tokens": series[i]
        })
      }
      return {
        "schemaVersion": 1, "providerId": providerId, "available": true,
        "generatedAt": new Date().toISOString(),
        "currentModel": { "name": current, "effort": effort, "lastSeen": new Date().toISOString() },
        "hourly": hourly,
        "totals": {
          "last24hTokens": total, "last24hRequests": Math.round(total / 6800),
          "last7dTokens": total * 4, "last7dRequests": Math.round(total / 1700)
        },
        "models": models
      }
    }
    return {
      "claude": document("claude",
        [0, 0, 0, 0, 0, 0, 40e3, 120e3, 260e3, 410e3, 380e3, 220e3, 310e3, 520e3, 640e3, 480e3, 300e3, 150e3, 210e3, 380e3, 290e3, 140e3, 60e3, 20e3],
        [{ "name": "claude-opus-5-5", "tokens": 5.7e6, "share": 0.6695 },
         { "name": "claude-sonnet-5-5", "tokens": 2.1e6, "share": 0.2439 },
         { "name": "claude-haiku-5-5", "tokens": 0.74e6, "share": 0.0866 }],
        "claude-sonnet-5-5", "medium"),
      "codex": document("codex",
        [0, 0, 0, 0, 0, 0, 0, 0, 90e3, 160e3, 40e3, 0, 0, 220e3, 340e3, 180e3, 60e3, 0, 0, 120e3, 260e3, 80e3, 0, 0],
        [{ "name": "gpt-6-luna", "tokens": 3.9e6, "share": 0.93 },
         { "name": "codex-auto-review", "tokens": 0.29e6, "share": 0.07 }],
        "gpt-6-luna", "medium"),
      "perplexity": document("perplexity",
        [0, 0, 0, 0, 0, 0, 0, 12e3, 30e3, 18e3, 0, 0, 24e3, 52e3, 20e3, 0, 0, 16e3, 40e3, 22e3, 0, 0, 0, 0],
        [{ "name": "sonar-pro", "tokens": 0.8e6, "share": 1 }],
        "sonar-pro", null)
    }
  }

  property InsightsRunner claudeRunner: InsightsRunner { providerId: "claude" }
  property InsightsRunner codexRunner: InsightsRunner { providerId: "codex" }
}
