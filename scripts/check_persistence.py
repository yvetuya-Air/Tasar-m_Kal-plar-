"""Sunucu yeniden başlatma denetimi: veriyi değiştirmeden tablo özetlerini karşılaştırır."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3

ROOT=Path(__file__).resolve().parents[1]
TABLES=('users','members','books','categories','loans','reservations','notifications','activity_logs')


def snapshot(database):
    result={}
    with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True) as db:
        db.execute('BEGIN')
        for table in TABLES:
            rows=db.execute(f'SELECT * FROM {table} ORDER BY id').fetchall()
            payload=json.dumps(rows,ensure_ascii=True,separators=(',',':')).encode('ascii')
            result[table]={'count':len(rows),'sha256':hashlib.sha256(payload).hexdigest()}
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=('capture','verify'))
    parser.add_argument('--database',type=Path,default=ROOT/'instance'/'library.sqlite3')
    parser.add_argument('--snapshot',type=Path,required=True)
    args=parser.parse_args()
    target=args.snapshot.resolve()
    if not target.is_relative_to(ROOT/'.test-tmp'):
        parser.error('Denetim özeti .test-tmp altında olmalıdır.')
    actual=snapshot(args.database)
    if args.mode=='capture':
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(actual,indent=2),encoding='utf-8')
        print('RESTART_SNAPSHOT_CAPTURED')
    else:
        expected=json.loads(target.read_text(encoding='utf-8'))
        if actual!=expected:
            raise SystemExit('RESTART_DATA_CHANGED: tablo veya kayıtlar değişti; inceleme gerekir.')
        print('RESTART_PERSISTENCE_VERIFIED: all 8 table counts and row digests match')
