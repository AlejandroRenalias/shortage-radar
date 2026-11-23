import csv
import io
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import archive
from build import HEADER


def content(count):
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer, delimiter=';')
    writer.writerow(HEADER)
    for n in range(count):
        writer.writerow([f'{n:06}', 'K', '2026-11-01', '2026-12-01', '2026-10-01', '2026-11-01', 'Company'])
    return buffer.getvalue().encode()


@pytest.fixture
def repository(tmp_path, monkeypatch):
    (tmp_path / 'data/snapshots').mkdir(parents=True)
    (tmp_path / 'data/source').mkdir(parents=True)
    (tmp_path / 'data/snapshots/2026-11-01.txt').write_bytes(content(751))
    metadata = tmp_path / 'data/source/metadata.json'
    metadata.write_text('{"original": true}\n', encoding='utf-8')
    monkeypatch.setattr(archive, 'ROOT', tmp_path)
    return tmp_path, metadata


def test_identical_download_with_the_same_header_leaves_all_tracked_files_untouched(repository, monkeypatch):
    root, metadata = repository
    metadata.write_text('{"shortages_last_modified": "same header", "snapshot_date": "2026-11-01"}' + chr(10), encoding='utf-8')
    original = metadata.read_bytes()
    monkeypatch.setattr(archive, 'download', lambda _: (content(751), 'same header'))
    archive.main('2026-11-02')
    assert metadata.read_bytes() == original
    assert [p.name for p in (root / 'data/snapshots').iterdir()] == ['2026-11-01.txt']


def test_identical_content_with_a_new_last_modified_updates_only_the_file_time(repository, monkeypatch):
    """Fimea can change the file's modification time without changing its content; the site shows that time, so it is recorded."""
    root, metadata = repository
    metadata.write_text('{"shortages_last_modified": "old header", "snapshot_date": "2026-11-01"}' + chr(10), encoding='utf-8')
    monkeypatch.setattr(archive, 'download', lambda _: (content(751), 'new header'))
    archive.main('2026-11-02')
    assert json.loads(metadata.read_text()) == {'shortages_last_modified': 'new header', 'snapshot_date': '2026-11-01'}
    assert [p.name for p in (root / 'data/snapshots').iterdir()] == ['2026-11-01.txt']


def test_missing_header_keeps_the_stored_time_only_for_the_same_bytes(repository, monkeypatch):
    root, metadata = repository
    metadata.write_text('{"shortages_last_modified": "stored", "snapshot_date": "2026-11-01"}' + chr(10), encoding='utf-8')
    monkeypatch.setattr(archive, 'download', lambda _: (content(751), None))
    archive.main('2026-11-02')
    assert json.loads(metadata.read_text()) == {'shortages_last_modified': 'stored', 'snapshot_date': '2026-11-01'}


def test_new_bytes_without_a_header_do_not_get_the_old_files_time(repository, monkeypatch):
    """Content A with Last-Modified 19 Nov, then content B on 23 Nov with no header: B's time is unknown, not A's."""
    root, metadata = repository
    metadata.write_text('{"shortages_last_modified": "Thu, 19 Nov 2026 10:00:00 GMT", "snapshot_date": "2026-11-01"}' + chr(10), encoding='utf-8')
    monkeypatch.setattr(archive, 'download', lambda _: (content(700), None))
    archive.main('2026-11-23')
    assert json.loads(metadata.read_text()) == {'shortages_last_modified': None, 'snapshot_date': '2026-11-23'}
    # The same bytes again, still without a header, stay unknown instead of becoming a time.
    archive.main('2026-11-24')
    assert json.loads(metadata.read_text())['shortages_last_modified'] is None


