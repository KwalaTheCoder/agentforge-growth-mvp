"""AgentForge v4.2: local manual task board, separate from prospect CRM."""
from contextlib import contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
import sqlite3
from urllib.parse import urlparse

DB = Path(__file__).resolve().parent / 'operations.sqlite3'
OWNERS = ('Founder 1', 'Founder 2')
STATUSES = ('Todo', 'In progress', 'Blocked', 'Done')
KINDS = ('Company research', 'Evidence verification', 'Proposal review', 'Manual follow-up', 'Internal operations')

@contextmanager
def connection(path=None):
    target = Path(path) if path is not None else DB
    con = sqlite3.connect(target, timeout=10)
    con.row_factory = sqlite3.Row
    try:
        con.execute('PRAGMA busy_timeout=10000')
        con.execute('''CREATE TABLE IF NOT EXISTS growth_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL, owner TEXT NOT NULL, kind TEXT NOT NULL,
            status TEXT NOT NULL, due_date TEXT NOT NULL DEFAULT '',
            source_url TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''')
        con.commit()
        yield con
        con.commit()
    except Exception:
        con.rollback()
        raise
    finally:
        con.close()

def validate(title, owner, kind, status, due_date='', source_url='', notes=''):
    title = str(title).strip()
    if not title or len(title) > 180:
        raise ValueError('Task title must be 1–180 characters.')
    if owner not in OWNERS or kind not in KINDS or status not in STATUSES:
        raise ValueError('Invalid owner, category or status.')
    due_date = str(due_date or '').strip()
    if due_date:
        try:
            parsed = date.fromisoformat(due_date)
        except ValueError:
            raise ValueError('Due date must use YYYY-MM-DD.') from None
        if parsed.isoformat() != due_date:
            raise ValueError('Due date must use YYYY-MM-DD.')
    source_url = str(source_url or '').strip()
    if source_url:
        try:
            parsed = urlparse(source_url)
            if parsed.scheme not in ('https', 'http') or not parsed.hostname or parsed.username or parsed.password:
                raise ValueError('Source must be a public HTTP(S) URL without credentials.')
        except ValueError:
            raise ValueError('Source must be a public HTTP(S) URL without credentials.') from None
    if len(source_url) > 1000 or len(str(notes)) > 3000:
        raise ValueError('Source URL or notes too long.')
    return (title, owner, kind, status, due_date, source_url, str(notes))

def create_task(title, owner, kind, due_date='', source_url='', notes='', path=None):
    vals = validate(title, owner, kind, 'Todo', due_date, source_url, notes)
    now = datetime.now(timezone.utc).isoformat()
    with connection(path) as con:
        cursor = con.execute('''INSERT INTO growth_tasks
            (title,owner,kind,status,due_date,source_url,notes,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?)''', (*vals, now, now))
        return cursor.lastrowid

def list_tasks(path=None):
    with connection(path) as con:
        return [dict(r) for r in con.execute('SELECT * FROM growth_tasks ORDER BY id DESC')]

def update_task(task_id, *, owner, status, due_date='', notes='', path=None):
    task_id = int(task_id)
    with connection(path) as con:
        row = con.execute('SELECT * FROM growth_tasks WHERE id=?', (task_id,)).fetchone()
        if row is None:
            raise ValueError('Task not found.')
        vals = validate(row['title'], owner, row['kind'], status, due_date, row['source_url'], notes)
        con.execute('''UPDATE growth_tasks SET owner=?,status=?,due_date=?,notes=?,updated_at=? WHERE id=?''',
                    (vals[1], vals[3], vals[4], vals[6], datetime.now(timezone.utc).isoformat(), task_id))

def summarize(tasks, today=None):
    today = today or date.today()
    active = [t for t in tasks if t['status'] != 'Done']
    due = [t for t in active if t['due_date'] and date.fromisoformat(t['due_date']) <= today]
    return {'total':len(tasks),'open':len(active),'due':len(due),
            'overdue':sum(date.fromisoformat(t['due_date']) < today for t in due),
            'by_owner':{owner:sum(t['owner']==owner for t in active) for owner in OWNERS}}
