"""Download the current basic register for a local or Pages build."""
import json
from archive import ROOT, download

data, modified = download('https://data.pilvi.fimea.fi/avoin-data/Perusrekisteri.xml')
(ROOT / 'data/source/register.xml').write_bytes(data)
(ROOT / 'data/source/register-metadata.json').write_text(json.dumps({'register_last_modified': modified}), encoding='utf-8')
