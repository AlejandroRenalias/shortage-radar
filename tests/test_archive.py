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
