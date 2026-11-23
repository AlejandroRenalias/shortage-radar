import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_groups import FLAGS, REASONS, examples, examples_text, group_packages, normalise_strength, summary_text

ROOT = Path(__file__).resolve().parents[1]
DAY = '2026-11-23'
SUBSTANCES = {'a': {'id': '1', 'name': 'Substance A'}, 'b': {'id': '2', 'name': 'Substance B'}, 'c': {'id': '3', 'name': 'Substance C'}}


def pkg(vnr, subs='a', strength='20 mg', form=('235', 'tablet'), routes=(('1055', 'Suun kautta'),), group='100', name='Medicine', product=None,
        authorisation=None, atc='N01AA01', market='1', entry='2020-01-01', exit_='', old=(), vet=False, device=None, import_=False, distribution=False, biological=False, licensed=True):
    return {
        'vnr': vnr, 'old': list(old), 'product': product or f'REL{vnr}', 'name': name, 'atc': atc, 'strength': strength, 'form_id': form[0], 'form': form[1],
        'routes': list(routes), 'substitution_group': group, 'vet': vet, 'target_species': [], 'biological': biological, 'plasma': False, 'licensed': licensed,
        'authorisation': authorisation or f'AUTH{vnr}', 'holder': 'Holder', 'parallel_import': '1' if import_ else '0', 'parallel_distribution': '1' if distribution else '0',
        'market': market, 'entry': entry, 'exit': exit_, 'shortage_flag': '0', 'pack': '', 'unit': '', 'device': device,
        'substances': [SUBSTANCES[s] for s in subs],
    }


def groups_of(*packages, **kw):
    return {tuple(g['vnrs']): g for g in group_packages(list(packages), **kw)}


def test_same_substance_strength_form_route_make_one_group_whatever_the_name_or_pack():
    result = group_packages([pkg('1', name='Brand'), pkg('2', name='Generic'), pkg('3', name='Generic', product='RELX')], day=DAY)
    assert [g['vnrs'] for g in result] == [['1', '2', '3']]
    assert not result[0]['unsure']
    assert not any(result[0][f] for f in FLAGS)


def test_combination_product_needs_every_substance_and_ignores_their_order():
    result = group_packages([pkg('1', 'ab'), pkg('2', 'ba'), pkg('3', 'ac'), pkg('4', 'a'), pkg('5', 'abc')], day=DAY)
    assert sorted(g['vnrs'] for g in result) == [['1', '2'], ['3'], ['4'], ['5']]


def test_combination_strength_text_is_kept_whole():
    result = group_packages([pkg('1', 'ab', '50 mg / 200 mg'), pkg('2', 'ab', '50 mg / 200 mg'), pkg('3', 'ab', '25 mg / 100 mg')], day=DAY)
    assert sorted(g['vnrs'] for g in result) == [['1', '2'], ['3']]


def test_different_strength_is_a_different_group_and_same_strength_in_other_spelling_is_not():
    assert len(group_packages([pkg('1', strength='20 mg'), pkg('2', strength='40 mg')], day=DAY)) == 2
    spelled = group_packages([pkg('1', strength='0,50 mg'), pkg('2', strength='0.5 MG'), pkg('3', strength='0.50  mg')], day=DAY)
    assert [g['vnrs'] for g in spelled] == [['1', '2', '3']]
    # Units are not converted, so 500 microgram and 0.5 mg stay apart.
    assert len(group_packages([pkg('1', strength='500 mikrog'), pkg('2', strength='0.5 mg')], day=DAY)) == 2
    assert normalise_strength('10 mg/ml') != normalise_strength('10 mg/g')
    assert normalise_strength('20,0 mg') == '20 mg'


def test_different_form_route_substance_atc_and_device_are_different_groups():
    base = pkg('1')
    others = [pkg('2', form=('173', 'plain tablet')), pkg('3', routes=(('1', 'Laskimoon'),)), pkg('4', routes=(('1055', 'Suun kautta'), ('1', 'Laskimoon'))),
              pkg('5', 'b'), pkg('6', atc='N01AA02'), pkg('7', device=['6', 'Injektioruisku'])]
    result = group_packages([base] + others, day=DAY)
    assert len(result) == 7
    assert not any(g[f] for g in result for f in FLAGS)


def test_other_active_ingredient_with_the_same_name_in_another_salt_is_not_merged():
    salts = [dict(pkg('1'), substances=[{'id': '10', 'name': 'Quetiapine fumarate'}]), dict(pkg('2'), substances=[{'id': '11', 'name': 'Quetiapine hemifumarate'}])]
    assert len(group_packages(salts, day=DAY)) == 2


def test_parallel_import_joins_the_original_and_is_listed_apart():
    original = pkg('1', name='Brand', authorisation='A1')
    imported = pkg('2', name='Brand', authorisation='A2', import_=True)
    distributed = pkg('3', name='Brand', authorisation='A3', distribution=True)
    [g] = group_packages([original, imported, distributed], day=DAY)
    assert g['vnrs'] == ['1', '2', '3']
    assert g['parallel_import'] == ['2'] and g['parallel_distribution'] == ['3']
    assert not g['unsure']
    # A parallel import of another strength is not joined.
    assert len(group_packages([original, dict(imported, strength='40 mg')], day=DAY)) == 2


