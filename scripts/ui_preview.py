"""Arayüz testleri için yalnızca .test-tmp altında bağımsız yerel sunucu."""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from app import create_app
from database import init_db,get_db
from seed import seed_demo
from services.demo_accounts import prepare_demo_accounts

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--database',required=True)
    parser.add_argument('--port',type=int,default=5001)
    args=parser.parse_args()
    path=Path(args.database).resolve()
    if not path.is_relative_to(ROOT/'.test-tmp'):
        parser.error('Arayüz test veritabanı .test-tmp içinde olmalıdır.')
    app=create_app({'DATABASE':str(path)})
    with app.app_context():
        init_db()
        seed_demo(get_db())
        prepare_demo_accounts(get_db())
    app.run(host='127.0.0.1',port=args.port)
