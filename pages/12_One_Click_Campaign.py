import json
import sys
from pathlib import Path
import streamlit as st
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))
from campaign_engine import normalize_orgs,run_campaign,generate_proposal
from direct_b2b import ollama_generate
st.set_page_config(page_title='AgentForge · One-click Campaign',layout='wide')
st.title('AgentForge · One-click Research & Proposals')
st.caption('Batch public research → evidence ranking → tailored proposal drafts. No automatic sending or CRM changes.')
st.warning('Technical issues do not establish paid buyer intent. Contact requires a separately verified lawful/appropriate route and human approval.')
raw=st.text_area('GitHub organizations (one per line, max 10)','ai2cm\npeeranha',height=110)
services=st.text_area('Services you actually deliver','Python, AI integration, automation, API engineering, debugging, testing')
lang=st.selectbox('Proposal language',['English','Persian'])
if st.button('Run Campaign — research and rank',type='primary'):
    try:
        orgs=normalize_orgs(raw)
        with st.spinner('Researching public sources and rechecking issues...'):
            st.session_state['af_campaign']=run_campaign(orgs)
            st.session_state.pop('af_drafts',None)
    except Exception as exc:st.error(str(exc))
report=st.session_state.get('af_campaign')
if report:
    rows=[]
    for r in report['results']:
        counts=r.get('decision_counts',{})
        rows.append({'company':r['company'],'technical_score':r.get('top_score',0),'issues':r.get('issues_found',0),
                     'investigate':counts.get('Investigate',0),'monitor':counts.get('Monitor',0),
                     'archive':counts.get('Archive',0),'status':'Error' if r.get('error') else 'Research only',
                     'error':r.get('error','')})
    st.subheader('Ranked research candidates')
    st.dataframe(rows,hide_index=True,use_container_width=True)
    st.download_button('Download complete research JSON',json.dumps(report,ensure_ascii=False,indent=2,default=str),
                       'agentforge_campaign_research.json','application/json')
    options=[r['company'] for r in report['results'] if r.get('top_evidence')]
    if options:
        selected=st.selectbox('Company for proposal draft',options)
        record=next(r for r in report['results'] if r['company']==selected)
        st.write('**Evidence used for the draft:**')
        st.dataframe(record['top_evidence'],hide_index=True,use_container_width=True)
        if st.button('Generate professional proposal (local Ollama)'):
            try:
                with st.spinner('Writing a source-grounded draft...'):
                    draft=generate_proposal(record,services,generator=ollama_generate,language=lang)
                st.session_state['af_drafts']={'company':selected,'draft':draft,'language':lang}
            except Exception as exc:st.error('Proposal generation failed: '+str(exc))
        draft=st.session_state.get('af_drafts')
        if draft and draft['company']==selected and draft['language']==lang:
            edited=st.text_area('Proposal draft — edit and fact-check before use',draft['draft'],height=430,key='af_edit_proposal')
            st.download_button('Download proposal draft',edited,file_name='proposal_'+selected+'.txt')
            st.info('Sending is intentionally not enabled: recipient identity, permitted contact basis, and sender credentials are not configured or verified. Review the draft and use your approved business channel.')

            st.divider()
            st.subheader('Gmail — reviewed, one-recipient send')
            st.caption('Only send to a verified recipient with a documented appropriate contact basis. No automatic outreach.')
            from gmail_delivery import connect, send_once
            secrets=st.text_input('Google OAuth Desktop client JSON path',value=str(ROOT/'gmail_client_secret.json'))
            if st.button('Connect Gmail via Google OAuth'):
                try:
                    connect(secrets)
                    st.success('Gmail connected locally')
                except Exception as exc:st.error(str(exc))
            to=st.text_input('Verified recipient email (single address)')
            subject=st.text_input('Email subject',value='Potential technical collaboration — '+selected)
            body=st.text_area('Final email text',value=edited,height=300,key='af_gmail_body')
            basis=st.text_area('Contact basis (e.g., explicit invitation to submit proposals, with source URL)',height=80)
            approval=st.checkbox('I verified the recipient, contact basis, proposal facts, and approve sending this exact email.')
            if st.button('Send this email via Gmail',type='primary',disabled=not approval):
                try:
                    response=send_once(to,subject,body,approved=approval,consent_basis=basis)
                    st.success('Sent via Gmail. Message ID: '+str(response.get('id','unknown')))
                except Exception as exc:st.error('Not sent: '+str(exc))
