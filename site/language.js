(() => {
  let saved;
  try { saved = localStorage.getItem('language'); } catch (_) {}
  // The phone's language setting: the first language of navigator.languages that the site has (Finnish or English), else English. The same rule as detectLanguage in lib.js.
  const list = Array.isArray(navigator.languages) && navigator.languages.length ? navigator.languages : [navigator.language];
  const found = list.map(l => String(l || '').toLowerCase().split('-')[0]).find(l => l === 'fi' || l === 'en');
  const language = ['en', 'fi'].includes(saved) ? saved : found || 'en';
  document.documentElement.lang = language;
  document.documentElement.classList.add('js');
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
