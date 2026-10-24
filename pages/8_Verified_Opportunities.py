"""Standalone Streamlit page; requires existing v1.7 opportunity_discovery.py."""
import sys
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from opportunity_discovery import DB, QUERIES
from verified_opportunities import screen_results, recent_enough

st.set_page_config(page_title='AgentForge · Verified Opportunities',layout='wide')
st.title('🔎 AgentForge v1.8 — Opportunity Verification')
st.caption('Payment indications are not verified contracts. No automatic contact or outreach.')

with sqlite3.connect(DB) as con:
    con.execute('''CREATE TABLE IF NOT EXISTS opportunity_v18_review (
       source_url TEXT PRIMARY KEY, title TEXT NOT NULL, payment_indication TEXT,
       amount_text TEXT, payment_evidence_score INTEGER, technical_fit_score INTEGER,
       buyer_confirmed INTEGER NOT NULL DEFAULT 0, payment_terms_confirmed INTEGER NOT NULL DEFAULT 0,
       contact_route_confirmed INTEGER NOT NULL DEFAULT 0,
       review_status TEXT NOT NULL DEFAULT 'Research', reviewer_notes TEXT NOT NULL DEFAULT '',
       updated_at TEXT NOT NULL)''')

query=st.selectbox('Search type',list(QUERIES))
limit=st.slider('Maximum candidates',5,30,15,5)
fetch_details=st.checkbox('Fetch current full issue details and state (recommended)',value=True)
if st.button('Screen public opportunities',type='primary'):
    try:
        with st.spinner('Retrieving and checking public issue evidence...'):
            rows,incomplete,errors=screen_results(query,limit,fetch_details)
        st.session_state['v18_rows']=rows
        st.session_state['v18_errors']=errors
        if incomplete:st.warning('GitHub search reports incomplete results.')
    except Exception as exc:
        st.error(f'Could not complete screening: {exc}')

rows=st.session_state.get('v18_rows',[])
errors=st.session_state.get('v18_errors',[])
if errors:
    st.warning(f'{len(errors)} issues could not be checked (API limit or other error); omitted rather than assumed valid.')
    with st.expander('Details of skipped issues'):
        st.code('\n'.join(errors[:30]))
if rows:
    st.info(f'{len(rows)} unique candidates screened. None is a verified buyer or confirmed payout without human review.')
    categories=sorted({r['payment_indication'] for r in rows})
    selected_categories=st.multiselect('Show categories',categories,default=categories)
    min_score=st.slider('Minimum payment-evidence score',0,100,0,5)
    show=[r for r in rows if r['payment_indication'] in selected_categories and r['payment_evidence_score']>=min_score]
    st.dataframe([{'title':r['title'],'payment_indication':r['payment_indication'],
                  'amount_mentioned':r['amounts'],'payment_evidence':r['payment_evidence_score'],
                  'technical_fit':r['technical_fit_score'],'state':r['issue_state'],
                  'updated_at':r['updated_at'],'url':r['url']} for r in show],hide_index=True,use_container_width=True)
    if show:
        ix=st.selectbox('Inspect a candidate',range(len(show)),format_func=lambda i:show[i]['title'])
        r=show[ix]
        st.markdown(f"**Source:** {r['url']}")
        st.write('**Screening result:**',r['payment_indication'])
        st.write('**Amount mentioned (not verified payment):**',r['amounts'] or 'None')
        st.write('**Technical services:**',r['services'])
        st.write('**Reason:**',r['reasons'])
        st.write('**Updated recently (90 days):**','Yes' if recent_enough(r['updated_at']) else 'No / unknown')
        st.text_area('Public issue excerpt — untrusted source',r['excerpt'],height=150,disabled=True)
        st.warning('Confirm the poster can authorize payment, current eligibility, amount and payout terms, and a permitted contact channel before qualifying.')
        with st.form('v18_review'):
            buyer=st.checkbox('I verified the payer or authorized project owner from the source')
            terms=st.checkbox('I verified current payment terms and eligibility')
            route=st.checkbox('I verified an allowed way to respond or contact')
            notes=st.text_area('Source-linked verification notes (required to mark Qualified)')
            qualify=st.checkbox('Mark as Qualified (all three checks + notes required)')
            if st.form_submit_button('Save review to CRM'):
                eligible=buyer and terms and route and bool(notes.strip()) and r['issue_state']=='open'
                if qualify and not eligible:
                    st.error('Cannot mark Qualified: verify payer, terms, contact route, add notes, and confirm issue is open.')
                else:
                    status='Qualified' if qualify else 'Research'
                    with sqlite3.connect(DB) as con:
                        con.execute('''INSERT INTO opportunity_v18_review
                          (source_url,title,payment_indication,amount_text,payment_evidence_score,
                           technical_fit_score,buyer_confirmed,payment_terms_confirmed,
                           contact_route_confirmed,review_status,reviewer_notes,updated_at)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
                           ON CONFLICT(source_url) DO UPDATE SET
                           title=excluded.title,payment_indication=excluded.payment_indication,
                           amount_text=excluded.amount_text,payment_evidence_score=excluded.payment_evidence_score,
                           technical_fit_score=excluded.technical_fit_score,
                           buyer_confirmed=excluded.buyer_confirmed,
                           payment_terms_confirmed=excluded.payment_terms_confirmed,
                           contact_route_confirmed=excluded.contact_route_confirmed,
                           review_status=excluded.review_status,reviewer_notes=excluded.reviewer_notes,
                           updated_at=excluded.updated_at''',
                           (r['url'],r['title'],r['payment_indication'],r['amounts'],
                            r['payment_evidence_score'],r['technical_fit_score'],int(buyer),int(terms),
                            int(route),status,notes.strip(),datetime.now(timezone.utc).isoformat()))
                    st.success(f'Saved as {status}; no messages were sent.')

st.divider()
st.subheader('Reviewed opportunity queue')
with sqlite3.connect(DB) as con:
    con.row_factory=sqlite3.Row
    saved=[dict(x) for x in con.execute('SELECT * FROM opportunity_v18_review ORDER BY updated_at DESC LIMIT 200')]
if saved:
    st.dataframe([{'title':x['title'],'review_status':x['review_status'],
                   'payment_evidence':x['payment_evidence_score'],
                   'technical_fit':x['technical_fit_score'],'amount_mentioned':x['amount_text'],
                   'url':x['source_url']} for x in saved],use_container_width=True,hide_index=True)
else:
    st.caption('No reviewed candidates yet.')
