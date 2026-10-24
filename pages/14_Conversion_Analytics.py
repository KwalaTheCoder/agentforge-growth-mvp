"""Read-only snapshot analytics, without fabricated conversion rates."""
import sys
from pathlib import Path
import streamlit as st
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from direct_b2b import all_prospects
from conversion_analytics import snapshot, safe_rows

st.set_page_config(page_title='AgentForge · Conversion Analytics', layout='wide')
st.title('AgentForge v4.3 · Conversion Analytics')
st.caption('Read-only CRM stage snapshot. No historical conversion rates can be calculated without event history.')
if st.button('Refresh CRM snapshot'):
    st.rerun()
try:
    prospects = all_prospects()
except Exception as exc:
    st.error(f'Cannot read local CRM: {exc}')
    st.stop()
report = snapshot(prospects)
a,b,c,d = st.columns(4)
a.metric('Unique prospects', report['total'])
b.metric('Active pipeline', report['active'])
c.metric('Won (current)', report['won'])
d.metric('Lost (current)', report['lost'])
st.subheader('Current pipeline distribution')
st.bar_chart(report['stages'])
if report['total']:
    st.metric('Won share of current CRM', f"{report['current_won_share_pct']:.1f}%")
else:
    st.info('No prospects recorded yet. Add research prospects in Direct B2B.')
st.warning('This is NOT a lead-to-contract conversion rate. The CRM does not record historical stage transitions, outreach dates, or cohorts. Do not use current stage counts as a conversion funnel.')
if report['unknown_stages']:
    st.warning(f"Unknown CRM stages found: {report['unknown_stages']}")
if report['missing_source_count']:
    st.warning(f"{report['missing_source_count']} rows have no source URL and were excluded.")
if report['duplicate_rows_removed']:
    st.info(f"{report['duplicate_rows_removed']} duplicate source rows removed from this snapshot.")
st.subheader('Current records')
if prospects:
    st.dataframe(safe_rows(prospects), hide_index=True, use_container_width=True)
st.caption('No automatic CRM writes, stage changes, outreach, or AI-generated buyer claims. Task completion does not affect these metrics.')
