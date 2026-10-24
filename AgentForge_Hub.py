"""AgentForge v2.2 unified launcher. Run: streamlit run AgentForge_Hub.py"""
from pathlib import Path
import sqlite3
import streamlit as st

ROOT = Path(__file__).resolve().parent
DB = ROOT / 'leads.sqlite3'
PAGES = [
    ('Direct B2B research', 'pages/10_Direct_B2B.py', 'Discover and review companies; never assume buying intent.'),
    ('Opportunity verification', 'pages/8_Verified_Opportunities.py', 'Screen public requests and verify payment evidence.'),
    ('Sales pipeline', 'pages/9_Sales_Pipeline.py', 'Manage reviewed opportunities and local proposal drafts.'),
    ('Follow-ups & dashboard', 'pages/11_Followups_Dashboard.py', 'Log interactions, next actions and realized revenue.'),
]

st.set_page_config(page_title='AgentForge | Growth Hub', page_icon='🚀', layout='wide')
st.title('🚀 AgentForge — Growth Hub v2.2')
st.caption('One local Streamlit address · Human-approved outreach · Existing CRM data preserved')

available = [(name, path, description) for name, path, description in PAGES if (ROOT / path).is_file()]
missing = [(name, path) for name, path, _ in PAGES if not (ROOT / path).is_file()]

st.subheader('Workspace')
a, b, c = st.columns(3)
a.metric('Installed workflows', len(available))
b.metric('Missing workflows', len(missing))
c.metric('Local database', 'Found' if DB.is_file() else 'Not found')
if missing:
    st.warning('Some older patch files are missing. Install the corresponding versions before using those workflows.')
    for name, path in missing:
        st.write(f'• {name}: `{path}`')
if not DB.is_file():
    st.info('No existing leads.sqlite3 found. Check you launched from the original AgentForge project directory.')

st.subheader('Open a workflow')
for name, path, description in available:
    left, right = st.columns([4, 1])
    left.markdown(f'**{name}**  \n{description}')
    if right.button('Open', key=path, use_container_width=True):
        st.switch_page(path)

st.divider()
st.subheader('Data checks (read-only)')
if DB.is_file():
    try:
        with sqlite3.connect(f'file:{DB.as_posix()}?mode=ro', uri=True, timeout=5) as con:
            tables = {row[0] for row in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            names = [('Direct B2B', 'b2b_v20_prospects'),
                     ('Reviewed GitHub requests', 'opportunity_v18_review'),
                     ('Follow-up interactions', 'af_v21_followups')]
            cols = st.columns(3)
            for col, (label, table) in zip(cols, names):
                count = con.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] if table in tables else 0
                col.metric(label, count)
    except (sqlite3.Error, OSError) as exc:
        st.warning(f'Database status unavailable: {exc}')

st.info('GitHub activity and monetary mentions do not confirm a paying buyer. Verify buyer, terms and permitted contact method before outreach. No automatic sending.')
st.caption('v2.3 hardening: legacy v1.7 workflow hidden; advanced stage transitions require factual events. Local acceptance tests still required.')
