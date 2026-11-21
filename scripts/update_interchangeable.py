"""Download and validate Fimea's current and upcoming substitution lists."""
import csv
import hashlib
import io
import json
import os
import re
import tempfile
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
PAGE = 'https://fimea.fi/laakehaut_ja_luettelot/laakevaihto/tietokantaan_ladattava_tiedosto'
PERIOD = re.compile(r'(\d{1,2})\.\s*(\d{1,2})\.\s*-\s*(\d{1,2})\.\s*(\d{1,2})\.(\d{4})')
REQUIRED = {'SUBSTITUUTIORYHMA', 'VNRNRO', 'PAKKAUSKOKO', 'LAAKENIMI'}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.current = None
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.current = [dict(attrs).get('href', ''), '']

    def handle_data(self, data):
        if self.current is not None:
            self.current[1] += data

    def handle_endtag(self, tag):
        if tag == 'a' and self.current is not None:
            self.links.append(self.current)
            self.current = None


def parse_links(page):
    parser = Links()
    parser.feed(page)
    result = []
    for href, title in parser.links:
        if 'GS-ladattava.txt' not in href:
            continue
        if not title.strip():
            continue
        match = PERIOD.search(title)
        if not match:
            raise ValueError(f'Cannot parse validity period: {title!r}')
        d1, m1, d2, m2, year = map(int, match.groups())
        start = date(year - (m1 > m2), m1, d1)
        end = date(year, m2, d2)
        if start > end:
            raise ValueError('Invalid validity period')
        url = urljoin(PAGE, href)
        if urlparse(url).scheme != 'https' or urlparse(url).hostname != 'fimea.fi':
            raise ValueError('Unexpected download host')
        result.append((start, end, ' '.join(title.split()), url))
    if len({(x[0], x[1]) for x in result}) != len(result) or not result:
        raise ValueError('Missing or duplicate list periods')
    return sorted(result)


def parse_rows(content):
    reader = csv.DictReader(io.StringIO(content.decode('cp1252'), newline=''), delimiter=';', strict=True)
    if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames) or len(set(reader.fieldnames)) != len(reader.fieldnames):
        raise ValueError('Unexpected list columns')
    count = 0
    for row in reader:
        if None in row or any(value is None for value in row.values()) or not re.fullmatch(r'\d{6}', row['VNRNRO']) or not row['SUBSTITUUTIORYHMA']:
            raise ValueError(f'Malformed list row {count + 2}')
        count += 1
    if not count:
        raise ValueError('Empty list')
    return count


def download(url):
    with urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0 shortage-radar/1.0'}), timeout=90) as response:
        return response.read(), response.headers.get('Last-Modified')


def update(folder, today, fetch=download):
    page, _ = fetch(PAGE)
    links = parse_links(page.decode('utf-8'))
    current = [item for item in links if item[0] <= today <= item[1]]
    future = [item for item in links if item[0] > today]
    if len(current) != 1:
        raise ValueError('Expected exactly one list valid today')
    selected = [('interchangeable', current[0])]
    if future:
        next_item = future[0]
        if (next_item[0] - current[0][1]).days != 1:
            raise ValueError('Gap or overlap before upcoming list')
        selected.append(('interchangeable-upcoming', next_item))
    previous = parse_rows((folder / 'interchangeable.txt').read_bytes())
    changes = {}
    for name, (start, end, title, url) in selected:
        content, modified = fetch(url)
        count = parse_rows(content)
        if count * 2 < previous:
            raise ValueError(f'Unexpected drop from {previous} to {count} rows')
        if not modified:
            raise ValueError('Missing Last-Modified header')
        timestamp = parsedate_to_datetime(modified)
        if timestamp.tzinfo is None:
            raise ValueError('Last-Modified has no timezone')
        metadata = {'valid_from': start.isoformat(), 'valid_until': end.isoformat(),
                    'last_modified_utc': timestamp.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                    'dataset': title, 'sha256': hashlib.sha256(content).hexdigest()}
        changes[folder / f'{name}.txt'] = content
        changes[folder / f'{name}-metadata.json'] = (json.dumps(metadata, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    pending = {path: content for path, content in changes.items() if not path.exists() or path.read_bytes() != content}
    staged = {}
    try:
        for path, content in pending.items():
            with tempfile.NamedTemporaryFile(dir=folder, prefix='.interchangeable-', delete=False) as file:
                staged[path] = Path(file.name)
                file.write(content)
                file.flush()
                os.fsync(file.fileno())
        for path, temporary in staged.items():
            temporary.replace(path)
            print(f'Updated {path.name}')
    finally:
        for temporary in staged.values():
            temporary.unlink(missing_ok=True)
    changed = bool(pending)
    if len(selected) == 1:
        for suffix in ('.txt', '-metadata.json'):
            path = folder / f'interchangeable-upcoming{suffix}'
            if path.exists():
                path.unlink()
                changed = True
                print(f'Removed {path.name}')
    print('Validation complete' if changed else 'No changes to interchangeable products')


if __name__ == '__main__':
    update(ROOT / 'data/source', datetime.now(ZoneInfo('Europe/Helsinki')).date())
