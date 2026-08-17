import asyncio,json,streamlit as st
from dashboard.meta_ads_workflow import MetaAdsDashboardWorkflow,campaigns_to_dataframe
from src.meta_ads.domain import MetaAccount,MetaCampaign,Period
def render_meta_ads(workflow=None):
 st.session_state.setdefault('meta_ads_response',None);workflow=workflow or MetaAdsDashboardWorkflow();st.subheader('Meta Ads intelligence');st.caption('Imported data only. Live Meta API reads and mutations are unavailable.')
 with st.form('meta-import',border=True):
  account=st.text_input('Ad account ID');currency=st.text_input('Currency','INR');start=st.date_input('Period start');end=st.date_input('Period end');raw=st.text_area('Campaign JSON array');go=st.form_submit_button('Analyze import',type='primary')
 if go:
  try:st.session_state.meta_ads_response=asyncio.run(workflow.execute(MetaAccount(ad_account_id=account,currency=currency),Period(date_from=start,date_to=end),[MetaCampaign.model_validate(x)for x in json.loads(raw)]))
  except Exception as e:st.error(str(e))
 r=st.session_state.meta_ads_response
 if r and r.audit:
  f=campaigns_to_dataframe(r.audit);st.caption(f'Data source: {r.audit.source}; currency: {r.audit.account.currency}');st.dataframe(f,hide_index=True);st.download_button('Export CSV',f.to_csv(index=False),'nexora_meta_ads.csv','text/csv')
