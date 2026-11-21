import json
from datetime import date
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build import interchangeable_source
from update_interchangeable import PAGE, parse_links, parse_rows, update


def csv_data(count):
    return ('SUBSTITUUTIORYHMA;VNRNRO;PAKKAUSKOKO;LAAKENIMI\n' + ''.join(f'0011;{i:06};10;Name\n' for i in range(count))).encode('cp1252')


PAGE_DATA = b'''<a href="/GS-ladattava.txt/current">Ladattava tiedosto jaksolle 1.10. -31.12.2026</a>
<a href="/GS-ladattava.txt/next">Ladattava tiedosto jaksolle 1.1. - 31.3.2027</a>'''
MODIFIED = 'Mon, 24 Aug 2026 11:55:28 GMT'


def test_parse_dates_and_rows():
    links = parse_links(PAGE_DATA.decode())
    assert [(x[0], x[1]) for x in links] == [(date(2026, 10, 1), date(2026, 12, 31)), (date(2027, 1, 1), date(2027, 3, 31))]
    assert parse_rows(csv_data(3)) == 3
    with pytest.raises(ValueError, match='columns'):
        parse_rows(b'error page')
    with pytest.raises(ValueError, match='Malformed'):
        parse_rows(csv_data(1) + b'broken;row\n')
    with pytest.raises(ValueError, match='validity'):
        parse_links('<a href="/GS-ladattava.txt/x">unknown</a>')


def test_update_future_no_change_and_promotion(tmp_path, capsys):
    (tmp_path / 'interchangeable.txt').write_bytes(csv_data(4))
    def fetch(url):
        return (PAGE_DATA, None) if url == PAGE else (csv_data(4 if url.endswith('current') else 5), MODIFIED)
    update(tmp_path, date(2026, 11, 1), fetch)
    assert json.loads((tmp_path / 'interchangeable-upcoming-metadata.json').read_text())['valid_from'] == '2027-01-01'
    assert interchangeable_source(tmp_path, '2026-12-31')[0].name == 'interchangeable.txt'
    assert interchangeable_source(tmp_path, '2027-01-01')[0].name == 'interchangeable-upcoming.txt'
    assert not interchangeable_source(tmp_path, '2027-04-01')[2]
    capsys.readouterr()
    update(tmp_path, date(2026, 11, 1), fetch)
    assert 'Updated' not in capsys.readouterr().out
    update(tmp_path, date(2027, 1, 1), fetch)
    assert parse_rows((tmp_path / 'interchangeable.txt').read_bytes()) == 5
    assert not (tmp_path / 'interchangeable-upcoming.txt').exists()


def test_refusal_leaves_files_untouched(tmp_path):
    original = csv_data(10)
    (tmp_path / 'interchangeable.txt').write_bytes(original)
    def fetch(url):
        return (PAGE_DATA, None) if url == PAGE else (csv_data(4 if url.endswith('next') else 10), MODIFIED)
    with pytest.raises(ValueError, match='Unexpected drop'):
        update(tmp_path, date(2026, 11, 1), fetch)
    assert sorted(p.name for p in tmp_path.iterdir()) == ['interchangeable.txt']
    assert (tmp_path / 'interchangeable.txt').read_bytes() == original
    with pytest.raises(ValueError, match='valid today'):
        update(tmp_path, date(2028, 1, 1), fetch)


def test_missing_timestamp_and_bad_period_refused(tmp_path):
    original = csv_data(2)
    (tmp_path / 'interchangeable.txt').write_bytes(original)
    def fetch(url):
        return (PAGE_DATA, None) if url == PAGE else (original, None)
    with pytest.raises(ValueError, match='Last-Modified'):
        update(tmp_path, date(2026, 11, 1), fetch)
    assert list(tmp_path.iterdir()) == [tmp_path / 'interchangeable.txt']
    with pytest.raises(ValueError):
        parse_links('<a href="/GS-ladattava.txt/x">1.2. - 31.2.2027</a>')


def test_half_previous_count_is_accepted(tmp_path):
    (tmp_path / 'interchangeable.txt').write_bytes(csv_data(10))
    def fetch(url):
        return (PAGE_DATA, None) if url == PAGE else (csv_data(5), MODIFIED)
    update(tmp_path, date(2026, 11, 1), fetch)
    assert parse_rows((tmp_path / 'interchangeable-upcoming.txt').read_bytes()) == 5
