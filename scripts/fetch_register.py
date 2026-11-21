"""Download and validate the basic register before replacing the local copy."""
import io
import json
import xml.etree.ElementTree as ET
from archive import ROOT, download

MIN_BYTES = 1_000_000


def main():
    data, modified = download('https://data.pilvi.fimea.fi/avoin-data/Perusrekisteri.xml')
    if len(data) < MIN_BYTES:
        raise ValueError('Register is unexpectedly small')
    parser = ET.iterparse(io.BytesIO(data), events=('start', 'end'))
    _, root = next(parser)
    if root.tag != 'Perusrekisteri':
        raise ValueError('Unexpected register root')
    for event, element in parser:
        if event == 'end':
            element.clear()
            root.clear()
    target = ROOT / 'data/source/register.xml'
    temporary = target.with_suffix('.xml.tmp')
    try:
        temporary.write_bytes(data)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    (ROOT / 'data/source/register-metadata.json').write_text(json.dumps({'register_last_modified': modified}), encoding='utf-8')


if __name__ == '__main__':
    main()