def test_versions_saved_in_the_same_minute_all_survive(repository, monkeypatch):
    """Three accepted versions at 10:30:01, :11 and :21 UTC: A and B are both kept; only the newest is the day's snapshot."""
    from datetime import datetime, timezone
    root, _ = repository
    versions = {1: content(700), 11: content(710), 21: content(720)}
    for second, data in versions.items():
        monkeypatch.setattr(archive, 'download', lambda _, data=data: (data, f'at {second}'))
        archive.main('2026-11-02', now=datetime(2026, 11, 2, 10, 30, second, tzinfo=timezone.utc))
    kept = sorted(p.read_bytes() for p in (root / 'data/snapshots/superseded').iterdir())
    assert kept == sorted([versions[1], versions[11]])
    assert (root / 'data/snapshots/2026-11-02.txt').read_bytes() == versions[21]
    # A replacement in the very same second keeps distinct bytes apart too.
    monkeypatch.setattr(archive, 'download', lambda _: (content(730), None))
    archive.main('2026-11-02', now=datetime(2026, 11, 2, 10, 30, 21, tzinfo=timezone.utc))
    assert versions[21] in [p.read_bytes() for p in (root / 'data/snapshots/superseded').iterdir()]
    assert len(list((root / 'data/snapshots/superseded').iterdir())) == 3


def test_same_day_refetch_with_changed_content_does_not_fail_and_keeps_both_versions(repository, monkeypatch, capsys):
    """The job runs four times a day. A second run on the same day that finds a changed file used to raise, which stopped
    every later step of the workflow. Now the day's snapshot is the newer content and the earlier one is kept with its time."""
    from datetime import datetime, timezone
    root, metadata = repository
    monkeypatch.setattr(archive, 'download', lambda _: (content(700), 'first'))
    archive.main('2026-11-02', now=datetime(2026, 11, 2, 4, 35, tzinfo=timezone.utc))
    monkeypatch.setattr(archive, 'download', lambda _: (content(720), 'second'))
    archive.main('2026-11-02', now=datetime(2026, 11, 2, 10, 5, tzinfo=timezone.utc))
    assert (root / 'data/snapshots/2026-11-02.txt').read_bytes() == content(720)
    superseded = list((root / 'data/snapshots/superseded').iterdir())
    assert len(superseded) == 1 and superseded[0].name.startswith('2026-11-02T100500Z-') and superseded[0].read_bytes() == content(700)
    assert json.loads(metadata.read_text()) == {'shortages_last_modified': 'second', 'snapshot_date': '2026-11-02'}
    assert 'Same-day refetch' in capsys.readouterr().out
    # A third run with the same content changes nothing.
    archive.main('2026-11-02', now=datetime(2026, 11, 2, 15, 35, tzinfo=timezone.utc))
    assert [p.name for p in (root / 'data/snapshots/superseded').iterdir()] == [superseded[0].name]
    # Snapshots read by the site are only the day files.
    assert [p.name for p in sorted((root / 'data/snapshots').glob('????-??-??.txt'))] == ['2026-11-01.txt', '2026-11-02.txt']


def test_later_steps_still_run_after_a_same_day_refetch(repository, monkeypatch, tmp_path):
    """The ledger step that follows the archive step writes the day's rows once, from the latest snapshot."""
    import build
    import ledger
    root, _ = repository
    monkeypatch.setattr(archive, 'download', lambda _: (content(700), 'first'))
    archive.main('2026-11-02')
    monkeypatch.setattr(archive, 'download', lambda _: (content(720), 'second'))
    archive.main('2026-11-02')
    monkeypatch.setattr(ledger, 'ROOT', root)
    monkeypatch.setattr(build, 'ROOT', root)
    (root / 'data/source/register.xml').write_text('<Perusrekisteri><Ajopvm>2026-11-02</Ajopvm></Perusrekisteri>', encoding='utf-8')
    assert ledger.record('2026-11-02', tmp_path / 'ledger', root / 'data/source/register.xml') == 720


