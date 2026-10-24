"""Manual operations planner. Does not change CRM or send messages."""
import sys
from pathlib import Path
from datetime import date
import streamlit as st
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from daily_operations import OWNERS, STATUSES, KINDS, create_task, list_tasks, update_task, summarize
st.set_page_config(page_title='AgentForge · Daily Operations',layout='wide')
st.title('AgentForge v4.2 · Daily Operations')
st.caption('Manual task board for two founders. Tasks are stored separately from CRM; no stage changes, automatic outreach or buyer-intent assumptions.')
try:
    tasks=list_tasks()
except Exception as exc:
    st.error(f'Cannot open local task database: {exc}')
    st.stop()
metrics=summarize(tasks)
a,b,c,d=st.columns(4)
a.metric('Open tasks',metrics['open'])
b.metric('Due or overdue',metrics['due'])
c.metric('Founder 1 open',metrics['by_owner'][OWNERS[0]])
d.metric('Founder 2 open',metrics['by_owner'][OWNERS[1]])
st.subheader('Create a manual task')
with st.form('create_growth_task',clear_on_submit=True):
    title=st.text_input('Task title',max_chars=180,placeholder='Verify company identity and source')
    left,right=st.columns(2)
    owner=left.selectbox('Assigned to',OWNERS)
    kind=right.selectbox('Task type',KINDS)
    due=st.date_input('Due date',value=None)
    source=st.text_input('Related public source URL (optional)')
    notes=st.text_area('Internal notes (optional)',max_chars=3000)
    submitted=st.form_submit_button('Save task')
    if submitted:
        try:
            create_task(title,owner,kind,due.isoformat() if due else '',source,notes)
            st.success('Task saved locally. CRM unchanged.')
            st.rerun()
        except Exception as exc: st.error(str(exc))
st.subheader('Daily task queue')
if not tasks:
    st.info('No tasks yet. Create one above to start the daily plan.')
else:
    def sort_key(t):
        return (t['status']=='Done', t['due_date']=='' ,t['due_date'] or '9999-12-31',t['id'])
    tasks=sorted(tasks,key=sort_key)
    st.dataframe([{'ID':t['id'],'Task':t['title'],'Owner':t['owner'],'Type':t['kind'],
                   'Status':t['status'],'Due':t['due_date'],'Source':t['source_url']} for t in tasks],
                 hide_index=True,use_container_width=True)
    st.subheader('Update an existing task')
    selected=st.selectbox('Task',list(range(len(tasks))),format_func=lambda i:f"#{tasks[i]['id']} · {tasks[i]['title']}")
    task=tasks[selected]
    with st.form(f"edit_task_{task['id']}"):
        x,y=st.columns(2)
        new_owner=x.selectbox('Owner',OWNERS,index=OWNERS.index(task['owner']))
        new_status=y.selectbox('Status',STATUSES,index=STATUSES.index(task['status']))
        initial=date.fromisoformat(task['due_date']) if task['due_date'] else None
        new_due=st.date_input('Due date',value=initial)
        new_notes=st.text_area('Notes',value=task['notes'],max_chars=3000)
        if st.form_submit_button('Update task'):
            try:
                update_task(task['id'],owner=new_owner,status=new_status,
                            due_date=new_due.isoformat() if new_due else '',notes=new_notes)
                st.success('Task updated. CRM unchanged.')
                st.rerun()
            except Exception as exc: st.error(str(exc))
    st.caption('Marking a task Done does not qualify a prospect or authorize contact. Review evidence in Direct B2B separately.')
