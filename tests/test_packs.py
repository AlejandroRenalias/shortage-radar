import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from packs import name_with_strength, pack_label, strength_label


@pytest.mark.parametrize('text,unit,form,en,fi', [
    ('98', 'kpl', 'tabletti, kalvopäällysteinen', '98 tablets', '98 tablettia'),
    ('1', 'kpl', 'tabletti', '1 tablet', '1 tabletti'),
    ('100', 'kpl', 'depottabletti', '100 tablets', '100 tablettia'),
    ('2', 'kpl', 'kapseli, kova', '2 capsules', '2 kapselia'),
    ('30', 'kpl', 'resoribletti', '30 tablets', '30 tablettia'),
    ('10', 'kpl', 'depotlaastari', '10 patches', '10 laastaria'),
    ('11 + 42', 'kpl', 'tabletti, kalvopäällysteinen', '11 + 42 tablets', '11 + 42 tablettia'),
    ('100 g', 'g', 'voide', '100 g', '100 g'),
    ('5 ml', 'ml', 'injektioneste, liuos', '5 ml', '5 ml'),
    ('5', 'ml', 'silmätipat, liuos', '5 ml', '5 ml'),
    ('5 x 0.5 ml', 'ml', 'injektioneste', '5 x 0.5 ml', '5 x 0,5 ml'),
    ('56 suihketta', 'suihketta', 'transdermaalisumute', '56 sprays', '56 suihketta'),
    ('30', 'annosta', 'jauhe oraaliliuosta varten', '30 doses', '30 annosta'),
    ('10', 'kpl', 'injektioneste, liuos', '10 pcs', '10 kpl'),
    ('3 x 28', 'kpl', 'tabletti, kalvopäällysteinen', '3 x 28 tablets', '3 x 28 tablettia'),
    ('28 x 1', 'kpl', 'kapseli, kova', '28 x 1 capsules', '28 x 1 kapselia'),
    ('98 x 1', 'kpl', 'tabletti', '98 x 1 tablets', '98 x 1 tablettia'),
    ('4 x 7', 'kpl', 'depotlaastari', '4 x 7 patches', '4 x 7 laastaria'),
    ('3 x 28', 'kpl', 'injektioneste', '3 x 28', '3 x 28'),
    ('', 'kpl', 'tabletti', '', ''),
])
def test_pack_label_common_cases(text, unit, form, en, fi):
    assert pack_label(text, unit, form) == {'en': en, 'fi': fi}


def test_register_text_with_a_unit_is_kept():
    assert pack_label('10 x 500 mg', 'kpl', 'injektiokuiva-aine')['fi'] == '10 x 500 mg'


def test_strength_label_uses_a_decimal_comma_in_finnish():
    assert strength_label('2.5 mg', 'fi') == '2,5 mg' and strength_label('2.5 mg', 'en') == '2.5 mg'
    assert strength_label('0.02 mg / 3 mg', 'fi') == '0,02 mg / 3 mg'
    assert strength_label('1.5 mg/ml + 5 mg/ml', 'fi') == '1,5 mg/ml + 5 mg/ml'
    assert strength_label(None, 'fi') == ''


def test_name_with_strength():
    assert name_with_strength('Apixaban Sandoz', '5 mg', 'en') == 'Apixaban Sandoz 5 mg'
    assert name_with_strength('Apixaban Sandoz', '2.5 mg', 'fi') == 'Apixaban Sandoz 2,5 mg'
    assert name_with_strength('Burana 400 mg', '400 mg', 'en') == 'Burana 400 mg'
    assert name_with_strength('Burana', '', 'en') == 'Burana'
