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

// Age picker: one choice per visitor, applied on every page.
(function () {
  var root = document.documentElement, KEY = "bm-age";
  function set(age) {
    root.dataset.age = age;
    document.querySelectorAll(".agepick button").forEach(function (b) {
      b.setAttribute("aria-pressed", String(b.dataset.age === age));
    });
    try { localStorage.setItem(KEY, age); } catch (e) {}
  }
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  if (saved && /^(25|30|35|40)$/.test(saved)) set(saved);
  document.querySelectorAll(".agepick button").forEach(function (b) {
    b.addEventListener("click", function () { set(b.dataset.age); });
  });
})();

// View picker (by age / by year / from peak). Falls back to the page's first
// option when the remembered view isn't offered here.
(function () {
  var root = document.documentElement, KEY = "bm-view";
  var btns = document.querySelectorAll(".viewpick button");
  if (!btns.length) return;
  function offered(v) { return Array.prototype.some.call(btns, function (b) { return b.dataset.view === v; }); }
  function set(v) {
    if (!offered(v)) v = btns[0].dataset.view;
    root.dataset.view = v;
    btns.forEach(function (b) { b.setAttribute("aria-pressed", String(b.dataset.view === v)); });
    try { localStorage.setItem(KEY, v); } catch (e) {}
  }
  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  set(saved || btns[0].dataset.view);
  btns.forEach(function (b) { b.addEventListener("click", function () { set(b.dataset.view); }); });
})();
