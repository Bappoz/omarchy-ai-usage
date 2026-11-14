.pragma library

// A quarter turn whose curvature ramps in/out, like CodeNotch's fluidTurn.
// Shared by the silhouette and the offset settings arc so their gap is even.
function flareWalk() {
  var points = [{u: 0, v: 0, heading: 0}]
  var u = 0, v = 0, count = 64
  for (var i = 1; i <= count; i++) {
    var t = (i - 0.5) / count
    var heading = Math.PI / 2 * t * t * (3 - 2 * t)
    u += Math.sin(heading) / count
    v += Math.cos(heading) / count
    points.push({u: u, v: v, heading: Math.PI / 2 * Math.pow(i / count, 2) * (3 - 2 * i / count)})
  }
  return points.map(function(p) { return {u: p.u / u, v: p.v / v, heading: p.heading} })
}

var FLARE = flareWalk()

function point(edge, u, v, depth) {
  if (edge === "left") return {x: depth - u, y: v}
  if (edge === "top") return {x: v, y: depth - u}
  if (edge === "bottom") return {x: v, y: u}
  return {x: u, y: v}
}
