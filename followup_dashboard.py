"""AgentForge v2.1 local follow-up log and cross-source dashboard.
Reads existing v1.8/v1.9/v2.0 tables; writes ONLY af_v21_followups.
"""
import sqlite3
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation
from datetime import datetime, timezone, date
from pathlib import Path

DB = Path(__file__).resolve().parent / 'leads.sqlite3'
KINDS = ('B2B', 'GitHub opportunity')
OUTCOMES = ('Research note', 'Contact sent', 'Reply received', 'Meeting scheduled', 'Proposal sent', 'Negotiating', 'Won', 'Lost')

@contextmanager
def connect():
    con = sqlite3.connect(DB, timeout=15)
    con.row_factory = sqlite3.Row
    con.execute('PRAGMA busy_timeout=15000')
    con.execute('''CREATE TABLE IF NOT EXISTS af_v21_followups (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      source_kind TEXT NOT NULL, source_url TEXT NOT NULL,
      outcome TEXT NOT NULL, event_date TEXT NOT NULL,
      next_followup TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '',
      amount_realized REAL, currency TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL)''')
    con.commit()
    try:
        with con:
            yield con
    finally:
        con.close()

def table_exists(con, name):
    return bool(con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone())

def prospects():
    with connect() as con:
        results=[]
        if table_exists(con,'b2b_v20_prospects'):
            for r in con.execute('SELECT * FROM b2b_v20_prospects'):
                d=dict(r)
                results.append({'kind':'B2B','source_url':d['source_url'],'name':d['company'],
                                'stage':d['stage'],'qualified':d['stage']!='Research',
                                'service':d['service']})
        if table_exists(con,'opportunity_v18_review'):
            sql='''SELECT v.source_url, v.title, v.review_status,
                 COALESCE(p.stage,'Research') AS pipeline_stage
                 FROM opportunity_v18_review v
                 LEFT JOIN opportunity_v19_pipeline p ON v.source_url=p.source_url'''
            if not table_exists(con,'opportunity_v19_pipeline'):
                sql="SELECT source_url, title, review_status, 'Research' AS pipeline_stage FROM opportunity_v18_review"
            for r in con.execute(sql):
                d=dict(r)
                results.append({'kind':'GitHub opportunity','source_url':d['source_url'],
                                'name':d['title'],'stage':d['pipeline_stage'],
                                'qualified':d['review_status']=='Qualified','service':''})
        return sorted(results,key=lambda r:(r['kind'],r['name'].lower()))

def events():
    with connect() as con:
        return [dict(r) for r in con.execute('SELECT * FROM af_v21_followups ORDER BY event_date DESC, id DESC')]

def save_event(kind, source_url, outcome, event_date, next_followup='', note='', amount_realized=None, currency=''):
    if kind not in KINDS or outcome not in OUTCOMES:
        raise ValueError('Invalid event type')
    date.fromisoformat(event_date)
    if next_followup:
        date.fromisoformat(next_followup)
    if len(note)>4000 or len(currency)>8:
        raise ValueError('Notes or currency too long')
    if amount_realized is not None:
        try:
            amount_realized = Decimal(str(amount_realized))
        except (InvalidOperation, ValueError):
            raise ValueError('Invalid monetary amount')
        if not amount_realized.is_finite() or amount_realized <= 0:
            raise ValueError('Revenue must be a positive finite amount')
        if outcome != 'Won' or not currency.strip():
            raise ValueError('Realized revenue requires Won, nonnegative amount and currency')
        if not currency.isalpha() or len(currency) != 3:
            raise ValueError('Use a three-letter currency code, e.g. USD')
    elif currency:
        raise ValueError('Currency without amount')
    candidates={(p['kind'],p['source_url']):p for p in prospects()}
    if (kind,source_url) not in candidates:
        raise ValueError('Prospect not found in source database')
    if outcome in ('Contact sent','Reply received','Meeting scheduled','Proposal sent','Negotiating','Won','Lost'):
        if not candidates[(kind,source_url)]['qualified']:
            raise ValueError('First verify and qualify this prospect in its original module')
        if not note.strip():
            raise ValueError('Provide a factual note supporting the recorded interaction')
    with connect() as con:
        if amount_realized is not None:
            existing = con.execute('''SELECT 1 FROM af_v21_followups
                WHERE source_kind=? AND source_url=? AND outcome='Won'
                AND amount_realized IS NOT NULL LIMIT 1''', (kind,source_url)).fetchone()
            if existing:
                raise ValueError('Revenue already recorded for this prospect. Do not record the same win twice; reconcile existing entries manually.')
        con.execute('''INSERT INTO af_v21_followups
            (source_kind,source_url,outcome,event_date,next_followup,note,amount_realized,currency,created_at)
            VALUES (?,?,?,?,?,?,?,?,?)''',
            (kind,source_url,outcome,event_date,next_followup,note,float(amount_realized) if amount_realized is not None else None,currency,
             datetime.now(timezone.utc).isoformat()))

def dashboard():
    ps=prospects()
    es=events()
    unique=lambda outcome:len({(e['source_kind'],e['source_url']) for e in es if e['outcome']==outcome})
    latest={}
    for e in es:
        key=(e['source_kind'],e['source_url'])
        if key not in latest or (e['event_date'],e['id'])>(latest[key]['event_date'],latest[key]['id']):
            latest[key]=e
    today=date.today().isoformat()
    due=[]
    for p in ps:
        key=(p['kind'],p['source_url'])
        history=sorted((e for e in es if (e['source_kind'],e['source_url'])==key),
                       key=lambda e:(e['event_date'],e['id']))
        if not history:
            continue
        last=history[-1]
        if last['outcome'] in ('Won','Lost'):
            continue
        # A research note without a date must not silently erase a pending reminder.
        # An explicit later follow-up date supersedes the earlier one.
        dated=[e for e in history if e['next_followup']]
        if dated and dated[-1]['next_followup']<=today:
            due.append({**p,'next_followup':dated[-1]['next_followup'],
                        'last_outcome':last['outcome']})
    revenues={}
    # Historical duplicates are NOT automatically summed: one revenue event per
    # prospect is counted. Existing duplicate rows remain untouched for audit.
    wins={}
    for e in sorted(es,key=lambda e:(e['event_date'],e['id'])):
        if e['outcome']=='Won' and e['amount_realized'] is not None:
            wins.setdefault((e['source_kind'],e['source_url']),e)
    for e in wins.values():
        currency=e['currency'].upper()
        revenues[currency]=revenues.get(currency,Decimal('0'))+Decimal(str(e['amount_realized']))
    revenues={currency:float(value) for currency,value in revenues.items()}
    return {'prospects':ps,'events':es,'due':due,'revenue':revenues,
            'b2b':sum(p['kind']=='B2B' for p in ps),
            'github':sum(p['kind']=='GitHub opportunity' for p in ps),
            'qualified':sum(p['qualified'] for p in ps),
            'contacted':unique('Contact sent'), 'replied':unique('Reply received'),
            'won':unique('Won')}
