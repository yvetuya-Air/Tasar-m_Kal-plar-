"""Depodaki Markdown bağlantılarını ve belge gizliliğini yerel olarak denetler."""
import argparse
from datetime import datetime, timedelta, timezone
from html import unescape
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def prose(text):
    lines = []
    fence = None
    for line in text.splitlines():
        match = re.match(r'^\s*(`{3,}|~{3,})', line)
        if match:
            marker = match.group(1)[0]
            fence = None if fence == marker else marker if fence is None else fence
            lines.append('')
        else:
            lines.append(line if fence is None else '')
    return '\n'.join(lines)


def headings(text):
    result, counts = set(), {}
    for line in prose(text).splitlines():
        match = re.match(r'^#{1,6}\s+(.+?)\s*#*$', line)
        if match:
            title = re.sub(r'<[^>]+>', '', unescape(match.group(1))).lower()
            title = re.sub(r'[^\w\-\s]', '', title, flags=re.UNICODE).replace(' ', '-')
            number = counts.get(title, 0)
            counts[title] = number + 1
            result.add(title + (f'-{number}' if number else ''))
    result.update(re.findall(r'\b(?:id|name)=["\']([^"\']+)', text))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--online', action='store_true', help='Harici HTTPS bağlantılarını da GET ile doğrula.')
    parser.add_argument('--stage', type=int, default=11)
    args = parser.parse_args()
    output = ROOT / f'docs/audit/documentation-links-stage{args.stage}.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text('{"status":"running"}', encoding='utf-8')
    files = [ROOT / 'README.md'] + sorted((ROOT / 'docs').rglob('*.md'))
    errors, links, external = [], [], set()
    texts = {path: path.read_text(encoding='utf-8-sig') for path in files}
    for path, text in texts.items():
        clean = prose(text)
        for match in re.finditer(r'!?\[[^\]\n]*(?:\][^\(\n][^\]\n]*)?\]\((<[^>]+>|[^\s)]+)(?:\s+"[^"]*")?\)', clean):
            target = unescape(match.group(1).strip('<>'))
            record = {'file': path.relative_to(ROOT).as_posix(), 'target': target}
            parsed = urlsplit(target)
            if parsed.scheme in ('http', 'https'):
                external.add(target)
                record['status'] = 'external'
            elif parsed.scheme:
                record['status'] = 'unsupported'
                errors.append(record)
            else:
                destination = (path.parent / unquote(parsed.path)).resolve() if parsed.path else path
                record['status'] = 'ok'
                if not destination.is_relative_to(ROOT) or not destination.exists():
                    record['status'] = 'missing'
                elif parsed.fragment and destination.suffix.lower() == '.md':
                    if unquote(parsed.fragment) not in headings(destination.read_text(encoding='utf-8-sig')):
                        record['status'] = 'missing_anchor'
                if record['status'] != 'ok':
                    errors.append(record)
            links.append(record)
    # Yerel gizli değerler yalnız eşitlik karşılaştırması için okunur; çıktıya yazılmaz.
    from dotenv import dotenv_values
    secrets = [value for key, value in dotenv_values(ROOT / '.env').items()
               if key in ('SECRET_KEY', 'GOOGLE_BOOKS_API_KEY') and value and len(value) >= 16]
    sensitive = []
    audit_texts = dict(texts)
    for path in (ROOT / 'docs').rglob('*'):
        if path.is_file() and path.suffix.lower() in ('.json', '.xml', '.mmd', '.svg'):
            audit_texts[path] = path.read_text(encoding='utf-8-sig')
    for path, text in audit_texts.items():
        if any(secret in text for secret in secrets) or re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|AIza[0-9A-Za-z_-]{30,}', text):
            sensitive.append(path.relative_to(ROOT).as_posix())
    online = []
    if args.online:
        for url in sorted(external):
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'LibraryDocumentationCheck/1.0'})
                with urllib.request.urlopen(req, timeout=20) as response:
                    online.append({'url': url, 'status': response.status})
            except Exception as error:
                online.append({'url': url, 'status': 'failed', 'reason': type(error).__name__})
    failed_online = [item for item in online if item['status'] == 'failed']
    report = {
        'executed_at': datetime.now(timezone(timedelta(hours=3))).isoformat(),
        'markdown_files': len(files), 'links': len(links), 'local_errors': errors,
        'secret_exposure_files': sensitive, 'external_checked': args.online,
        'external_results': online, 'external_pending': [] if args.online else sorted(external),
        'status': 'passed' if not errors and not sensitive and not failed_online else 'failed',
    }
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=True))
    return 0 if report['status'] == 'passed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