def test_partial_file_is_rejected_without_writes(repository, monkeypatch):
    root, metadata = repository
    original = metadata.read_bytes()
    monkeypatch.setattr(archive, 'download', lambda _: (content(150), 'header'))
    with pytest.raises(ValueError, match='Unexpected drop'):
        archive.main('2026-11-02')
    assert metadata.read_bytes() == original
    assert [p.name for p in (root / 'data/snapshots').iterdir()] == ['2026-11-01.txt']


def test_changed_download_records_snapshot_and_source_time(repository, monkeypatch):
    root, metadata = repository
    monkeypatch.setattr(archive, 'download', lambda _: (content(700), 'source timestamp'))
    archive.main('2026-11-02')
    assert (root / 'data/snapshots/2026-11-02.txt').read_bytes() == content(700)
    assert json.loads(metadata.read_text()) == {'shortages_last_modified': 'source timestamp', 'snapshot_date': '2026-11-02'}


@pytest.mark.parametrize('count', [413, 638])
def test_large_drop_rejected(repository, monkeypatch, count):
    monkeypatch.setattr(archive, 'download', lambda _: (content(count), None))
    with pytest.raises(ValueError, match='Unexpected drop'):
        archive.main('2026-11-02')


def test_explicit_override_allows_large_drop(repository, monkeypatch):
    root, _ = repository
    monkeypatch.setattr(archive, 'download', lambda _: (content(413), None))
    archive.main('2026-11-02', allow_large_drop=True)
    assert (root / 'data/snapshots/2026-11-02.txt').exists()


@pytest.mark.parametrize('bad', [content(751)[:-1], content(751).replace(b'Company', b'', 1), content(751) + content(1).split(b'\n', 1)[1]])
def test_invalid_snapshot_does_not_commit(repository, monkeypatch, bad):
    root, metadata = repository
    before = metadata.read_bytes()
    monkeypatch.setattr(archive, 'download', lambda _: (bad, None))
    with pytest.raises(ValueError):
        archive.main('2026-11-02')
    assert metadata.read_bytes() == before
    assert len(list((root / 'data/snapshots').iterdir())) == 1


def test_download_checks_length_and_digest(monkeypatch):
    import base64
    import hashlib
    class Response:
        def __init__(self, headers): self.headers = headers
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): return b'abc'
    monkeypatch.setattr(archive.time, 'sleep', lambda _: None)
    for headers, error in [({'Content-Length': '4'}, 'Content-Length'), ({'Content-MD5': 'bad'}, 'Content-MD5')]:
        monkeypatch.setattr(archive.urllib.request, 'urlopen', lambda *a, **k: Response(headers))
        with pytest.raises(ValueError, match=error): archive.download('https://example.com')
    digest = base64.b64encode(hashlib.md5(b'abc').digest()).decode()
    monkeypatch.setattr(archive.urllib.request, 'urlopen', lambda *a, **k: Response({'Content-Length': '3', 'Content-MD5': digest}))
    assert archive.download('https://example.com')[0] == b'abc'


def test_rejected_snapshot_is_saved_for_diagnosis(repository, monkeypatch, tmp_path):
    target = tmp_path / 'rejected.txt'
    monkeypatch.setenv('REJECTED_DOWNLOAD', str(target))
    bad = content(413)
    monkeypatch.setattr(archive, 'download', lambda _: (bad, None))
    with pytest.raises(ValueError, match='Unexpected drop'):
        archive.main('2026-11-02')
    assert target.read_bytes() == bad


def test_rejected_truncated_response_is_saved(monkeypatch, tmp_path):
    import http.client
    target = tmp_path / 'rejected.txt'
    monkeypatch.setenv('REJECTED_DOWNLOAD', str(target))
    class Response:
        headers = {}
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def read(self): raise http.client.IncompleteRead(b'partial', 10)
    monkeypatch.setattr(archive.urllib.request, 'urlopen', lambda *a, **k: Response())
    monkeypatch.setattr(archive.time, 'sleep', lambda _: None)
    with pytest.raises(http.client.IncompleteRead): archive.download('https://example.com')
    assert target.read_bytes() == b'partial'
