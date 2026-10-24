import json
import os
import sys
from pathlib import Path
import streamlit as st
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from paid_opportunity_radar import discover
st.set_page_config(page_title='AgentForge · Paid Opportunity Radar',layout='wide')
st.title('Paid Opportunity Radar')
st.caption('Read-only search across Python, automation, AI and backend/API. Bounty claims are not proof of payment or available work.')
st.warning('Do not contact anyone or start work based only on a GitHub issue. Verify the issuer, terms, availability, payout method and your own ability to deliver.')
limit=st.slider('Results per search',5,30,15)
if st.button('Discover and rank public opportunities',type='primary'):
    with st.spinner('Searching GitHub public issues...'):
        st.session_state['af_paid_radar']=discover(limit,token=os.getenv('GITHUB_TOKEN'))
report=st.session_state.get('af_paid_radar')
if report:
    if report['errors']: st.warning('Some searches failed; results may be incomplete.')
    rows=report['opportunities']
    st.metric('Public candidates found',len(rows))
    st.dataframe([{'Score':r['score'],'Status':r['status'],'Opportunity':r['title'],'Skills':', '.join(r['skill_matches']),'Payment':r['payment_evidence'],'Last update (days)':r['age_days_since_update'],'Flags':'; '.join(r['red_flags']),'Source':r['url']} for r in rows],hide_index=True,use_container_width=True)
    st.download_button('Download evidence report JSON',json.dumps(report,indent=2,ensure_ascii=False),'paid_opportunity_radar.json','application/json')
    if rows:
        selected=st.selectbox('Inspect source and risks',range(len(rows)),format_func=lambda i:rows[i]['title'][:110])
        item=rows[selected]
        st.link_button('Open original GitHub issue',item['url'])
        st.write('**Skill matches:**',', '.join(item['skill_matches']) or 'None')
        st.write('**Warnings:**','; '.join(item['red_flags']) or 'No automatic flags; manual verification still required')
        st.write('**Claimed amounts (not verified):**',', '.join(item['amount_mentions_unverified']) or 'None')
        st.text_area('Source excerpt (untrusted public content)',item['description_excerpt'],height=180)
        st.info('Next: verify the official terms and ability to deliver. For a suitable company, use One-click Campaign to draft a proposal; Gmail send requires explicit approval.')
