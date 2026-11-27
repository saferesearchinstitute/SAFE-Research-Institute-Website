/* ============================================
   SAFE Research Institute - Research reports
   The table in research.html is the single list of reports and news.
   This script (1) draws the cover for the newest report,
   (2) on the home page, copies the newest rows from research.html into
   the "Latest" section, and (3) on research.html, offers a Reports / News
   filter once the list holds both kinds.
   ============================================ */

(function () {
  const HOME_ROWS = 5;

  function isNews(row) {
    const cells = row.querySelectorAll('td');
    return cells.length > 2 && cells[2].textContent.trim().toLowerCase() === 'news';
  }

  function setUpFilter(rows) {
    const bar = document.getElementById('listFilter');
    if (!bar) return;
    const kinds = new Set(rows.map(r => (isNews(r) ? 'news' : 'report')));
    if (kinds.size < 2) return;
    bar.hidden = false;
    bar.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => {
        bar.querySelectorAll('button').forEach(b => b.classList.toggle('active', b === btn));
        const show = btn.dataset.show;
        rows.forEach(r => { r.hidden = show !== 'all' && (isNews(r) ? 'news' : 'report') !== show; });
      });
    });
  }

  function buildCover(row, slot) {
    if (!row || !slot || row.querySelector('.data-table-empty')) return;
    const cells = row.querySelectorAll('td');
    if (cells.length < 3) return;
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
    type.textContent = cells[2].textContent.trim();
    const title = document.createElement('div');
    title.className = 'report-cover-title';
    title.textContent = cells[0].textContent.trim();
    mid.append(type, title);

    const foot = document.createElement('div');
    foot.className = 'report-cover-foot';
    foot.append('SAFE Research Institute', document.createElement('br'), cells[1].textContent.trim());

    cover.append(mark, mid, foot);
    slot.replaceChildren(cover);
  }

  document.addEventListener('DOMContentLoaded', () => {
    const slot = document.getElementById('featuredCover');
    const full = document.getElementById('reportsTable');
    const latest = document.getElementById('latestReports');

    if (full) {
      const rows = Array.from(full.querySelectorAll('tbody tr'));
      buildCover(rows.find(r => !isNews(r)), slot);
      setUpFilter(rows);
      return;
    }
    if (!latest) return;

    fetch('research.html')
      .then(res => (res.ok ? res.text() : Promise.reject(new Error('research.html: ' + res.status))))
      .then(html => {
        const doc = new DOMParser().parseFromString(html, 'text/html');
        const rows = Array.from(doc.querySelectorAll('#reportsTable tbody tr')).slice(0, HOME_ROWS);
        if (!rows.length) return;
        const body = latest.querySelector('tbody');
        body.replaceChildren(...rows.map(r => document.importNode(r, true)));
        // the cover shows the newest report, even when a news item is newer
        const all = Array.from(doc.querySelectorAll('#reportsTable tbody tr'));
        const newest = all.find(r => !isNews(r));
        buildCover(newest ? document.importNode(newest, true) : null, slot);
      })
      .catch(() => { /* the static row linking to the Research page stays in place */ });
  });
})();
