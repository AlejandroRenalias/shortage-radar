"""Fetch the EU Union list of critical medicines (EMA) and the Fimea dosage form names, and keep pinned copies in data/critical.

The list is pinned: a new EMA version is not taken in silently. Run `python scripts/fetch_critical.py list` and read the
version it prints; pass `--version` to accept another one. The workbook is cached in data/source (ignored by git) and EMA
is asked politely: one request, a User-Agent and a pause before it. EMA answers 429 to fast bursts, so a 429 is retried slowly.
"""
import argparse
import csv
import io
import json
import re
import time
import urllib.error
import urllib.request
import zipfile
import xml.etree.ElementTree as ET
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = ROOT / 'data/critical'
EMA_URL = 'https://www.ema.europa.eu/en/documents/other/union-list-critical-medicines-en.xlsx'
FORMS_URL = 'https://data.pilvi.fimea.fi/avoin-data/pharmaceutical_form.csv'
USER_AGENT = 'shortage-radar/1.0 (+https://github.com/AlejandroRenalias/shortage-radar)'
PINNED_VERSION = '2.1'
HEADER = ['ATC level 5', 'ATC description', 'Route of administration', 'Date of inclusion']
MIN_ROWS = 250
NS = '{http://schemas.openxmlformats.org/spreadsheetml/2006/main}'
ATC5 = re.compile(r'^[A-Z]\d\d[A-Z]{2}\d\d$')


def download(url, cache, pause=5, attempts=4):
    """Download with a User-Agent, a pause first, and a slow retry on 429 or 5xx. The result is cached on disk."""
    if cache.exists():
        return cache.read_bytes()
    time.sleep(pause)
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': USER_AGENT}), timeout=90) as response:
                content = response.read()
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(content)
            return content
        except urllib.error.HTTPError as error:
            if error.code not in (429, 500, 502, 503, 504) or attempt == attempts - 1:
                raise
            time.sleep(30 * (attempt + 1))


def excel_date(serial):
    return (date(1899, 12, 30) + timedelta(days=int(float(serial)))).isoformat()


def read_workbook(content):
    """{'meta': {...}, 'rows': [...]} from the EMA workbook, with the sheet row number of every list row.

    Only the standard library is used. The sheet has a title block, the header in one row and group headings between
    the data rows; a data row is a row whose first cell is an ATC level 5 code.
    """
    z = zipfile.ZipFile(io.BytesIO(content))
    strings = [''.join(t.text or '' for t in si.iter(NS + 't')) for si in ET.fromstring(z.read('xl/sharedStrings.xml')).findall(NS + 'si')]
    cells = {}
    for row in ET.fromstring(z.read('xl/worksheets/sheet1.xml')).iter(NS + 'row'):
        for c in row.findall(NS + 'c'):
            v = c.find(NS + 'v')
            if v is not None:
                cells[(int(row.get('r')), re.match(r'[A-Z]+', c.get('r')).group())] = strings[int(v.text)] if c.get('t') == 's' else v.text
    header_row = next((r for (r, col), v in cells.items() if col == 'A' and v.strip() == HEADER[0]), None)
    if header_row is None or [cells.get((header_row, c), '').split('\n')[0].strip() for c in 'ABCD'] != HEADER:
        raise ValueError('Unexpected header in the EU list workbook')
    column_a = [(r, v.strip()) for (r, col), v in sorted(cells.items()) if col == 'A']
    title = next((v for r, v in column_a if v.startswith('Union list of critical medicines')), '')
    version = re.search(r'version\s+(\d+(?:\.\d+)*)', title)
    reference = next((v for r, v in column_a if re.fullmatch(r'EMA/\d+/\d{4}', v)), '')
    published = next((excel_date(v) for r, v in column_a if r < header_row and re.fullmatch(r'\d{5}', v)), '')
    rows = []
    for r, v in column_a:
        if r > header_row and ATC5.match(v):
            rows.append({'atc': v, 'description': cells.get((r, 'B'), '').strip(), 'route': cells.get((r, 'C'), '').strip(),
                         'included': excel_date(cells[(r, 'D')]) if (r, 'D') in cells else '', 'row': r})
    if len(rows) < MIN_ROWS or len({x['atc'] for x in rows}) != len(rows):
        raise ValueError(f'Unexpected EU list: {len(rows)} rows')
    return {'meta': {'title': title, 'version': version.group(1) if version else '', 'reference': reference, 'published': published}, 'rows': rows}


def save_list(parsed, retrieved):
    FOLDER.mkdir(parents=True, exist_ok=True)
    with (FOLDER / 'eu-list.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f, lineterminator='\n')
        writer.writerow(['atc', 'description', 'route', 'date_of_inclusion', 'source_row'])
        writer.writerows([x['atc'], x['description'], x['route'], x['included'], x['row']] for x in parsed['rows'])
    meta = dict(parsed['meta'], source_url=EMA_URL, retrieved=retrieved, rows=len(parsed['rows']),
                note='source_row is the row number in the first sheet of the EMA workbook.')
    (FOLDER / 'eu-list.json').write_text(json.dumps(meta, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    return meta


def save_forms(content):
    """Dosage form names from Fimea's pharmaceutical_form.csv, reduced to id and the Finnish and English names."""
    reader = csv.DictReader(io.StringIO(content.decode('utf-8-sig')), delimiter=';')
    rows = sorted(({'id': r['id'], 'name_fi': r['name_fi'], 'name_en': r['name_en']} for r in reader), key=lambda r: int(r['id']))
    if len(rows) < 100:
        raise ValueError('Unexpected form list')
    FOLDER.mkdir(parents=True, exist_ok=True)
    with (FOLDER / 'forms.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, ['id', 'name_fi', 'name_en'], lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('what', choices=['list', 'forms'])
    parser.add_argument('--version', default=PINNED_VERSION, help='the list version to accept')
    args = parser.parse_args()
    cache = ROOT / 'data/source'
    if args.what == 'list':
        parsed = read_workbook(download(EMA_URL, cache / 'union-list-critical-medicines.xlsx'))
        if parsed['meta']['version'] != args.version:
            raise SystemExit(f"EMA now publishes version {parsed['meta']['version']}, not {args.version}. Check it, then run with --version.")
        print(save_list(parsed, date.today().isoformat()))
    else:
        print(save_forms(download(FORMS_URL, cache / 'pharmaceutical_form.csv')), 'forms')


if __name__ == '__main__':
    main()
