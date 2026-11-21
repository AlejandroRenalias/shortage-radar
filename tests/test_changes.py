import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from build import HEADER, events, register
from changes import FEED_MAX_ENTRIES, date_text, feeds, week_summary

ATOM = '{http://www.w3.org/2005/Atom}'


def row(vnr, start='2026-11-01', notified='2026-10-01', company='Company'):
    return dict(zip(HEADER, [vnr, 'K', start, '2026-12-01', notified, '2026-11-01', company]))


def sample():
    snapshots = [
        ('2026-10-01', [row('111111'), row('222222'), row('333333')]),
        ('2026-11-10', [row('111111'), row('222222'), row('333333')]),
        # 222222 left, 444444 is new, 333333 is replaced by a changed record, 555555 appears and leaves.
        ('2026-11-14', [row('111111'), row('333333', notified='2026-11-12'), row('444444', notified='2026-11-13'), row('555555')]),
        ('2026-11-18', [row('111111'), row('333333', notified='2026-11-12'), row('444444', notified='2026-11-13')]),
    ]
    es, history = events(snapshots)
    for e in es:
        e['name'] = f"Medicine {e['NordicArticleNumber']}"
        e['pack_label'] = {'en': '30 tablets', 'fi': '30 tablettia'}
    return es, snapshots, history


def test_week_summary_counts_arrivals_and_exits_against_a_stated_capture():
    es, snapshots, history = sample()
    summary = week_summary(es, snapshots, history)
    assert summary == {'from': '2026-11-10', 'to': '2026-11-18', 'days': 8, 'new': 2, 'left': 2, 'count_from': 3, 'count_to': 3}
    assert summary['count_from'] + summary['new'] - summary['left'] == summary['count_to']


def test_week_summary_is_empty_without_a_close_enough_capture():
    es, snapshots, history = sample()
    assert week_summary(es, snapshots[2:], history[2:]) is None
    far = [h for h in history if h['date'] != '2026-11-10']
    assert week_summary(es, snapshots, far) is None


def test_feeds_are_valid_atom_in_both_languages():
    es, snapshots, history = sample()
    files = feeds(es, snapshots, history)
    assert set(files) == {'feed.xml', 'feed-fi.xml'}
    for name, lang in (('feed.xml', 'en'), ('feed-fi.xml', 'fi')):
        root = ET.fromstring(files[name].encode('utf-8'))
        assert root.tag == ATOM + 'feed' and root.get('{http://www.w3.org/XML/1998/namespace}lang') == lang
        for child in ('id', 'title', 'updated', 'author'):
            assert root.find(ATOM + child) is not None
        assert any(l.get('rel') == 'self' and l.get('href').endswith(name) for l in root.findall(ATOM + 'link'))
        datetime.strptime(root.findtext(ATOM + 'updated'), '%Y-%m-%dT%H:%M:%SZ')
        entries = root.findall(ATOM + 'entry')
        ids = [e.findtext(ATOM + 'id') for e in entries]
        assert len(ids) == len(set(ids))
        for e in entries:
            datetime.strptime(e.findtext(ATOM + 'updated'), '%Y-%m-%dT%H:%M:%SZ')
            assert e.findtext(ATOM + 'title') and e.findtext(ATOM + 'summary')
            assert e.find(ATOM + 'link').get('href').startswith('https://alejandrorenalias.github.io/shortage-radar/')
    english = [e.findtext(ATOM + 'title') for e in ET.fromstring(files['feed.xml'].encode('utf-8')).findall(ATOM + 'entry')]
    assert 'New on the list: Medicine 444444, 30 tablets' in english and 'Left the list: Medicine 222222, 30 tablets' in english
    assert not any('333333' in t for t in english)
    finnish = [e.findtext(ATOM + 'title') for e in ET.fromstring(files['feed-fi.xml'].encode('utf-8')).findall(ATOM + 'entry')]
    assert 'Uusi listalla: Medicine 444444, 30 tablettia' in finnish


