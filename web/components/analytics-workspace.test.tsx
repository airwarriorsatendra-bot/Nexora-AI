// @vitest-environment jsdom
import "@testing-library/jest-dom/vitest";
import {cleanup,fireEvent,render,screen,waitFor} from "@testing-library/react";
import {afterEach,describe,expect,it,vi} from "vitest";
import {AnalyticsWorkspace} from "./analytics-workspace";
import * as api from "../lib/api";
const data={report:null,gsc:{},ga4:{},history:[],gsc_resources:{summary:{clicks:10,impressions:100,average_position:4,source:"GOOGLE_SEARCH_CONSOLE"},queries:[{query:"alpha",clicks:10,source:"GOOGLE_SEARCH_CONSOLE"}],pages:[],history:[]},ga4_resources:{summary:[{sessions:20,activeUsers:15,source:"GOOGLE_ANALYTICS_4"}],traffic:[],pages:[],acquisition:[],events:[],devices:[],countries:[]}};
afterEach(()=>{cleanup();vi.restoreAllMocks()});
describe("AnalyticsWorkspace",()=>{
 it("labels separated sources and uses N/A for missing evidence",()=>{render(<AnalyticsWorkspace data={data}/>);expect(screen.getAllByText("Google Search Console").length).toBeGreaterThan(0);expect(screen.getAllByText("Google Analytics 4").length).toBeGreaterThan(0);expect(screen.getAllByText("N/A").length).toBeGreaterThan(0);expect(screen.getAllByText(/chart requires at least two/)).toHaveLength(2)});
 it("renders query evidence and requests server filtering",async()=>{vi.spyOn(api,"getAnalyticsResource").mockResolvedValue({items:[{query:"alpha",clicks:10,source:"GOOGLE_SEARCH_CONSOLE"}],total:1,limit:25,offset:0,has_more:false});render(<AnalyticsWorkspace data={data}/>);fireEvent.click(screen.getByRole("tab",{name:"GSC queries"}));fireEvent.change(screen.getByLabelText("Filter evidence"),{target:{value:"alpha"}});fireEvent.click(screen.getByRole("button",{name:"Apply"}));await waitFor(()=>expect(api.getAnalyticsResource).toHaveBeenCalled());expect(screen.getByText("alpha")).toBeInTheDocument()});
 it("shows exports and source-separation copy",()=>{render(<AnalyticsWorkspace data={data}/>);fireEvent.click(screen.getByRole("tab",{name:"Cross-source evidence"}));expect(screen.getByText(/attribution is not inferred/i)).toBeInTheDocument();fireEvent.click(screen.getByRole("tab",{name:"Exports"}));expect(screen.getByText("gsc queries").getAttribute("href")).toContain("/api/nexora/analytics/exports/gsc-queries?")});
 it("keeps Google refresh explicit and requires resource plus dates",()=>{render(<AnalyticsWorkspace data={data}/>);expect(screen.getByRole("button",{name:/Explicit refresh/})).toBeDisabled();expect(screen.getByText(/Google is contacted only/)).toBeInTheDocument()});
});
