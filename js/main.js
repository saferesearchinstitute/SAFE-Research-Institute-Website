/* ============================================
   SAFE Research Institute - Main JavaScript
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {

  // --- Mobile navigation toggle ---
  const navToggle = document.getElementById('navToggle');
  const navLinks = document.getElementById('navLinks');

  if (navToggle && navLinks) {
    const setOpen = (open) => {
      navLinks.classList.toggle('active', open);
      navToggle.setAttribute('aria-expanded', String(open));
      const spans = navToggle.querySelectorAll('span');
      spans[0].style.transform = open ? 'translateY(7px) rotate(45deg)' : '';
      spans[1].style.opacity = open ? '0' : '';
      spans[2].style.transform = open ? 'translateY(-7px) rotate(-45deg)' : '';
    };
    navToggle.addEventListener('click', () => setOpen(!navLinks.classList.contains('active')));
    navLinks.querySelectorAll('a').forEach(link => link.addEventListener('click', () => setOpen(false)));

    // --- Mark the current page in the navigation ---
    // The header markup is identical on every page; this sets aria-current.
    const here = (location.pathname.split('/').pop() || 'index').replace(/\.html$/, '') || 'index';
    const inLibrary = /\/(library|news)\//.test(location.pathname);
    const section = {
      library: 'library', policy: 'library',
      education: 'education',
      about: 'about', donate: 'donate'
        }[here];
    const current = inLibrary ? 'library' : section;
    navLinks.querySelectorAll('a').forEach(link => {
      const target = link.getAttribute('href').split('/').pop().replace(/\.html$/, '');
      if (current && target === current) link.setAttribute('aria-current', 'page');
    });
  }

  // --- Volunteer form: conditional fields ---
  const taskForceSelect = document.getElementById('taskForceSelect');
  if (taskForceSelect) {
    const allConditional = document.querySelectorAll('.conditional-fields');
    taskForceSelect.addEventListener('change', () => {
      allConditional.forEach(el => el.classList.remove('active'));
      const target = document.getElementById(`fields-${taskForceSelect.value}`);
      if (target) target.classList.add('active');
    });
  }

});
