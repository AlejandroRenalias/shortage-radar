"""Download, validate and capture changed Fimea data."""
import hashlib
import json
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from build import ROOT, read_snapshot

URL = 'https://data.pilvi.fimea.fi/avoin-data/Shortages.txt'
REGISTER = 'https://data.pilvi.fimea.fi/avoin-data/Perusrekisteri.xml'


def download(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'shortage-radar/1.0'}), timeout=90) as response:
                return response.read(), response.headers.get('Last-Modified')
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def main():
    content, modified = download(URL)
    day = datetime.now(ZoneInfo('Europe/Helsinki')).date().isoformat()
    folder = ROOT / 'data/snapshots'
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / '.candidate'
    temporary.write_bytes(content)
    try:
        rows = read_snapshot(temporary)
        if len(rows) < 100:
            raise ValueError(f'Unexpectedly small shortage file: {len(rows)} rows')
        previous = sorted(folder.glob('????-??-??.txt'))
        target = folder / f'{day}.txt'
        if target.exists() and target.read_bytes() != content:
            raise ValueError(f'{target} already exists with different content')
        if not previous or previous[-1].read_bytes() != content:
            temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    data, register_modified = download(REGISTER)
    dest = ROOT / 'data/source/register.xml'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    metadata = {'shortages_last_modified': modified, 'register_last_modified': register_modified, 'retrieved_utc': datetime.now(timezone.utc).isoformat(), 'shortages_sha256': hashlib.sha256(content).hexdigest()}
    (ROOT / 'data/source/metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
