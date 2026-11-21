import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import fetch_register


def test_register_validation_preserves_existing_file(tmp_path, monkeypatch):
    (tmp_path / 'data/source').mkdir(parents=True)
    target = tmp_path / 'data/source/register.xml'
    target.write_bytes(b'previous')
    monkeypatch.setattr(fetch_register, 'ROOT', tmp_path)
    monkeypatch.setattr(fetch_register, 'MIN_BYTES', 10)
    for data in (b'<x/>', b'<wrong>123456</wrong>', b'<Perusrekisteri>broken'):
        monkeypatch.setattr(fetch_register, 'download', lambda _: (data, None))
        with pytest.raises(Exception): fetch_register.main()
        assert target.read_bytes() == b'previous'
    monkeypatch.setattr(fetch_register, 'download', lambda _: (b'<Perusrekisteri/>', 'date'))
    fetch_register.main()
    assert target.read_bytes() == b'<Perusrekisteri/>'
