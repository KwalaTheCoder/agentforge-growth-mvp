"""Read-only local security audit. Does not inspect or print secret values."""
import argparse
import json
import os
from pathlib import Path
try:
    import tomllib
except ImportError:
    tomllib=None

PROJECT_ROOT=Path(__file__).resolve().parents[1]
SENSITIVE_PATHS=('leads.sqlite3','leads.sqlite3-wal','leads.sqlite3-shm',
                 '.env','.streamlit/secrets.toml','backups/')
def _gitignore_coverage(root):
    path=root/'.gitignore'
    if not path.is_file():
        return False, ['Missing .gitignore']
    rules=[]
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        s=line.strip()
        if s and not s.startswith('#') and not s.startswith('!'):
            rules.append(s.replace('\\','/').lstrip('/'))
    required={'leads.sqlite3','leads.sqlite3-wal','leads.sqlite3-shm',
              '.env','.streamlit/secrets.toml','backups/'}
    missing=sorted(required-set(rules))
    return not missing,missing
def audit(root=PROJECT_ROOT):
    root=Path(root)
    checks=[]
    def add(name,passed,detail):
        checks.append({'check':name,'passed':bool(passed),'detail':detail})
    ok,missing=_gitignore_coverage(root)
    add('gitignore_sensitive_paths',ok,
        'Sensitive file patterns present' if ok else 'Missing ignore patterns: '+', '.join(missing))
    config=root/'.streamlit/config.toml'
    if not config.is_file():
        add('streamlit_binding',False,'No explicit Streamlit bind address; start with --server.address 127.0.0.1')
    elif tomllib is None:
        add('streamlit_binding',False,'Cannot parse config; Python 3.11+ needed')
    else:
        try:
            data=tomllib.loads(config.read_text(encoding='utf-8-sig'))
            server=data.get('server',{})
            addr=str(server.get('address','')).strip()
            add('streamlit_binding',addr in ('127.0.0.1','localhost'),
                'Explicit loopback binding' if addr in ('127.0.0.1','localhost')
                else 'Address not explicitly loopback; CLI and environment overrides must be checked')
            add('streamlit_cors_xsrf',server.get('enableCORS',True) is not False and
                server.get('enableXsrfProtection',True) is not False,
                'CORS and XSRF not explicitly disabled' if server.get('enableCORS',True) is not False and
                server.get('enableXsrfProtection',True) is not False else 'CORS or XSRF disabled')
        except (ValueError,UnicodeError) as exc:
            add('streamlit_binding',False,'Cannot parse Streamlit config: '+type(exc).__name__)
    add('backup_folder',True,'Backups are sensitive: keep local, private, and excluded from version control')
    add('outreach',True,'Manual verification required: audit cannot prove that no external messages are sent')
    return {'root':str(root),'passed':sum(c['passed'] for c in checks),
            'total':len(checks),'checks':checks,'ready_for_local_review':all(
                c['passed'] for c in checks if c['check'] not in ('backup_folder','outreach'))}
def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',default=str(PROJECT_ROOT))
    args=parser.parse_args()
    result=audit(args.root)
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['ready_for_local_review'] else 1
if __name__=='__main__':
    raise SystemExit(main())
