"""Launch: python -m streamlit run pages/11_Followups_Dashboard.py --server.port 8506"""
import sys
from pathlib import Path
from datetime import date
import streamlit as st
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
import followup_dashboard as fd

st.set_page_config(page_title='AgentForge · Follow-ups',layout='wide')
st.title('AgentForge v2.1 — Follow-ups & Sales Dashboard')
st.caption('Local-only. Two independent sources. No automated outreach. Revenue is recorded only after an actual win.')
try:
    d=fd.dashboard()
except Exception as exc:
    st.error(f'Unable to read local CRM: {exc}')
    st.stop()

cols=st.columns(6)
for c,(label,value) in zip(cols,[('Direct B2B',d['b2b']),('GitHub research',d['github']),
                                 ('Qualified',d['qualified']),('Contact sent',d['contacted']),
                                 ('Replies',d['replied']),('Won',d['won'])]):
    c.metric(label,value)
if d['revenue']:
    st.write('**Realized revenue (separate currencies):** '+', '.join(f'{amount:,.2f} {currency}' for currency,amount in d['revenue'].items()))
else:
    st.info('No realized revenue recorded. No projected revenue is counted as earned.')

st.subheader('Follow-ups due today or overdue')
if d['due']:
    st.dataframe(pd.DataFrame(d['due'])[['kind','name','stage','next_followup','last_outcome','source_url']],use_container_width=True,hide_index=True)
else:
    st.caption('No due follow-ups recorded.')

st.subheader('Unified research queue')
if d['prospects']:
    st.dataframe(pd.DataFrame(d['prospects'])[['kind','name','stage','qualified','service','source_url']],use_container_width=True,hide_index=True)
else:
    st.warning('No B2B prospects or reviewed GitHub opportunities found. Save a Research prospect in v2.0 or v1.8 first.')

st.subheader('Record a follow-up or interaction')
if d['prospects']:
    options={f"{p['kind']} · {p['name'][:85]} · {p['source_url']}":p for p in d['prospects']}
    with st.form('event',clear_on_submit=False):
        selection=st.selectbox('Prospect',list(options))
        p=options[selection]
        st.caption(f"Current source stage: {p['stage']} · Qualified: {'Yes' if p['qualified'] else 'No'}")
        outcome=st.selectbox('Event',fd.OUTCOMES)
        event_date=st.date_input('Event date',value=date.today())
        followup=st.date_input('Next follow-up (optional)',value=None)
        note=st.text_area('Factual notes / contact evidence',max_chars=4000,
                          placeholder='What actually happened? Do not record an unsent message as contacted.')
        st.caption('Only record realized revenue when an actual contract is won; do not include pipeline estimates.')
        revenue=st.text_input('Realized revenue amount (optional; Won only)',placeholder='e.g. 500')
        currency=st.text_input('Currency (required if revenue is entered)',placeholder='USD / EUR / GBP')
        submitted=st.form_submit_button('Save event locally')
    if submitted:
        try:
            amount=float(revenue.strip()) if revenue.strip() else None
            fd.save_event(p['kind'],p['source_url'],outcome,event_date.isoformat(),
                          followup.isoformat() if followup else '',note,amount,currency.strip().upper())
            st.success('Event saved locally. No message sent.')
            st.rerun()
        except (ValueError,TypeError) as exc:
            st.error(str(exc))

st.subheader('Interaction history')
if d['events']:
    df=pd.DataFrame(d['events'])
    st.dataframe(df[['event_date','source_kind','source_url','outcome','next_followup','note','amount_realized','currency']],
                 use_container_width=True,hide_index=True)
    st.download_button('Export interaction log CSV',df.to_csv(index=False).encode('utf-8-sig'),
                       'agentforge_v21_followups.csv','text/csv')
else:
    st.caption('No interactions logged yet.')
st.caption('Conversion rates are intentionally omitted until a meaningful sample of verified outreach exists. This page never sends messages.')
