import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_groups import (COUNTEREXAMPLES, FLAGS, REASONS, composition_status, examples, examples_text, group_packages, normalise_strength, read_register,
                          same_key_comparison, shortage_join, summarise, summary_text)

ROOT = Path(__file__).resolve().parents[1]
REGISTER = ROOT / 'data/source/register.xml'
DAY = '2026-11-23'
SUBSTANCES = {'a': {'id': '1', 'name': 'Substance A'}, 'b': {'id': '2', 'name': 'Substance B'}, 'c': {'id': '3', 'name': 'Substance C'}}


def pkg(vnr, subs='a', strength='20 mg', form=('235', 'tablet'), routes=(('1055', 'Suun kautta'),), group='100', name='Medicine', product=None,
        authorisation=None, eu='', atc='N01AA01', market='1', entry='2020-01-01', exit_='', old=(), vet=False, device=None, import_=False, distribution=False,
        biological=False, licensed=True, amounts=None):
    """A register package. `amounts` is {substance key: (amount, unit)}; by default every substance has 10 mg."""
    amounts = amounts or {s: ('10', 'mg') for s in subs}
    return {
        'vnr': vnr, 'old': list(old), 'product': product or f'REL{vnr}', 'name': name, 'atc': atc, 'strength': strength, 'form_id': form[0], 'form': form[1],
        'routes': list(routes), 'substitution_group': group, 'vet': vet, 'target_species': [], 'biological': biological, 'plasma': False, 'licensed': licensed,
        'authorisation': authorisation if authorisation is not None else f'AUTH{vnr}', 'eu_authorisation': eu, 'holder': 'Holder',
        'parallel_import': '1' if import_ else '0', 'parallel_distribution': '1' if distribution else '0',
        'market': market, 'entry': entry, 'exit': exit_, 'shortage_flag': '0', 'pack': '', 'unit': '', 'device': device,
        'substances': [SUBSTANCES[s] for s in subs],
        'amounts': [{'id': SUBSTANCES[s]['id'], 'name': SUBSTANCES[s]['name'], 'amount': a, 'unit': u, 'min': '', 'max': '', 'per': '', 'as_id': ''} for s, (a, u) in amounts.items()],
    }


def one(*packages, **kw):
    [g] = group_packages(list(packages), **kw)
    return g


def test_same_substance_strength_form_route_make_one_group_whatever_the_name_or_pack():
    g = one(pkg('1', name='Brand'), pkg('2', name='Generic'), pkg('3', name='Generic', product='RELX'), day=DAY)
    assert g['vnrs'] == ['1', '2', '3'] and not g['unsure']
    assert not any(g[f] for f in FLAGS)


def test_combination_product_needs_every_substance_and_ignores_their_order():
    result = group_packages([pkg('1', 'ab'), pkg('2', 'ba'), pkg('3', 'ac'), pkg('4', 'a'), pkg('5', 'abc')], day=DAY)
    assert sorted(g['vnrs'] for g in result) == [['1', '2'], ['3'], ['4'], ['5']]


def test_combination_strength_text_is_kept_whole_and_not_mapped_to_substances():
    result = group_packages([pkg('1', 'ab', '50 mg / 200 mg'), pkg('2', 'ab', '50 mg / 200 mg'), pkg('3', 'ab', '25 mg / 100 mg')], day=DAY)
    assert sorted(g['vnrs'] for g in result) == [['1', '2'], ['3']]
    # Caninda: the text "8 mg / 2.5 mg" is in the order of the product, not of the substance ids. The group keeps the text as text.
    g = one(pkg('1', 'ba', '8 mg / 2.5 mg', product='R'), pkg('2', 'ba', '8 mg / 2.5 mg', product='R'), day=DAY)
    assert g['inputs']['strength_text'] == '8 mg / 2.5 mg'
    assert [s[1] for s in g['inputs']['substances']] == ['Substance A', 'Substance B']
    assert not any('component' in key for key in g)
    assert 'not mapped to the substances' in examples_text([('combination', [g])])


