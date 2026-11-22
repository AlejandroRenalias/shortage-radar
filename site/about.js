// About: static text from the shared copy, plus the citation with the data date.
let data;
function render() { if (data) renderCitation(data); }
start(render);
wireCitation();
loadCurrent().then(d => { data = d; renderChrome(d); render(); }).catch(() => {});
