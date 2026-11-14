import QtQuick
import Quickshell.Io

QtObject {
  id: root
  property var queue: []
  readonly property string helperPath: String(Qt.resolvedUrl("../../helpers/desktop_feedback.py")).replace(/^file:\/\//, "")

  function send(providerId, event, notify, sound) {
    if (["claude", "codex", "antigravity", "cursor"].indexOf(providerId) < 0) return
    if (["finished", "blocked", "80", "100", "preview"].indexOf(event) < 0) return
    if (!notify && !sound) return
    var args = ["python3", root.helperPath, "--provider", providerId, "--event", event]
    if (notify) args.push("--notify")
    if (["complete", "bell", "message"].indexOf(sound) >= 0) args.push("--sound", sound)
    root.queue = root.queue.concat([args]).slice(-16)
    next()
  }

  function next() {
    if (feedback.running || queue.length === 0) return
    feedback.command = queue[0]
    queue = queue.slice(1)
    feedback.running = true
  }

  property Process feedback: Process {
    stdout: StdioCollector { waitForEnd: true }
    stderr: StdioCollector { waitForEnd: true }
    onExited: Qt.callLater(root.next)
  }
}
