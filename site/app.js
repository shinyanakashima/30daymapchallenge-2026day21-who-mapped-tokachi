(() => {
  "use strict";

  const COLORS = {
    paper: "#f6f3ec", sea: "#d9e1e5", land: "#e6e2d6", outline: "#1f2428",
    new: "#d9480f", old: "#59616a", oldMinor: "#8d949a", farm: "#cdd3a8", wood: "#93a98a",
  };
  const FRAME_MS = 1400;
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ------------------------------------------------------------------ text
  const MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const T = {
    en: {
      kicker: "#30DayMapChallenge 2026 · Day 21 · OpenStreetMap",
      title: "Who mapped Tokachi?",
      lede: "Every line on OpenStreetMap was added by someone, and every edit is kept. Watch the map of Tokachi, Hokkaido, being drawn from a blank sheet.",
      asOf: "Map as of",
      layers: "Show",
      roads: "Roads", buildings: "Buildings (per 2 km cell)", farmland: "Farmland", woods: "Woods & windbreaks",
      keyNew: "Drawn in the past 12 months", keyOld: "Drawn earlier",
      finaleHead: "You can draw this map, too.",
      finaleBody: "OpenStreetMap is edited by volunteers. A farm road, a new shop, a windbreak that is missing: anyone with an account can add it.",
      finaleLink: "Open OpenStreetMap and start editing",
      close: "Close",
      loading: "Loading map data…",
      chartRoads: "Road length", chartBuildings: "Buildings", chartUsers: "People who edited (past 12 months)",
      play: "Play", pause: "Pause", year: "Year",
      km: (v) => `${fmt(v)} km`,
      count: (v) => fmt(v),
      people: (v) => `${fmt(v)}`,
      usersTip: (a, b, v) => `${a} – ${b}: ${fmt(v)} people`,
      roadsTip: (d, v) => `${d}: ${fmt(v)} km`,
      bldgTip: (d, v) => `${d}: ${fmt(v)} buildings`,
      date: (s) => { const [y, m, d] = s.split("-").map(Number); return `${d} ${MONTHS_EN[m - 1]} ${y}`; },
      aboutHead: "About the data",
      credit: 'Map data © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a> (ODbL) · History and statistics: <a href="https://ohsome.org/" target="_blank" rel="noopener">ohsome</a> by HeiGIT · Outline: MLIT National Land Numerical Information (N03)',
      mapLabel: "Map of Tokachi showing OpenStreetMap features by the year they were drawn",
    },
    ja: {
      kicker: "#30DayMapChallenge 2026 · Day 21 · OpenStreetMap",
      title: "十勝の地図は、誰が描いた？",
      lede: "OpenStreetMap の線は、どれも誰かが描き足したもの。そして、すべての編集の履歴が残っています。白紙だった十勝の地図が描かれていく様子を、年ごとに見ていきます。",
      asOf: "この日の地図",
      layers: "表示",
      roads: "道路", buildings: "建物（約2km四方ごと）", farmland: "農地", woods: "林・防風林",
      keyNew: "直前の1年で描かれたもの", keyOld: "それより前に描かれたもの",
      finaleHead: "この地図は、あなたも描き足せる。",
      finaleBody: "OpenStreetMap はボランティアが編集している地図です。農道、新しいお店、まだ描かれていない防風林。アカウントがあれば、誰でも描き足せます。",
      finaleLink: "OpenStreetMap を開いて編集する",
      close: "閉じる",
      loading: "地図データを読み込んでいます…",
      chartRoads: "道路の長さ", chartBuildings: "建物の数", chartUsers: "編集した人の数（直前1年）",
      play: "再生", pause: "一時停止", year: "年",
      km: (v) => `${fmt(v)} km`,
      count: (v) => `${fmt(v)} 棟`,
      people: (v) => `${fmt(v)} 人`,
      usersTip: (a, b, v) => `${a}〜${b}：${fmt(v)} 人`,
      roadsTip: (d, v) => `${d}：${fmt(v)} km`,
      bldgTip: (d, v) => `${d}：${fmt(v)} 棟`,
      date: (s) => { const [y, m, d] = s.split("-").map(Number); return `${y}年${m}月${d}日`; },
      aboutHead: "データについて",
      credit: '地図データ © <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a>（ODbL）・履歴と集計：<a href="https://ohsome.org/" target="_blank" rel="noopener">ohsome</a> by HeiGIT・管内の形：国土数値情報（行政区域 N03）',
      mapLabel: "十勝の地図。OpenStreetMap に描かれた年ごとに色分けしています",
    },
  };

  let lang = "en";
  const fmt = (v) => Math.round(v).toLocaleString(lang === "ja" ? "ja-JP" : "en-US");
  const t = (k) => T[lang][k];

  // ----------------------------------------------------------------- state
  let stats = null;
  let notes = null;
  let frame = 0;
  let timer = null;
  let finaleShown = false;
  const $ = (s) => document.querySelector(s);
  const slider = $("#slider");
  const playBtn = $("#play");

  // ------------------------------------------------------------------- map
  const map = new maplibregl.Map({
    container: "map",
    style: {
      version: 8,
      sources: {},
      layers: [{ id: "bg", type: "background", paint: { "background-color": COLORS.sea } }],
    },
    bounds: [[142.62, 42.12], [144.08, 43.68]],
    fitBoundsOptions: { padding: window.innerWidth <= 760 ? { top: 64, bottom: 10, left: 10, right: 10 } : 20 },
    minZoom: 6,
    maxZoom: 15,
    attributionControl: false,
    dragRotate: false,
    pitchWithRotate: false,
  });
  map.touchZoomRotate.disableRotation();
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
  map.addControl(new maplibregl.AttributionControl({
    compact: true,
    customAttribution: '© <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener">OpenStreetMap contributors</a> · ohsome by HeiGIT · N03',
  }), "bottom-right");

  const getJSON = (u) => fetch(u).then((r) => { if (!r.ok) throw new Error(`${u}: ${r.status}`); return r.json(); });

  // buildings come as counts per ~2 km grid cell at every frame
  function buildingsToGeoJSON(b) {
    return {
      type: "FeatureCollection",
      features: b.rows.map(([x, y, counts]) => {
        const props = {};
        counts.forEach((n, k) => {
          props[`n${k}`] = n;
          props[`d${k}`] = Math.max(0, n - (k ? counts[k - 1] : 0));
        });
        return { type: "Feature", properties: props, geometry: { type: "Point", coordinates: [x, y] } };
      }),
    };
  }
  const bRadius = (field) => ["interpolate", ["linear"], ["zoom"],
    7, ["*", 0.07, ["sqrt", ["get", field]]],
    10, ["*", 0.3, ["sqrt", ["get", field]]],
    13, ["*", 1.6, ["sqrt", ["get", field]]]];

  // features existing at frame k: a <= k <= z (z missing = still there)
  const alive = (k) => ["all", ["<=", ["get", "a"], k], [">=", ["coalesce", ["get", "z"], 999], k]];
  const isNew = (k) => ["all", ["==", ["get", "a"], k], [">=", ["coalesce", ["get", "z"], 999], k]];
  const isOld = (k) => ["all", ["<", ["get", "a"], k], [">=", ["coalesce", ["get", "z"], 999], k]];

  const GROUPS = {
    farmland: ["farmland-old", "farmland-new"],
    woods: ["woods-old", "woods-new", "woods-line-old", "woods-line-new"],
    buildings: ["buildings-old", "buildings-new"],
    roads: ["roads-old-minor", "roads-old", "roads-new"],
  };

  function addLayers(data) {
    map.addSource("hokkaido", { type: "geojson", data: data.hokkaido });
    map.addSource("tokachi", { type: "geojson", data: data.tokachi });
    map.addSource("farmland", { type: "geojson", data: data.farmland });
    map.addSource("woods", { type: "geojson", data: data.woods });
    map.addSource("roads", { type: "geojson", data: data.roads, buffer: 32, tolerance: 0.5 });
    map.addSource("buildings", { type: "geojson", data: buildingsToGeoJSON(data.buildings) });

    map.addLayer({ id: "land", type: "fill", source: "hokkaido", paint: { "fill-color": COLORS.land } });
    map.addLayer({ id: "tokachi-fill", type: "fill", source: "tokachi", paint: { "fill-color": COLORS.paper } });

    const poly = (src) => ["==", ["geometry-type"], "Polygon"];
    map.addLayer({ id: "farmland-old", type: "fill", source: "farmland", filter: isOld(0), paint: { "fill-color": COLORS.farm, "fill-opacity": 0.85 } });
    map.addLayer({ id: "farmland-new", type: "fill", source: "farmland", filter: isNew(0), paint: { "fill-color": COLORS.new, "fill-opacity": 0.35 } });
    map.addLayer({ id: "woods-old", type: "fill", source: "woods", filter: ["all", poly(), isOld(0)], paint: { "fill-color": COLORS.wood, "fill-opacity": 0.75 } });
    map.addLayer({ id: "woods-new", type: "fill", source: "woods", filter: ["all", poly(), isNew(0)], paint: { "fill-color": COLORS.new, "fill-opacity": 0.35 } });
    const line = ["==", ["geometry-type"], "LineString"];
    map.addLayer({ id: "woods-line-old", type: "line", source: "woods", filter: ["all", line, isOld(0)], paint: { "line-color": COLORS.wood, "line-width": 2 } });
    map.addLayer({ id: "woods-line-new", type: "line", source: "woods", filter: ["all", line, isNew(0)], paint: { "line-color": COLORS.new, "line-width": 2 } });

    map.addLayer({
      id: "roads-old-minor", type: "line", source: "roads", filter: ["all", [">=", ["get", "c"], 2], isOld(0)],
      layout: { "line-join": "round", "line-cap": "round" },
      paint: { "line-color": COLORS.oldMinor, "line-width": ["interpolate", ["linear"], ["zoom"], 7, 0.35, 10, 0.7, 14, 1.6] },
    });
    map.addLayer({
      id: "roads-old", type: "line", source: "roads", filter: ["all", ["<", ["get", "c"], 2], isOld(0)],
      layout: { "line-join": "round", "line-cap": "round" },
      paint: { "line-color": COLORS.old, "line-width": ["interpolate", ["linear"], ["zoom"], 7, ["match", ["get", "c"], 0, 1.3, 0.8], 12, ["match", ["get", "c"], 0, 3, 2], 14, ["match", ["get", "c"], 0, 5, 3.5]] },
    });
    map.addLayer({
      id: "buildings-old", type: "circle", source: "buildings", filter: [">", ["get", "n0"], 0],
      paint: { "circle-color": COLORS.old, "circle-opacity": 0.35, "circle-radius": bRadius("n0"), "circle-stroke-color": COLORS.old, "circle-stroke-width": 0.6, "circle-stroke-opacity": 0.6 },
    });
    map.addLayer({
      id: "roads-new", type: "line", source: "roads", filter: isNew(0),
      layout: { "line-join": "round", "line-cap": "round" },
      paint: { "line-color": COLORS.new, "line-width": ["interpolate", ["linear"], ["zoom"], 7, ["match", ["get", "c"], 0, 1.8, 1, 1.3, 0.7], 12, ["match", ["get", "c"], 0, 3.5, 1, 2.5, 1.6], 14, 4] },
    });
    map.addLayer({
      id: "buildings-new", type: "circle", source: "buildings", filter: [">", ["get", "d0"], 0],
      paint: { "circle-color": COLORS.new, "circle-opacity": 0.6, "circle-radius": bRadius("d0") },
    });
    map.addLayer({ id: "tokachi-line", type: "line", source: "tokachi", paint: { "line-color": COLORS.outline, "line-width": 1.2, "line-opacity": 0.8 } });
  }

  function setMapFrame(k) {
    if (!map.getLayer("roads-new")) return;
    map.setFilter("farmland-old", isOld(k));
    map.setFilter("farmland-new", isNew(k));
    const poly = ["==", ["geometry-type"], "Polygon"];
    const line = ["==", ["geometry-type"], "LineString"];
    map.setFilter("woods-old", ["all", poly, isOld(k)]);
    map.setFilter("woods-new", ["all", poly, isNew(k)]);
    map.setFilter("woods-line-old", ["all", line, isOld(k)]);
    map.setFilter("woods-line-new", ["all", line, isNew(k)]);
    map.setFilter("roads-old-minor", ["all", [">=", ["get", "c"], 2], isOld(k)]);
    map.setFilter("roads-old", ["all", ["<", ["get", "c"], 2], isOld(k)]);
    map.setFilter("roads-new", isNew(k));
    map.setFilter("buildings-old", [">", ["get", `n${k}`], 0]);
    map.setPaintProperty("buildings-old", "circle-radius", bRadius(`n${k}`));
    map.setFilter("buildings-new", [">", ["get", `d${k}`], 0]);
    map.setPaintProperty("buildings-new", "circle-radius", bRadius(`d${k}`));
  }

  // ---------------------------------------------------------------- charts
  const tip = $("#tip");
  function drawChart(id, values, fmtVal, tipText) {
    const fig = document.getElementById(id);
    const svg = fig.querySelector("svg");
    const W = svg.clientWidth || 300;
    const H = svg.clientHeight || 70;
    const top = 4, bottom = 14;
    const n = values.length;
    const max = Math.max(...values.filter((v) => v != null), 1);
    const step = W / n;
    const bw = Math.max(2, Math.min(step - 2, 18));
    let s = `<line class="base" x1="0" x2="${W}" y1="${H - bottom + 0.5}" y2="${H - bottom + 0.5}"/>`;
    values.forEach((v, i) => {
      const h = v == null ? 0 : Math.max(v > 0 ? 1 : 0, (v / max) * (H - top - bottom));
      const x = i * step + (step - bw) / 2;
      const y = H - bottom - h;
      const cls = i === frame ? "bar now" : i < frame ? "bar past" : "bar";
      const r = Math.min(2, bw / 2, h);
      s += h > 0
        ? `<path class="${cls}" d="M${x},${H - bottom} V${y + r} Q${x},${y} ${x + r},${y} H${x + bw - r} Q${x + bw},${y} ${x + bw},${y + r} V${H - bottom} Z"/>`
        : "";
    });
    const years = stats.timestamps.map((d) => d.slice(0, 4));
    const ticks = [0, Math.round((n - 1) / 2), n - 1];
    ticks.forEach((i, j) => {
      const anchor = j === 0 ? "start" : j === 2 ? "end" : "middle";
      const x = j === 0 ? 0 : j === 2 ? W : i * step + step / 2;
      const label = i === n - 1 && stats.timestamps[i].slice(5) !== "01-01" ? t("date")(stats.timestamps[i]) : years[i];
      s += `<text class="axis" x="${x}" y="${H - 3}" text-anchor="${anchor}">${label}</text>`;
    });
    values.forEach((v, i) => {
      s += `<rect class="hit" data-i="${i}" x="${i * step}" y="0" width="${step}" height="${H}"/>`;
    });
    svg.setAttribute("viewBox", `0 0 ${W} ${H}`);
    svg.innerHTML = s;
    fig.querySelector(".val").textContent = values[frame] == null ? "—" : fmtVal(values[frame]);
    svg.onmousemove = (e) => {
      const i = e.target.dataset && e.target.dataset.i;
      if (i == null) { tip.hidden = true; return; }
      const v = values[+i];
      tip.textContent = v == null ? "—" : tipText(+i, v);
      tip.hidden = false;
      const pr = $("#panel").getBoundingClientRect();
      const x = Math.min(e.clientX - pr.left + 10, pr.width - tip.offsetWidth - 4);
      tip.style.left = `${Math.max(4, x)}px`;
      tip.style.top = `${e.clientY - pr.top - 34}px`;
    };
    svg.onmouseleave = () => { tip.hidden = true; };
    svg.onclick = (e) => {
      const i = e.target.dataset && e.target.dataset.i;
      if (i != null) { stop(); setFrame(+i); }
    };
  }

  function drawCharts() {
    if (!stats) return;
    const d = (i) => t("date")(stats.timestamps[i]);
    drawChart("chart-roads", stats.roadKm, t("km"), (i, v) => T[lang].roadsTip(d(i), v));
    drawChart("chart-buildings", stats.buildings, t("count"), (i, v) => T[lang].bldgTip(d(i), v));
    drawChart("chart-users", stats.users, t("people"), (i, v) =>
      T[lang].usersTip(i === 0 ? t("date")("2007-10-08") : d(i - 1), d(i), v));
  }

  // ----------------------------------------------------------------- story
  function storyFor(k) {
    if (!notes) return "";
    const n = notes.frames[stats.timestamps[k]];
    if (!n) return "";
    const txt = n[lang];
    const src = n.source ? `<span class="src">${n.source[lang]}</span>` : "";
    return txt + src;
  }

  function setFrame(k) {
    frame = Math.max(0, Math.min(stats.timestamps.length - 1, k));
    slider.value = String(frame);
    const ds = t("date")(stats.timestamps[frame]);
    $("#date").textContent = ds;
    $("#slider-label").textContent = ds;
    slider.setAttribute("aria-valuetext", ds);
    $("#story").innerHTML = storyFor(frame);
    setMapFrame(frame);
    drawCharts();
    if (frame === stats.timestamps.length - 1 && !finaleShown) {
      finaleShown = true;
      $("#finale").hidden = false;
    }
  }

  function play() {
    if (!stats) return;
    if (frame >= stats.timestamps.length - 1) setFrame(0);
    $("#finale").hidden = true;
    if (frame === 0) finaleShown = false;
    timer = setInterval(() => {
      if (frame >= stats.timestamps.length - 1) { stop(); return; }
      setFrame(frame + 1);
      if (frame >= stats.timestamps.length - 1) stop();
    }, FRAME_MS);
    updatePlay();
  }
  function stop() {
    if (timer) clearInterval(timer);
    timer = null;
    updatePlay();
  }
  function updatePlay() {
    const playing = !!timer;
    $("#play-icon").setAttribute("d", playing ? "M3.5 2.5h3v11h-3zM9.5 2.5h3v11h-3z" : "M4 2.5v11l9-5.5z");
    playBtn.setAttribute("aria-label", playing ? t("pause") : t("play"));
  }

  // ------------------------------------------------------------------ i18n
  function applyLang(l) {
    lang = l;
    document.documentElement.lang = l;
    document.title = l === "ja" ? "十勝の地図は、誰が描いた？ | Who mapped Tokachi?" : "Who mapped Tokachi?";
    document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
    document.querySelectorAll("[data-i18n-aria]").forEach((el) => { el.setAttribute("aria-label", t(el.dataset.i18nAria)); });
    $(".credit").innerHTML = t("credit");
    if (notes) $(".about-body").innerHTML = notes.about[l];
    document.querySelectorAll(".lang button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.lang === l)));
    $("#map").setAttribute("aria-label", t("mapLabel"));
    slider.setAttribute("aria-label", t("year"));
    updatePlay();
    if (stats) setFrame(frame);
    try { localStorage.setItem("wmt-lang", l); } catch (e) { /* storage unavailable */ }
  }

  document.querySelectorAll(".lang button").forEach((b) => b.addEventListener("click", () => applyLang(b.dataset.lang)));
  slider.addEventListener("input", () => { stop(); setFrame(+slider.value); });
  playBtn.addEventListener("click", () => (timer ? stop() : play()));
  $("#finale-close").addEventListener("click", () => { $("#finale").hidden = true; });
  document.querySelectorAll(".layers input").forEach((inp) => inp.addEventListener("change", () => {
    const vis = inp.checked ? "visible" : "none";
    GROUPS[inp.dataset.layer].forEach((id) => map.getLayer(id) && map.setLayoutProperty(id, "visibility", vis));
  }));
  window.addEventListener("resize", () => drawCharts());

  let initial = "en";
  try {
    const saved = localStorage.getItem("wmt-lang");
    if (saved === "ja" || saved === "en") initial = saved;
  } catch (e) { /* storage unavailable */ }
  const q = new URLSearchParams(location.search);
  if (q.get("lang") === "ja" || q.get("lang") === "en") initial = q.get("lang");
  applyLang(initial);

  const files = ["stats", "notes", "hokkaido", "tokachi", "farmland", "woods", "roads", "buildings"];
  const urls = { stats: "data/stats.json", notes: "data/notes.json", buildings: "data/buildings.json" };
  const loaded = Promise.all(files.map((f) => getJSON(urls[f] || `data/${f}.geojson`)))
    .then((arr) => Object.fromEntries(files.map((f, i) => [f, arr[i]])));

  Promise.all([loaded, new Promise((res) => map.on("load", res))]).then(([data]) => {
    stats = data.stats;
    notes = data.notes;
    slider.max = String(stats.timestamps.length - 1);
    addLayers(data);
    applyLang(lang);
    const startFrame = q.has("frame") ? +q.get("frame") : 0;
    setFrame(startFrame);
    $("#loading").hidden = true;
    if (!reduceMotion && !q.has("frame")) setTimeout(play, 800);
  }).catch((err) => {
    console.error(err);
    $("#loading").textContent = String(err);
  });
})();
