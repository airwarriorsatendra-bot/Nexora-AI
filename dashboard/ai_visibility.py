from __future__ import annotations
import asyncio
import pandas as pd
import streamlit as st
from dashboard.ai_visibility_workflow import AIVisibilityDashboardWorkflow
from src.ai_visibility.domain import VisibilityReport,VisibilityRequest
def run(c):return asyncio.run(c)
def observations_frame(r):return pd.DataFrame([{"Prompt":o.prompt,"Category":o.category.value,"Provider":o.provider,"Model":o.model,"Brand mentioned":o.brand_mention is not None if o.state.value=="SUCCESS" else None,"Mention count":o.brand_mention.count if o.brand_mention else 0,"Target cited":o.target_domain_cited,"Competitors mentioned":", ".join(m.name for m in o.competitor_mentions),"Sources":", ".join(c.url for c in o.citations),"Observation state":o.state.value,"Observed at":o.observed_at} for o in r.run.observations])
def markdown(r):return "# Nexora AI Visibility Report\n\n"+f"- Brand: {r.run.brand_name}\n- Target domain: {r.run.target_domain}\n- Prompts: {r.run.prompt_count}\n- Repetitions: {r.run.repetitions}\n- Observed brand mention coverage: {r.brand_mention_coverage:.1%}\n- Citation coverage: {f'{r.citation_coverage:.1%}' if r.citation_coverage is not None else 'NOT AVAILABLE'}\n\n## Actions\n"+"\n".join(f"- {x}" for x in r.actions)+"\n\n## Limitations\n"+"\n".join(f"- {x}" for x in r.limitations)+"\n"
def render_ai_visibility(workflow=None):
 workflow=workflow or AIVisibilityDashboardWorkflow();st.subheader("AI Visibility Monitoring");st.caption("Observed brand, competitor, and source visibility across configured AI provider APIs.");st.warning("AI responses are nondeterministic and provider/model specific. These observations do not represent universal AI rankings.");st.session_state.setdefault("ai_visibility_report",None)
 try:capabilities=run(workflow.providers());prompts=run(workflow.prompts());candidates=run(workflow.candidates())
 except Exception:capabilities=[];prompts=[];candidates=[]
 with st.form("ai-visibility-prompt",border=True):new_prompt=st.text_input("Add monitoring prompt",max_chars=4000);add=st.form_submit_button("Add prompt")
 if add and new_prompt:
  try:run(workflow.add_prompt(new_prompt));st.success("Monitoring prompt added. No provider call was made.")
  except Exception:st.error("The prompt could not be added.")
 if candidates:
  with st.form("ai-visibility-evidence-import",border=True):candidate=st.selectbox("Persisted evidence candidate",candidates,format_func=lambda x:f"{x[2]} · {x[0]} · {x[1]}");promote=st.form_submit_button("Add evidence prompt")
  if promote:
   try:run(workflow.add_prompt(candidate[2]));st.success("Persisted evidence promoted explicitly. No provider call was made.")
   except Exception:st.error("The evidence candidate could not be promoted.")
 if not capabilities:st.info("No supported AI response provider is configured. Persisted prompts and history remain available; monitoring calls are disabled.")
 labels=[f"{p.provider} · {p.model} · {p.classification.value}" for p in capabilities]
 with st.form("ai-visibility-run",border=True):
  brand=st.text_input("Target brand");domain=st.text_input("Target domain");aliases=st.text_input("Brand aliases",help="Comma-separated explicit aliases.");competitors=st.text_area("Competitors",help="One per line: Name=domain");chosen_prompts=st.multiselect("Monitored prompts",prompts,format_func=lambda p:p.text);chosen_providers=st.multiselect("Providers",labels,default=labels);repetitions=st.number_input("Repetitions",1,3,1);calls=len(chosen_prompts)*len(chosen_providers)*int(repetitions);st.caption(f"Prompts: {len(chosen_prompts)} · Providers: {len(chosen_providers)} · Repetitions: {int(repetitions)} · Total API calls: {calls}");submitted=st.form_submit_button("Run monitoring",type="primary",disabled=not capabilities)
 if submitted:
  try:
   comps={};
   for line in competitors.splitlines():
    if "=" in line:name,value=line.split("=",1);comps[name.strip()]=(value.strip(),)
   requests=[VisibilityRequest(prompt=p,brand_name=brand,brand_aliases=tuple(x.strip() for x in aliases.split(",") if x.strip()),target_domain=domain,competitors=comps) for p in chosen_prompts];provider_names=[capabilities[labels.index(x)].provider for x in chosen_providers];st.session_state.ai_visibility_report=run(workflow.run(requests,int(repetitions),provider_names))
  except Exception:st.error("Monitoring could not be completed. Provider failures are not recorded as brand absence.")
 report=st.session_state.ai_visibility_report
 history=run(workflow.history());history_frame=pd.DataFrame([{"Prompt":o.prompt,"Provider":o.provider,"Model":o.model,"Brand mentioned":o.brand_mention is not None if o.state.value=="SUCCESS" else None,"Target cited":o.target_domain_cited,"State":o.state.value,"Observed at":o.observed_at} for o in history])
 if not isinstance(report,VisibilityReport):
  st.info("Add or select prompts, review the API-call preview, then run monitoring explicitly. No provider call occurs on rerender.")
  if not history_frame.empty:st.subheader("Persisted observation history");st.dataframe(history_frame,hide_index=True,width="stretch")
  return
 with st.container(horizontal=True):st.metric("Monitored prompts",report.run.prompt_count,border=True);st.metric("Brand mention coverage",f"{report.brand_mention_coverage:.1%}",border=True);st.metric("Citation coverage",f"{report.citation_coverage:.1%}" if report.citation_coverage is not None else "NOT AVAILABLE",border=True);st.metric("Competitors observed",report.competitors_observed,border=True);st.metric("Target domain citations",report.target_domain_citations,border=True)
 obs=observations_frame(report);providers=pd.DataFrame([x.model_dump(mode="json") for x in report.provider_summaries]);competitor=pd.DataFrame([{"Competitor":m.name,"Prompt":o.prompt,"Provider":o.provider,"Mention order":m.mention_order} for o in report.run.observations for m in o.competitor_mentions]);sources=pd.DataFrame([{"Domain":c.domain,"URL":c.url,"Provider":o.provider,"Classification":"Target" if c.is_target else "Competitor" if c.competitor else "Other"} for o in report.run.observations for c in o.citations]);pt,ot,ct,stt,dt=st.tabs(["Provider breakdown","Prompt observations","Competitors","Structured citations","Prompt detail"])
 with pt:st.dataframe(providers,hide_index=True,width="stretch")
 with ot:st.dataframe(obs,hide_index=True,width="stretch")
 with ct:st.dataframe(competitor,hide_index=True,width="stretch")
 with stt:st.dataframe(sources,hide_index=True,width="stretch") if not sources.empty else st.info("Structured citation tracking is not available in these observations.")
 with dt:
  selected=st.selectbox("Observation",report.run.observations,format_func=lambda o:f"{o.provider} · {o.prompt}");st.write(selected.response_text or "No successful response text.");st.caption(f"Grounding classification: {selected.classification.value} · State: {selected.state.value}")
 st.subheader("History");st.dataframe(history_frame,hide_index=True,width="stretch")
 with st.container(horizontal=True):st.download_button("Export observations CSV",obs.to_csv(index=False),"ai_visibility_observations.csv","text/csv");st.download_button("Export providers CSV",providers.to_csv(index=False),"ai_visibility_providers.csv","text/csv");st.download_button("Export competitors CSV",competitor.to_csv(index=False),"ai_visibility_competitors.csv","text/csv");st.download_button("Export citations CSV",sources.to_csv(index=False),"ai_visibility_citations.csv","text/csv");st.download_button("Export history CSV",history_frame.to_csv(index=False),"ai_visibility_history.csv","text/csv");st.download_button("Export Markdown",markdown(report),"ai_visibility_report.md","text/markdown")