def test_different_strength_is_a_different_group_and_same_strength_in_other_spelling_is_not():
    assert len(group_packages([pkg('1', strength='20 mg'), pkg('2', strength='40 mg')], day=DAY)) == 2
    assert one(pkg('1', strength='0,50 mg'), pkg('2', strength='0.5 MG'), pkg('3', strength='0.50  mg'), day=DAY)['vnrs'] == ['1', '2', '3']
    # Units are not converted, so 500 microgram and 0.5 mg stay apart.
    assert len(group_packages([pkg('1', strength='500 mikrog'), pkg('2', strength='0.5 mg')], day=DAY)) == 2
    assert normalise_strength('10 mg/ml') != normalise_strength('10 mg/g')
    assert normalise_strength('20,0 mg') == '20 mg'


def test_different_form_route_substance_atc_and_device_are_different_groups():
    packages = [pkg('1'), pkg('2', form=('173', 'plain tablet')), pkg('3', routes=(('1', 'Laskimoon'),)), pkg('4', routes=(('1055', 'Suun kautta'), ('1', 'Laskimoon'))),
                pkg('5', 'b'), pkg('6', atc='N01AA02'), pkg('7', device=['6', 'Injektioruisku'])]
    result = group_packages(packages, day=DAY)
    assert len(result) == 7
    assert not any(g[f] for g in result for f in FLAGS)


def test_other_salt_with_a_similar_name_is_not_merged():
    salts = [dict(pkg('1'), substances=[{'id': '10', 'name': 'Quetiapine fumarate'}]), dict(pkg('2'), substances=[{'id': '11', 'name': 'Quetiapine hemifumarate'}])]
    assert len(group_packages(salts, day=DAY)) == 2


# Review 1: EU authorisations. NovoRapid 007523 and Fiasp 472559, Insulin Lispro Sanofi 117084 and Liprolog 165713.
def test_eu_authorisations_are_read_and_biologicals_of_two_products_stay_unsure():
    novorapid = pkg('1', name='NovoRapid', authorisation='', eu='EU/1/99/119/001,008,015', biological=True, group='')
    fiasp = pkg('2', name='Fiasp', authorisation='', eu='EU/1/16/1160/007-009', biological=True, group='')
    g = one(novorapid, fiasp, day=DAY)
    assert g['unsure'] and 'biological_several_products' in g['unsure_reasons'] and 'several_products_no_register_group' in g['unsure_reasons']
    assert g['authorisations'] == ['EU:EU/1/16/1160', 'EU:EU/1/99/119']
    # Even with a register code, a biological from two product records is unsure.
    assert 'biological_several_products' in one(dict(novorapid, substitution_group='7'), dict(fiasp, substitution_group='7'), day=DAY)['unsure_reasons']


def test_a_blank_or_shared_licence_is_not_an_identity_and_the_product_record_is_the_boundary():
    blank = one(pkg('1', authorisation='', eu=''), pkg('2', authorisation='', eu=''), day=DAY)
    assert 'authorisation_identity_missing' in blank['unsure_reasons']
    one_blank = one(pkg('1', authorisation='', eu=''), pkg('2'), day=DAY)
    assert 'authorisation_identity_missing' in one_blank['unsure_reasons']
    # Two product records under the same EU number, no register code: still a cross-product group without backing.
    shared = one(pkg('1', eu='EU/1/00/1/001', group=''), pkg('2', eu='EU/1/00/1/002', group=''), day=DAY)
    assert shared['authorisations'] == ['EU:EU/1/00/1'] and 'several_products_no_register_group' in shared['unsure_reasons']
    # Packages of one product record need no identity: the product record is the presentation.
    assert not one(pkg('1', product='R', authorisation='', eu=''), pkg('2', product='R', authorisation='', eu=''), day=DAY)['unsure']


