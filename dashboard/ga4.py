"""GA4 source panel; all API access is explicit and user initiated."""
from __future__ import annotations
from datetime import date,timedelta
import pandas as pd
import streamlit as st
from dashboard.research_workflow import run_async
from dashboard.ga4_workflow import GA4DashboardWorkflow
from src.ga4.domain import ReportingPeriod,GA4Dimension
def _frame(snapshot):
 return pd.DataFrame([{**{d.value:k for d,k in zip(row.dimensions,row.keys)},**{name:float(value) for name,value in row.metrics.items()},'source':snapshot.source,'property_id':snapshot.property.property_id,'date_from':snapshot.period.start_date,'date_to':snapshot.period.end_date} for row in snapshot.records])
def render_ga4(workflow=None):
 workflow=workflow or GA4DashboardWorkflow();st.subheader('Google Analytics 4');st.caption('READ ONLY · Explicit refresh only. GA4 users, sessions, and events remain source-specific.')
 st.session_state.setdefault('ga4_properties',());st.session_state.setdefault('ga4_views',None)
 if not workflow.configured():st.info('Google Analytics 4 · Not configured. Reauthorize the shared Google OAuth client with analytics.readonly and set GA4_PROPERTY_ID.');return
 if st.button('Discover GA4 properties',key='ga4-discover'):
  try:st.session_state.ga4_properties=run_async(workflow.properties())
  except Exception:st.error('GA4 properties could not be loaded. Check read-only access and API enablement.')
 properties=st.session_state.ga4_properties
 if not properties:st.info('Discover an accessible GA4 property before refreshing.');return
 choices={p.property_id:p for p in properties};end=date.today()-timedelta(days=1)
 with st.form('ga4-refresh'):
  pid=st.selectbox('GA4 property',tuple(choices));dates=st.date_input('GA4 reporting period',(end-timedelta(days=27),end));submit=st.form_submit_button('Refresh GA4 data',type='primary')
 if submit:
  try:st.session_state.ga4_views=run_async(workflow.refresh(choices[pid],ReportingPeriod(start_date=dates[0],end_date=dates[1])))
  except Exception:st.error('GA4 data could not be refreshed. No credentials or provider details are displayed.')
 views=st.session_state.ga4_views
 if not views:return
 totals=views[()].totals
 with st.container(horizontal=True):
  for name in ('activeUsers','sessions','engagedSessions','engagementRate'):
   value=totals.get(name,0);st.metric(name.replace('Users',' users').replace('Rate',' rate'),f'{value:.2%}' if name=='engagementRate' else f'{value:g}',border=True)
 for title,dimension in (('Traffic acquisition',GA4Dimension.CHANNEL),('Landing pages',GA4Dimension.LANDING_PAGE),('Events',GA4Dimension.EVENT),('Device / country',GA4Dimension.DEVICE),('Country',GA4Dimension.COUNTRY)):
  frame=_frame(views[(dimension,)])
  if not frame.empty:
   st.subheader(title);st.dataframe(frame,hide_index=True);st.download_button(f'Export {title} CSV',frame.to_csv(index=False),f'nexora_ga4_{dimension.value}.csv','text/csv')
