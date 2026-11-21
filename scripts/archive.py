"""Download, validate and capture changed Fimea data."""
import argparse
import base64
import hashlib
import http.client
import json
import os
import time
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from build import ROOT, read_snapshot

URL = 'https://data.pilvi.fimea.fi/avoin-data/Shortages.txt'


def save_rejected(content):
    path = os.environ.get('REJECTED_DOWNLOAD')
    if path:
        Path(path).write_bytes(content)


def download(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'shortage-radar/1.0'}), timeout=90) as response:
                try:
                    content = response.read()
                except http.client.IncompleteRead as error:
                    save_rejected(error.partial)
                    raise
                length = response.headers.get('Content-Length')
                if length is not None and len(content) != int(length):
                    save_rejected(content)
                    raise ValueError('Content-Length mismatch')
                digest = response.headers.get('Content-MD5')
                if digest and base64.b64encode(hashlib.md5(content).digest()).decode('ascii') != digest.strip():
                    save_rejected(content)
                    raise ValueError('Content-MD5 mismatch')
                return content, response.headers.get('Last-Modified')
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2 ** attempt)


def main(day=None, allow_large_drop=False):
    content, modified = download(URL)
    day = day or datetime.now(ZoneInfo('Europe/Helsinki')).date().isoformat()
    folder = ROOT / 'data/snapshots'
    folder.mkdir(parents=True, exist_ok=True)
    temporary = folder / '.candidate'
    temporary.write_bytes(content)
    try:
        rows = read_snapshot(temporary)
        if len(rows) < 100:
            raise ValueError(f'Unexpectedly small shortage file: {len(rows)} rows')
        previous = sorted(folder.glob('????-??-??.txt'))
        if previous:
            previous_count = len(read_snapshot(previous[-1]))
            if not allow_large_drop and len(rows) * 100 < previous_count * 85:
                raise ValueError(f'Unexpected drop from {previous_count} to {len(rows)} rows; refusing snapshot')
        target = folder / f'{day}.txt'
        if target.exists() and target.read_bytes() != content:
            raise ValueError(f'{target} already exists with different content')
        if not previous or previous[-1].read_bytes() != content:
            temporary.replace(target)
            metadata = {'shortages_last_modified': modified, 'snapshot_date': day}
            (ROOT / 'data/source/metadata.json').write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    except Exception:
        save_rejected(content)
        raise
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--allow-large-drop', action='store_true')
    main(allow_large_drop=parser.parse_args().allow_large_drop)
