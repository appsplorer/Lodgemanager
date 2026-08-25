'use client';
import {cacheGet,cachePut,cachedBaseUpdatedAt,invalidateTenantCache,queueMutation,type OfflineMutation} from './offline';
const ORIGIN=(process.env.NEXT_PUBLIC_API_ORIGIN||'/api').replace(/\/$/,'');
const OFFLINE_BLOCKED=[/^\/auth\//,/^\/mfa\//,/^\/billing\//,/^\/dues\/(payments|assessments)/,/^\/platform\//,/^\/settings\/(users|custom-roles)/,/payment-link/,/record-payment/,/\/(waive|adjust|reverse|approve)$/,/dues\/cycles\/.*\/(generate|late-fees|transition)/,/webhook/,/impersonat/,/\/transition$/,/\/send$/,/\/merge$/,/\/anonymize$/,/members\/bulk/,/export-approvals/,/credential/,/checkout/,/portal/];
class ApiError extends Error{status:number;constructor(status:number,message:string){super(message);this.status=status}}
export function selectedLodge():string{return typeof window==='undefined'?'':localStorage.getItem('lodgeflow:selected-lodge')||''}
export function setSelectedLodge(id:string){localStorage.setItem('lodgeflow:selected-lodge',id);window.dispatchEvent(new CustomEvent('lodgeflow:lodge-change',{detail:id}))}
function csrf(){if(typeof document==='undefined')return'';return document.cookie.split('; ').find(x=>x.startsWith('csrftoken='))?.split('=')[1]||''}
function blockedOffline(path:string){return OFFLINE_BLOCKED.some(x=>x.test(path))}
function makeHeaders(init:RequestInit,lodgeId:string,idempotencyKey?:string,baseUpdatedAt?:string){const h=new Headers(init.headers||{});if(!(init.body instanceof FormData)&&init.body!==undefined)h.set('Content-Type','application/json');const token=csrf();if(token)h.set('X-CSRFToken',token);if(lodgeId)h.set('X-Lodge-ID',lodgeId);if(idempotencyKey)h.set('Idempotency-Key',idempotencyKey);if(baseUpdatedAt)h.set('X-LodgeFlow-Base-Updated-At',baseUpdatedAt);h.set('X-Requested-With','LodgeFlow');return h}
function url(path:string){return`${ORIGIN}${path.startsWith('/')?path:`/${path}`}`}
async function ensureCsrf():Promise<void>{if(csrf())return;const r=await fetch(url('/csrf/'),{credentials:'include',cache:'no-store',headers:{'X-Requested-With':'LodgeFlow'}});if(!r.ok)throw await httpError(r)}
function canUseCachedError(e:unknown){return e instanceof TypeError||(e instanceof ApiError&&(e.status===429||e.status>=500))}

export async function api<T=Record<string,unknown>>(path:string,init:RequestInit={},lodgeId=selectedLodge()):Promise<T>{
 const method=(init.method||'GET').toUpperCase();
 if(method==='GET'){
  try{const r=await fetch(url(path),{...init,credentials:'include',headers:makeHeaders(init,lodgeId),cache:'no-store'});if(!r.ok)throw await httpError(r);const data=await parse<T>(r);void cachePut(path,lodgeId,data);return data}
  catch(e){if(canUseCachedError(e)){const cached=await cacheGet<T>(path,lodgeId);if(cached!==undefined)return cached}if(e instanceof ApiError&&(e.status===401||e.status===403))void invalidateTenantCache(lodgeId);throw e}
 }
 const queueable=!blockedOffline(path)&&!(init.body instanceof FormData);const idem=queueable?crypto.randomUUID():undefined;const baseUpdatedAt=queueable?await cachedBaseUpdatedAt(path,lodgeId):undefined;
 if(typeof navigator!=='undefined'&&!navigator.onLine){
  if(!queueable)throw new Error(init.body instanceof FormData?'File uploads require an internet connection so files can be malware-scanned before storage.':'This security, approval or financial-provider action requires an internet connection.');
  const q=await queueMutation({path,method,body:typeof init.body==='string'?init.body:undefined,lodgeId,idempotencyKey:idem,baseUpdatedAt});return{offlineQueued:true,queueId:q.id} as T;
 }
 try{await ensureCsrf();const r=await fetch(url(path),{...init,method,credentials:'include',headers:makeHeaders(init,lodgeId,idem,baseUpdatedAt),cache:'no-store'});if(!r.ok)throw await httpError(r);const data=await parse<T>(r);void invalidateTenantCache(lodgeId);return data}
 catch(e){if(queueable&&e instanceof TypeError){const q=await queueMutation({path,method,body:typeof init.body==='string'?init.body:undefined,lodgeId,idempotencyKey:idem,baseUpdatedAt});return{offlineQueued:true,queueId:q.id} as T}throw e}
}
export async function replayMutation(m:OfflineMutation):Promise<'done'|'retry'|'conflict'>{
 try{await ensureCsrf();const r=await fetch(url(m.path),{method:m.method,body:m.body,credentials:'include',headers:makeHeaders({},m.lodgeId||'',m.idempotencyKey,m.baseUpdatedAt),cache:'no-store'});if(r.ok){if(m.lodgeId)void invalidateTenantCache(m.lodgeId);return'done'}if(r.status===401||r.status===403||r.status===429||r.status>=500)return'retry';return'conflict'}catch(e){return e instanceof TypeError?'retry':'conflict'}
}
export async function apiBlob(path:string,lodgeId=selectedLodge()):Promise<Blob>{if(typeof navigator!=='undefined'&&!navigator.onLine)throw new Error('Media previews require an internet connection.');const init:RequestInit={method:'GET'};const r=await fetch(url(path),{...init,credentials:'include',headers:makeHeaders(init,lodgeId),cache:'no-store'});if(!r.ok)throw await httpError(r);return await r.blob()}
export async function apiDownload(path:string,filename:string,lodgeId=selectedLodge(),init:RequestInit={}):Promise<void>{if(typeof navigator!=='undefined'&&!navigator.onLine)throw new Error('Downloads and generated exports require an internet connection.');const method=(init.method||'GET').toUpperCase();if(method!=='GET'&&method!=='HEAD')await ensureCsrf();const r=await fetch(url(path),{...init,method,credentials:'include',headers:makeHeaders(init,lodgeId),cache:'no-store'});if(!r.ok)throw await httpError(r);const blob=await r.blob(),u=URL.createObjectURL(blob),a=document.createElement('a');a.href=u;a.download=filename;document.body.appendChild(a);a.click();a.remove();URL.revokeObjectURL(u)}
async function parse<T>(r:Response):Promise<T>{if(r.status===204)return{} as T;const ct=r.headers.get('content-type')||'';return ct.includes('application/json')?await r.json() as T:({text:await r.text()} as T)}
async function httpError(r:Response):Promise<ApiError>{let message=`Request failed (${r.status})`;try{const x=await r.json();message=x.detail||x.error||message}catch{}return new ApiError(r.status,message)}
