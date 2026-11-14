import QtQuick
import Quickshell
import "../../src/ui" as UI
import "../../src/model" as Model

// Runs under Quickshell offscreen. All readings are synthetic; no collectors,
// alerts, sounds, desktop launches or preference writes are invoked.
ShellRoot {
  Window {
    id: window
    width: 1000; height: 800; visible: true
    property int eventCount: 0
    Rectangle { anchors.fill: parent; color: "#20232a" }
    Model.Preferences { id: prefs; shell: null }
    Model.SessionStore {
      id: sessions
      enabled: false
      onEventOccurred: window.eventCount++
    }
    UI.ExpandedCard {
      id: card
      x: 20; y: 20
      width: implicitWidth; height: implicitHeight
      preferences: prefs.values
      maxBodyHeight: 500
      settingsOpen: true
      sessions: [{name:"Synthetic session",state:"busy",detail:"Terminal · example",pid:null}]
      snapshot: ({providerId:"claude", displayName:"Claude",status:"ACTIVE",lastUpdated:null,
        windows:[{id:"session",name:"Current session",usedPercent:73,resetAt:new Date(Date.now()+60000).toISOString(),durationMinutes:300}]})
    }
    UI.SettingsPane {
      id: settings
      x: 350; y: 20; width: 230
      preferences: prefs.values
      onPreferenceChanged: function(key, value) { prefs.update(key, value) }
    }
    UI.CompactNotch {
      id: rail
      x: 800; y: 50; width: implicitWidth; height: implicitHeight
      unfolded: true
      providers: [{id:"claude",displayName:"Claude",usedPercent:73},{id:"codex",displayName:"Codex",usedPercent:21}]
      sessions: [{providerId:"claude",state:"busy"},{providerId:"codex",state:"waiting"}]
    }
    function check(value, message) { if (!value) throw new Error(message) }
    Timer {
      interval: 500; running: true
      onTriggered: {
        try {
          prefs.values = prefs.defaults()
          settings.activate("peekDuration")
          window.check(prefs.values.peekDuration === 10, "peek duration did not persist")
          settings.activate("busyIndicator")
          window.check(prefs.values.busyIndicator === "breath", "indicator selection failed")
          prefs.update("offset", 0.27)
          prefs.update("edge", "top")
          window.check(prefs.values.offset === 0.5, "new edge did not restore default")
          prefs.update("offset", 0.72)
          prefs.update("edge", "right")
          window.check(prefs.values.offset === 0.27, "previous edge position was lost")
          var order = prefs.values.providerOrder.slice()
          settings.activate("providerClaude")
          settings.activate("providerClaude")
          window.check(prefs.values.providerOrder[3] === "claude", "reenabled provider did not join end")
          prefs.update("providerOrder", order)
          var s = {id:"aaaaaaaaaaaaaaaaaaaaaaaa",providerId:"claude",name:"Synthetic",detail:"Terminal",state:"busy",pid:null,started:null}
          sessions.applyText(JSON.stringify({schemaVersion:1,sessions:[s]}))
          window.check(window.eventCount === 0, "startup announced a session")
          s.state = "waiting"
          sessions.applyText(JSON.stringify({schemaVersion:1,sessions:[s]}))
          window.check(window.eventCount === 1, "waiting transition was lost")
          sessions.applyText("invalid")
          window.check(sessions.failed && sessions.sessions.length === 0, "bad session document was accepted")
          window.check(card.bodyHeight <= 500, "card exceeds available height")
          ;["General","Accounts","Activity","Alerts"].forEach(function(category) {
            settings.category = category
            window.check(settings.rows().filter(function(r) { return settings.rowCategory(r.key) === category }).length > 0, "empty settings category")
          })
          console.log("SMOKE_OK: preferences, sessions, settings and surface")
        } catch (error) { console.error("SMOKE_FAIL: " + error) }
        Qt.quit()
      }
    }
  }
}
