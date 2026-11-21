import json
import shutil
import subprocess
from pathlib import Path

import pytest


@pytest.mark.skipif(not shutil.which('node'), reason='Node.js is required to exercise the page script')
@pytest.mark.parametrize(('start', 'end', 'available', 'note'), [
    ('2000-01-01', '2000-03-31', True, 'Interchangeable groups unavailable: list expired on 2000-03-31.'),
    ('2000-01-01', '2999-12-31', False, 'Interchangeable groups unavailable for today.'),
    ('2000-01-01', '2999-12-31', True, ''),
])
def test_source_label_and_expiry_note(start, end, available, note):
    data = {'events': [], 'history': [{'date': '2026-01-01', 'count': 0}],
            'snapshot_date': '2026-01-01', 'archive_start': '2026-01-01',
            'source_metadata': {'interchangeable_available': available,
                                'interchangeable': {'dataset': 'Finnish source title', 'valid_from': start,
                                                    'valid_until': end, 'last_modified_utc': 'timestamp'}}}
    script = r'''
const fs = require('fs'), vm = require('vm');
const nodes = {};
const document = {getElementById(id) {return nodes[id] ||= {value:'', textContent:'', innerHTML:'', hidden:true, addEventListener(){}}}};
document.getElementById('interchangeable-note');
const data = JSON.parse(process.argv[1]);
const fetch = () => Promise.resolve({ok:true, json: () => Promise.resolve(data)});
vm.runInNewContext(fs.readFileSync(process.argv[2], 'utf8'), {document, fetch, Intl, Date, Math, Object, String});
setImmediate(() => console.log(JSON.stringify({note:nodes['interchangeable-note'], footer:nodes['source-times'].textContent})));
'''
    result = subprocess.run(['node', '-e', script, json.dumps(data), str(Path(__file__).resolve().parents[1] / 'site/app.js')],
                            check=True, text=True, encoding='utf-8', capture_output=True)
    rendered = json.loads(result.stdout)
    assert rendered['note']['textContent'] == note
    assert rendered['note']['hidden'] is (not bool(note))
    assert f'Interchangeable medicinal products ({start}–{end}): timestamp' in rendered['footer']
    assert 'Finnish source title' not in rendered['footer']
