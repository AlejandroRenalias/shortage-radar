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


def test_identical_download_leaves_all_tracked_files_untouched(repository, monkeypatch):
    root, metadata = repository
    original = metadata.read_bytes()
    monkeypatch.setattr(archive, 'download', lambda _: (content(751), 'new header'))
    archive.main('2026-11-02')
    assert metadata.read_bytes() == original
    assert [p.name for p in (root / 'data/snapshots').iterdir()] == ['2026-11-01.txt']


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
