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


def test_stale_source_opens_the_issue_and_a_fresh_one_closes_it(monkeypatch):
    """The maintainer's alert for an old Fimea file or register, and for a register source that cannot be used."""
    for k, v in {'GITHUB_REPOSITORY': 'owner/repo', 'PIPELINE': 'source-stale', 'RESULT': 'failure', 'GITHUB_SERVER_URL': 'https://github.com', 'GITHUB_RUN_ID': '9'}.items():
        monkeypatch.setenv(k, v)
    issue, calls = None, []
    def fake(*args, data=None):
        calls.append((args, data))
        return ([issue] if issue else []) if data is None and args[0] == 'api' and 'issues?state=open' in args[1] else None
    monkeypatch.setattr(pipeline_alert, 'gh', fake)
    monkeypatch.setattr(pipeline_alert.subprocess, 'run', lambda *a, **k: None)
    pipeline_alert.main()
    created = calls[-1][1]
    assert created['title'] == 'Scheduled data pipeline failure'
    assert 'source-stale: https://github.com/owner/repo/actions/runs/9' in created['body'] and 'more than 2 days old' in created['body']
    issue = {'title': created['title'], 'number': 7, 'body': created['body']}
    monkeypatch.setenv('RESULT', 'success')
    pipeline_alert.main()
    assert calls[-1][1]['state'] == 'closed'


def test_the_archive_workflow_reports_register_and_age_outcomes():
    text = (Path(__file__).resolve().parents[1] / '.github/workflows/archive.yml').read_text(encoding='utf-8')
    assert 'python scripts/source_age.py' in text
    assert 'PIPELINE=source-stale' in text and 'PIPELINE=register-source' in text
