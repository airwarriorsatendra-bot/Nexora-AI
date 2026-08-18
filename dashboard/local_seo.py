"""Premium offline-first Local SEO Intelligence 2.0 workspace."""
from __future__ import annotations
import asyncio
import streamlit as st
from dashboard.local_seo_workflow import LocalSEODashboardWorkflow,frame,issues_to_dataframe,local_report
from src.local_seo.domain import LocalBusiness
from src.shared.value_objects.location import Location

def run(coro):
 try:asyncio.get_running_loop()
 except RuntimeError:return asyncio.run(coro)
 raise RuntimeError("Local SEO workflow cannot run inside an active event loop.")
def _table(values,key,exclude=()):
 data=frame(values,exclude)
 if data.empty:st.info("No persisted evidence is available.")
 else:st.dataframe(data,hide_index=True,width="stretch",key=key)
def render_local_seo(workflow=None):
 st.session_state.setdefault("local_seo_response",None);workflow=workflow or LocalSEODashboardWorkflow();st.subheader("Local SEO Intelligence");st.caption("Evidence-backed local business, NAP, reviews, rankings, citations, competitors, and actions. Provider refreshes are always explicit.")
 try:snapshot=run(workflow.snapshot())
 except Exception:snapshot=None;st.error("Persisted Local SEO intelligence could not be loaded.")
 with st.expander("Run website evidence audit",expanded=snapshot is None):
  with st.form("local-seo",border=False):
   left,right=st.columns(2);name=left.text_input("Business name",key="local-name");website=right.text_input("Website URL",key="local-url");phone=left.text_input("Phone",key="local-phone");address=right.text_input("Address",key="local-address");city=left.text_input("City",key="local-city");state=right.text_input("State",key="local-state");category=left.text_input("Primary category",key="local-category");submit=st.form_submit_button("Run local audit",type="primary",icon=":material/search:")
  if submit:
   try:st.session_state.local_seo_response=run(workflow.execute(LocalBusiness(name=name,website=website,phone=phone,location=Location(address=address,city=city,state=state),primary_category=category)))
   except Exception as exc:st.error(str(exc))
 response=st.session_state.local_seo_response
 if response and response.audit:
  audit=response.audit
  with st.container(horizontal=True):st.metric("Local audit score",f"{audit.overall_score:.0f}",border=True);st.metric("Audit issues",len(audit.issues),border=True);st.metric("Citation evidence",audit.signals["citation_consistency"],border=True)
  findings=issues_to_dataframe(audit);st.dataframe(findings,hide_index=True,width="stretch",key="local-issues");st.download_button("Audit findings CSV",findings.to_csv(index=False),"local_audit_findings.csv","text/csv")
 elif response:st.error(response.message)
 if snapshot is None:return
 locations=len(snapshot.locations);reviews=sum(x.review_count for x in snapshot.review_summaries);ratings=[x.average_rating for x in snapshot.review_summaries if x.average_rating is not None];response_rates=[x.response_rate for x in snapshot.review_summaries if x.response_rate is not None];citation_total=len(snapshot.citations);citation_present=sum(x.state.value.startswith("PRESENT") for x in snapshot.citations);local_pack=sum(x.current.result_type.value=="LOCAL_PACK" for x in snapshot.ranks)
 with st.container(horizontal=True):
  for label,value in (("Locations",locations if locations else "N/A"),("GBP connected","Yes" if any(x.provider=="GOOGLE_BUSINESS_PROFILE" for x in snapshot.locations) else "N/A"),("Average rating",f"{sum(ratings)/len(ratings):.2f}" if ratings else "N/A"),("Reviews",reviews if snapshot.review_summaries else "N/A"),("Response rate",f"{sum(response_rates)/len(response_rates):.1%}" if response_rates else "N/A"),("Local Pack observations",local_pack if snapshot.ranks else "N/A"),("Citation coverage",f"{citation_present}/{citation_total}" if citation_total else "N/A"),("Open opportunities",len(snapshot.opportunities))):st.metric(label,value,border=True)
 tabs=st.tabs(["Overview","Business profile","Locations","NAP","Reviews","Local rankings","Local queries","Landing pages","Citations","Competitors","Opportunities","History"])
 with tabs[0]:st.caption("Unavailable evidence remains N/A. Nexora does not claim Google ranking causality.")
 with tabs[1]:_table([x for x in snapshot.locations if x.provider=="GOOGLE_BUSINESS_PROFILE"],"local-gbp")
 with tabs[2]:_table(snapshot.locations,"local-locations")
 with tabs[3]:_table(snapshot.nap_assessments,"local-nap")
 with tabs[4]:_table(snapshot.reviews,"local-reviews",("reviewer_name",));_table(snapshot.review_summaries,"local-review-summary")
 with tabs[5]:_table(snapshot.ranks,"local-ranks")
 with tabs[6]:_table(snapshot.queries,"local-queries")
 with tabs[7]:_table(snapshot.landing_pages,"local-pages")
 with tabs[8]:_table(snapshot.citations,"local-citations")
 with tabs[9]:_table(snapshot.competitors,"local-competitors")
 with tabs[10]:_table(snapshot.opportunities,"local-opportunities")
 with tabs[11]:_table(snapshot.history,"local-history")
 exports=(("Locations CSV",snapshot.locations,"local_locations.csv",()),("NAP audit CSV",snapshot.nap_assessments,"local_nap.csv",()),("Reviews CSV",snapshot.reviews,"local_reviews.csv",("reviewer_name",)),("Local rankings CSV",snapshot.ranks,"local_rankings.csv",()),("Local queries CSV",snapshot.queries,"local_queries.csv",()),("Landing pages CSV",snapshot.landing_pages,"local_pages.csv",()),("Local citations CSV",snapshot.citations,"local_citations.csv",()),("Local competitors CSV",snapshot.competitors,"local_competitors.csv",()),("Local opportunities CSV",snapshot.opportunities,"local_opportunities.csv",()),("Local history CSV",snapshot.history,"local_history.csv",()))
 with st.container(horizontal=True):
  for label,values,filename,exclude in exports:st.download_button(label,frame(values,exclude).to_csv(index=False),filename,"text/csv")
  st.download_button("Markdown Local SEO report",local_report(snapshot),"local_seo_report.md","text/markdown")
