"""Akademik UML/ER ve kod bloklarını gerçek kaynaklardan eşitler."""
import argparse
import ast
from pathlib import Path
import re
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
FILES = ['models/book.py', 'patterns/factory_method.py', 'patterns/adapter.py',
         'patterns/open_library_adapter.py', 'patterns/strategy.py', 'patterns/observer.py',
         'services/google_books_api.py', 'services/open_library_api.py',
         'services/notification_service.py']


def sources():
    classes = {}
    for filename in FILES:
        text = (ROOT / filename).read_text(encoding='utf-8-sig')
        for node in ast.parse(text).body:
            if isinstance(node, ast.ClassDef):
                classes[node.name] = (filename, text, node)
    return classes


def uml(classes, names, relations):
    lines = ['classDiagram', '    direction TB']
    for name in names:
        node = classes[name][2]
        lines.append(f'    class {name} {{')
        abstract = any(isinstance(item, ast.FunctionDef) and any(
            ast.unparse(dec) == 'abstractmethod' for dec in item.decorator_list)
            for item in node.body)
        if abstract:
            lines.append('        <<abstract>>')
        for item in node.body:
            if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                lines.append(f'        +{item.target.id}')
            elif isinstance(item, ast.FunctionDef) and (not item.name.startswith('_') or item.name == '__init__'):
                arguments = [arg.arg for arg in item.args.posonlyargs + item.args.args + item.args.kwonlyargs
                             if arg.arg not in ('self', 'cls')]
                if item.args.kwarg:
                    arguments.append('data')
                lines.append(f'        +{item.name}({", ".join(arguments)})')
        lines.append('    }')
    for name in names:
        for base in classes[name][2].bases:
            parent = ast.unparse(base)
            if parent in names:
                lines.append(f'    {parent} <|-- {name}')
    lines.extend('    ' + relation for relation in relations)
    return '\n'.join(lines) + '\n'


def snippet(classes, name):
    filename, text, node = classes[name]
    start = min([node.lineno] + [dec.lineno for dec in node.decorator_list])
    code = '\n'.join(text.splitlines()[start - 1:node.end_lineno])
    return f'Kaynak: [{filename}](../{filename}), `{name}`.\n\n```python\n{code}\n```'


