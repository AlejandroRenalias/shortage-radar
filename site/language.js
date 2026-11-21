(() => {
  let saved;
  try { saved = localStorage.getItem('language'); } catch (_) {}
  const language = ['en', 'fi'].includes(saved) ? saved : (navigator.language || '').toLowerCase().startsWith('fi') ? 'fi' : 'en';
  document.documentElement.lang = language;
  if (language === 'fi') document.documentElement.classList.add('i18n-pending');
})();
