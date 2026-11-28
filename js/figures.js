/* ============================================
   SAFE Research Institute - Interactive figures
   Loaded only on publications that declare interactive figures.

   The page already holds everything without this script: each figure has
   a static image, a caption, and its numbers in an HTML table. This script
   reads that same table and draws a chart from it (so the chart and the
   table cannot disagree), then hides the static image. If a library fails
   to load, the static image stays.

   Libraries: D3, Observable Plot, and (for maps) topojson-client plus the
   us-atlas state shapes. Versions are pinned in docs/templates/build_site.py.
   ============================================ */

(function () {
  if (!window.Plot || !window.d3) return;
  const Plot = window.Plot, d3 = window.d3;

  const C = { aubergine: '#534A6D', violet: '#69698F', teal: '#93B7BD', mist: '#BFDADA', ink: '#2A2438', deep: '#2C6B74', muted: '#676380', warm: '#B4553A', rule: '#DAD8E4' };
  const SERIES = [C.aubergine, C.deep, C.warm, C.violet, '#9A6B00', C.teal];
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  // Postal code, FIPS code (the id us-atlas uses) and name for the 50 states and DC.
  const STATES = 'AL01Alabama|AK02Alaska|AZ04Arizona|AR05Arkansas|CA06California|CO08Colorado|CT09Connecticut|DE10Delaware|DC11District of Columbia|FL12Florida|GA13Georgia|HI15Hawaii|ID16Idaho|IL17Illinois|IN18Indiana|IA19Iowa|KS20Kansas|KY21Kentucky|LA22Louisiana|ME23Maine|MD24Maryland|MA25Massachusetts|MI26Michigan|MN27Minnesota|MS28Mississippi|MO29Missouri|MT30Montana|NE31Nebraska|NV32Nevada|NH33New Hampshire|NJ34New Jersey|NM35New Mexico|NY36New York|NC37North Carolina|ND38North Dakota|OH39Ohio|OK40Oklahoma|OR41Oregon|PA42Pennsylvania|RI44Rhode Island|SC45South Carolina|SD46South Dakota|TN47Tennessee|TX48Texas|UT49Utah|VT50Vermont|VA51Virginia|WA53Washington|WV54West Virginia|WI55Wisconsin|WY56Wyoming'
    .split('|').map(s => ({ postal: s.slice(0, 2), fips: s.slice(2, 4), name: s.slice(4) }));
  const byPostal = new Map(STATES.map(s => [s.postal, s]));
  const byFips = new Map(STATES.map(s => [s.fips, s]));
  const placeName = v => (byPostal.has(v) ? byPostal.get(v).name : v);

  // ---------- data: read the figure's own HTML table ----------
  function readTable(table) {
    const fields = Array.from(table.querySelectorAll('thead th')).map(th => th.dataset.field || th.textContent.trim());
    const labels = {};
    table.querySelectorAll('thead th').forEach((th, i) => { labels[fields[i]] = th.textContent.trim(); });
    const rows = Array.from(table.querySelectorAll('tbody tr')).map(tr => {
      const row = {};
      Array.from(tr.cells).forEach((td, i) => {
        const raw = td.textContent.trim();
        const num = raw === '' ? null : Number(raw.replace(/,/g, ''));
        row[fields[i]] = raw === '' ? null : (Number.isFinite(num) && /^-?[\d.,]+(e-?\d+)?$/i.test(raw) ? num : raw);
      });
      return row;
    });
    return { fields, labels, rows };
  }

  const fmt = v => (typeof v === 'number' ? (Math.abs(v) >= 1000 ? d3.format(',.0f')(v) : d3.format(',.4~g')(v)) : (v == null ? 'no value' : String(v)));

  // ---------- one chart ----------
  function draw(holder, data, spec, state) {
    const s = Object.assign({}, spec, state.step || {});
    const width = Math.max(300, Math.floor(holder.clientWidth));
    const small = width < 520;
    const lab = f => (s.labels && s.labels[f]) || data.labels[f] || f;
    const hi = state.place != null && s.key ? state.place : (s.highlight != null ? s.highlight : null);
    const hiField = state.place != null && s.key ? s.key : (s.highlightField || s.x);
    const isHi = d => hi != null && String(d[hiField]) === String(hi);
    const fillFor = d => (hi == null ? C.aubergine : (isHi(d) ? C.warm : C.teal));
    const tipChannels = fields => Object.fromEntries(fields.filter(Boolean).map(f => [lab(f), d => (f === s.key ? placeName(d[f]) : d[f])]));
    let rows = data.rows;
    if (s.filter) rows = rows.filter(d => String(d[s.filter.field]) === String(s.filter.value));
    if (s.exclude) rows = rows.filter(d => !s.exclude.values.map(String).includes(String(d[s.exclude.field])));
    const base = { width, marginLeft: 56, marginBottom: 44, style: { fontFamily: 'inherit', fontSize: small ? '11px' : '12.5px', color: C.ink, background: '#fff', overflow: 'visible' } };
    let options;

    if (s.type === 'line') {
      const hasBand = s.low && s.high && rows.some(d => d[s.low] != null && d[s.high] != null);
      options = Object.assign(base, {
        height: small ? 280 : 380,
        x: { label: lab(s.x), tickFormat: d => String(d), nice: true },
        y: { label: lab(s.y), grid: true, zero: s.zero !== false && !s.yDomain, domain: s.yDomain },
        color: s.series ? { legend: true, range: SERIES } : undefined,
        marks: [
          hasBand ? Plot.areaY(rows.filter(d => d[s.low] != null), { x: s.x, y1: s.low, y2: s.high, fill: C.mist, fillOpacity: 0.7 }) : null,
          s.yDomain ? null : Plot.ruleY([0], { stroke: C.rule }),
          Plot.lineY(rows, s.series ? { x: s.x, y: s.y, z: s.series, stroke: s.series, strokeWidth: 2 } : { x: s.x, y: s.y, stroke: C.muted, strokeWidth: 1.5 }),
          Plot.dot(rows, { x: s.x, y: s.y, r: d => (isHi(d) ? 7 : 4.5), fill: s.series ? s.series : fillFor, stroke: '#fff', tip: true,
            channels: tipChannels([s.x, s.y, s.low, s.high, s.series]) })
        ]
      });
    } else if (s.type === 'bar' || s.type === 'stacked') {
      const values = s.type === 'stacked' ? s.values : [s.y];
      const tidy = s.type === 'stacked'
        ? rows.flatMap(d => values.map(f => Object.assign({}, d, { __series: lab(f), __value: d[f] })))
        : rows.map(d => Object.assign({}, d, { __value: d[s.y] }));
      const cats = rows.length;
      const horizontal = s.orient ? s.orient === 'h' : cats > 7;
      const order = s.sort === false ? undefined : (horizontal ? { y: '-x' } : { x: '-y' });
      const common = { fill: s.type === 'stacked' ? '__series' : fillFor, tip: true, channels: tipChannels([s.key && s.key !== s.x ? s.key : null]) };
      options = Object.assign(base, horizontal ? {
        height: Math.max(260, cats * (small ? 17 : 20) + 70),
        marginLeft: s.marginLeft || (small ? 96 : 150),
        x: { label: s.type === 'stacked' ? (s.valueLabel || '') : lab(s.y), grid: true },
        y: { label: null, tickFormat: d => (s.x === s.key ? placeName(d) : d) },
        color: s.type === 'stacked' ? { legend: true, range: SERIES } : undefined,
        marks: [Plot.barX(tidy, Object.assign({ y: s.x, x: '__value', sort: order }, common)), Plot.ruleX([0], { stroke: C.ink })]
      } : {
        height: small ? 300 : 380,
        x: { label: null, tickFormat: d => String(d) },
        y: { label: s.type === 'stacked' ? (s.valueLabel || '') : lab(s.y), grid: true },
        color: s.type === 'stacked' ? { legend: true, range: SERIES } : undefined,
        marks: [Plot.barY(tidy, Object.assign({ x: s.x, y: '__value', sort: s.sort ? order : undefined }, common)), Plot.ruleY([0], { stroke: C.ink })]
      });
    } else if (s.type === 'scatter') {
      // points outside a stated axis range are left off the chart; they stay in the data table
      const inside = (v, dom) => !dom || (v != null && v >= dom[0] && v <= dom[1]);
      rows = rows.filter(d => inside(d[s.x], s.xDomain) && inside(d[s.y], s.yDomain));
      options = Object.assign(base, {
        height: small ? 320 : 420,
        x: { label: lab(s.x), grid: true, domain: s.xDomain },
        y: { label: lab(s.y), grid: true, domain: s.yDomain },
        marks: [
          Plot.ruleY([0], { stroke: C.rule }), Plot.ruleX([0], { stroke: C.rule }),
          Plot.dot(rows.filter(d => !isHi(d)), { x: s.x, y: s.y, r: 3, clip: true, fill: hi == null ? C.aubergine : C.teal, fillOpacity: hi == null ? 0.45 : 0.3, tip: true,
            channels: tipChannels([s.name, s.key && s.key !== s.name ? s.key : null]) }),
          Plot.dot(rows.filter(isHi), { x: s.x, y: s.y, r: 5, clip: true, fill: C.warm, stroke: '#fff', tip: true, channels: tipChannels([s.name, s.key]) })
        ]
      });
    } else if (s.type === 'map') {
      if (!state.shapes) return null;
      const value = new Map(rows.map(d => [String(d[s.key]), d]));
      const feats = state.shapes.features.filter(f => byFips.has(f.id));
      const rowOf = f => value.get(byFips.get(f.id).postal);
      options = {
        width, height: Math.round(width * 610 / 975) + 40, projection: { type: 'identity', domain: { type: 'FeatureCollection', features: feats } },
        style: base.style,
        color: { type: s.diverging ? 'diverging' : 'quantize', scheme: s.diverging ? 'PuOr' : 'Purples', n: 6, pivot: s.diverging ? 0 : undefined,
          legend: true, label: lab(s.value), unknown: '#e9e7ef' },
        marks: [
          Plot.geo(feats, { fill: f => (rowOf(f) ? rowOf(f)[s.value] : null), stroke: '#fff', strokeWidth: 0.75 }),
          Plot.geo(feats.filter(f => hi != null && byFips.get(f.id).postal === String(hi)), { fill: 'none', stroke: C.warm, strokeWidth: 3 }),
          Plot.tip(feats, Plot.pointer(Plot.centroid({
            title: f => `${byFips.get(f.id).name}\n${lab(s.value)}: ${fmt(rowOf(f) ? rowOf(f)[s.value] : null)}`
          })))
        ]
      };
      const chart = Plot.plot(options);
      chart.addEventListener('click', () => {
        const f = chart.value;
        if (f && f.id && byFips.has(f.id)) document.dispatchEvent(new CustomEvent('place:select', { detail: { key: s.key, value: byFips.get(f.id).postal } }));
      });
      chart.style.cursor = 'pointer';
      return chart;
    } else {
      return null;
    }
    return Plot.plot(options);
  }

  // ---------- download the chart as drawn ----------
  function exportPng(svg, name) {
    const clone = svg.cloneNode(true);
    const w = svg.clientWidth || Number(svg.getAttribute('width')) || 900;
    const h = svg.clientHeight || Number(svg.getAttribute('height')) || 500;
    clone.setAttribute('xmlns', 'http://www.w3.org/2000/svg');
    clone.setAttribute('width', w);
    clone.setAttribute('height', h);
    clone.style.fontFamily = 'Helvetica, Arial, sans-serif';
    const url = URL.createObjectURL(new Blob([new XMLSerializer().serializeToString(clone)], { type: 'image/svg+xml;charset=utf-8' }));
    const img = new Image();
    img.onload = () => {
      const scale = 2, canvas = document.createElement('canvas');
      canvas.width = w * scale; canvas.height = h * scale;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#fff'; ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      URL.revokeObjectURL(url);
      canvas.toBlob(blob => {
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob); a.download = name;
        document.body.appendChild(a); a.click(); a.remove();
      }, 'image/png');
    };
    img.src = url;
  }

  // ---------- wire one figure ----------
  function setUp(fig, shapes) {
    let spec;
    try { spec = JSON.parse(fig.dataset.chart); } catch (e) { return; }
    const table = fig.querySelector('.figure-data table');
    if (!table) return;
    const data = readTable(table);
    const still = fig.querySelector('img');
    const holder = document.createElement('div');
    holder.className = 'figure-chart';
    holder.setAttribute('role', 'img');
    holder.setAttribute('aria-label', still ? still.alt : 'Chart');
    (still || fig.firstChild).before(holder);
    const state = { shapes, place: null, step: null };

    function render() {
      let chart = null;
      try { chart = draw(holder, data, spec, state); } catch (e) { chart = null; }
      if (!chart) { holder.hidden = true; if (still) still.hidden = false; return; }
      holder.replaceChildren(chart);
      holder.hidden = false;
      if (still) still.hidden = true;          // only after a chart exists
      fig.classList.add('is-interactive');
    }
    render();

    let lastWidth = holder.clientWidth;
    new ResizeObserver(() => {
      if (Math.abs(holder.clientWidth - lastWidth) > 12) { lastWidth = holder.clientWidth; render(); }
    }).observe(holder);

    document.addEventListener('place:select', e => {
      if (spec.key && e.detail.key === spec.key) { state.place = e.detail.value; render(); }
    });

    // PNG of the chart as currently drawn (the static link stays for readers without scripts)
    const png = fig.querySelector('a[data-download="png"]');
    if (png) png.addEventListener('click', e => {
      const svg = holder.querySelector('svg:last-of-type') || holder.querySelector('svg');
      if (!svg || holder.hidden) return;
      e.preventDefault();
      exportPng(svg, png.getAttribute('download') || 'figure.png');
    });

    // Scroll-led steps: the list is already in the page; here it becomes a sticky figure with steps beside it.
    const steps = fig.querySelector('.figure-steps');
    if (steps && steps.children.length) {
      fig.classList.add('scrolly');
      // chart, caption, data and downloads travel together beside the steps
      const wrap = document.createElement('div');
      wrap.className = 'scrolly-figure';
      Array.from(fig.children).filter(el => el !== steps).forEach(el => wrap.appendChild(el));
      fig.prepend(wrap);
      const items = Array.from(steps.children);
      const activate = li => {
        items.forEach(x => x.classList.toggle('is-active', x === li));
        let override = null;
        try { override = li.dataset.step ? JSON.parse(li.dataset.step) : null; } catch (e) { override = null; }
        state.step = override; render();
      };
      const io = new IntersectionObserver(entries => {
        entries.forEach(en => { if (en.isIntersecting) activate(en.target); });
      }, { rootMargin: '-45% 0px -45% 0px', threshold: 0 });
      items.forEach(li => {
        io.observe(li);
        li.tabIndex = 0;
        li.addEventListener('focus', () => activate(li));
        li.addEventListener('click', () => activate(li));
      });
    }
  }

  // ---------- "find your state" ----------
  // ---------- state map inside the lookup: toggle between measures, click to select ----------
  function setUpLookupMap(box, data, key, shapes) {
    const fig = box.querySelector('.place-map');
    if (!fig || !shapes) return;
    let cfg;
    try { cfg = JSON.parse(fig.dataset.map); } catch (e) { return; }
    const holder = fig.querySelector('.place-map-chart');
    const toggle = fig.querySelector('.place-map-toggle');
    const hint = fig.querySelector('.place-map-hint');
    const feats = shapes.features.filter(f => byFips.has(f.id));
    const rowBy = new Map(data.rows.map(d => [String(d[key]), d]));
    const rowOf = f => rowBy.get(byFips.get(f.id).postal);
    const unit = m => (m.unit ? ' ' + m.unit : '');
    const state = { measure: cfg.measures[0], place: null };

    function render() {
      const width = Math.max(280, Math.floor(holder.clientWidth));
      const m = state.measure;
      const chart = Plot.plot({
        width, height: Math.round(width * 610 / 975) + 46,
        projection: { type: 'identity', domain: { type: 'FeatureCollection', features: feats } },
        style: { fontFamily: 'inherit', fontSize: width < 520 ? '11px' : '12.5px', color: C.ink, background: '#fff', overflow: 'visible' },
        // one sequential ramp, light to dark; no red-green pairing
        color: { type: 'quantize', scheme: 'Purples', n: 6, legend: true, label: width < 520 ? (m.unit || m.label) : m.label + (m.unit ? ' (' + m.unit + ')' : ''), unknown: '#f1f0f5' },
        marks: [
          Plot.geo(feats, { fill: f => (rowOf(f) ? rowOf(f)[m.field] : null), stroke: '#6f6b86', strokeWidth: 0.6 }),
          Plot.geo(feats.filter(f => state.place != null && byFips.get(f.id).postal === String(state.place)), { fill: 'none', stroke: C.ink, strokeWidth: 3 }),
          Plot.tip(feats, Plot.pointer(Plot.centroid({
            title: f => [byFips.get(f.id).name].concat(cfg.measures.map(x => `${x.label}: ${fmt(rowOf(f) ? rowOf(f)[x.field] : null)}${unit(x)}`)).join('\n')
          })))
        ]
      });
      chart.style.cursor = 'pointer';
      chart.addEventListener('click', () => {
        const f = chart.value;
        if (f && f.id && byFips.has(f.id)) document.dispatchEvent(new CustomEvent('place:select', { detail: { key, value: byFips.get(f.id).postal } }));
      });
      const hadFocus = holder.contains(document.activeElement);
      holder.replaceChildren(chart);
      holder.setAttribute('role', 'group');
      holder.setAttribute('aria-label', 'Map of the United States shaded by ' + m.label + (state.place ? '. Selected: ' + placeName(state.place) : '') + '. Arrow keys move between states, Enter selects.');
      keys(chart, hadFocus);
    }

    // Keyboard: the map is one tab stop; arrow keys move to the nearest state
    // in that direction, Home and End jump to the first and last by name,
    // Enter or Space selects. Focus shows the same values as hover.
    const path = d3.geoPath();
    const centre = new Map(feats.map(f => [f.id, path.centroid(f)]));
    const order = feats.slice().sort((x, y) => byFips.get(x.id).name.localeCompare(byFips.get(y.id).name));
    const describe = f => [byFips.get(f.id).name].concat(cfg.measures.map(x => `${x.label}: ${fmt(rowOf(f) ? rowOf(f)[x.field] : null)}${unit(x)}`)).join('. ');
    const hintText = hint.textContent;
    let current = null;
    function keys(chart, refocus) {
      const group = chart.querySelector('g[aria-label="geo"]');
      const paths = group ? Array.from(group.querySelectorAll('path')) : [];
      if (paths.length !== feats.length) return;
      const el = new Map(feats.map((f, i) => [f.id, paths[i]]));
      const selected = feats.find(f => state.place != null && byFips.get(f.id).postal === String(state.place));
      if (!current || !el.has(current)) current = (selected || order[0]).id;
      const go = id => { el.get(current).setAttribute('tabindex', '-1'); current = id; el.get(id).setAttribute('tabindex', '0'); el.get(id).focus(); };
      const pick = f => document.dispatchEvent(new CustomEvent('place:select', { detail: { key, value: byFips.get(f.id).postal } }));
      const DIR = { ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowDown: [0, 1], ArrowUp: [0, -1] };
      feats.forEach(f => {
        const p = el.get(f.id);
        p.setAttribute('tabindex', f.id === current ? '0' : '-1');
        p.setAttribute('role', 'button');
        p.setAttribute('aria-label', describe(f));
        p.setAttribute('aria-pressed', String(f === selected));
        p.addEventListener('focus', () => { current = f.id; hint.textContent = describe(f); });
        p.addEventListener('blur', () => { hint.textContent = hintText; });
        p.addEventListener('keydown', e => {
          if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(f); return; }
          const i = order.indexOf(f);
          if (e.key === 'Home') { e.preventDefault(); go(order[0].id); return; }
          if (e.key === 'End') { e.preventDefault(); go(order[order.length - 1].id); return; }
          const d = DIR[e.key];
          if (!d) return;
          e.preventDefault();
          const [cx, cy] = centre.get(f.id);
          let best = null, score = Infinity;
          feats.forEach(g => {
            if (g === f) return;
            const [x, y] = centre.get(g.id);
            const along = (x - cx) * d[0] + (y - cy) * d[1];
            const across = Math.abs((x - cx) * d[1]) + Math.abs((y - cy) * d[0]);
            if (along <= 1 || across > along * 1.5) return;
            const sc = along + across * 2;
            if (sc < score) { score = sc; best = g; }
          });
          if (best) go(best.id);
        });
      });
      if (refocus) el.get(current).focus();
    }

    cfg.measures.forEach((m, i) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = m.label;
      btn.setAttribute('aria-pressed', String(i === 0));
      btn.classList.toggle('active', i === 0);
      btn.addEventListener('click', () => {
        state.measure = m;
        toggle.querySelectorAll('button').forEach(b => { b.classList.toggle('active', b === btn); b.setAttribute('aria-pressed', String(b === btn)); });
        render();
      });
      toggle.appendChild(btn);
    });
    holder.hidden = false;
    hint.hidden = false;
    toggle.hidden = cfg.measures.length < 2;
    render();
    let last = holder.clientWidth;
    new ResizeObserver(() => { if (Math.abs(holder.clientWidth - last) > 12) { last = holder.clientWidth; render(); } }).observe(holder);
    document.addEventListener('place:select', e => { if (e.detail.key === key) { state.place = e.detail.value; render(); } });
  }

  function setUpLookup(box, shapes) {
    let cfg;
    try { cfg = JSON.parse(box.dataset.lookup); } catch (e) { return; }
    const table = box.querySelector('table');
    if (!table) return;
    const data = readTable(table);
    const label = document.createElement('label');
    label.textContent = cfg.prompt || 'Choose a place';
    const select = document.createElement('select');
    select.className = 'form-control';
    select.id = 'placeSelect';
    label.htmlFor = select.id;
    select.append(new Option(cfg.placeholder || 'Select', ''));
    data.rows.map(r => r[cfg.key]).filter(Boolean)
      .sort((a, b) => placeName(a).localeCompare(placeName(b)))
      .forEach(v => select.append(new Option(placeName(v), v)));
    const out = document.createElement('dl');
    out.className = 'place-result';
    out.setAttribute('aria-live', 'polite');
    const controls = document.createElement('div');
    controls.className = 'place-controls';
    controls.append(label, select);
    box.querySelector('.place-lookup-body').prepend(controls, out);
    setUpLookupMap(box, data, cfg.key, shapes);

    function show(value, announce) {
      const row = data.rows.find(r => String(r[cfg.key]) === String(value));
      out.replaceChildren();
      if (!row) return;
      const head = document.createElement('div');
      head.className = 'place-name';
      head.textContent = placeName(value);
      out.append(head);
      (cfg.fields || []).forEach(f => {
        const wrap = document.createElement('div');
        const dt = document.createElement('dt'); dt.textContent = f.label || data.labels[f.field] || f.field;
        const dd = document.createElement('dd'); dd.textContent = fmt(row[f.field]) + (f.unit && row[f.field] != null ? ' ' + f.unit : '');
        wrap.append(dt, dd); out.append(wrap);
      });
      if (select.value !== value) select.value = value;
      if (announce) history.replaceState(null, '', '#' + cfg.key + '=' + encodeURIComponent(value));
    }
    select.addEventListener('change', () => {
      document.dispatchEvent(new CustomEvent('place:select', { detail: { key: cfg.key, value: select.value || null } }));
    });
    document.addEventListener('place:select', e => { if (e.detail.key === cfg.key) show(e.detail.value, true); });
    const m = location.hash.match(new RegExp('^#' + cfg.key + '=([^&]+)'));
    if (m) document.dispatchEvent(new CustomEvent('place:select', { detail: { key: cfg.key, value: decodeURIComponent(m[1]) } }));
  }

  document.addEventListener('DOMContentLoaded', () => {
    const figures = Array.from(document.querySelectorAll('figure[data-chart]'));
    const needsMap = figures.some(f => /"type"\s*:\s*"map"/.test(f.dataset.chart)) || !!document.querySelector('.place-map');
    const start = shapes => {
      figures.forEach(f => setUp(f, shapes));
      document.querySelectorAll('.place-lookup[data-lookup]').forEach(box => setUpLookup(box, shapes));
    };
    const src = document.documentElement.dataset.usAtlas;
    if (needsMap && window.topojson && src) {
      fetch(src, document.documentElement.dataset.usAtlasIntegrity ? { integrity: document.documentElement.dataset.usAtlasIntegrity } : undefined).then(r => r.json())
        .then(us => start(window.topojson.feature(us, us.objects.states)))
        .catch(() => start(null));
    } else {
      start(null);
    }
  });
})();