def er_diagram():
    with sqlite3.connect(':memory:') as db:
        db.executescript((ROOT / 'schema.sql').read_text(encoding='utf-8'))
        tables = [row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        lines = ['erDiagram']
        relationships = []
        for table in tables:
            columns = db.execute(f'PRAGMA table_info({table})').fetchall()
            foreign = {row[3]: row[2] for row in db.execute(f'PRAGMA foreign_key_list({table})')}
            lines.append(f'    {table} {{')
            for _, name, kind, required, _, primary in columns:
                key = ' PK' if primary else ' FK' if name in foreign else ''
                lines.append(f'        {kind.lower()} {name}{key}')
                if name in foreign:
                    parent_end = '||' if required else '|o'
                    child_end = 'o|' if table == 'members' and name == 'user_id' else 'o{'
                    relationships.append(f'    {foreign[name]} {parent_end}--{child_end} {table} : {name}')
            lines.append('    }')
        lines.extend(relationships)
    return '\n'.join(lines) + '\n'


def route_table():
    from app import create_app
    app = create_app({'TESTING': True})
    lines = ['| Yol | Yöntemler | Endpoint |', '| --- | --- | --- |']
    for rule in sorted(app.url_map.iter_rules(), key=lambda value: value.rule):
        path = rule.rule.replace('<', '&lt;').replace('>', '&gt;')
        methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
        lines.append(f'| {path} | {methods} | {rule.endpoint} |')
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    classes = sources()
    specs = {
        'factory': (['Book', 'PhysicalBook', 'EBook', 'AudioBook', 'BookCreator',
                     'PhysicalBookCreator', 'EBookCreator', 'AudioBookCreator'],
                    ['BookCreator ..> Book : ürün sözleşmesi', 'PhysicalBookCreator ..> PhysicalBook : oluşturur',
                     'EBookCreator ..> EBook : oluşturur', 'AudioBookCreator ..> AudioBook : oluşturur'],
                    ['BookCreator', 'PhysicalBookCreator', 'EBookCreator', 'AudioBookCreator']),
        'adapter': (['BookDataProvider', 'GoogleBooksAPI', 'OpenLibraryAPI', 'GoogleBooksAdapter',
                     'OpenLibraryAdapter', 'BookImportData', 'BookSearchPage'],
                    ['GoogleBooksAdapter --> GoogleBooksAPI : api', 'OpenLibraryAdapter --> OpenLibraryAPI : api',
                     'GoogleBooksAdapter ..> BookImportData : dönüştürür',
                     'OpenLibraryAdapter ..> BookImportData : dönüştürür', 'BookSearchPage o-- BookImportData : sonuçlar'],
                    ['BookDataProvider', 'BookImportData']),
        'strategy': (['PenaltyStrategy', 'StudentPenalty', 'TeacherPenalty', 'StandardPenalty', 'PenaltyCalculator'],
                     ['PenaltyCalculator --> PenaltyStrategy : değiştirilebilir strateji'],
                     ['StudentPenalty', 'TeacherPenalty', 'StandardPenalty', 'PenaltyCalculator']),
        'observer': (['Observer', 'Subject', 'BookAvailabilitySubject', 'MemberObserver', 'NotificationService'],
                     ['BookAvailabilitySubject --> Observer : gözlemciler', 'MemberObserver --> NotificationService : update devri',
                      'NotificationService ..> BookAvailabilitySubject : yayın'],
                     ['BookAvailabilitySubject', 'MemberObserver']),
    }
    outputs = {}
    blocks = {}
    for key, (names, relations, examples) in specs.items():
        diagram = uml(classes, names, relations)
        outputs[f'docs/diagrams/{key}.mmd'] = diagram
        examples_text = '\n\n'.join(snippet(classes, name) for name in examples)
        if key == 'adapter':
            filename, text, node = classes['GoogleBooksAdapter']
            method = next(item for item in node.body if isinstance(item, ast.FunctionDef) and item.name == 'adapt')
            code = '\n'.join(text.splitlines()[method.lineno - 1:method.end_lineno])
            examples_text += f'\n\nKaynak: [{filename}](../{filename}), `GoogleBooksAdapter.adapt`.\n\n```python\n{code}\n```'
        blocks[key] = '```mermaid\n' + diagram + '```\n\n' + examples_text
    er = er_diagram()
    outputs['docs/diagrams/er.mmd'] = er
    # Önceki belgelerdeki bağlantıları koru.
    outputs['docs/diagrams/veritabani.mmd'] = er
    outputs['docs/diagrams/factory_method.mmd'] = outputs['docs/diagrams/factory.mmd']
    blocks['er'] = '```mermaid\n' + er + '```'
    blocks['routes'] = route_table()
    for filename in ['docs/TASARIM_KALIPLARI.md', 'docs/MIMARI.md']:
        content = (ROOT / filename).read_text(encoding='utf-8')
        for key, body in blocks.items():
            pattern = rf'<!-- SOURCE:{key} -->.*?<!-- END:{key} -->'
            content = re.sub(pattern, lambda _: f'<!-- SOURCE:{key} -->\n\n{body}\n\n<!-- END:{key} -->', content, flags=re.S)
        outputs[filename] = content
    changed = []
    for filename, content in outputs.items():
        path = ROOT / filename
        if not path.exists() or path.read_text(encoding='utf-8') != content:
            changed.append(filename)
            if not args.check:
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding='utf-8')
    print(('STALE: ' if args.check and changed else 'SOURCE_DOCS_OK: ') + ', '.join(changed or ['unchanged']))
    return 1 if args.check and changed else 0


if __name__ == '__main__':
    raise SystemExit(main())
