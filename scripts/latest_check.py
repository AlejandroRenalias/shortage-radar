"""Find the latest successful archive job, including runs whose deployment failed."""
import json
import os
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo


def api(path):
    return json.loads(subprocess.check_output(['gh', 'api', path], text=True))


def main():
    repo = os.environ['GITHUB_REPOSITORY']
    runs = api(f'repos/{repo}/actions/workflows/archive.yml/runs?branch=main&per_page=100')['workflow_runs']
    for run in runs:
        jobs = api(f"repos/{repo}/actions/runs/{run['id']}/jobs?per_page=100")['jobs']
        for job in jobs:
            if job['name'] == 'archive' and job['conclusion'] == 'success' and job['completed_at']:
                completed = datetime.fromisoformat(job['completed_at'].replace('Z', '+00:00'))
                print(completed.astimezone(ZoneInfo('Europe/Helsinki')).date().isoformat())
                return



if __name__ == '__main__':
    main()
