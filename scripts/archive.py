"""Download, validate and capture changed Fimea data."""
import argparse
import base64
import hashlib
import http.client
import json
import os
import time
import urllib.error
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
        except Exception as error:
            # A missing file (404) and other client errors do not change on a second try.
            if attempt == 2 or (isinstance(error, urllib.error.HTTPError) and error.code < 500):
                raise
            time.sleep(2 ** attempt)


def main(day=None, allow_large_drop=False, now=None):
    """Download the shortage file and save it as the snapshot of `day` when the content changed.

    The job runs four times a day. A later run of the same day that finds changed content does not fail: the day's snapshot
    becomes the newer content (the list the site shows must be the latest), and the content it replaces is kept in
    data/snapshots/superseded/<day>T<HHMM>Z.txt, named by the UTC time of the run that found the change. The daily ledger
    keeps the rows of the first run, and the SHA-256 in them matches the superseded file.
    The source's Last-Modified goes to data/source/metadata.json whenever it differs from the stored one, also when the content is the same."""
    content, modified = download(URL)
    now = now or datetime.now(ZoneInfo('UTC'))
    day = day or now.astimezone(ZoneInfo('Europe/Helsinki')).date().isoformat()
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
        changed = not previous or previous[-1].read_bytes() != content
        if changed and target.exists():
            saved = folder / 'superseded' / f"{day}T{now.astimezone(ZoneInfo('UTC')):%H%M}Z.txt"
            saved.parent.mkdir(exist_ok=True)
            saved.write_bytes(target.read_bytes())
            print(f'Same-day refetch: the file changed since the earlier run of {day}; the earlier content is kept in {saved.relative_to(ROOT)}')
        if changed:
            temporary.replace(target)
        path = ROOT / 'data/source/metadata.json'
        stored = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
        if changed or (modified and stored.get('shortages_last_modified') != modified):
            metadata = {'shortages_last_modified': modified or stored.get('shortages_last_modified'), 'snapshot_date': day if changed else stored.get('snapshot_date', day)}
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(metadata, indent=2) + '\n', encoding='utf-8')
    except Exception:
        save_rejected(content)
        raise
    finally:
        temporary.unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--allow-large-drop', action='store_true')
    main(allow_large_drop=parser.parse_args().allow_large_drop)
