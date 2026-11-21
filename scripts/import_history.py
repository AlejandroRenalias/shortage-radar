"""Import earlier copies of Fimea's shortage file from the Internet Archive.

Each accepted capture is stored as data/snapshots/imported/<date>.txt, dated by
the capture time in Helsinki, with the header normalised to the current
Shortages.txt header. data/snapshots/imported/manifest.json records every
capture considered: archive timestamp, URLs, digest, row count and, for skipped
captures, the reason. The script is safe to re-run: stored captures are not
downloaded again and existing files are never overwritten.
"""
import base64
import hashlib
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zlib
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from build import HEADER, ROOT, read_snapshot

FOLDER = ROOT / 'data/snapshots/imported'
MANIFEST = FOLDER / 'manifest.json'
BASE = 'https://data.pilvi.fimea.fi/avoin-data/'
SOURCES = ['Saatavuushairiot.txt', 'Shortages.txt', 'Restnoteringar.txt']
# Finnish and English column names, in the order of HEADER.
HEADER_NAMES = {
    'fi': ['VNR', 'Voimassa', 'SaatavuushairioAlkupaiva', 'SaatavuushairioLoppupaiva', 'Ilmoituspaiva', 'Muokkauspaiva', 'Yritys'],
    'en': HEADER,
}
RSS_URL = 'https://fimea.fi/c/laakehaut_ja_luettelot/saatavuushairio-uusi/rss'
RSS_SUMMARY = FOLDER / 'rss-counts.json'
MIN_ROWS = 100
DELAY_SECONDS = 1.5
USER_AGENT = 'shortage-radar-history-import/1.0'


def fetch(url, binary=True):
    for attempt in range(4):
        try:
            request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
            with urllib.request.urlopen(request, timeout=120) as response:
                return response.read()
        except urllib.error.HTTPError as error:
            if error.code in (404, 403):
                raise
            if attempt == 3:
                raise
        except Exception:
            if attempt == 3:
                raise
        time.sleep(5 * 2 ** attempt)


def gunzip(content):
    if content[:2] == b'\x1f\x8b':
        return zlib.decompressobj(31).decompress(content)
    return content


def list_captures(name, url=None):
    """Return (timestamp, digest) of HTTP 200 captures of one URL."""
    query = urllib.parse.urlencode({'url': url or BASE.removeprefix('https://') + name, 'fl': 'timestamp,digest', 'filter': 'statuscode:200'})
    text = fetch('https://web.archive.org/cdx/search/cdx?' + query).decode('ascii')
    return [tuple(line.split()) for line in text.splitlines() if line.strip()]


def capture_date(timestamp):
    moment = datetime.strptime(timestamp, '%Y%m%d%H%M%S').replace(tzinfo=timezone.utc)
    return moment.astimezone(ZoneInfo('Europe/Helsinki')).date().isoformat()


def sha1_digest(content):
    return base64.b32encode(hashlib.sha1(content).digest()).decode('ascii')


def normalise(content):
    """Replace the header line with the current English header, keeping every other byte."""
    text = content.decode('utf-8-sig')
    first, separator, rest = text.partition('\n')
    ending = '\r\n' if first.endswith('\r') else '\n'
    columns = first.rstrip('\r').split(';')
    unquoted = [c.strip('"') for c in columns]
    for names in HEADER_NAMES.values():
        if unquoted == names:
            break
    else:
        raise ValueError('unexpected header')
    header = ';'.join(f'"{c}"' for c in HEADER) + ending
    return (header + rest).encode('utf-8')


def validate(content, previous_rows):
    """Apply the same checks as scripts/archive.py and return the row count."""
    candidate = FOLDER / '.candidate'
    candidate.write_bytes(content)
    try:
        count = len(read_snapshot(candidate))
    finally:
        candidate.unlink(missing_ok=True)
    if count < MIN_ROWS:
        raise ValueError(f'Unexpectedly small shortage file: {count} rows')
    if previous_rows is not None and count * 2 < previous_rows:
        raise ValueError(f'Unexpected drop from {previous_rows} to {count} rows')
    return count


def load_manifest():
    if MANIFEST.exists():
        return {(c['source'], c['archive_timestamp']): c for c in json.loads(MANIFEST.read_text(encoding='utf-8'))['captures']}
    return {}


def save_manifest(entries):
    captures = sorted(entries.values(), key=lambda c: (c['archive_timestamp'], c['source']))
    text = json.dumps({'provider': 'Internet Archive Wayback Machine', 'captures': captures}, indent=2, ensure_ascii=False) + '\n'
    MANIFEST.write_text(text, encoding='utf-8')


