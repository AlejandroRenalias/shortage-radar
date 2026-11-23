"""How old Fimea's two source files are, and the one rule for calling them stale.

The shortage file is stale when its HTTP Last-Modified date is more than STALE_DAYS days before today (Helsinki time). The
basic register is stale when its own run date (`Ajopvm`) is more than STALE_DAYS days before today. Fimea has changed the
shortage file on weekends, so two days is the limit, not one. The same limit is `STALE_DAYS` in site/lib.js, which shows the banner;
this script gives the maintainer the same answer: it exits 1 and prints one line for each stale file, and the workflow opens the
pipeline issue (scripts/pipeline_alert.py) from that.
"""
import json
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


def main():
    reasons = stale_reasons(read_metadata())
    names = {'shortages': 'Fimea shortage file (Last-Modified)', 'register': 'Fimea basic register (Ajopvm)'}
    for r in reasons:
        print(f"::warning::{names[r['file']]} is {r['days']} days old (dated {r['date']}); the limit is {STALE_DAYS} days.")
    if not reasons:
        print(f'Both source files are at most {STALE_DAYS} days old.')
    return 1 if reasons else 0


if __name__ == '__main__':
    raise SystemExit(main())
