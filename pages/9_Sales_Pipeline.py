import sys
import io
import csv
from pathlib import Path
from datetime import date
import streamlit as st
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from sales_pipeline import all_opportunities, save, make_prompt, ollama_draft, STAGES

st.set_page_config(page_title='AgentForge · Sales Pipeline',layout='wide')
st.title('AgentForge v1.9 — Opportunity → Proposal → CRM')
st.caption('Local workflow. No automatic sending. GitHub bounty candidates are not confirmed B2B clients.')
try:
    records=all_opportunities()
except Exception as e:
    st.error(f'Could not read CRM: {e}')
    st.stop()
if not records:
    st.info('No saved v1.8 reviews yet. Open v1.8, inspect an opportunity and save a review first (Research is allowed).')
    st.stop()

c1,c2,c3=st.columns(3)
c1.metric('Reviewed opportunities',len(records))
c2.metric('v1.8 qualified',sum(r['review_status']=='Qualified' for r in records))
c3.metric('Contacted or later',sum(r['pipeline_stage'] in STAGES[3:] for r in records))
st.subheader('Opportunity queue')
filter_stage=st.selectbox('Filter pipeline stage',['All']+STAGES)
visible=[r for r in records if filter_stage=='All' or r['pipeline_stage']==filter_stage]
st.dataframe([{'title':r['title'],'stage':r['pipeline_stage'],'v1.8_review':r['review_status'],
               'payment_evidence':r['payment_evidence_score'],'technical_fit':r['technical_fit_score'],
               'source_url':r['source_url']} for r in visible],use_container_width=True,hide_index=True)
if not visible: st.stop()
idx=st.selectbox('Choose opportunity',range(len(visible)),format_func=lambda i:visible[i]['title'][:120])
r=visible[idx]
st.markdown(f'**Evidence source:** {r["source_url"]}')
st.write('v1.8 review:',r['review_status'],' | Amount mentioned (unverified):',r['amount_text'] or 'None')
if r['review_status']!='Qualified':
    st.warning('This is not yet Qualified. Complete payer, terms, and contact verification in v1.8 before advancing the sales stage.')
key=r['source_url']
with st.form('pipeline_editor'):
    stage=st.selectbox('Pipeline stage (actual interactions in Follow-ups)',STAGES[:3],index=STAGES[:3].index(r['pipeline_stage']) if r['pipeline_stage'] in STAGES[:3] else 0)
    buyer=st.text_input('Verified buyer / organization',r['buyer_name'])
    channel=st.text_input('Permitted contact route (record exact channel)',r['contact_channel'])
    scope=st.text_area('Confirmed project scope',r['project_scope'])
    budget=st.text_input('Verified budget / terms (not inferred)',r['budget_verified'])
    notes=st.text_area('Source-linked verification notes',r['verification_notes'])
    follow=st.text_input('Next follow-up date (YYYY-MM-DD; optional)',r['next_followup'])
    draft=st.text_area('Manual outreach / proposal draft',r['draft'],height=220)
    submitted=st.form_submit_button('Save pipeline record',type='primary')
if submitted:
    try:
        if follow:
            date.fromisoformat(follow)
        save({'source_url':key,'stage':stage,'buyer_name':buyer,'contact_channel':channel,
              'project_scope':scope,'budget_verified':budget,'verification_notes':notes,
              'next_followup':follow,'draft':draft})
        st.success('Saved locally. No message sent.')
    except Exception as exc:
        st.error(str(exc))

st.subheader('Local AI proposal draft')
st.caption('Only for human-reviewed opportunities. Generated text must be checked for factual accuracy and suitability before use.')
lang=st.selectbox('Draft language',['English','Persian'])
if st.button('Generate with local Ollama',disabled=r['review_status']!='Qualified'):
    try:
        with st.spinner('Generating locally...'):
            # Reuse latest form values if the user edited them, but do not save automatically.
            context=dict(r)
            context.update({'project_scope':scope,'verification_notes':notes,'contact_channel':channel})
            output=ollama_draft(make_prompt(context,lang))
        st.session_state['v19_generated']=(key,output)
    except Exception as exc:
        st.error(f'Ollama unavailable: {exc}')
if st.session_state.get('v19_generated',(None,None))[0]==key:
    generated=st.text_area('AI draft — review, then copy into the editor above and save',st.session_state['v19_generated'][1],height=220)
    st.code(generated,language=None)

st.divider()
output=io.StringIO()
writer=csv.writer(output)
writer.writerow(['title','source_url','v18_review','stage','buyer','channel','scope','verified_budget','followup','notes'])
for row in records:
    writer.writerow([row['title'],row['source_url'],row['review_status'],row['pipeline_stage'],row['buyer_name'],
                     row['contact_channel'],row['project_scope'],row['budget_verified'],row['next_followup'],row['verification_notes']])
st.download_button('Export pipeline CSV',output.getvalue().encode('utf-8-sig'),file_name='agentforge_pipeline_v19.csv',mime='text/csv')
