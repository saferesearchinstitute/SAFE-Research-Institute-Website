/* ============================================
   SAFE Research Institute - Evidence Library
   The rows in library.html are written into the page by the build
   (docs/templates/build_site.py), so the list reads without JavaScript.
   This script adds filters by type and topic and a full-text search
   that uses library/search-index.json.
   Columns: Title, Type, Topic, Updated, PDF.
   ============================================ */

(function () {
  document.addEventListener('DOMContentLoaded', () => {
    const table = document.getElementById('libraryTable');
    if (!table) return;
    const rows = Array.from(table.querySelectorAll('tbody tr'));
    const cellText = (row, i) => (row.cells[i] ? row.cells[i].textContent.trim() : '');
    const state = { filters: {}, hits: null };

    function apply() {
      let shown = 0;
      rows.forEach(row => {
        const okFilters = Object.entries(state.filters).every(([col, value]) => value === null || cellText(row, Number(col)) === value);
        const okSearch = state.hits === null || state.hits.has(row.dataset.id);
        row.hidden = !(okFilters && okSearch);
        if (!row.hidden) shown += 1;
      });
      return shown;
    }

    // --- Filters: a bar appears only when its column holds two or more values ---
    document.querySelectorAll('.list-filter').forEach(bar => {
      const col = bar.dataset.column;
      const values = Array.from(new Set(rows.map(r => cellText(r, Number(col))).filter(Boolean)));
      if (values.length < 2) return;
      const label = document.createElement('span');
      label.className = 'list-filter-label';
      label.textContent = bar.dataset.name;
      bar.appendChild(label);
      const make = (text, value) => {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.textContent = text;
        btn.setAttribute('aria-pressed', 'false');
        btn.addEventListener('click', () => {
          bar.querySelectorAll('button').forEach(b => {
            b.classList.toggle('active', b === btn);
            b.setAttribute('aria-pressed', String(b === btn));
          });
          state.filters[col] = value;
          apply();
        });
        bar.appendChild(btn);
        return btn;
      };
      const all = make('All', null);
      all.classList.add('active');
      all.setAttribute('aria-pressed', 'true');
      values.forEach(v => make(v, v));
      state.filters[col] = null;
      bar.hidden = false;
    });

    // --- Search: titles, summaries and full text, from a prebuilt index ---
    const form = document.getElementById('librarySearch');
    const input = document.getElementById('libraryQuery');
    const status = document.getElementById('libraryStatus');
    if (!form || !input) return;
    form.hidden = false;
    form.addEventListener('submit', e => e.preventDefault());
    let index = null;
    const load = () => index || (index = fetch('library/search-index.json')
      .then(res => (res.ok ? res.json() : []))
      .then(items => items.map(it => ({ id: it.id, hay: [it.title, it.summary, it.type, it.topic, it.text].join(' ').toLowerCase() })))
      .catch(() => []));
    input.addEventListener('focus', load, { once: true });
    input.addEventListener('input', () => {
      const terms = input.value.toLowerCase().split(/\s+/).filter(Boolean);
      if (!terms.length) {
        state.hits = null;
        apply();
        status.textContent = '';
        return;
      }
      load().then(items => {
        state.hits = new Set(items.filter(it => terms.every(t => it.hay.includes(t))).map(it => it.id));
        const shown = apply();
        status.textContent = shown === 0
          ? 'No documents match. Try fewer or different words.'
          : shown + (shown === 1 ? ' document matches.' : ' documents match.');
      });
    });
  });
})();
