import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_groups import group_packages, unit_size
from test_audit_groups import DAY, one, pkg

SYRINGE = ('66', 'injektioneste, liuos, esitäytetty ruisku')


# Round 2, Trexan group m4091940612e4: the register gives 25 mg/ml and one product record for pre-filled syringes of 0.3, 0.4, 0.6, 0.8 and 1.0 ml.
def test_prefilled_syringes_of_other_volumes_are_other_presentations_and_package_only_without_a_device_id():
    def trexan(vnr, ml):
        return pkg(vnr, strength='25 mg/ml', form=SYRINGE, product='REL44952', container=['2', 'Esitäytetty ruisku'], pack=f'{ml} ml',
                   pack_size=str(float(ml)).rstrip('0').rstrip('.'), amounts={'a': ('25', 'mg')})
    packages = [trexan('562071', '0.3'), trexan('049212', '0.4'), trexan('456852', '1.0')]
    groups = {tuple(g['vnrs']): g for g in group_packages(packages, day=DAY)}
    assert set(groups) == {('562071',), ('049212',), ('456852',)}
    assert all(g['unsure_reasons'] == ['device_not_verified'] and not g['first_release_candidate'] for g in groups.values())
    # The same 25 mg in the register is not a per-unit strength and does not join them.
    assert {a['amount'] for p in packages for a in p['amounts']} == {'25'}
    # With a device id they are still three groups: one unit is the presentation, not the pack total or count.
    with_device = group_packages([dict(p, device=['6', 'Injektioruisku']) for p in packages], day=DAY)
    assert len(with_device) == 3 and not any(g['unsure'] for g in with_device)
    assert sorted(g['inputs']['presentation']['unit_size'] for g in with_device) == ['0.3 ml', '0.4 ml', '1 ml']


def test_unit_size_is_the_size_of_one_unit_and_never_the_pack_count_or_total():
    inj = ('245', 'injektioneste')
    assert unit_size(pkg('1', form=inj, pack='5 x 1 ml', pack_size='1')) == '1 ml'
    assert unit_size(pkg('1', form=inj, pack='0,30 ml', pack_size='0.3')) == '0.3 ml'
    assert unit_size(pkg('1', form=inj, pack='5 ml', pack_size='1')) == ''
    assert unit_size(pkg('1', form=inj, pack='10 x 6 x 1 ml', pack_size='1', pack_factor='6')) == ''
    assert unit_size(pkg('1', form=inj, pack='4 x 5 ml', pack_size='1', pack_unit='kpl')) == ''
    # An injectable whose unit size is not verified is package-only; so is one with no container.
    assert one(pkg('1', form=inj, pack='4 x 5 ml', pack_size='1', pack_unit='kpl'), day=DAY)['unsure_reasons'] == ['presentation_not_verified']
    assert one(pkg('1', form=inj, container=None), day=DAY)['unsure_reasons'] == ['presentation_not_verified']


# Round 2, Celeston Chronodose 433078 (5 ml vial) and 473507 (5 x 1 ml ampoules): one product record, other immediate containers.
def test_other_injectable_containers_are_other_groups_and_other_boxes_are_not():
    form = ('245', 'injektioneste, suspensio')
    vial = pkg('433078', form=form, strength='(3+3) mg/ml', product='REL403', container=['4', 'Injektiopullo'], pack='5 ml', pack_size='5')
    ampoule = pkg('473507', form=form, strength='(3+3) mg/ml', product='REL403', container=['1', 'Ampulli'], pack='5 x 1 ml', pack_size='1')
    groups = group_packages([vial, ampoule], day=DAY)
    assert sorted(g['vnrs'] for g in groups) == [['433078'], ['473507']]
    assert not any(g['unsure'] for g in groups)
    # The same container and unit size in another pack count is one group.
    assert sorted(one(ampoule, dict(ampoule, vnr='9', pack='10 x 1 ml'), day=DAY)['vnrs']) == ['473507', '9']
    # Tablets in a blister or in a jar are not a difference of presentation.
    blister = dict(pkg('1'), container=['9', 'Läpipainopakkaus'], pack='30')
    jar = dict(pkg('2'), container=['3', 'Purkki'], pack='100')
    assert one(blister, jar, day=DAY)['vnrs'] == ['1', '2']


def test_a_single_package_can_be_unsure_for_its_own_data():
    g = one(pkg('1', routes=()), day=DAY)
    assert len(g['vnrs']) == 1 and g['unsure_reasons'] == ['route_not_stated']


def test_first_release_candidates_are_unsure_free_single_product_presentations():
    assert one(pkg('1', product='R', container=['9', 'Läpipainopakkaus']), pkg('2', product='R', container=['9', 'Läpipainopakkaus']), day=DAY)['first_release_candidate']
    assert not one(pkg('1'), pkg('2'), day=DAY)['first_release_candidate']  # two product records
    assert not one(pkg('1', routes=()), day=DAY)['first_release_candidate']


# Round 3, Zovirax cream 081243 (tube, container 14) and 081252 (pump bottle, container 11): one product record, blank device ids, equal fields.
def test_one_product_with_other_or_unknown_containers_is_not_a_first_release_candidate():
    cream = ('17', 'emulsiovoide')
    tube = pkg('081243', form=cream, strength='50 mg/g', product='REL1777', container=['14', 'Tuubi'], pack='10 g')
    pump = pkg('081252', form=cream, strength='50 mg/g', product='REL1777', container=['11', 'Pumppupullo'], pack='25 g')
    g = one(tube, pump, day=DAY)
    # The equivalence rule is unchanged: one group, not unsure. Only eligibility is withheld.
    assert g['vnrs'] == ['081243', '081252'] and not g['unsure'] and not g['container_verified'] and not g['first_release_candidate']
    # A blank container is not a known container, also when every member is blank.
    blank = one(dict(tube, container=None), dict(pump, container=None), day=DAY)
    assert not blank['unsure'] and not blank['first_release_candidate']
    assert not one(tube, dict(pump, container=None), day=DAY)['first_release_candidate']
    # The same known container on every member, and a single package, stay eligible.
    assert one(tube, dict(tube, vnr='2'), day=DAY)['first_release_candidate']
    assert one(dict(tube, container=None), day=DAY)['first_release_candidate']
