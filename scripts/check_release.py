"""GitHub aday dosyalarını, gerçek test kanıtlarını ve kaynakları denetler."""
import ast
from datetime import datetime, timedelta, timezone
import fnmatch
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    from dotenv import dotenv_values
    from app import create_app
    listing = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'],
                             cwd=ROOT, check=True, capture_output=True).stdout.decode('utf-8')
    paths = sorted(set(filter(None, listing.split('\0'))))
    secret_values = [value for key, value in dotenv_values(ROOT / '.env').items()
                     if key in ('SECRET_KEY', 'GOOGLE_BOOKS_API_KEY') and value and len(value) >= 16]
    forbidden, sensitive, source = [], [], []
    app = create_app({'TESTING': True})
    for name in paths:
        path = ROOT / name
        if path.is_dir():
            continue
        parts = path.parts
        blocked = any(part in ('.venv', '.test-tmp', '.ui-tools', 'node_modules', '__pycache__', 'instance', '.pytest_cache') for part in Path(name).parts)
        blocked |= path.name != '.env.example' and (path.name == '.env' or path.name.startswith('.env.'))
        blocked |= any(fnmatch.fnmatch(path.name.lower(), pattern) for pattern in ('*.sqlite*', '*.db', '*.db-*', '*.pem', '*.key', '*.p12', '*.log', '*.pyc'))
        if blocked:
            forbidden.append(name)
        data = path.read_bytes()
        if path.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.gif', '.ico'):
            text = data.decode('utf-8-sig')
            if any(value in text for value in secret_values) or re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|AIza[0-9A-Za-z_-]{30,}|ghp_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,}|AKIA[A-Z0-9]{16}', text):
                sensitive.append(name)
            if path.suffix == '.py':
                tree = ast.parse(text)
                source.append({'file': name, 'sha256': hashlib.sha256(data).hexdigest(),
                               'classes': [item.name for item in ast.walk(tree) if isinstance(item, ast.ClassDef)]})
            elif path.suffix == '.html':
                app.jinja_env.parse(text)
                source.append({'file': name, 'sha256': hashlib.sha256(data).hexdigest()})
            elif path.suffix in ('.css', '.js', '.cjs', '.sql'):
                source.append({'file': name, 'sha256': hashlib.sha256(data).hexdigest()})
    suites = ET.parse(ROOT / 'docs/audit/pytest-stage12.xml')
    cases = []
    for item in suites.iter('testcase'):
        status = 'error' if item.find('error') is not None else 'failed' if item.find('failure') is not None else 'skipped' if item.find('skipped') is not None else 'passed'
        cases.append({'module': item.get('classname'), 'name': item.get('name'), 'seconds': float(item.get('time', '0')), 'status': status})
    counts = {status: sum(item['status'] == status for item in cases) for status in ('passed', 'failed', 'error', 'skipped')}
    seconds = sum(float(item.get('time', '0')) for item in suites.iter('testsuite'))
    browser = json.loads((ROOT / 'docs/screenshots/stage12/ui-test-result.json').read_text(encoding='utf-8'))
    setup = json.loads((ROOT / 'docs/audit/setup-stage12.json').read_text(encoding='utf-8'))
    google = json.loads((ROOT / 'docs/audit/google-books-stage12.json').read_text(encoding='utf-8'))
    links = json.loads((ROOT / 'docs/audit/documentation-links-stage12.json').read_text(encoding='utf-8'))
    diagrams = json.loads((ROOT / 'docs/audit/diagrams-stage12.json').read_text(encoding='utf-8'))
    export = json.loads((ROOT / 'docs/audit/export-stage12.json').read_text(encoding='utf-8'))
    checks = {'candidate_files_allowed': not forbidden, 'no_detected_secrets': not sensitive,
              'pytest': bool(cases) and not any(counts[key] for key in ('failed', 'error', 'skipped')),
              'browser': browser.get('auditStage') == 12 and browser.get('status') == 'passed' and not browser.get('javascriptErrors'),
              'clean_install_setup': setup.get('status') == 'passed',
              'documentation_links': links.get('status') == 'passed',
              'mermaid_diagrams': diagrams.get('status') == 'passed',
              'git_export_install': export.get('status') == 'passed'}
    report = {'executed_at': datetime.now(timezone(timedelta(hours=3))).isoformat(),
              'status': 'passed' if all(checks.values()) else 'failed', 'checks': checks,
              'candidate_files': len(paths), 'forbidden_files': forbidden, 'detected_secret_files': sensitive,
              'pytest': {**counts, 'total': len(cases), 'suite_seconds': seconds},
              'browser_checks': browser.get('checks'), 'google_books_status': google.get('status'),
              'release_tag_ready': google.get('status') == 'passed' and all(checks.values()),
              'limits': ['Fiziksel telefon, ekran okuyucu ve Firefox/Safari denemeleri yürütülmedi.',
                         'Yeni kurulum aynı Windows makinesinde temiz ortamda doğrulandı; ikinci fiziksel bilgisayar denenmedi.',
                         'Gizli değer taraması kapsamlı bir güvenlik sertifikası değildir.'],
              'source_inventory': source, 'test_cases': cases}
    (ROOT / 'docs/audit/release-stage12.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('status', 'candidate_files', 'checks', 'pytest', 'browser_checks', 'release_tag_ready')}, ensure_ascii=True))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
