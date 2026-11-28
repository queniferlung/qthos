// qthos.co dashboard: four stat tiles and one line chart, drawn from data.json.
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const svg = document.getElementById("chart-svg");
  const tip = document.getElementById("tip");
  const tiles = document.getElementById("tiles");
  let metrics = [];
  const revealed = new Set(); // graphs that have already played their draw-in
  let current = 0;

  const full = (n) => Math.round(n).toLocaleString("en-US");
  const short = (n) => {
    if (n >= 1e6) return (n / 1e6).toFixed(n % 1e6 === 0 ? 0 : 1) + "M";
    if (n >= 1e3) return Math.round(n / 1e3) + "K";
    return String(Math.round(n));
  };
  const day = (iso) => {
    const [, m, d] = iso.split("-").map(Number);
    return MONTHS[m - 1] + " " + d;
  };
  const tday = (iso) => Date.parse(iso + "T00:00:00Z") / 864e5;
  const el = (name, attrs, parent) => {
    const node = document.createElementNS(NS, name);
    for (const k in attrs) node.setAttribute(k, attrs[k]);
    if (parent) parent.appendChild(node);
    return node;
  };

  // Round the axis top up to a clean number so the middle gridline is clean too.
  function niceMax(v) {
    const pow = Math.pow(10, Math.floor(Math.log10(v)));
    for (const step of [1, 1.2, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]) {
      if (step * pow >= v) return step * pow;
    }
    return 10 * pow;
  }

  function build(data) {
    const views = data.views;
    const followers = data.followers;
    const since = day(data.since);

    const lump = data.viewsLump;
    // If a lifetime total is given, the early period with no daily data absorbs
    // the difference so the daily rows still add up to it.
    const dailyTotal = views.reduce((t, r) => t + r[1], 0);
    const lumpViews = data.lifetimeViews ? Math.max(0, data.lifetimeViews - dailyTotal) : lump.views;
    let running = lumpViews;
    // No daily views exist for the lump period, so its shape is estimated:
    // the known total is shared out day by day in proportion to follower gains.
    const t0 = tday(lump.from);
    const t1 = tday(lump.to);
    const weights = new Array(t1 - t0 + 1).fill(0);
    for (let i = 1; i < followers.length; i++) {
      const from = tday(followers[i - 1][0]);
      const to = tday(followers[i][0]);
      const gain = Math.max(0, followers[i][1] - followers[i - 1][1]) / (to - from);
      for (let d = from + 1; d <= to; d++) {
        if (d >= t0 && d <= t1) weights[d - t0] += gain;
      }
    }
    const floor = weights.reduce((a, b) => a + b, 0) / weights.length / 4; // quiet days still get views
    const totalWeight = weights.reduce((a, b) => a + b + floor, 0);
    let share = 0;
    const estimated = weights.map((w, i) => {
      share += w + floor;
      const d = new Date((t0 + i) * 864e5).toISOString().slice(0, 10);
      return {
        label: day(d), t: t0 + i, value: (lumpViews * share) / totalWeight,
        tipValue: (lumpViews * (w + floor)) / totalWeight,
      };
    });
    // The line is the running total; hovering shows that day's own views.
    const lifetime = estimated
      .concat(views.map(([d, v]) => ({ label: day(d), t: tday(d), value: (running += v), tipValue: v })));

    const sum = (rows) => rows.reduce((t, r) => t + r[1], 0);
    const last30 = sum(views.slice(-30));
    const firstF = followers[0][1];
    const lastF = followers[followers.length - 1][1];
    const gained = lastF - firstF;
    const months = data.monthly.map((m) => ({ name: MONTHS[Number(m.month.slice(5)) - 1], views: m.views }));
    const monthlyAvg = months.reduce((t, m) => t + m.views, 0) / months.length;

    document.getElementById("dash-range").textContent =
      "Updated " + day(data.updated);

    return [
      {
        label: "Lifetime views",
        value: data.lifetimeLabel || full(running),
        sub: "since " + since,
        unit: "daily views",
        points: lifetime,
      },
      {
        label: "Followers growth",
        value: (gained >= 0 ? "+" : "−") + full(Math.abs(gained)),
        sub: "since " + since,
        unit: "followers",
        points: followers.map(([d, v]) => ({ label: day(d), t: tday(d), value: v })),
      },
      {
        label: "30 days views",
        value: full(last30),
        sub: "",
        unit: "views that day",
        points: views.slice(-30).map(([d, v]) => ({ label: day(d), t: tday(d), value: v })),
      },
      {
        label: "Monthly average views",
        value: full(monthlyAvg),
        sub: "",
        unit: "total views",
        points: months.map((m) => ({ label: m.name, value: m.views })),
        markers: true,
        allLabels: true,
      },
    ];
  }

  // On first load each stat shuffles through random smaller numbers, then lands on its value.
  function shuffleIn(node, finalText, delay) {
    const digits = finalText.replace(/\D/g, "");
    if (!digits || (window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches)) return;
    const target = parseInt(digits, 10);
    const prefix = (finalText.match(/^\D*/) || [""])[0];
    const floor = Math.pow(10, digits.length - 1); // same number of digits, so the box does not jump
    if (target <= floor) return;
    const random = () => prefix + full(floor + Math.floor(Math.random() * (target - floor)));
    const duration = 1100;
    node.textContent = random();
    // Plain timers (not animation frames), so the real value always lands even in a background tab.
    const timer = setInterval(() => { node.textContent = random(); }, 55);
    setTimeout(() => { clearInterval(timer); node.textContent = finalText; }, delay + duration);
  }
  let shuffled = false;

  function renderTiles() {
    tiles.innerHTML = "";
    metrics.forEach((m, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "tile";
      b.setAttribute("role", "tab");
      b.setAttribute("aria-selected", i === current ? "true" : "false");
      b.innerHTML =
        '<span class="tile-label"></span><span class="tile-value"></span><span class="tile-sub"></span>';
      b.children[0].textContent = m.label;
      b.children[1].textContent = m.value;
      if (!shuffled) shuffleIn(b.children[1], m.value, i * 120);
      b.children[2].textContent = m.sub || "\u00a0"; // keep tile heights equal
      b.addEventListener("click", () => { current = i; renderTiles(); draw(); });
      tiles.appendChild(b);
    });
    shuffled = true;
  }

  function draw() {
    const m = metrics[current];
    const pts = m.points;
    const W = Math.max(280, svg.clientWidth || svg.parentNode.clientWidth);
    const H = Math.round(Math.min(360, Math.max(240, W * 0.42)));
    const pad = { l: 58, r: 18, t: 14, b: 34 };
    const iw = W - pad.l - pad.r;
    const ih = H - pad.t - pad.b;
    const top = niceMax(Math.max.apply(null, pts.map((p) => p.value)));
    // Dated series sit at their true date; the monthly series is evenly spaced.
    const pos = pts.map((p, i) => (p.t === undefined ? i : p.t));
    const span = pos[pos.length - 1] - pos[0] || 1;
    const x = (i) => pad.l + ((pos[i] - pos[0]) / span) * iw;
    const nearest = (target) => {
      let best = 0;
      for (let i = 1; i < pos.length; i++) {
        if (Math.abs(pos[i] - target) < Math.abs(pos[best] - target)) best = i;
      }
      return best;
    };
    const y = (v) => pad.t + ih - (v / top) * ih;

    svg.innerHTML = "";
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.setAttribute("aria-label", m.label + ": " + m.value + (m.sub ? ", " + m.sub : ""));
    tip.hidden = true;

    [0, top / 2, top].forEach((v) => {
      el("line", { class: "grid", x1: pad.l, x2: W - pad.r, y1: y(v), y2: y(v) }, svg);
      const t = el("text", { class: "axis-text", x: pad.l - 12, y: y(v) + 5, "text-anchor": "end" }, svg);
      t.textContent = short(v);
    });

    const labelAt = m.allLabels
      ? pts.map((_, i) => i)
      : [0, nearest(pos[0] + span / 2), pts.length - 1];
    labelAt.forEach((i, n) => {
      const anchor = n === 0 ? "start" : n === labelAt.length - 1 ? "end" : "middle";
      const t = el("text", { class: "axis-text", x: x(i), y: H - 8, "text-anchor": anchor }, svg);
      t.textContent = pts[i].label;
    });

    const path = (from, to) =>
      pts.slice(from, to + 1).map((p, k) => (k ? "L" : "M") + x(from + k).toFixed(1) + " " + y(p.value).toFixed(1)).join(" ");
    const solidFrom = m.dashedTo || 0;
    if (m.dashedTo) el("path", { class: "line est", d: path(0, m.dashedTo) }, svg);
    const line = el("path", { class: "line", d: path(solidFrom, pts.length - 1) }, svg);
    const dots = m.markers
      ? pts.map((p, i) => el("circle", { class: "dot", cx: x(i), cy: y(p.value), r: 5 }, svg))
      : [];

    // The first time a graph is shown, its line draws in from left to right. After that it is static.
    if (!revealed.has(current)) {
      revealed.add(current);
      const still = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (!still && line.getTotalLength) {
        const length = line.getTotalLength();
        const duration = 1300;
        line.style.strokeDasharray = length;
        line.style.strokeDashoffset = length;
        dots.forEach((d) => { d.style.opacity = 0; });
        line.getBoundingClientRect(); // apply the start state before animating
        line.style.transition = "stroke-dashoffset " + duration + "ms ease-in-out";
        line.style.strokeDashoffset = 0;
        dots.forEach((d, i) => {
          d.style.transition = "opacity 250ms ease " + Math.round((i / Math.max(1, dots.length - 1)) * duration) + "ms";
          d.style.opacity = 1;
        });
        setTimeout(() => { line.style.transition = ""; line.style.strokeDasharray = ""; line.style.strokeDashoffset = ""; }, duration + 100);
      }
    }

    const cross = el("line", { class: "cross", y1: pad.t, y2: pad.t + ih, visibility: "hidden" }, svg);
    const dot = el("circle", { class: "dot", r: 6, visibility: "hidden" }, svg);

    function move(ev) {
      const box = svg.getBoundingClientRect();
      const px = ((ev.clientX - box.left) / box.width) * W;
      const i = nearest(pos[0] + ((px - pad.l) / iw) * span);
      const p = pts[i];
      cross.setAttribute("x1", x(i)); cross.setAttribute("x2", x(i));
      dot.setAttribute("cx", x(i)); dot.setAttribute("cy", y(p.value));
      cross.setAttribute("visibility", "visible"); dot.setAttribute("visibility", "visible");
      tip.innerHTML = "<b></b><span></span>";
      tip.firstChild.textContent = full(p.tipValue === undefined ? p.value : p.tipValue);
      tip.lastChild.textContent = p.label + " · " + (p.extra || m.unit);
      tip.hidden = false;
      // Layout pixels, not screen pixels, so this stays right when the page is zoomed.
      const width = svg.clientWidth;
      const left = x(i) * (width / W);
      const flip = left > width / 2;
      tip.style.left = flip ? "" : left + 12 + "px";
      tip.style.right = flip ? width - left + 12 + "px" : "";
    }
    function leave() {
      cross.setAttribute("visibility", "hidden"); dot.setAttribute("visibility", "hidden");
      tip.hidden = true;
    }
    svg.onpointermove = move;
    svg.onpointerdown = move;
    svg.onpointerleave = leave;
  }

  fetch("data.json", { cache: "no-cache" })
    .then((r) => r.json())
    .then((data) => {
      metrics = build(data);
      const asked = parseInt(location.hash.slice(1), 10);
      if (asked >= 1 && asked <= metrics.length) current = asked - 1;
      renderTiles();
      draw();
      let timer;
      window.addEventListener("resize", () => { clearTimeout(timer); timer = setTimeout(draw, 120); });
    })
    .catch(() => { document.getElementById("dash-range").textContent = "Stats unavailable right now"; });
})();
