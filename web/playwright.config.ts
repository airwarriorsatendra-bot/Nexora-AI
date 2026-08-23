import {defineConfig} from "@playwright/test";
export default defineConfig({
 testDir:"./e2e",timeout:120_000,workers:1,retries:0,reporter:"line",
 use:{baseURL:"http://127.0.0.1:3102",headless:true,navigationTimeout:10_000,launchOptions:{executablePath:"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"}},
});