# Review 2: Physioneal 35 and 40 Clear-Flex (016111, 016129, 016194) have the same glucose per ml and other calcium and lactate.
def test_same_strength_text_with_other_composition_is_flagged_and_unsure():
    base = {'a': ('13.6', 'g'), 'b': ('5.4', 'g'), 'c': ('0.25', 'g')}
    forty = pkg('1', 'abc', '13.6 mg/ml', product='P40', amounts=base)
    thirty_five = pkg('2', 'abc', '13.6 mg/ml', product='P35', amounts={'a': ('13.6', 'g'), 'b': ('5.4', 'g'), 'c': ('0.18', 'g')})
    g = one(forty, thirty_five, dict(forty, vnr='3'), day=DAY)
    assert g['quantity_review'] and g['composition'] == 'differs'
    assert {'composition_differs', 'composition_not_verified'} <= set(g['unsure_reasons'])
    # An off-market member does not hide it.
    old = dict(thirty_five, market='0', entry='2001-01-01', exit='2005-01-01')
    assert one(forty, old, day=DAY)['quantity_review']


def test_composition_is_verified_across_pack_sizes_and_units_and_incomplete_data_gives_no_verdict():
    small = pkg('1', 'ab', amounts={'a': ('1', 'g'), 'b': ('50', 'mg')}, product='P1')
    large = pkg('2', 'ab', amounts={'a': ('2500', 'mg'), 'b': ('125', 'mg')}, product='P2')
    assert composition_status([small, large]) == 'verified'
    assert not one(small, large, day=DAY)['unsure']
    missing = pkg('3', 'ab', amounts={'a': ('2', 'g'), 'b': ('', '')}, product='P3')
    assert composition_status([small, missing]) == 'incomplete'
    g = one(small, missing, day=DAY)
    assert not g['quantity_review'] and 'composition_not_verified' in g['unsure_reasons']
    # Packages of one product record are one presentation; missing amounts do not make them unsure.
    assert not one(dict(small, product='P'), dict(missing, product='P'), day=DAY)['unsure']
    # Another unit that is not a mass is not compared with a mass.
    iu = pkg('4', 'ab', amounts={'a': ('2', 'IU'), 'b': ('125', 'mg')}, product='P4')
    assert composition_status([small, iu]) == 'incomplete'
    assert composition_status([small]) == 'not_applicable'


# Review 3: Liprolog KwikPen 517586 and Junior KwikPen 544210 have no device id; the EMA shows other dose steps.
def test_device_bearing_presentations_of_two_product_records_need_a_device_id():
    pen = ('462', 'injektioneste, liuos, esitäytetty kynä')
    one_pen, other_pen = pkg('1', form=pen, eu='EU/1/01/1/001'), pkg('2', form=pen, eu='EU/1/01/1/002')
    assert 'device_not_verified' in one(one_pen, other_pen, day=DAY)['unsure_reasons']
    with_device = [dict(p, device=['5', 'Kynä']) for p in (one_pen, other_pen)]
    assert not one(*with_device, day=DAY)['unsure']
    # One product record is one presentation.
    assert not one(pkg('1', form=pen, product='R'), pkg('2', form=pen, product='R'), day=DAY)['unsure']
    # A plain tablet needs no device id.
    assert not one(pkg('1'), pkg('2'), day=DAY)['unsure']


