"""Kurulum komutlarını temiz kaynak kopyasında ve bağımsız SQLite ile sınar."""
import argparse
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--python', type=Path, default=Path(sys.executable))
    parser.add_argument('--stage', type=int, default=11)
    args = parser.parse_args()
    python = str(args.python.resolve())
    child_env = {**os.environ, 'PYTHONIOENCODING': 'utf-8'}
    target = ROOT / '.test-tmp' / (f'docs{args.stage}-setup-' + uuid4().hex)
    target.mkdir(parents=True)
    for name in ('app.py', 'config.py', 'database.py', 'security.py', 'seed.py', 'schema.sql', 'requirements.txt', '.env.example'):
        shutil.copy2(ROOT / name, target / name)
    for name in ('models', 'patterns', 'routes', 'services', 'templates', 'static'):
        shutil.copytree(ROOT / name, target / name, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(target / '.env.example', target / '.env')
    secret = secrets.token_hex(32)
    env_text = (target / '.env').read_text(encoding='utf-8').replace('SECRET_KEY=\n', 'SECRET_KEY=' + secret + '\n')
    (target / '.env').write_text(env_text, encoding='utf-8')
    steps = []
    commands = [
        ['-m', 'pip', 'check'],
        ['-c', 'import secrets; assert len(secrets.token_hex(32)) == 64'],
        *[['-m', 'flask', '--app', 'app:create_app', command]
          for command in ('init-db', 'seed-demo', 'demo-accounts', 'check-db',
                          'init-db', 'seed-demo', 'demo-accounts', 'check-db')],
        ['-m', 'flask', '--app', 'app:create_app', 'run', '--help'],
    ]
    for command in commands:
        result = subprocess.run([python, *command], cwd=target, env=child_env, capture_output=True, text=True, encoding='utf-8', timeout=60)
        steps.append({'command': 'python ' + ' '.join(command), 'exit_code': result.returncode,
                      'stdout': result.stdout.strip(), 'stderr': result.stderr.strip()})
        if result.returncode:
            break
    code = '''
import json,re
from app import create_app
from database import get_db
app=create_app({'TESTING':True})
with app.app_context():
    db=get_db()
    counts={t:db.execute('SELECT COUNT(*) FROM '+t).fetchone()[0] for t in ('users','members','books','categories','loans','reservations','notifications')}
    assert counts=={'users':2,'members':3,'books':2,'categories':1,'loans':2,'reservations':1,'notifications':1}
client=app.test_client()
page=client.get('/giris')
assert page.status_code==200
token=re.search(rb'name="csrf_token" value="([^"]+)"',page.data).group(1).decode()
response=client.post('/giris',data={'csrf_token':token,'username':'demo_yonetici','password':'DemoYonetici!2026'})
assert response.status_code==302
for path in ('/panel','/kitaplar','/uyeler','/odunc','/rezervasyonlar','/bildirimler','/tasarim-kaliplari','/ayarlar'):
    assert client.get(path).status_code==200,path
print(json.dumps({'tables':counts,'admin_login':302,'private_pages':8}))
'''
    if all(item['exit_code'] == 0 for item in steps):
        result = subprocess.run([python, '-c', code], cwd=target, env=child_env, capture_output=True, text=True, encoding='utf-8', timeout=60)
        steps.append({'command': 'Yalıtılmış demo giriş ve özel sayfa kontrolü', 'exit_code': result.returncode,
                      'stdout': result.stdout.strip(), 'stderr': result.stderr.strip()})
    report = {'executed_at': datetime.now(timezone(timedelta(hours=3))).isoformat(),
              'independent_database': True, 'source_copy': target.relative_to(ROOT).as_posix(),
              'status': 'passed' if all(item['exit_code'] == 0 for item in steps) else 'failed', 'steps': steps,
              'limits': ['Python/Git grafik kurucuları ve uzak git clone yürütülmedi.',
                         'run --help CLI seçeneklerini denetler; canlı sunucu ayrıca doğrulandı.']}
    output = ROOT / f'docs/audit/setup-stage{args.stage}.json'
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'status': report['status'], 'steps': len(steps)}, ensure_ascii=True))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
