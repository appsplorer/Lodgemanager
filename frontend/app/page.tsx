import Link from 'next/link';
import type {Metadata} from 'next';
import {MarketingMotion} from '@/components/MarketingMotion';
import {CmsBlockRenderer,type CMSBlock} from '@/components/PublicCmsBlocks';
import {PublicAnalytics} from '@/components/PublicAnalytics';

type CMSPage={title:string;blocks:CMSBlock[];meta_title?:string;meta_description?:string;canonical_url?:string;og?:Record<string,string>};
const fallback:CMSPage={title:'LodgeFlow',meta_title:'LodgeFlow · Private Lodge Administration',meta_description:'Secure lodge administration for members, meetings, candidates, dues, finance, documents, communications and reporting.',blocks:[
 {type:'hero',eyebrow:'Private lodge administration',title:'Run the Lodge office with clarity, continuity and control.',body:'One secure workspace for members, officers, candidates, meetings, dues, finance, documents, communications and reporting—designed around the work Lodge officers actually do.',primary_label:'Open workspace',primary_href:'/login',secondary_label:'Explore features',secondary_href:'#features'},
 {type:'features',eyebrow:'Built around lodge work',title:'Everything officers need, without spreadsheet sprawl.',items:[
  {title:'Member records',body:'Profiles, status, degrees, key dates, custom fields, tags, notes, duplicate review and governed import/export.'},{title:'Officer continuity',body:'Current rosters, term history, succession planning and handover-ready records.'},{title:'Candidate journey',body:'Configurable stages, mentors, checklists, milestones and progression analytics.'},{title:'Meetings & minutes',body:'Recurring agendas, attendance, visitors and a draft → review → approved → locked minutes workflow.'},{title:'Dues & payments',body:'Variable dues, proration, arrears, late fees, statements, numbered receipts and payment links.'},{title:'Documents & communications',body:'Permission-aware files, merge templates, segmented messages, scheduled reminders and delivery logs.'},{title:'Finance',body:'Expenses, charity tracking, cash-runway signals and meeting/event economics.'},{title:'Reports & insights',body:'Membership, attendance, candidate and finance reporting plus 35 officer-focused insight tools.'}
 ]},
 {type:'security',eyebrow:'Private by design',title:'Your Lodge records stay inside your Lodge.',items:[{title:'Tenant isolation',body:'Server-side tenant scoping is enforced before application views execute.'},{title:'Granular RBAC',body:'View, create, edit, delete, export, approve and administrative permissions.'},{title:'MFA & audit chain',body:'TOTP MFA, rate limiting and tamper-evident audit history protect privileged work.'},{title:'Encrypted credentials',body:'Payment and infrastructure secrets remain encrypted server-side with rotation metadata.'}]},
 {type:'cta',eyebrow:'Ready for officer continuity',title:'One system the next Secretary can actually inherit.',primary_label:'Enter LodgeFlow',primary_href:'/login'}
]};

async function getPage():Promise<CMSPage>{
 const base=process.env.API_INTERNAL_URL||process.env.NEXT_PUBLIC_API_ORIGIN||'http://backend:8000/api';
 try{const r=await fetch(`${base}/public/pages/home`,{next:{revalidate:60}});if(r.ok)return await r.json()}catch{}
 return fallback;
}
export async function generateMetadata():Promise<Metadata>{const p=await getPage();return {title:p.meta_title||p.title,description:p.meta_description||fallback.meta_description,alternates:p.canonical_url?{canonical:p.canonical_url}:undefined,openGraph:{title:p.og?.title||p.meta_title||p.title,description:p.og?.description||p.meta_description,type:'website'}}}

export default async function Home(){const page=await getPage();return <main className="marketing"><PublicAnalytics/><MarketingMotion/><header className="marketing-nav"><div className="brand"><div className="brand-mark">LF</div><strong>LodgeFlow</strong></div><nav><a href="#features">Features</a><a href="#security">Security</a><a href="#pricing">Plans</a><Link className="button-link" href="/login">Sign in</Link></nav></header>{page.blocks.map((b,i)=><CmsBlockRenderer block={b} index={i} key={`${b.type}-${i}`}/>)}<footer>© 2026 LodgeFlow · Private lodge administration · Original implementation</footer></main>}
