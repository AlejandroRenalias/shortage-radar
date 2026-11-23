// Critical medicines: the table is plain HTML; this adds a filter by text, match type and status.
const rows = [...document.querySelectorAll('#eu-body tr[data-type]')];
const input = $('eu-q'), select = $('eu-type'), status = $('eu-status'), shown = $('eu-shown');
function filter() {
  const q = fold(input.value.trim()), type = select.value, when = status.value;
  let n = 0;
  rows.forEach(tr => { const show = (!type || tr.dataset.type === type) && (!when || tr.dataset.status === when) && (!q || fold(tr.dataset.text).includes(q)); tr.hidden = !show; if (show) n++; });
  shown.textContent = `Showing ${n} of ${rows.length}.`;
}
// These pages are in English only, whatever language the visitor chose for the rest of the site.
start(() => { document.documentElement.lang = 'en'; });
if (input) { [input, select, status].forEach(el => el.addEventListener(el === input ? 'input' : 'change', filter)); filter(); }