# Review 4: Rybelsus 130247 and parallel-distributed Wegovy 074190 (and the 4 mg versions) have different EU licences.
def test_parallel_flag_is_a_channel_and_joins_only_through_the_same_eu_authorisation():
    original = pkg('1', name='Rybelsus', authorisation='', eu='EU/1/20/1430/001-003', product='RO')
    other_brand = pkg('2', name='Wegovy', authorisation='', eu='EU/1/21/1608/001', product='RW', distribution=True)
    result = {tuple(g['vnrs']): g for g in group_packages([original, other_brand], day=DAY)}
    assert set(result) == {('1',), ('2',)}
    assert not result[('1',)]['unsure'] and result[('2',)]['unsure_reasons'] == ['parallel_not_linked']
    assert result[('2',)]['parallel_distribution'] == ['2']
    # The same EU authorisation is a source-backed link: the distribution joins the original (and the register must back it, here by one code).
    linked = pkg('2', name='Rybelsus', authorisation='', eu='EU/1/20/1430/004', product='RD', distribution=True)
    g = one(original, linked, day=DAY)
    assert g['vnrs'] == ['1', '2'] and g['parallel_distribution'] == ['2'] and not g['unsure']
    # A national parallel import has no EU number to link with, even with the original's name and every other input equal.
    national = pkg('1', name='Brand', authorisation='A1', product='RO')
    imported = pkg('2', name='Brand', authorisation='A2', product='RI', import_=True)
    result = {tuple(g['vnrs']): g for g in group_packages([national, imported], day=DAY)}
    assert set(result) == {('1',), ('2',)} and result[('2',)]['unsure_reasons'] == ['parallel_not_linked']
    # Several packages of one unlinked import stay together; another strength is not joined in any case.
    assert len(group_packages([national, imported, dict(imported, vnr='3'), dict(imported, vnr='4', strength='40 mg')], day=DAY)) == 3


def test_several_products_without_register_code_are_unsure_but_one_code_backs_them():
    assert one(pkg('1', group=''), pkg('2', group=''), day=DAY)['unsure_reasons'] == ['several_products_no_register_group']
    assert not one(pkg('1'), pkg('2'), day=DAY)['unsure']


def test_register_groups_that_disagree_make_a_group_unsure_only_through_current_packages():
    assert one(pkg('1', group='100'), pkg('2', group='200'), day=DAY)['unsure_reasons'] == ['register_group_disagrees']
    assert one(pkg('1', group='100'), pkg('2', group=''), day=DAY)['unsure_reasons'] == ['register_group_disagrees']
    # A package that left the market long ago does not count, unless it is in the shortage file.
    old = pkg('2', group='', market='0', entry='2001-01-01', exit_='2005-01-01')
    assert not one(pkg('1', group='100'), old, day=DAY)['unsure']
    assert one(pkg('1', group='100'), old, day=DAY, listed={'2'})['unsure']
    assert one(pkg('1', group='100'), old)['unsure']


def test_missing_data_makes_a_group_unsure_with_the_reason():
    assert one(pkg('1', strength=''), day=DAY)['unsure_reasons'] == ['strength_not_stated']
    assert one(pkg('1', routes=()), day=DAY)['unsure_reasons'] == ['route_not_stated']
    assert one(pkg('1', subs=''), day=DAY)['unsure_reasons'] == ['no_substance_listed']
    assert one(pkg('1', vet=True), day=DAY)['unsure_reasons'] == ['veterinary']
    assert one(pkg('1', licensed=False), day=DAY)['unsure_reasons'] == ['no_marketing_authorisation_record']
    split = group_packages([pkg('1', 'a', product='R1'), pkg('2', 'b', product='R1')], day=DAY)
    assert all('product_substances_inconsistent' in g['unsure_reasons'] for g in split)


# Review 5: 018486 Topimax, 370212 Mirena and 424765 Haemate each have two register records.
def test_a_vnr_on_two_register_records_is_unsure_ambiguous_and_outside_the_confident_count():
    twice = [pkg('1', product='R1', group='100'), pkg('1', product='R2', group='100', strength='40 mg'), pkg('2', product='R3')]
    groups = group_packages(twice, day=DAY)
    assert all('vnr_listed_twice' in g['unsure_reasons'] for g in groups if '1' in g['vnrs'])
    join = shortage_join(twice, {'1', '2', '9'})
    assert join['ambiguous'] == ['1'] and join['unmatched'] == ['9'] and list(join['matched']) == ['2']
    summary = summarise(groups, twice, {'1', '2', '9'}, DAY)
    assert summary['shortage_vnrs_ambiguous'] == ['1'] and summary['shortage_vnrs_confident'] == 1
    assert summary['register_vnrs_on_two_records'] == ['1']
    # Only the group of the confident VNR is in the shortage scope.
    assert summary['scopes']['in_current_shortage']['groups'] == 1


