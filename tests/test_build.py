import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build import HEADER, events, read_snapshot, register


def row(end='2026-12-01', vnr='012345'):
    return dict(zip(HEADER, [vnr, 'K', '2026-11-01', end, '2026-10-01', '2026-11-01', 'Company']))


def test_changes_removal_and_reappearance():
    result, history = events([('2026-11-01', [row()]), ('2026-11-02', [row('2026-12-05')]), ('2026-11-03', []), ('2026-11-04', [row()])])
    assert len(result) == 2
    assert result[0]['first_estimated_end'] == '2026-12-01'
    assert result[0]['end_changes'][-1] == {'seen': '2026-11-02', 'date': '2026-12-05'}
    assert result[0]['last_seen'] == '2026-11-02'
    assert result[0]['removed_on'] == '2026-11-03'
    assert result[1]['removed_on'] is None
    assert history[-1]['count'] == 1


def test_duplicate_identity_rejected():
    with pytest.raises(ValueError, match='duplicate'):
        events([('2026-11-01', [row(), row()])])


def test_bad_file_rejected(tmp_path):
    p = tmp_path / 'bad.txt'
    p.write_text('error page', encoding='utf-8')
    with pytest.raises(ValueError, match='header'):
        read_snapshot(p)


def test_register_groups_follow_product_references(tmp_path):
    path = tmp_path / 'register.xml'
    path.write_text('''<Perusrekisteri>
      <Pakkaus Laakevalmiste-ref="p1"><VNR-numero>012345</VNR-numero></Pakkaus>
      <Pakkaus Laakevalmiste-ref="p1"><VNR-numero>012346</VNR-numero></Pakkaus>
      <Pakkaus Laakevalmiste-ref="p2"><VNR-numero>012347</VNR-numero></Pakkaus>
      <Laakevalmiste id="p1"><Kauppanimi>Example</Kauppanimi>
        <Substituutioryhma listname="Substitution Group" id="0042" value="0042"/>
      </Laakevalmiste>
      <Laakevalmiste id="p2"><Substituutioryhma/></Laakevalmiste>
    </Perusrekisteri>''', encoding='utf-8')
    products = register(path, {'012345', '012346', '012347', '999999'})
    assert products['012345']['substitution_group'] == '0042'
    assert products['012346']['substitution_group'] == '0042'
    assert products['012347']['substitution_group'] == ''
    assert '999999' not in products
