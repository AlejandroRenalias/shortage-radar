import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import latest_check


def test_stops_after_newest_successful_archive(monkeypatch, capsys):
    monkeypatch.setenv('GITHUB_REPOSITORY', 'owner/repo')
    calls = []
    def api(path):
        calls.append(path)
        if '/workflows/' in path:
            return {'workflow_runs': [{'id': 3}, {'id': 2}, {'id': 1}]}
        if '/3/' in path:
            return {'jobs': [{'name': 'archive', 'conclusion': 'failure', 'completed_at': None}]}
        if '/2/' in path:
            return {'jobs': [{'name': 'archive', 'conclusion': 'success', 'completed_at': '2026-11-21T23:00:00Z'}]}
        raise AssertionError('Older run should not be queried')
    monkeypatch.setattr(latest_check, 'api', api)
    latest_check.main()
    assert capsys.readouterr().out.strip() == '2026-11-22'
    assert len(calls) == 3
