"""AgentForge Client Opportunities — compatible with opportunity_discovery.discover_opportunities."""
import sys
import sqlite3
from pathlib import Path
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from opportunity_discovery import QUERIES, discover_opportunities

DB = ROOT / 'client_opportunities_local.sqlite3'

def connect():
    con = sqlite3.connect(str(DB), timeout=10)
    con.row_factory = sqlite3.Row
    con.execute("""CREATE TABLE IF NOT EXISTS client_leads (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        source_url TEXT UNIQUE NOT NULL,
        title TEXT NOT NULL,
        organization TEXT NOT NULL DEFAULT '',
        contact_route TEXT NOT NULL DEFAULT '',
        status TEXT NOT NULL DEFAULT 'Discovered',
        notes TEXT NOT NULL DEFAULT '',
        proposal TEXT NOT NULL DEFAULT '',
        updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )""")
    con.commit()
    return con

def save_lead(item, organization, route, notes, proposal):
    with connect() as con:
        con.execute("""INSERT INTO client_leads (source_url,title,organization,contact_route,notes,proposal)
            VALUES (?,?,?,?,?,?) ON CONFLICT(source_url) DO UPDATE SET
            organization=excluded.organization, contact_route=excluded.contact_route,
            notes=excluded.notes, proposal=excluded.proposal,
            updated_at=CURRENT_TIMESTAMP""",
            (item['url'],item['title'],organization,route,notes,proposal))

def list_leads():
    with connect() as con:
        return [dict(row) for row in con.execute('SELECT * FROM client_leads ORDER BY updated_at DESC, id DESC')]

def update_lead(lead_id, status, route, notes, proposal):
    with connect() as con:
        con.execute("""UPDATE client_leads SET status=?,contact_route=?,notes=?,proposal=?,
            updated_at=CURRENT_TIMESTAMP WHERE id=?""", (status,route,notes,proposal,lead_id))

def proposal_for(item):
    title = str(item.get('title') or 'your project').replace('\n',' ')[:180]
    return (f'Hi, I saw your request: "{title}".\n\n'
            'I work with Python, API integrations, backend development and automation. '
            'I would be interested in discussing a focused implementation with clear deliverables.\n\n'
            'Could you share the current scope, timeline and budget, and whether you are accepting proposals? '
            'I can then suggest an approach and estimate.\n\nBest regards')

st.set_page_config(page_title='AgentForge · Client Opportunities', layout='wide')
st.title('🎯 Client Opportunities — Discover → Propose → Follow up')
st.caption('Uses the existing GitHub discovery engine. No automatic messages. LinkedIn/email outreach is manual or requires explicit approval.')
mode = st.selectbox('Search category', list(QUERIES.keys()))
limit = st.slider('Issues to inspect', 5, 20, 10)
if st.button('Discover opportunities', type='primary'):
    try:
        with st.spinner('Searching and inspecting public opportunities...'):
            st.session_state['client_results'] = discover_opportunities(mode=mode, limit=limit)
    except Exception as exc:
        st.error(f'Discovery failed: {exc}')

report = st.session_state.get('client_results')
if report:
    items = report.get('items') or []
    st.write(f"Inspected: **{len(items)}** | Search hits: **{report.get('unique_search_hits',0)}**")
    if report.get('incomplete_results'):
        st.warning('GitHub search results may be incomplete.')
    for err in report.get('failures') or []:
        st.warning(str(err))
    if items:
        st.dataframe([{'Title':x.get('title'),'Priority':x.get('priority_score'),
            'Action':x.get('actionability'),'Availability':x.get('work_availability'),
            'Skills':x.get('skills'),'URL':x.get('url')} for x in items],
            use_container_width=True, hide_index=True)
        selected = st.selectbox('Choose a lead', range(len(items)),
            format_func=lambda i: f"{items[i].get('actionability','')} · {items[i].get('title','')[:100]}")
        item = items[selected]
        st.link_button('Open original GitHub issue', item['url'])
        st.write('**Why ranked:**',item.get('actionability_reason',''))
        st.write('**Funding:**',item.get('funding_status','Unknown'))
        st.write('**Availability:**',item.get('work_availability','Unknown'))
        st.info('A public issue is not necessarily a client. Confirm contact relevance before sending a proposal.')
        with st.form(f'lead_form_{selected}'):
            organization = st.text_input('Company / client (optional)', value=item.get('repository',''))
            route = st.text_input('Public business email or LinkedIn URL (only if verified)')
            notes = st.text_area('Notes / next step')
            proposal = st.text_area('Editable proposal — copy into Gmail or LinkedIn',
                value=proposal_for(item), height=230)
            if st.form_submit_button('Save lead and proposal'):
                save_lead(item,organization,route,notes,proposal)
                st.success('Lead and draft saved locally. Nothing has been sent.')
    else:
        st.info('No inspected opportunities in this search. Try another category.')

st.divider()
st.subheader('Saved leads and follow-ups')
leads = list_leads()
if leads:
    st.dataframe([{k:lead[k] for k in ('id','title','status','organization','contact_route','source_url')}
        for lead in leads],use_container_width=True,hide_index=True)
    lead_id = st.selectbox('Update lead', [r['id'] for r in leads],
        format_func=lambda i: next(f"#{r['id']} · {r['title'][:90]}" for r in leads if r['id']==i))
    lead = next(r for r in leads if r['id']==lead_id)
    with st.form('update_lead'):
        statuses = ['Discovered','Draft ready','Sent manually','Follow-up due','Replied','Negotiating','Won','Lost']
        status = st.selectbox('Status',statuses,index=statuses.index(lead['status']) if lead['status'] in statuses else 0)
        route = st.text_input('Contact route',value=lead['contact_route'])
        notes = st.text_area('Notes',value=lead['notes'])
        proposal = st.text_area('Proposal',value=lead['proposal'],height=220)
        if st.form_submit_button('Update lead'):
            update_lead(lead_id,status,route,notes,proposal)
            st.success('Saved. Mark Sent manually only after actually sending.')
else:
    st.caption('No leads saved yet.')
