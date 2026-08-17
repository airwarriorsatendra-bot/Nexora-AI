"""Streamlit imported-data Google Ads intelligence page."""
from __future__ import annotations
import asyncio,json
import streamlit as st
from dashboard.google_ads_workflow import GoogleAdsDashboardWorkflow,campaigns_to_dataframe
from src.google_ads.domain import GoogleAdsAccount,GoogleAdsCampaign,ReportingPeriod
def run(c):
 try:asyncio.get_running_loop()
 except RuntimeError:return asyncio.run(c)
 raise RuntimeError('Google Ads analysis cannot run in an active event loop.')
def render_google_ads(workflow=None):
 st.session_state.setdefault('google_ads_response',None);workflow=workflow or GoogleAdsDashboardWorkflow();st.subheader('Google Ads Intelligence · IMPORT MODE');st.caption('Analyze supplied imported campaign data. Live Google Ads connectivity and mutations are unavailable.')
 with st.form('google-ads-import',border=True):
  customer=st.text_input('Customer ID',key='ads-customer');currency=st.text_input('Currency','INR',key='ads-currency');start=st.date_input('Period start',key='ads-start');end=st.date_input('Period end',key='ads-end');raw=st.text_area('Campaign JSON array',placeholder='[{"campaign_id":"1","name":"Search","impressions":1000,"clicks":50,"cost":"100","conversions":"2","conversion_value":"500"}]',key='ads-json');submit=st.form_submit_button('Analyze imported data',type='primary')
 if submit:
  try:st.session_state.google_ads_response=run(workflow.execute(GoogleAdsAccount(customer_id=customer,currency_code=currency.upper()),ReportingPeriod(date_from=start,date_to=end),[GoogleAdsCampaign.model_validate(x) for x in json.loads(raw)]))
  except Exception as exc:st.error(str(exc))
 response=st.session_state.google_ads_response
 if response and response.audit:
  audit=response.audit;frame=campaigns_to_dataframe(audit);st.subheader('Campaign performance');st.caption(f'Data source: {audit.source}; reporting period: {audit.period.date_from} to {audit.period.date_to}; currency: {audit.account.currency_code}')
  st.dataframe(frame,hide_index=True,key='ads-campaigns');st.download_button('Export campaigns CSV',frame.to_csv(index=False),'nexora_google_ads_campaigns.csv','text/csv')
  if audit.recommendations:st.dataframe([x.model_dump(mode='json') for x in audit.recommendations],hide_index=True,key='ads-recommendations')
