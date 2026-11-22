(() => {
  // Old links to the home page with a search go to the list.
  if (document.documentElement.dataset.page === 'index') {
    try { const q = (new URLSearchParams(location.search).get('q') || '').trim().slice(0, 100); if (q) location.replace('shortages.html?q=' + encodeURIComponent(q)); } catch (_) {}
  }
  let saved;
  try { saved = localStorage.getItem('language'); } catch (_) {}
  const language = ['en', 'fi'].includes(saved) ? saved : (navigator.language || '').toLowerCase().startsWith('fi') ? 'fi' : 'en';
  document.documentElement.lang = language;
  if (language === 'fi') document.documentElement.classList.add('i18n-pending');
  window.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
      if (document.documentElement.dataset.appReady) return;
      const error = document.getElementById('load-error'), loading = document.getElementById('loading');
      if (error) error.hidden = false;
      if (loading) loading.hidden = true;
      document.documentElement.classList.remove('i18n-pending');
    }, 2000);
  });
})();