def test_feed_keeps_only_the_last_14_days_and_escapes_text():
    snapshots = [('2026-08-01', [row('111111')]), ('2026-08-02', [row('111111'), row('222222')]), ('2026-11-18', [row('111111'), row('222222')]), ('2026-11-19', [row('111111')])]
    es, history = events(snapshots)
    es[0]['name'] = 'A & B <tablets>'
    es[1]['name'] = 'A & B <tablets>'
    root = ET.fromstring(feeds(es, snapshots, history)['feed.xml'].encode('utf-8'))
    titles = [e.findtext(ATOM + 'title') for e in root.findall(ATOM + 'entry')]
    assert titles == ['Left the list: A & B <tablets>']


def test_register_gives_pack_label_and_no_contact_details(tmp_path):
    path = tmp_path / 'register.xml'
    path.write_text('''<Perusrekisteri>
      <Pakkaus Laakevalmiste-ref="p1"><VNR-numero>012345</VNR-numero><Pakkauskokoteksti>98</Pakkauskokoteksti>
        <Pakkauskokoyksikko id="kpl" value="kpl"/>
        <SaatavuushairioTiedot><Saatavuushairio>1</Saatavuushairio>
        <SaatavuushairioLisatietojenAntaja>CONTACT-PLACEHOLDER</SaatavuushairioLisatietojenAntaja></SaatavuushairioTiedot></Pakkaus>
      <Laakevalmiste id="p1"><Kauppanimi>Example</Kauppanimi><Laakemuoto id="1" value="tabletti, kalvopäällysteinen"/></Laakevalmiste>
    </Perusrekisteri>''', encoding='utf-8')
    product = register(path, {'012345'})['012345']
    assert product['pack_label'] == {'en': '98 tablets', 'fi': '98 tablettia'}
    assert 'CONTACT-PLACEHOLDER' not in str(product) and not any('contact' in key for key in product)


def test_feed_window_is_14_days():
    snapshots = [('2026-11-01', [row('111111')]), ('2026-11-03', [row('111111'), row('222222')]), ('2026-11-10', [row('111111'), row('222222'), row('333333')]), ('2026-11-17', [row('111111')])]
    es, history = events(snapshots)
    root = ET.fromstring(feeds(es, snapshots, history)['feed.xml'].encode('utf-8'))
    titles = sorted(e.findtext(ATOM + 'title') for e in root.findall(ATOM + 'entry'))
    # 2026-11-03 is exactly 14 days before the latest capture and is outside the window.
    assert titles == ['Left the list: VNR 222222', 'Left the list: VNR 333333', 'New on the list: VNR 333333']


def test_feed_is_capped_and_links_open_the_site_on_the_medicine():
    vnrs = [f'{n:06d}' for n in range(1, 251)]
    snapshots = [('2026-11-01', [row('999999')]), ('2026-11-20', [row('999999')] + [row(v) for v in vnrs])]
    es, history = events(snapshots)
    files = feeds(es, snapshots, history)
    root = ET.fromstring(files['feed.xml'].encode('utf-8'))
    entries = root.findall(ATOM + 'entry')
    assert len(entries) == FEED_MAX_ENTRIES
    first = entries[0]
    vnr = first.findtext(ATOM + 'title').rsplit('VNR ', 1)[1]
    assert first.find(ATOM + 'link').get('href') == f'https://alejandrorenalias.github.io/shortage-radar/?q={vnr}'
    ids_before = [e.findtext(ATOM + 'id') for e in entries]
    assert ids_before == [e.findtext(ATOM + 'id') for e in ET.fromstring(feeds(es, snapshots, history)['feed.xml'].encode('utf-8')).findall(ATOM + 'entry')]
    assert all(i.startswith('tag:alejandrorenalias.github.io,2026:shortage-radar/') for i in ids_before)


def test_finnish_feed_uses_finnish_dates_and_english_feed_the_site_format():
    snapshots = [('2026-11-01', [row('111111')]), ('2026-11-20', [row('111111'), row('222222', start='2026-11-30')])]
    es, history = events(snapshots)
    files = feeds(es, snapshots, history)
    assert 'Ilmoitettu alkamispäivä: 30.11.2026' in files['feed-fi.xml'] and 'Havaittu ensimmäisen kerran tilannekuvassa 20.11.2026' in files['feed-fi.xml']
    assert 'Reported start: 30 Nov 2026' in files['feed.xml']
    assert date_text('2026-09-05', 'fi') == '5.9.2026' and date_text('2026-09-05', 'en') == '5 Sep 2026'
    assert '2026-11-30' not in files['feed-fi.xml'].replace('2026-11-30T', '')
