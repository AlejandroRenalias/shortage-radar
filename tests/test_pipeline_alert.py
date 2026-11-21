import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import pipeline_alert


def test_success_keeps_other_failure_open(monkeypatch):
    for k, v in {'GITHUB_REPOSITORY': 'owner/repo', 'PIPELINE': 'pages', 'RESULT': 'success', 'GITHUB_SERVER_URL': 'https://github.com', 'GITHUB_RUN_ID': '5'}.items():
        monkeypatch.setenv(k, v)
    issue = {'title': 'Scheduled data pipeline failure', 'number': 4, 'body': '<!-- pipeline-state:{"archive":"https://example.com/run","pages":"https://example.com/old"} -->'}
    calls = []
    def fake(*args, data=None):
        calls.append((args, data))
        return [issue] if data is None else None
    monkeypatch.setattr(pipeline_alert, 'gh', fake)
    pipeline_alert.main()
    assert calls[-1][1]['state'] == 'open'
    assert 'https://example.com/run' in calls[-1][1]['body']
    assert 'https://example.com/old' not in calls[-1][1]['body']
    monkeypatch.setenv('PIPELINE', 'archive')
    issue['body'] = calls[-1][1]['body']
    pipeline_alert.main()
    assert calls[-1][1]['state'] == 'closed'
