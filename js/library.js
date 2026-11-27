/* ============================================
   SAFE Research Institute - Evidence Library
   The table in library.html is the single list of published work.
   This script (1) draws the cover for the newest document,
   (2) on the home page, copies the newest rows from library.html, and
   (3) on library.html, offers a filter by type once the list holds
   more than one type.
   Columns: Title, Type, Topic, Updated, PDF.
   ============================================ */

(function () {
  const HOME_ROWS = 10;
  const TYPE = 1, DATE = 3;

  const cellText = (row, i) => {
    const cells = row.querySelectorAll('td');
    return cells.length > i ? cells[i].textContent.trim() : '';
  };
  const isNews = row => cellText(row, TYPE).toLowerCase() === 'news';

  function setUpFilter(rows) {
    const bar = document.getElementById('listFilter');
    if (!bar) return;
    const types = Array.from(new Set(rows.map(r => cellText(r, TYPE)).filter(Boolean)));
    if (types.length < 2) return;
    const make = (label, value) => {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.textContent = label;
      btn.addEventListener('click', () => {
        bar.querySelectorAll('button').forEach(b => b.classList.toggle('active', b === btn));
        rows.forEach(r => { r.hidden = value !== null && cellText(r, TYPE) !== value; });
      });
      bar.appendChild(btn);
      return btn;
    };
    make('All', null).classList.add('active');
    types.forEach(t => make(t, t));
    bar.hidden = false;
  }

  function buildCover(row, slot) {
    if (!row || !slot || row.querySelector('.data-table-empty')) return;
    const cells = row.querySelectorAll('td');
    if (cells.length < 4) return;
    const link = cells[0].querySelector('a');
    const cover = document.createElement(link ? 'a' : 'div');
    cover.className = 'report-cover';
    if (link) cover.href = link.getAttribute('href');

    const mark = document.createElement('img');
    mark.className = 'report-cover-mark';
    mark.src = 'img/logo-mark.svg';
    mark.alt = '';
    mark.width = 68;
    mark.height = 68;

    const mid = document.createElement('div');
    const type = document.createElement('div');
    type.className = 'report-cover-type';
    type.textContent = cellText(row, TYPE);
    const title = document.createElement('div');
    title.className = 'report-cover-title';
    title.textContent = cellText(row, 0);
    mid.append(type, title);

    const foot = document.createElement('div');
    foot.className = 'report-cover-foot';
    foot.append('SAFE Research Institute', document.createElement('br'), cellText(row, DATE));

    cover.append(mark, mid, foot);
    slot.replaceChildren(cover);
  }

  document.addEventListener('DOMContentLoaded', () => {
    const slot = document.getElementById('featuredCover');
    const full = document.getElementById('libraryTable');
    const latest = document.getElementById('latestReports');

    if (full) {
      const rows = Array.from(full.querySelectorAll('tbody tr'));
      // the cover shows the newest document, even when a news item is newer
      buildCover(rows.find(r => !isNews(r)), slot);
      setUpFilter(rows);
      return;
    }
    if (!latest) return;

    fetch('library.html')
      .then(res => (res.ok ? res.text() : Promise.reject(new Error('library.html: ' + res.status))))
      .then(html => {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const all = Array.from(doc.querySelectorAll('#libraryTable tbody tr'));
        if (!all.length) return;
        const body = latest.querySelector('tbody');
        body.replaceChildren(...all.slice(0, HOME_ROWS).map(r => document.importNode(r, true)));
        const newest = all.find(r => !isNews(r));
        buildCover(newest ? document.importNode(newest, true) : null, slot);
      })
      .catch(() => { /* the static row linking to the library stays in place */ });
  });
})();
