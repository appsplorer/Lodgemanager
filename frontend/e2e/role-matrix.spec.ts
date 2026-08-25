import {expect,test,type Page} from '@playwright/test';

const rolePassword=process.env.LOCAL_ROLE_PASSWORD || process.env.LOCAL_ADMIN_PASSWORD || 'LodgeFlowLocal123!';
const adminEmail=process.env.LOCAL_ADMIN_EMAIL || 'admin@lodgeflow.local';

async function login(page:Page,email:string,password=rolePassword){
  await page.goto('/login');
  await page.getByLabel('Email').fill(email);
  await page.getByLabel('Password').fill(password);
  await page.getByRole('button',{name:/sign in securely/i}).click();
  await expect(page).toHaveURL(/\/dashboard$/,{timeout:20_000});
  await page.waitForFunction(()=>Boolean(localStorage.getItem('lodgeflow:selected-lodge')));
}

async function tenantStatus(page:Page,path:string){
  return await page.evaluate(async requestedPath=>{
    const lodgeId=localStorage.getItem('lodgeflow:selected-lodge') || '';
    const response=await fetch(`/api${requestedPath}`,{credentials:'include',cache:'no-store',headers:{'X-Lodge-ID':lodgeId,'X-Requested-With':'LodgeFlow'}});
    return response.status;
  },path);
}

const roleMatrix=[
  {role:'secretary',expectedAllowed:'/members',expectedForbidden:'/expenses'},
  {role:'treasurer',expectedAllowed:'/dues/assessments',expectedForbidden:'/candidates'},
  {role:'membership',expectedAllowed:'/members',expectedForbidden:'/dues/assessments'},
  {role:'mentor',expectedAllowed:'/candidates',expectedForbidden:'/expenses'},
  {role:'auditor',expectedAllowed:'/audit',expectedForbidden:'/communications'},
  {role:'viewer',expectedAllowed:'/reports/catalog',expectedForbidden:'/reports/generate/R001?format=csv'},
] as const;

for(const {role,expectedAllowed,expectedForbidden} of roleMatrix){
  test(`${role} role permits its purpose and blocks a forbidden module`,async({page})=>{
    await login(page,`${role}@lodgeflow.local`);
    expect(await tenantStatus(page,expectedAllowed),`${role} allowed endpoint`).toBe(200);
    expect(await tenantStatus(page,expectedForbidden),`${role} forbidden endpoint`).toBe(403);
  });
}

test('owner reaches completed member, officer, candidate and settings workspaces',async({page})=>{
  await login(page,adminEmail,process.env.LOCAL_ADMIN_PASSWORD || rolePassword);
  for(const [path,heading] of [['/members','Members'],['/officers','Officers'],['/candidates','Candidates'],['/settings','Settings']] as const){
    await page.goto(path);
    await expect(page.getByRole('heading',{name:heading,level:1})).toBeVisible();
  }
  await page.goto('/members');
  const search=page.getByPlaceholder('Search members, candidates, meetings, documents…');
  await search.fill('Arthur');
  await expect(page.getByText('Arthur Bennett').first()).toBeVisible({timeout:10_000});
});

test('public account recovery pages expose complete accessible forms',async({page})=>{
  await page.goto('/forgot-password');
  await expect(page.getByRole('heading',{name:/reset/i})).toBeVisible();
  await expect(page.getByLabel(/email/i)).toBeVisible();
  await page.goto('/invite?token=invalid-test-token');
  await expect(page.getByLabel(/password/i).first()).toBeVisible();
});
