import {expect,test,Page} from '@playwright/test';
import AxeBuilder from '@axe-core/playwright';

const adminEmail=process.env.LOCAL_ADMIN_EMAIL || 'admin@lodgeflow.local';
const adminPassword=process.env.LOCAL_ADMIN_PASSWORD || 'LodgeFlowLocal123!';

async function login(page:Page){
  await page.goto('/login');
  await page.getByLabel('Email').fill(adminEmail);
  await page.getByLabel('Password').fill(adminPassword);
  await page.getByRole('button',{name:/sign in securely/i}).click();
  await expect(page).toHaveURL(/\/dashboard$/,{timeout:20_000});
  await expect(page.getByRole('heading',{name:'Dashboard'})).toBeVisible();
}

test('public website renders without horizontal overflow and has no serious axe violations',async({page})=>{
  await page.goto('/');
  await expect(page.locator('body')).toBeVisible();
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth-document.documentElement.clientWidth);
  expect(overflow).toBeLessThanOrEqual(2);
  const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
  expect(result.violations.filter(v=>['critical','serious'].includes(v.impact||''))).toEqual([]);
});

test('authentication reaches a tenant-scoped live dashboard',async({page})=>{
  await login(page);
  await expect(page.getByText(/Active members/i)).toBeVisible();
  await expect(page.getByText(/Audited changes/i)).toBeVisible();
  await expect(page.getByText(/Loading dashboard/i)).toHaveCount(0,{timeout:20_000});
});

test('primary workspace navigation remains keyboard reachable',async({page})=>{
  await login(page);
  const links=page.getByRole('link');
  expect(await links.count()).toBeGreaterThan(3);
  await page.keyboard.press('Tab');
  const focused=page.locator(':focus');
  await expect(focused).toBeVisible();
});

test('authenticated dashboard has no serious axe violations',async({page})=>{
  await login(page);
  const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze();
  expect(result.violations.filter(v=>['critical','serious'].includes(v.impact||''))).toEqual([]);
});

test('warmed primary page LCP stays within the release budget',async({page},testInfo)=>{
  const budget=Number(process.env.LCP_BUDGET_MS || '2500');
  await page.addInitScript(()=>{
    (window as typeof window & {__lodgeflowLcp?:number}).__lodgeflowLcp=0;
    try{
      new PerformanceObserver(list=>{
        const entries=list.getEntries();
        const last=entries[entries.length-1] as PerformanceEntry & {renderTime?:number;loadTime?:number};
        if(last)(window as typeof window & {__lodgeflowLcp?:number}).__lodgeflowLcp=last.renderTime||last.loadTime||last.startTime;
      }).observe({type:'largest-contentful-paint',buffered:true});
    }catch{/* Unsupported observers are caught by the >0 assertion below. */}
  });
  await page.goto('/');
  await page.waitForLoadState('networkidle');
  await page.reload();
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(750);
  const lcp=await page.evaluate(()=>(window as typeof window & {__lodgeflowLcp?:number}).__lodgeflowLcp||0);
  await testInfo.attach('warmed-lcp.json',{body:Buffer.from(JSON.stringify({lcp_ms:lcp,budget_ms:budget,project:testInfo.project.name},null,2)),contentType:'application/json'});
  expect(lcp,'Largest Contentful Paint entry was not observed').toBeGreaterThan(0);
  expect(lcp,'warmed primary page LCP').toBeLessThan(budget);
});
