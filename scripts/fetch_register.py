"""Download and validate the basic register before replacing the local copy.

Fimea names the register by year (`Perusrekisteri2026.xml`). The name is made from the current year, not fixed, and the run
exits with a clear message instead of keeping an old register when
- the file of the next year exists: Fimea may have moved to it, so a person must check it and decide (`NEXT_YEAR_EXISTS`);
- the file of the current year is missing and the last year's file is older than STALE_DAYS (`MISSING`);
- the file has no run date (`Ajopvm`), or is too small, or is not a register.
The register's run date and file name go to data/source/register-metadata.json for the site's stale banner and for source_age.py.
"""
import io
import json
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

from archive import ROOT, download
from source_age import STALE_DAYS, iso_day

MIN_BYTES = 1_000_000
BASE = 'https://data.pilvi.fimea.fi/avoin-data/'


class RegisterSourceError(ValueError):
    pass


def name_for(year):
    return f'Perusrekisteri{year}.xml'


def exists(url):
    """True or False when Fimea answers 200 or 404; None when the answer is unclear (a network error or another status)."""
    try:
        with urllib.request.urlopen(urllib.request.Request(url, method='HEAD', headers={'User-Agent': 'shortage-radar/1.0'}), timeout=30):
            return True
    except urllib.error.HTTPError as error:
        return False if error.code == 404 else None
    except OSError:
        return None


def run_date(data):
    """Check that `data` is a register and return its run date (`Ajopvm`, ISO)."""
    parser = ET.iterparse(io.BytesIO(data), events=('start', 'end'))
    _, root = next(parser)
    if root.tag != 'Perusrekisteri':
        raise ValueError('Unexpected register root')
    found = ''
    for event, element in parser:
        if event == 'end':
            if element.tag == 'Ajopvm' and not found:
                found = (element.text or '').strip()
            element.clear()
            root.clear()
    if not iso_day(found):
        raise RegisterSourceError(f'The register has no readable run date (Ajopvm: {found!r})')
    return found


def main(today=None):
    today = today or datetime.now(ZoneInfo('Europe/Helsinki')).date()
    year = today.year
    following = name_for(year + 1)
    if exists(BASE + following):
        raise RegisterSourceError(f'NEXT_YEAR_EXISTS: Fimea has published {following}. Check that file, then change the register source in scripts/fetch_register.py; this run keeps the old register.')
    data = modified = name = None
    for candidate in (name_for(year), name_for(year - 1)):
        try:
            data, modified = download(BASE + candidate)
            name = candidate
            break
        except urllib.error.HTTPError as error:
            if error.code != 404:
                raise
    if data is None:
        raise RegisterSourceError(f'MISSING: Fimea has no {name_for(year)} or {name_for(year - 1)} (HTTP 404).')
    if len(data) < MIN_BYTES:
        raise ValueError('Register is unexpectedly small')
    ran = run_date(data)
    # The last year's file is accepted only while Fimea still keeps it up to date.
    if name != name_for(year) and (today - iso_day(ran)).days > STALE_DAYS:
        raise RegisterSourceError(f'MISSING: Fimea has no {name_for(year)}, and {name} is dated {ran}, more than {STALE_DAYS} days ago.')
    target = ROOT / 'data/source/register.xml'
    temporary = target.with_suffix('.xml.tmp')
    try:
        temporary.write_bytes(data)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    (ROOT / 'data/source/register-metadata.json').write_text(json.dumps({'register_last_modified': modified, 'register_date': ran, 'register_file': name}), encoding='utf-8')
    print(f'{name}: run date {ran}, file modified {modified}')


if __name__ == '__main__':
    main()
