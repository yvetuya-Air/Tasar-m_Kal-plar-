"""Test sonuçlarını değiştirmeden yayımlanan XML'den makine adını çıkarır."""
from pathlib import Path
import sys
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


if __name__ == '__main__':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    backup = ROOT / '.test-tmp/junit-private-originals'
    backup.mkdir(parents=True, exist_ok=True)
    changed = []
    for path in (ROOT / 'docs/audit').glob('pytest-*.xml'):
        original = path.read_bytes()
        tree = ET.fromstring(original)
        before = [ET.tostring(item) for item in tree.iter('testcase')]
        if not any('hostname' in item.attrib for item in tree.iter()):
            continue
        target = backup / path.name
        if not target.exists():
            target.write_bytes(original)
        for item in tree.iter():
            item.attrib.pop('hostname', None)
        assert before == [ET.tostring(item) for item in tree.iter('testcase')]
        ET.ElementTree(tree).write(path, encoding='utf-8', xml_declaration=True)
        changed.append(path.name)
    print('Yalnız makine adı kaldırıldı: ' + ', '.join(changed))
