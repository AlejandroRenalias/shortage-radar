import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build import HEADER
from import_history import capture_date, normalise, sha1_digest, summarise_rss

FINNISH = '"VNR";"Voimassa";"SaatavuushairioAlkupaiva";"SaatavuushairioLoppupaiva";"Ilmoituspaiva";"Muokkauspaiva";"Yritys"'
ROW = '"044575";"K";"2024-11-15";"2024-12-31";"2024-11-15";"2024-11-18";"Orifarm Oy"'


def test_finnish_header_maps_to_current_header_and_keeps_rows():
    out = normalise(f'{FINNISH}\r\n{ROW}\r\n'.encode('utf-8'))
    assert out.decode('utf-8') == ';'.join(f'"{c}"' for c in HEADER) + f'\r\n{ROW}\r\n'


def test_english_header_is_unchanged_and_unknown_header_rejected():
    english = ';'.join(f'"{c}"' for c in HEADER)
    assert normalise(f'{english}\n{ROW}\n'.encode()) == f'{english}\n{ROW}\n'.encode()
    with pytest.raises(ValueError, match='header'):
        normalise(b'"Nr";"Giltig"\n"1";"K"\n')


def test_capture_date_uses_helsinki_time():
    assert capture_date('20261120234409') == '2026-11-21'   # 01:44 in Helsinki
    assert capture_date('20260915010123') == '2026-09-15'
    assert capture_date('20260701225959') == '2026-07-02'   # summer time, UTC+3
    assert capture_date('20260701205959') == '2026-07-01'


def test_digest_matches_archive_format():
    assert sha1_digest(b'') == '3I42H3S6NNFQ2MSVX7XZKYAYSCX5QBYJ'


def test_rss_summary_counts_items_and_dates():
    xml = '''<rss xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
      <item><content:encoded>alkaa: 2026-04-27, päättyy: 2026-08-10</content:encoded><guid>1</guid></item>
      <item><content:encoded>alkaa: 2025-01-02, päättyy: 2026-09-01</content:encoded><guid>1</guid></item>
    </channel></rss>'''
    assert summarise_rss(xml.encode()) == {'items': 2, 'unique_guids': 1, 'earliest_start': '2025-01-02', 'latest_end': '2026-09-01'}
