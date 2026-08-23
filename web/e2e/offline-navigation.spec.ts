import {expect,test} from "@playwright/test";
const routes=["/","/seo","/seo/rank-tracking","/seo/site-crawl","/seo/competitor-gaps","/seo/content","/seo/aeo-geo","/ai-visibility","/backlinks","/outreach","/local-seo","/analytics","/google-ads","/meta-ads","/settings"];
test("all Beta 17 routes navigate with zero external-provider calls",async({page})=>{
 const external:string[]=[];
 page.on("request",request=>{const url=new URL(request.url());if(!["127.0.0.1","localhost"].includes(url.hostname))external.push(request.url())});
 for(const route of routes){const response=await page.goto(route,{waitUntil:"domcontentloaded"});expect(response?.status(),route).toBe(200);await expect(page.locator("body"),route).toContainText(/Nexora AI/i)}
 expect(external).toEqual([]);
});
