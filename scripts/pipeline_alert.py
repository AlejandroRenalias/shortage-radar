"""Maintain one issue containing the outstanding scheduled pipeline failures."""
import json
import os
import subprocess


def gh(*args, data=None):
    result = subprocess.run(['gh', *args], input=json.dumps(data) if data is not None else None,
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout) if result.stdout.strip() else None


def main():
    repo = os.environ['GITHUB_REPOSITORY']
    pipeline = os.environ['PIPELINE']
    result = os.environ['RESULT']
    run = f"{os.environ['GITHUB_SERVER_URL']}/{repo}/actions/runs/{os.environ['GITHUB_RUN_ID']}"
    issues = gh('api', f'repos/{repo}/issues?state=open&labels=data-pipeline&per_page=100')
    issue = next((i for i in issues if i['title'] == 'Scheduled data pipeline failure' and 'pull_request' not in i), None)
    failures = {}
    if issue:
        marker = next((line for line in issue['body'].splitlines() if line.startswith('<!-- pipeline-state:')), None)
        if marker:
            failures = json.loads(marker.removeprefix('<!-- pipeline-state:').removesuffix(' -->'))
    if result == 'success':
        failures.pop(pipeline, None)
    else:
        failures[pipeline] = run
    if not issue and not failures:
        return
    if not issue:
        subprocess.run(['gh', 'label', 'create', 'data-pipeline', '--repo', repo, '--force'], check=True)
    body = 'Scheduled pipeline failures needing attention:\n\n' + ''.join(f'- {name}: {url}\n' for name, url in sorted(failures.items()))
    body += '\n<!-- pipeline-state:' + json.dumps(failures, separators=(',', ':')) + ' -->'
    if issue:
        gh('api', '--method', 'PATCH', f"repos/{repo}/issues/{issue['number']}", '--input', '-', data={'body': body, 'state': 'open' if failures else 'closed'})
    else:
        gh('api', '--method', 'POST', f'repos/{repo}/issues', '--input', '-', data={'title': 'Scheduled data pipeline failure', 'body': body, 'labels': ['data-pipeline']})


if __name__ == '__main__':
    main()
