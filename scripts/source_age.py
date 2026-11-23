"""How old Fimea's two source files are, and the one rule for calling them stale.

The shortage file is stale when its HTTP Last-Modified date is more than STALE_DAYS days before today (Helsinki time). The
basic register is stale when its own run date (`Ajopvm`) is more than STALE_DAYS days before today. Fimea has changed the
shortage file on weekends, so two days is the limit, not one. The same limit is `STALE_DAYS` in site/lib.js, which shows the banner;
this script gives the maintainer the same answer: it exits 1 and prints one line for each stale file, and the workflow opens the
pipeline issue (scripts/pipeline_alert.py) from that.
"""
import json
import os
import xml.etree.ElementTree as ET
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]

STALE_DAYS = 2
HELSINKI = ZoneInfo('Europe/Helsinki')


def register_date(path):
    """The run date of a register file (`Ajopvm`), or '' when it has none."""
    for _, el in ET.iterparse(path, events=('end',)):
        if el.tag == 'Ajopvm':
            return (el.text or '').strip()
    return ''


def http_day(value):
    """The Helsinki calendar day of an HTTP date such as 'Sun, 22 Nov 2026 23:20:01 GMT'; None when it cannot be read."""
    try:
        return parsedate_to_datetime(value).astimezone(HELSINKI).date()
    except (TypeError, ValueError):
        return None


def iso_day(value):
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def stale_reasons(metadata, today=None):
    """[{'file', 'date', 'days'}] for each source file older than STALE_DAYS; `metadata` is data/source/metadata.json joined with
    register-metadata.json. A date that is missing or unreadable is unknown, not stale, so it gives no reason here."""
    today = today or datetime.now(HELSINKI).date()
    found = []
    for file, day in (('shortages', http_day(metadata.get('shortages_last_modified'))), ('register', iso_day(metadata.get('register_date')))):
        if day and (today - day).days > STALE_DAYS:
            found.append({'file': file, 'date': day.isoformat(), 'days': (today - day).days})
    return found


def read_metadata(folder=None):
    folder = folder or ROOT / 'data/source'
    out = {}
    for name in ('metadata.json', 'register-metadata.json'):
        path = folder / name
        if path.exists():
            out.update(json.loads(path.read_text(encoding='utf-8')))
    return out


def unknown_files(metadata):
    """The files whose date is missing or unreadable: their age is not known."""
    return [file for file, day in (('shortages', http_day(metadata.get('shortages_last_modified'))), ('register', iso_day(metadata.get('register_date')))) if not day]


def status(metadata, today=None):
    """'stale' when a known date is more than STALE_DAYS old (evidence of staleness, even if the other file is unknown);
    'fresh' only when both dates are known and recent; else 'unknown', which proves nothing either way."""
    if stale_reasons(metadata, today):
        return 'stale'
    return 'unknown' if unknown_files(metadata) else 'fresh'


def main():
    metadata = read_metadata()
    reasons = stale_reasons(metadata)
    unknown = unknown_files(metadata)
    names = {'shortages': 'Fimea shortage file (Last-Modified)', 'register': 'Fimea basic register (Ajopvm)'}
    for r in reasons:
        print(f"::warning::{names[r['file']]} is {r['days']} days old (dated {r['date']}); the limit is {STALE_DAYS} days.")
    for file in unknown:
        print(f"::warning::The age of the {names[file]} is unknown: no readable date.")
    result = 'stale' if reasons else 'unknown' if unknown else 'fresh'
    if result == 'fresh':
        print(f'Both source files are at most {STALE_DAYS} days old.')
    # The workflow opens the stale alert on 'stale', closes it only on 'fresh', and leaves it as it is on 'unknown'.
    if os.environ.get('GITHUB_OUTPUT'):
        with open(os.environ['GITHUB_OUTPUT'], 'a', encoding='utf-8') as f:
            f.write(f'status={result}\n')
    print(f'status={result}')
    return 1 if reasons else 0


if __name__ == '__main__':
    raise SystemExit(main())
