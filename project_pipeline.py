"""Offline CSV intake and conservative project triage; never verifies offers."""
import csv
import hashlib
import io
import re
import sqlite3
from urllib.parse import urlparse

REQUIRED = ('title','source_url','description')
CONTRACT = re.compile(r'\b(freelanc(?:e|er)|contractor|contract work|fixed.price|project.based|paid bounty|paid project|statement of work|sow)\b', re.I)
EMPLOYMENT = re.compile(r'\b(full.time|permanent|salaried|staff software engineer|employee benefits|w.2|full time employee)\b', re.I)
BUDGET = re.compile(r'(?:[$€£]\s?\d[\d,.]*|\b(?:budget|fixed price|hourly rate|paid bounty|payment)\b)', re.I)
SKILLS = {'AI / Automation': r'\b(ai|llm|agent|automation|machine learning|chatbot)\b',
          'Python / Backend':r'\b(python|fastapi|django|backend|api|postgres)\b',
          'Full-stack / Web':r'\b(react|next\.?js|frontend|full.stack|website|web app)\b',
          'DevOps / Cloud':r'\b(devops|docker|kubernetes|ci/cd|cloud|terraform)\b',
          'Cybersecurity':r'\b(security|pentest|hardening|vulnerability)\b'}

def qualify(row):
    title = str(row.get('title') or '')
    description = str(row.get('description') or row.get('body') or '')
    text = title + '\n' + description + '\n' + str(row.get('contract_type') or '')
    signals, gaps = [], []
    employment = bool(EMPLOYMENT.search(text))
    contract = bool(CONTRACT.search(text))
    budget = bool(str(row.get('budget') or '').strip()) or bool(BUDGET.search(text))
    services = [name for name, pattern in SKILLS.items() if re.search(pattern,text,re.I)]
    score = 10
    if contract: score += 30; signals.append('Contract/freelance wording')
    else: gaps.append('No explicit independent contract signal')
    if budget: score += 20; signals.append('Budget/payment wording (not verified)')
    else: gaps.append('No budget/payment evidence')
    if services: score += 20; signals.append('Skill match: ' + ', '.join(services[:3]))
    else: gaps.append('No clear skill match')
    if str(row.get('application_url') or '').startswith('https://'): score += 10; signals.append('Application URL provided (not verified)')
    else: gaps.append('Application channel not verified')
    if str(row.get('location') or '').strip(): signals.append('Location field supplied (eligibility unverified)')
    else: gaps.append('Geographic eligibility unknown')
    if not services:
        score = min(score, 30)
    if employment:
        score = min(score, 15)
        signals.append('Employment wording detected')
    score = max(0,min(100,score))
    return {'score':score, 'priority':'Review' if score>=60 and not employment else ('Low — employment' if employment else 'Research'),
            'signals':signals, 'gaps':gaps, 'services':services, 'employment':employment}

def import_project_csv(raw):
    if len(raw)>2_000_000: raise ValueError('CSV exceeds 2 MB')
    try: text=raw.decode('utf-8-sig')
    except UnicodeDecodeError: raise ValueError('CSV must be UTF-8')
    reader=csv.DictReader(io.StringIO(text))
    if not reader.fieldnames or any(c not in reader.fieldnames for c in REQUIRED):
        raise ValueError('Required columns: title, source_url, description')
    result=[]; seen=set()
    for idx, row in enumerate(reader):
        if idx>=500: raise ValueError('Maximum 500 rows per import')
        title=(row.get('title') or '').strip()[:300]
        url=(row.get('source_url') or '').strip()
        desc=(row.get('description') or '').strip()[:5000]
        parsed=urlparse(url)
        if not title or not desc or parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
            continue
        source_id='projectcsv:'+hashlib.sha256(url.encode('utf-8')).hexdigest()[:32]
        if source_id in seen: continue
        seen.add(source_id)
        item={k:(row.get(k) or '').strip()[:5000] for k in ('budget','contract_type','location','application_url','published_at')}
        item.update(title=title,source_url=url,description=desc,source_id=source_id)
        result.append(item)
    return result

def init_project_reviews(db):
    with sqlite3.connect(db) as c:
        c.execute("""CREATE TABLE IF NOT EXISTS project_reviews (
            opportunity_id INTEGER PRIMARY KEY, source_checked INTEGER NOT NULL DEFAULT 0,
            contract_checked INTEGER NOT NULL DEFAULT 0, eligible_checked INTEGER NOT NULL DEFAULT 0,
            channel_checked INTEGER NOT NULL DEFAULT 0, evidence_url TEXT NOT NULL DEFAULT '',
            reviewed_at TEXT NOT NULL DEFAULT '')""")

def get_project_review(db, opportunity_id):
    with sqlite3.connect(db) as c:
        c.row_factory=sqlite3.Row
        row=c.execute('SELECT * FROM project_reviews WHERE opportunity_id=?',(opportunity_id,)).fetchone()
        return dict(row) if row else {}

def save_project_review(db, opportunity_id, source_checked, contract_checked, eligible_checked, channel_checked, evidence_url):
    from datetime import datetime, timezone
    with sqlite3.connect(db) as c:
        c.execute("""INSERT INTO project_reviews VALUES (?,?,?,?,?,?,?)
          ON CONFLICT(opportunity_id) DO UPDATE SET
          source_checked=excluded.source_checked, contract_checked=excluded.contract_checked,
          eligible_checked=excluded.eligible_checked, channel_checked=excluded.channel_checked,
          evidence_url=excluded.evidence_url, reviewed_at=excluded.reviewed_at""",
          (opportunity_id,int(source_checked),int(contract_checked),int(eligible_checked),int(channel_checked),
           evidence_url.strip()[:1000],datetime.now(timezone.utc).isoformat()))
