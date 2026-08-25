import {notFound} from 'next/navigation';
import type {Metadata} from 'next';
import Link from 'next/link';
import {MarketingMotion} from '@/components/MarketingMotion';
import {CmsBlockRenderer,type CMSBlock} from '@/components/PublicCmsBlocks';
import {PublicAnalytics} from '@/components/PublicAnalytics';

type PageData={slug:string;title:string;blocks:CMSBlock[];meta_title?:string;meta_description?:string;canonical_url?:string;robots_index?:boolean;og?:Record<string,string>};
async function getPage(slug:string):Promise<PageData|null>{const base=process.env.API_INTERNAL_URL||process.env.NEXT_PUBLIC_API_ORIGIN||'http://backend:8000/api';try{const r=await fetch(`${base}/public/pages/${encodeURIComponent(slug)}`,{next:{revalidate:60}});if(r.ok)return await r.json()}catch{}return null}
export async function generateMetadata({params}:{params:Promise<{slug:string}>}):Promise<Metadata>{const{slug}=await params;const p=await getPage(slug);if(!p)return {};return {title:p.meta_title||p.title,description:p.meta_description,robots:p.robots_index===false?{index:false,follow:false}:undefined,alternates:p.canonical_url?{canonical:p.canonical_url}:undefined,openGraph:{title:p.og?.title||p.meta_title||p.title,description:p.og?.description||p.meta_description,type:'website'}}}
export default async function CmsRoute({params}:{params:Promise<{slug:string}>}){const{slug}=await params;const page=await getPage(slug);if(!page)notFound();return <main className="marketing"><PublicAnalytics/><MarketingMotion/><header className="marketing-nav"><Link href="/" className="brand"><div className="brand-mark">LF</div><strong>LodgeFlow</strong></Link><nav><Link href="/">Home</Link><Link className="button-link" href="/login">Sign in</Link></nav></header>{page.blocks.map((b,i)=><CmsBlockRenderer block={b} index={i} key={`${b.type}-${i}`}/>) }<footer>© 2026 LodgeFlow · Private lodge administration</footer></main>}
