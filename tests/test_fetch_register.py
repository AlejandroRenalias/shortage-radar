import json
import sys
import urllib.error
from datetime import date
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_register

TODAY = date(2026, 11, 23)


def register(run_date='2026-11-23'):
    return f'<Perusrekisteri><Versiotiedot><Ajopvm>{run_date}</Ajopvm></Versiotiedot></Perusrekisteri>'.encode()


@pytest.fixture
def folder(tmp_path, monkeypatch):
    (tmp_path / 'data/source').mkdir(parents=True)
    monkeypatch.setattr(fetch_register, 'ROOT', tmp_path)
    monkeypatch.setattr(fetch_register, 'MIN_BYTES', 10)
    monkeypatch.setattr(fetch_register, 'exists', lambda url: False)
    (tmp_path / 'data/source/register.xml').write_bytes(b'previous')
    return tmp_path


def serve(monkeypatch, files):
    """`files` maps a file name to (bytes, Last-Modified); any other name is a 404."""
    def download(url):
        name = url.rsplit('/', 1)[1]
        if name not in files:
            raise urllib.error.HTTPError(url, 404, 'Not Found', {}, None)
        return files[name]
    monkeypatch.setattr(fetch_register, 'download', download)


def test_register_validation_preserves_existing_file(folder, monkeypatch):
    target = folder / 'data/source/register.xml'
    for data in (b'<x/>', b'<wrong>123456</wrong>', b'<Perusrekisteri>broken', b'<Perusrekisteri/>'):
        serve(monkeypatch, {'Perusrekisteri2026.xml': (data, None)})
        with pytest.raises(Exception): fetch_register.main(TODAY)
        assert target.read_bytes() == b'previous'
    serve(monkeypatch, {'Perusrekisteri2026.xml': (register(), 'date')})
    fetch_register.main(TODAY)
    assert target.read_bytes() == register()


def test_file_name_comes_from_the_year_and_the_run_date_and_name_are_recorded(folder, monkeypatch):
    asked = []
    monkeypatch.setattr(fetch_register, 'download', lambda url: asked.append(url) or (register(), 'Mon, 23 Nov 2026 00:31:00 GMT'))
    fetch_register.main(TODAY)
    assert asked == ['https://data.pilvi.fimea.fi/avoin-data/Perusrekisteri2026.xml']
    assert json.loads((folder / 'data/source/register-metadata.json').read_text()) == {
        'register_last_modified': 'Mon, 23 Nov 2026 00:31:00 GMT', 'register_date': '2026-11-23', 'register_file': 'Perusrekisteri2026.xml'}


def test_next_year_file_appearing_fails_clearly_and_keeps_the_old_register(folder, monkeypatch):
    """Fimea publishes Perusrekisteri2027.xml: the run stops before it downloads anything, so a person decides."""
    probed = []
    monkeypatch.setattr(fetch_register, 'exists', lambda url: probed.append(url) or url.endswith('Perusrekisteri2027.xml'))
    monkeypatch.setattr(fetch_register, 'download', lambda url: pytest.fail('nothing is downloaded'))
    with pytest.raises(fetch_register.RegisterSourceError, match='NEXT_YEAR_EXISTS.*Perusrekisteri2027.xml'):
        fetch_register.main(TODAY)
    assert probed == ['https://data.pilvi.fimea.fi/avoin-data/Perusrekisteri2027.xml']
    assert (folder / 'data/source/register.xml').read_bytes() == b'previous'


def test_an_unclear_answer_about_next_year_does_not_stop_the_run(folder, monkeypatch):
    monkeypatch.setattr(fetch_register, 'exists', lambda url: None)
    serve(monkeypatch, {'Perusrekisteri2026.xml': (register(), None)})
    fetch_register.main(TODAY)


def test_missing_register_fails_clearly(folder, monkeypatch):
    serve(monkeypatch, {})
    with pytest.raises(fetch_register.RegisterSourceError, match='MISSING.*Perusrekisteri2026.xml.*Perusrekisteri2025.xml'):
        fetch_register.main(TODAY)
    assert (folder / 'data/source/register.xml').read_bytes() == b'previous'


def test_other_http_errors_are_not_called_missing(folder, monkeypatch):
    def download(url): raise urllib.error.HTTPError(url, 403, 'Forbidden', {}, None)
    monkeypatch.setattr(fetch_register, 'download', download)
    with pytest.raises(urllib.error.HTTPError): fetch_register.main(TODAY)


def test_last_years_file_is_used_in_january_only_while_it_is_fresh(folder, monkeypatch):
    january = date(2027, 1, 2)
    serve(monkeypatch, {'Perusrekisteri2026.xml': (register('2027-01-01'), 'x')})
    fetch_register.main(january)
    assert json.loads((folder / 'data/source/register-metadata.json').read_text())['register_file'] == 'Perusrekisteri2026.xml'
    serve(monkeypatch, {'Perusrekisteri2026.xml': (register('2026-12-20'), 'x')})
    with pytest.raises(fetch_register.RegisterSourceError, match='MISSING.*2026-12-20'):
        fetch_register.main(january)


def test_old_register_is_downloaded_and_its_date_recorded_for_the_stale_banner(folder, monkeypatch):
    """An old run date is not an error here: the banner and source_age.py report it, and the site still shows the newest data there is."""
    serve(monkeypatch, {'Perusrekisteri2026.xml': (register('2026-11-18'), 'x')})
    fetch_register.main(TODAY)
    assert json.loads((folder / 'data/source/register-metadata.json').read_text())['register_date'] == '2026-11-18'


@pytest.mark.parametrize('xml', [b'<Perusrekisteri/>', b'<Perusrekisteri><Ajopvm></Ajopvm></Perusrekisteri>', b'<Perusrekisteri><Ajopvm>yesterday</Ajopvm></Perusrekisteri>'])
def test_register_without_a_readable_run_date_fails(folder, monkeypatch, xml):
    serve(monkeypatch, {'Perusrekisteri2026.xml': (xml, None)})
    with pytest.raises(fetch_register.RegisterSourceError, match='run date'):
        fetch_register.main(TODAY)


def test_exists_reads_the_http_status(monkeypatch):
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): pass
    for outcome, expected in [(Response(), True), (urllib.error.HTTPError('u', 404, 'x', {}, None), False), (urllib.error.HTTPError('u', 500, 'x', {}, None), None), (OSError('offline'), None)]:
        def urlopen(*a, outcome=outcome, **k):
            if isinstance(outcome, Exception): raise outcome
            return outcome
        monkeypatch.setattr(fetch_register.urllib.request, 'urlopen', urlopen)
        assert fetch_register.exists('https://example.com/x') is expected
