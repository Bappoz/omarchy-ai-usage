from __future__ import annotations

import json
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ActivityTests(unittest.TestCase):
    def js(self, expression: str) -> object:
        if shutil.which("node") is None:
            self.skipTest("node not available")
        source = (ROOT / "src/model/Activity.js").read_text().replace(".pragma library", "")
        output = subprocess.run(["node", "-e", source + "\nconsole.log(JSON.stringify(" + expression + "))"],
                                capture_output=True, text=True, check=True)
        return json.loads(output.stdout)

    def test_only_leaving_busy_announces_and_first_read_is_silent(self) -> None:
        result = self.js('''(function() {
          var s={id:"a",providerId:"claude",state:"busy"};
          var a=absorb(null,[s]); s.state="waiting";
          var b=absorb(a.previous,[s]); s.state="idle";
          var c=absorb(b.previous,[s]);
          var d=absorb(c.previous,[]);
          return [a.events.length,b.events[0].reason,c.events.length,d.events.length];
        })()''')
        self.assertEqual(result, [0, "blocked", 0, 0])

    def test_unknown_state_is_not_completion(self) -> None:
        self.assertEqual(self.js('absorb({"claude:a":"busy"},[{id:"a",providerId:"claude",state:"unknown"}]).events'), [])

    def test_waiting_session_outranks_busy(self) -> None:
        self.assertEqual(self.js('summary([{providerId:"claude",state:"busy"},{providerId:"claude",state:"waiting"}],"claude").state'), "waiting")

    def test_limit_alerts_latch_until_real_rollover(self) -> None:
        result = self.js('''(function() {
          var s={status:"ACTIVE",providerId:"claude",headlineWindowId:"session",windows:[{id:"session",usedPercent:79,resetAt:"2026-11-14T05:00:00Z"}]};
          var now=Date.parse("2026-11-14T04:00:00Z"), p=null, out=[];
          [79,80,81,79,80,100,100].forEach(function(used){s.windows[0].usedPercent=used;var r=quotaCrossings(p,s,now);p=r.previous;out.push(r.thresholds)});
          s.windows[0].resetAt="2026-11-14T10:00:00Z";s.windows[0].usedPercent=2;
          var r=quotaCrossings(p,s,Date.parse("2026-11-14T05:01:00Z"));p=r.previous;out.push(r.thresholds);
          s.windows[0].usedPercent=80;out.push(quotaCrossings(p,s,Date.parse("2026-11-14T06:00:00Z")).thresholds);
          return out;
        })()''')
        self.assertEqual(result, [[], [80], [], [], [], [100], [], [], [80]])

    def test_starting_above_limit_and_stale_readings_are_silent(self) -> None:
        result = self.js('''(function(){var s={status:"ACTIVE",headlineWindowId:"session",windows:[{id:"session",usedPercent:100}]};
          var a=quotaCrossings(null,s,0);s.status="STALE";s.windows[0].usedPercent=80;
          var b=quotaCrossings(a.previous,s,0);return [a.thresholds,b.thresholds,b.previous.high]})()''')
        self.assertEqual(result, [[], [], 100])

    def test_reset_countdown_uses_clock_over_cached_copy(self) -> None:
        result = self.js('''(function(){var w={resetAt:"2026-11-14T05:00:00Z",resetCopy:"Resets in 5h"};
          return [resetCopy(w,Date.parse("2026-11-14T04:59:30Z"),"remaining"),resetCopy(w,Date.parse("2026-11-14T05:00:00Z"),"remaining")]})()''')
        self.assertEqual(result, ["Resets in 30s", "Reset due"])

    def test_order_is_complete_unique_and_rejects_unknown_providers(self) -> None:
        self.assertEqual(self.js('providerOrder(["cursor","cursor","unknown","claude"])'), ["cursor", "claude", "codex", "antigravity"])


if __name__ == "__main__":
    unittest.main()
