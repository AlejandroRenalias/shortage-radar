(() => {
  let saved;
  try { saved = localStorage.getItem('language'); } catch (_) {}
  const language = ['en', 'fi'].includes(saved) ? saved : (navigator.language || '').toLowerCase().startsWith('fi') ? 'fi' : 'en';
  document.documentElement.lang = language;
  if (language === 'fi') document.documentElement.classList.add('i18n-pending');
  window.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
      if (document.documentElement.dataset.appReady) return;
      const list = document.getElementById('list'), updated = document.getElementById('updated');
      if (updated) updated.textContent = language === 'fi' ? 'Tietojen lataaminen epäonnistui' : 'Unable to load data';
      if (list) {
        list.textContent = language === 'fi' ? 'Tietoja ei voitu ladata. ' : 'Data could not be loaded. ';
        const link = document.createElement('a'); link.href = 'https://fimea.fi/en/about_us/open-data'; link.textContent = language === 'fi' ? 'Fimean avoin data' : 'Fimea open data'; list.append(link);
      }
      document.documentElement.classList.remove('i18n-pending');
    }, 2000);
  });
})();