def summarise_rss(content):
    """Count items and date ranges in an RSS capture. Items carry no VNR."""
    items = ET.fromstring(content).findall('./channel/item')
    starts, ends = [], []
    for item in items:
        found = re.findall(r'\d{4}-\d\d-\d\d', item.findtext('{http://purl.org/rss/1.0/modules/content/}encoded') or '')
        if len(found) >= 2:
            starts.append(found[0])
            ends.append(found[1])
    guids = {item.findtext('guid') for item in items}
    return {'items': len(items), 'unique_guids': len(guids), 'earliest_start': min(starts, default=None), 'latest_end': max(ends, default=None)}


def import_rss():
    """Summarise archived copies of the RSS feed. The feed lists items without VNRs, so only counts are kept."""
    old = {c['archive_timestamp']: c for c in json.loads(RSS_SUMMARY.read_text(encoding='utf-8'))['captures']} if RSS_SUMMARY.exists() else {}
    result = {}
    for timestamp, digest in list_captures(None, RSS_URL.removeprefix('https://')):
        if timestamp in old and 'items' in old[timestamp]:
            result[timestamp] = old[timestamp]
            continue
        entry = {'archive_timestamp': timestamp, 'archive_url': f'https://web.archive.org/web/{timestamp}id_/{RSS_URL}', 'archive_digest': digest, 'date': capture_date(timestamp)}
        try:
            time.sleep(DELAY_SECONDS)
            raw = gunzip(fetch(entry['archive_url']))
            if sha1_digest(raw) != digest:
                raise ValueError('content does not match the archive digest')
            entry.update(summarise_rss(raw))
        except Exception as error:
            entry.update(status='skipped', reason=f'{type(error).__name__}: {error}')
            print(f'skip rss {timestamp}: {entry["reason"]}')
        result[timestamp] = entry
    captures = [result[t] for t in sorted(result)]
    RSS_SUMMARY.write_text(json.dumps({'provider': 'Internet Archive Wayback Machine', 'captures': captures}, indent=2) + '\n', encoding='utf-8')
    print(f'rss captures={sum("items" in c for c in captures)} skipped={sum("items" not in c for c in captures)}')


def main():
    FOLDER.mkdir(parents=True, exist_ok=True)
    entries = load_manifest()
    captures = []
    for name in SOURCES:
        captures += [(timestamp, name, digest) for timestamp, digest in list_captures(name)]
        time.sleep(DELAY_SECONDS)
    captures.sort()
    own_days = {p.stem for p in (ROOT / 'data/snapshots').glob('????-??-??.txt')}
    taken, previous_rows = {}, None
    for timestamp, name, digest in captures:
        key = (name, timestamp)
        day = capture_date(timestamp)
        url = f'{BASE}{name}'
        entry = {'source': name, 'source_url': url, 'archive_timestamp': timestamp, 'archive_url': f'https://web.archive.org/web/{timestamp}id_/{url}', 'archive_digest': digest, 'date': day}
        old = entries.get(key)
        target = FOLDER / f'{day}.txt'
        if old and old.get('status') == 'imported' and target.exists() and hashlib.sha256(target.read_bytes()).hexdigest() == old['sha256']:
            taken[day] = key
            previous_rows = old['rows']
            continue
        reason = None
        if day in own_days:
            reason = 'a snapshot saved by this project exists for this date'
        elif day in taken:
            reason = f'an earlier capture {taken[day][1]} already covers this date'
        else:
            try:
                time.sleep(DELAY_SECONDS)
                raw = gunzip(fetch(entry['archive_url']))
                if sha1_digest(raw) != digest:
                    raise ValueError('content does not match the archive digest')
                content = normalise(raw)
                rows = validate(content, previous_rows)
                if target.exists() and target.read_bytes() != content:
                    raise ValueError(f'{target} already exists with different content')
            except Exception as error:
                reason = f'{type(error).__name__}: {error}'
        if reason:
            entry.update(status='skipped', reason=reason)
            print(f'skip {name} {timestamp}: {reason}')
        else:
            target.write_bytes(content)
            entry.update(status='imported', rows=rows, sha256=hashlib.sha256(content).hexdigest(), file=f'data/snapshots/imported/{day}.txt')
            taken[day] = key
            previous_rows = rows
            print(f'import {name} {timestamp} -> {day}: {rows} rows')
        entries[key] = entry
        save_manifest(entries)
    save_manifest(entries)
    imported = sum(e['status'] == 'imported' for e in entries.values())
    print(f'imported={imported} skipped={len(entries) - imported}')
    import_rss()


if __name__ == '__main__':
    sys.exit(main())