def test_on_market_counts_need_the_register_flag_and_dates_only_packages_are_reported():
    flagged_off = pkg('2', market='0')
    packages = [pkg('1'), flagged_off]
    groups = group_packages(packages, day=DAY)
    summary = summarise(groups, packages, set(), DAY)
    assert summary['packages_on_market_by_dates_only'] == ['2']
    assert summary['scopes']['on_market']['groups'] == 1


def test_biological_products_from_several_authorisations_are_unsure_even_in_one_register_group():
    g = one(pkg('1', biological=True, authorisation='A1'), pkg('2', biological=True, authorisation='A2'), day=DAY)
    assert g['unsure_reasons'] == ['biological_several_products']


def test_groups_do_not_depend_on_input_order_and_ids_are_stable():
    packages = [pkg('1'), pkg('2', 'b'), pkg('3', strength='40 mg'), pkg('4', 'ab')]
    forward = group_packages(packages, day=DAY)
    assert forward == group_packages(list(reversed(packages)), day=DAY)
    assert len({g['id'] for g in forward}) == 4 and all(re.fullmatch(r'm[0-9a-f]{12}', g['id']) for g in forward)
    assert all(r in REASONS for g in forward for r in g['unsure_reasons'])


BANNED = r'\bsafe|suitab|switch|interchang|\balternative|in stock|can replace'


def test_generated_text_makes_no_claim_about_switching_or_availability():
    packages = [pkg(str(i), 'a', name=f'M{i}') for i in range(10, 16)] + [pkg('20', 'b', strength='5 mg'), pkg('21', 'b', strength='10 mg')]
    groups = group_packages(packages, day=DAY)
    listed = {'10', '20', '21'}
    found = examples(groups, listed)
    text = examples_text(found, [('case', groups[:1])])
    assert 'Substance A' in text and not re.search(BANNED, text, re.I)
    summary = summarise(groups, packages, listed, DAY)
    summary.update(sources={'register_file': 'r.xml'}, register_groups={'register_groups': 0}, same_key=same_key_comparison(groups, packages, listed, DAY))
    assert not re.search(BANNED, summary_text(summary).replace('what can replace what', ''), re.I)


def test_spec_makes_no_claim_about_switching_and_names_every_reason():
    spec = (ROOT / 'docs/medicine-groups-spec.md').read_text(encoding='utf-8')
    assert not re.search(r'\bsafe\b|suitab', spec, re.I)
    for reason in REASONS:
        assert f'`{reason}`' in spec


@pytest.mark.skipif(not REGISTER.exists(), reason='the register is not in the repository; run scripts/fetch_register.py')
def test_review_counterexamples_in_the_real_register():
    """The cases of the review, on the real register. They are in data/audit/examples.md too."""
    packages = read_register(REGISTER)
    from source_age import register_date
    groups = group_packages(packages, register_date(REGISTER))
    holding = {}
    for g in groups:
        for v in g['vnrs']:
            holding.setdefault(v, []).append(g)
    for label, vnrs in COUNTEREXAMPLES.items():
        found = {g['id']: g for v in vnrs for g in holding.get(v, [])}
        assert found, label
        if label.startswith('Caninda'):
            assert len(found) == 1 and all('component' not in k for k in next(iter(found.values())))
        elif label.startswith('VNRs with two'):
            assert all(g['unsure'] and 'vnr_listed_twice' in g['unsure_reasons'] for g in found.values())
        else:
            # Never two of the VNRs in one group the audit calls sure.
            assert not any(not g['unsure'] and len(set(vnrs) & set(g['vnrs'])) > 1 for g in found.values()), label
    assert sum(g['quantity_review'] for g in groups if {'016111', '016129', '016194'} & set(g['vnrs'])) >= 1