def test_several_own_authorisations_without_register_group_are_unsure_but_parallel_imports_alone_are_not():
    generics = [pkg('1', group='', authorisation='A1'), pkg('2', group='', authorisation='A2')]
    [g] = group_packages(generics, day=DAY)
    assert g['unsure'] and g['unsure_reasons'] == ['several_products_no_register_group']
    with_import = [pkg('1', group='', authorisation='A1'), pkg('2', group='', authorisation='A2', import_=True)]
    [g] = group_packages(with_import, day=DAY)
    assert not g['unsure']
    # The same two generics in one register group are not unsure.
    assert not group_packages([pkg('1', authorisation='A1'), pkg('2', authorisation='A2')], day=DAY)[0]['unsure']


def test_register_groups_that_disagree_make_a_group_unsure_only_through_current_packages():
    disagree = group_packages([pkg('1', group='100'), pkg('2', group='200')], day=DAY)[0]
    assert disagree['unsure_reasons'] == ['register_group_disagrees']
    some_without = group_packages([pkg('1', group='100'), pkg('2', group='')], day=DAY)[0]
    assert some_without['unsure_reasons'] == ['register_group_disagrees']
    # A package that left the market long ago does not count, unless it is in the shortage file.
    old = pkg('2', group='', market='0', entry='2001-01-01', exit_='2005-01-01')
    assert not group_packages([pkg('1', group='100'), old], day=DAY)[0]['unsure']
    assert group_packages([pkg('1', group='100'), old], day=DAY, listed={'2'})[0]['unsure']
    assert group_packages([pkg('1', group='100'), old])[0]['unsure']


def test_missing_data_makes_a_group_unsure_with_the_reason():
    assert group_packages([pkg('1', strength='')], day=DAY)[0]['unsure_reasons'] == ['strength_not_stated']
    assert group_packages([pkg('1', routes=())], day=DAY)[0]['unsure_reasons'] == ['route_not_stated']
    assert group_packages([pkg('1', subs='')], day=DAY)[0]['unsure_reasons'] == ['no_substance_listed']
    assert group_packages([pkg('1', vet=True)], day=DAY)[0]['unsure_reasons'] == ['veterinary']
    assert group_packages([pkg('1', licensed=False)], day=DAY)[0]['unsure_reasons'] == ['no_marketing_authorisation_record']
    # A VNR on two register packages cannot be placed.
    twice = group_packages([pkg('1', product='R1'), pkg('1', product='R2', strength='40 mg')], day=DAY)
    assert all(g['unsure_reasons'] == ['vnr_listed_twice'] for g in twice)
    # A product whose packages list different substances is a data conflict.
    split = group_packages([pkg('1', 'a', product='R1'), pkg('2', 'b', product='R1')], day=DAY)
    assert all('product_substances_inconsistent' in g['unsure_reasons'] for g in split)


def test_biological_products_from_several_authorisations_are_unsure_even_in_one_register_group():
    [g] = group_packages([pkg('1', biological=True, authorisation='A1'), pkg('2', biological=True, authorisation='A2')], day=DAY)
    assert g['unsure_reasons'] == ['biological_several_products']


def test_groups_do_not_depend_on_input_order_and_ids_are_stable():
    packages = [pkg('1'), pkg('2', 'b'), pkg('3', strength='40 mg'), pkg('4', 'ab')]
    forward = group_packages(packages, day=DAY)
    backward = group_packages(list(reversed(packages)), day=DAY)
    assert forward == backward
    assert len({g['id'] for g in forward}) == 4 and all(re.fullmatch(r'm[0-9a-f]{12}', g['id']) for g in forward)
    assert all(r in REASONS for g in forward for r in g['unsure_reasons'])


def test_examples_and_summary_text_make_no_claim_about_switching():
    packages = [pkg(str(i), 'a', group='1', name=f'M{i}') for i in range(10, 16)] + [pkg('20', 'b', strength='5 mg'), pkg('21', 'b', strength='10 mg')]
    groups = group_packages(packages, day=DAY)
    text = examples_text(examples(groups, {'10', '20', '21'}))
    assert 'Substance A' in text
    assert not re.search(r'\bsafe|suitab|switch|substitut', text, re.I)
    assert not re.search(r'\bsafe|suitab|switch', summary_text({'register_day': DAY, 'packages': 1, 'groups': 1, 'shortage_vnrs': 0, 'shortage_vnrs_found_in_register': 0,
                                                                  'scopes': {}, 'register_groups': {}, 'alternatives': {}}), re.I)


def test_spec_makes_no_claim_about_switching():
    spec = (ROOT / 'docs/medicine-groups-spec.md').read_text(encoding='utf-8')
    assert not re.search(r'\bsafe\b|suitab', spec, re.I)
    for reason in REASONS:
        assert f'`{reason}`' in spec
