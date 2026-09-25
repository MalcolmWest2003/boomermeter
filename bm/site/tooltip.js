// Crosshair + tooltip for every chart that carries a .tt-data blob.
(function () {
  var tt = document.getElementById("tt");
  document.querySelectorAll("script.tt-data").forEach(function (blob) {
    var svg = document.getElementById(blob.dataset.for);
    if (!svg) return;
    var data = JSON.parse(blob.textContent);
    var hover = svg.querySelector(".hover"), line = svg.querySelector(".xhair");
    var hit = svg.querySelector(".hit");
    function move(ev) {
      var pt = svg.createSVGPoint();
      var src = ev.touches ? ev.touches[0] : ev;
      pt.x = src.clientX; pt.y = src.clientY;
      var p = pt.matrixTransform(svg.getScreenCTM().inverse());
      var rows = [], xLab = null, xPos = null, best = Infinity;
      data.series.forEach(function (s) {
        var bi = -1, bd = Infinity;
        for (var i = 0; i < s.px.length; i++) {
          var dd = Math.abs(s.px[i] - p.x);
          if (dd < bd) { bd = dd; bi = i; }
        }
        if (bi < 0 || bd > 40) return;
        if (bd < best) { best = bd; xLab = s.xl[bi]; xPos = s.px[bi]; }
        rows.push('<div><i style="background:var(' + s.color + ')"></i>' + s.name + ': <b>' + s.yl[bi] + '</b></div>');
      });
      if (!rows.length) { leave(); return; }
      hover.setAttribute("visibility", "visible");
      line.setAttribute("x1", xPos); line.setAttribute("x2", xPos);
      tt.innerHTML = "<div>" + xLab + "</div>" + rows.join("");
      tt.hidden = false;
      var x = src.clientX + 14, y = src.clientY + 14;
      if (x + tt.offsetWidth > window.innerWidth - 8) x = src.clientX - tt.offsetWidth - 14;
      tt.style.left = x + "px"; tt.style.top = y + "px";
    }
    function leave() { hover.setAttribute("visibility", "hidden"); tt.hidden = true; }
    hit.addEventListener("mousemove", move);
    hit.addEventListener("touchstart", move, { passive: true });
    hit.addEventListener("touchmove", move, { passive: true });
    hit.addEventListener("mouseleave", leave);
    hit.addEventListener("touchend", leave);
  });
})();
