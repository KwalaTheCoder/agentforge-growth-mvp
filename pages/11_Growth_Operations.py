"""AgentForge v4.0: read-only Growth Operations Dashboard."""
import sys
from pathlib import Path
import streamlit as st
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))
from direct_b2b import all_prospects
from growth_operations import summarize, rows, PIPELINE

st.set_page_config(page_title='AgentForge · Growth Operations',layout='wide')
st.title('AgentForge v4.0 · Growth Operations')
st.caption('Read-only CRM overview. No automatic outreach, stage updates, or AI-generated buyer claims.')
if st.button('Refresh CRM snapshot',key='v40_refresh'):
    st.rerun()
try:
    records=all_prospects()
except Exception as exc:
    st.error(f'Unable to read local CRM: {exc}')
    st.stop()
report=summarize(records)
a,b,c,d=st.columns(4)
a.metric('Total prospects',report['total'])
b.metric('Research',len(report['research']))
c.metric('Follow-ups due',len(report['due']))
d.metric('Drafts to review',len(report['drafts_for_review']))
st.subheader('Pipeline snapshot')
st.bar_chart(report['stages'])
if report['other_stages']:
    st.warning('Unrecognized stages found; review CRM data manually.')
st.subheader('Follow-up queue')
st.caption('Dates are interpreted as local calendar dates. Due today and overdue are included; Won/Lost are excluded.')
if report['due']:
    st.dataframe(rows(sorted(report['due'],key=lambda x:x.get('followup') or '')),hide_index=True,use_container_width=True)
else:
    st.info('No due follow-ups recorded.')
if report['invalid_dates']:
    st.warning(f"{len(report['invalid_dates'])} records have an invalid follow-up date.")
st.subheader('Drafts for human review')
st.caption('A saved draft is not approval to contact the company. Check qualification and all factual claims first.')
if report['drafts_for_review']:
    st.dataframe(rows(report['drafts_for_review']),hide_index=True,use_container_width=True)
else:
    st.info('No saved drafts currently marked Draft ready.')
st.subheader('Research backlog')
if report['research']:
    st.dataframe(rows(report['research']),hide_index=True,use_container_width=True)
else:
    st.info('No Research-stage records.')
st.caption('To edit a lead, use Direct B2B. This page never writes to the database.')
