'use client';
import {useCallback,useEffect,useState} from 'react';

type AnalyticsConfig={enabled:boolean;requires_consent:boolean;google_measurement_id?:string;meta_pixel_id?:string};
type SiteConfig={settings?:{analytics?:AnalyticsConfig}};
type Consent='granted'|'denied'|null;
type MetaPixel=((...args:unknown[])=>void)&{queue?:unknown[][];loaded?:boolean;version?:string};
const CONSENT_KEY='lodgeflow:analytics-consent';

function loadScript(id:string,src:string){
 if(document.getElementById(id))return;
 const script=document.createElement('script');script.id=id;script.async=true;script.src=src;script.referrerPolicy='strict-origin-when-cross-origin';const nonce=document.querySelector<HTMLScriptElement>('script[nonce]')?.nonce;if(nonce)script.nonce=nonce;document.head.appendChild(script);
}
function startGoogle(id:string){
 const w=window as typeof window & {dataLayer?:unknown[];gtag?:(...args:unknown[])=>void};
 w.dataLayer=w.dataLayer||[];w.gtag=(...args:unknown[])=>{w.dataLayer?.push(args)};w.gtag('js',new Date());w.gtag('config',id,{anonymize_ip:true});loadScript('lodgeflow-ga4',`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(id)}`);
}
function startMeta(id:string){
 const w=window as typeof window & {fbq?:MetaPixel};
 if(!w.fbq){const fbq:MetaPixel=(...args:unknown[])=>{fbq.queue=fbq.queue||[];fbq.queue.push(args)};fbq.loaded=true;fbq.version='2.0';w.fbq=fbq}
 w.fbq?.('init',id);w.fbq?.('track','PageView');loadScript('lodgeflow-meta-pixel','https://connect.facebook.net/en_US/fbevents.js');
}

export function PublicAnalytics(){
 const[config,setConfig]=useState<AnalyticsConfig|null>(null),[consent,setConsent]=useState<Consent>(null),[show,setShow]=useState(false);
 useEffect(()=>{try{const value=localStorage.getItem(CONSENT_KEY);setConsent(value==='granted'||value==='denied'?value:null)}catch{};fetch('/api/public/site-config',{cache:'no-store'}).then(r=>r.ok?r.json():null).then((x:SiteConfig|null)=>setConfig(x?.settings?.analytics||null)).catch(()=>setConfig(null))},[]);
 useEffect(()=>{if(!config?.enabled)return;const allowed=!config.requires_consent||consent==='granted';setShow(Boolean(config.requires_consent&&consent===null));if(!allowed)return;if(config.google_measurement_id)startGoogle(config.google_measurement_id);if(config.meta_pixel_id)startMeta(config.meta_pixel_id)},[config,consent]);
 const choose=useCallback((value:Exclude<Consent,null>)=>{try{localStorage.setItem(CONSENT_KEY,value)}catch{};setConsent(value);setShow(false)},[]);
 if(!config?.enabled)return null;
 return <>{show&&<aside className="analytics-consent" role="dialog" aria-label="Analytics consent"><strong>Optional analytics</strong><span>Allow privacy-conscious website analytics and configured marketing pixels. Declining keeps them disabled.</span><div><button className="secondary" onClick={()=>choose('denied')}>Decline analytics</button><button className="primary" onClick={()=>choose('granted')}>Grant analytics</button></div></aside>}{config.requires_consent&&consent!==null&&!show&&<button className="analytics-preferences" onClick={()=>setShow(true)}>Analytics preferences</button>}</>;
}
