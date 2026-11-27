/* ============================================
   SAFE Research Institute - Research reports
   The reports table in research.html is the single list of reports.
   This script (1) draws the cover for the first row and
   (2) on the home page, copies the newest rows from research.html.
   ============================================ */

(function () {
  const HOME_ROWS = 5;

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
      buildCover(full.querySelector('tbody tr'), slot);
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
        buildCover(body.querySelector('tr'), slot);
      })
      .catch(() => { /* the static row linking to the Research page stays in place */ });
  });
})();
