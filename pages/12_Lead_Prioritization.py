"""Read-only lead research prioritization; not buyer-intent prediction."""
import sys
from pathlib import Path
import streamlit as st
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from direct_b2b import all_prospects
from lead_prioritization import ranked
st.set_page_config(page_title='AgentForge · Lead Prioritization',layout='wide')
st.title('AgentForge v4.1 · Lead Prioritization')
st.caption('Research priority only. A high score does not mean buyer intent, budget, permission to contact, or sales likelihood. No writes or outreach.')
if st.button('Refresh CRM snapshot',key='v41_refresh'):st.rerun()
try:
    data=ranked(all_prospects())
except Exception as exc:
    st.error(f'Unable to read CRM: {exc}');st.stop()
a,b,c=st.columns(3)
a.metric('Total prospects',len(data))
b.metric('Follow-ups due',sum(x['followup_due'] for x in data))
c.metric('Qualification checks complete',sum(x['outreach_ready'] for x in data))
if not data:
    st.info('No prospects in CRM. Add a research lead in Direct B2B first.')
else:
    st.subheader('Research and follow-up queue')
    st.dataframe([{'Company':x['company'],'Stage':x['stage'],'Research priority (0–100)':x['research_score'],
                   'Next manual action':x['next_action'],'Follow-up due':x['followup_due'],
                   'Qualification checks complete':x['outreach_ready'],'Source':x['source_url']} for x in data],
                 hide_index=True,use_container_width=True)
    st.subheader('Why each record has this priority')
    options=list(range(len(data)))
    idx=st.selectbox('Inspect prospect',options,format_func=lambda i:f"{data[i]['company'] or 'Unnamed'} — {data[i]['research_score']}/100",key='v41_select')
    item=data[idx]
    st.write('**Next action:**',item['next_action'])
    st.write('**Qualification:**',item['outreach_reason'])
    for reason in item['reasons']:st.write('• '+reason)
    st.caption('Research signals are not evidence of purchasing intent. Verify claims and contact permission manually in Direct B2B.')
