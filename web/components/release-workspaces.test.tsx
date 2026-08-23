// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import {afterEach,describe,expect,it} from "vitest";
import {cleanup,fireEvent,render,screen} from "@testing-library/react";
import {RankTrackingWorkspace} from "./rank-tracking-workspace";
import {SiteCrawlWorkspace} from "./site-crawl-workspace";
import {CompetitorGapWorkspace} from "./competitor-gap-workspace";
import {ContentWorkspace} from "./content-workspace";
import {AEOGEOWorkspace} from "./aeo-geo-workspace";
import {AIVisibilityWorkspace} from "./ai-visibility-workspace";
import {BacklinksWorkspace} from "./backlinks-workspace";
import {OutreachWorkspace} from "./outreach-workspace";
import {LocalSEOWorkspace} from "./local-seo-workspace";
import {PaidMediaWorkspace} from "./paid-media-workspace";
import {vi} from "vitest";
vi.mock("next/navigation",()=>({useRouter:()=>({refresh:vi.fn(),push:vi.fn()})}));
afterEach(cleanup);
describe("Beta 17 workflow states",()=>{
 it("renders Rank Tracking empty state without executing a check",()=>{render(<RankTrackingWorkspace initial={null}/>);expect(screen.getByText(/No tracked keywords/i)).toBeInTheDocument();expect(screen.getByRole("button",{name:/Check ranks/})).toBeDisabled()});
 it("renders Site Crawl empty state without crawling",()=>{render(<SiteCrawlWorkspace initial={null}/>);expect(screen.getByText(/No persisted crawl selected/i)).toBeInTheDocument()});
 it("renders Competitor Gap API error state",()=>{render(<CompetitorGapWorkspace report={null}/>);expect(screen.getByRole("alert")).toHaveTextContent(/unavailable/i)});
 it("renders current Content Intelligence empty state and no fake history",()=>{render(<ContentWorkspace targets={[]}/>);expect(screen.getByText(/No content-brief targets/i)).toBeInTheDocument()});
 it("renders AEO GEO persisted-evidence empty state",()=>{render(<AEOGEOWorkspace targets={[]}/>);expect(screen.getByText(/No persisted tracked-domain evidence/i)).toBeInTheDocument()});
 it("renders AI Visibility provider-safe controls with no providers",()=>{render(<AIVisibilityWorkspace initial={{providers:[],prompts:[],history:[]}}/>);expect(screen.getByText(/Page load makes zero provider calls/i)).toBeInTheDocument();expect(screen.getByRole("button",{name:/Review API calls/})).toBeDisabled()});
 it("renders Backlinks tabs and keeps Moz action disabled without targets",()=>{const initial={backlinks:[],opportunities:[],authority:[],prospects:[],referring_domains:[],prospect_history:[],intersect:[],competitor_gaps:[],anchors:[],reclamation:[],moz_configured:false};render(<BacklinksWorkspace initial={initial as never}/>);expect(screen.getByRole("tab",{name:"History"})).toBeInTheDocument();expect(screen.getByRole("button",{name:/Preview Moz requests/})).toBeDisabled()});
 it("renders Outreach safety gates with live sending disabled",()=>{const initial={prospects:[],contacts:[],campaigns:[],sequences:[],steps:[],messages:[],replies:[],followups:[],suppressions:[],history:[],analytics:{prospects:0,contacts:0,sent:0,failed:0,bounced:0,replies:0,positive_replies:0,negative_replies:0},gmail_configured:false,live_send_enabled:false,sender_email:"",reply_provider_configured:false,provider_name:"OFFLINE"};render(<OutreachWorkspace initial={initial}/>);expect(screen.getByText("LIVE SEND DISABLED")).toBeInTheDocument();expect(screen.getByRole("button",{name:/Check replies/})).toBeDisabled()});
 it("renders all Local SEO evidence tabs and blocks unconfigured GBP",()=>{const data={locations:[],nap_assessments:[],reviews:[],review_summaries:[],ranks:[],queries:[],landing_pages:[],citations:[],competitors:[],opportunities:[],history:[]};render(<LocalSEOWorkspace initial={{data,gbp_configured:false} as never}/>);expect(screen.getByRole("tab",{name:"History"})).toBeInTheDocument();expect(screen.getByRole("button",{name:/Refresh GBP/})).toBeDisabled()});
 it("keeps Google and Meta Ads in explicit import mode",()=>{const {rerender}=render(<PaidMediaWorkspace platform="google-ads" initial={[]}/>);expect(screen.getByText("IMPORT MODE")).toBeInTheDocument();rerender(<PaidMediaWorkspace platform="meta-ads" initial={[]}/>);fireEvent.change(screen.getByLabelText(/Ad account ID/),{target:{value:"1"}});expect(screen.getByText(/Live ad connectivity/i)).toBeInTheDocument()});
});
