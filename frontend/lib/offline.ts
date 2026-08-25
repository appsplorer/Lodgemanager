'use client';

export type OfflineMutation = {
  id: string;
  idempotencyKey: string;
  path: string;
  method: string;
  body?: string;
  lodgeId?: string;
  createdAt: number;
  attempts: number;
  lastError?: string;
  baseUpdatedAt?: string;
};
type Sealed={iv:string;data:string};
type CacheRecord={key:string;lodgeId:string;expiresAt:number;touchedAt:number;sealed:Sealed};
type QueueRecord={id:string;createdAt:number;sealed:Sealed};

const DB_NAME='lodgeflow-private-offline-v3';
const DB_VERSION=1;
const MAX_CACHE_RECORDS=250;
const MAX_QUEUE_RECORDS=500;
const DEFAULT_TTL=24*60*60*1000;
let dbPromise:Promise<IDBDatabase>|null=null;

function database():Promise<IDBDatabase>{
 if(dbPromise)return dbPromise;
 dbPromise=new Promise((resolve,reject)=>{const r=indexedDB.open(DB_NAME,DB_VERSION);r.onupgradeneeded=()=>{const d=r.result;if(!d.objectStoreNames.contains('meta'))d.createObjectStore('meta');if(!d.objectStoreNames.contains('cache'))d.createObjectStore('cache',{keyPath:'key'});if(!d.objectStoreNames.contains('queue'))d.createObjectStore('queue',{keyPath:'id'})};r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)});
 return dbPromise;
}
function request<T>(r:IDBRequest<T>):Promise<T>{return new Promise((resolve,reject)=>{r.onsuccess=()=>resolve(r.result);r.onerror=()=>reject(r.error)})}
function txDone(tx:IDBTransaction):Promise<void>{return new Promise((resolve,reject)=>{tx.oncomplete=()=>resolve();tx.onerror=()=>reject(tx.error);tx.onabort=()=>reject(tx.error||new Error('IndexedDB transaction aborted'))})}
async function getOne<T>(name:string,key:IDBValidKey):Promise<T|undefined>{const d=await database(),tx=d.transaction(name,'readonly'),value=await request(tx.objectStore(name).get(key)) as T|undefined;await txDone(tx);return value}
async function getAll<T>(name:string):Promise<T[]>{const d=await database(),tx=d.transaction(name,'readonly'),value=await request(tx.objectStore(name).getAll()) as T[];await txDone(tx);return value}
async function putOne(name:string,value:unknown,key?:IDBValidKey):Promise<void>{const d=await database(),tx=d.transaction(name,'readwrite');if(key===undefined)tx.objectStore(name).put(value);else tx.objectStore(name).put(value,key);await txDone(tx)}
async function deleteKeys(name:string,keys:IDBValidKey[]):Promise<void>{if(!keys.length)return;const d=await database(),tx=d.transaction(name,'readwrite'),s=tx.objectStore(name);keys.forEach(k=>s.delete(k));await txDone(tx)}
async function clearStore(name:string):Promise<void>{const d=await database(),tx=d.transaction(name,'readwrite');tx.objectStore(name).clear();await txDone(tx)}
function b64(bytes:Uint8Array):string{let s='';bytes.forEach(b=>s+=String.fromCharCode(b));return btoa(s)}
function fromB64(s:string):Uint8Array{const raw=atob(s);return Uint8Array.from(raw,c=>c.charCodeAt(0))}

async function getDeviceKey():Promise<CryptoKey>{
 if(!globalThis.crypto?.subtle)throw new Error('Secure offline storage is unavailable in this browser.');
 const existing=await getOne<CryptoKey>('meta','device-aes-key');if(existing)return existing;
 const key=await crypto.subtle.generateKey({name:'AES-GCM',length:256},false,['encrypt','decrypt']);
 await putOne('meta',key,'device-aes-key');return key;
}
async function seal(value:unknown):Promise<Sealed>{const key=await getDeviceKey(),iv=crypto.getRandomValues(new Uint8Array(12)),raw=new TextEncoder().encode(JSON.stringify(value)),encrypted=await crypto.subtle.encrypt({name:'AES-GCM',iv},key,raw);return{iv:b64(iv),data:b64(new Uint8Array(encrypted))}}
async function unseal<T>(value:Sealed):Promise<T>{const key=await getDeviceKey(),plain=await crypto.subtle.decrypt({name:'AES-GCM',iv:fromB64(value.iv)},key,fromB64(value.data));return JSON.parse(new TextDecoder().decode(plain)) as T}


function rowsFromPayload(value:any):any[]{
 if(Array.isArray(value))return value;
 if(Array.isArray(value?.results))return value.results;
 return [];
}
export async function cachedBaseUpdatedAt(path:string,lodgeId:string):Promise<string|undefined>{
 try{
  const clean=path.split('?')[0].replace(/\/$/,'');
  const parts=clean.split('/').filter(Boolean);
  if(parts.length<2)return undefined;
  const id=parts[parts.length-1];
  if(!/^[0-9a-f-]{32,36}$/i.test(id))return undefined;
  const collection='/'+parts.slice(0,-1).join('/');
  const payload=await cacheGet<any>(collection,lodgeId);
  const row=rowsFromPayload(payload).find(x=>String(x?.id||'')===id);
  return typeof row?.updated_at==='string'?row.updated_at:undefined;
 }catch{return undefined}
}

export function offlineCacheKey(path:string,lodgeId=''):string{return`${lodgeId}::${path}`}
export async function cachePut<T>(path:string,lodgeId:string,value:T,ttl=DEFAULT_TTL):Promise<void>{const now=Date.now(),key=offlineCacheKey(path,lodgeId);await putOne('cache',{key,lodgeId,expiresAt:now+ttl,touchedAt:now,sealed:await seal(value)} satisfies CacheRecord);await trimCache()}
export async function cacheGet<T>(path:string,lodgeId:string):Promise<T|undefined>{try{const key=offlineCacheKey(path,lodgeId),r=await getOne<CacheRecord>('cache',key);if(!r)return undefined;if(r.expiresAt<Date.now()){await deleteKeys('cache',[key]);return undefined}await putOne('cache',{...r,touchedAt:Date.now()});return await unseal<T>(r.sealed)}catch{return undefined}}
export async function invalidateTenantCache(lodgeId:string):Promise<void>{const rows=await getAll<CacheRecord>('cache');await deleteKeys('cache',rows.filter(x=>x.lodgeId===lodgeId).map(x=>x.key))}
export async function cacheStats():Promise<{entries:number;queued:number;oldest?:number}>{const [cache,queue]=await Promise.all([getAll<CacheRecord>('cache'),getAll<QueueRecord>('queue')]);return{entries:cache.length,queued:queue.length,oldest:cache.length?Math.min(...cache.map(x=>x.touchedAt)):undefined}}
export async function queueMutation(input:Omit<OfflineMutation,'id'|'createdAt'|'attempts'|'idempotencyKey'> & {idempotencyKey?:string}):Promise<OfflineMutation>{const existing=await getAll<QueueRecord>('queue');if(existing.length>=MAX_QUEUE_RECORDS)throw new Error('Offline change queue is full. Reconnect and synchronize before making more offline edits.');const m:OfflineMutation={...input,id:crypto.randomUUID(),idempotencyKey:input.idempotencyKey||crypto.randomUUID(),createdAt:Date.now(),attempts:0};await putOne('queue',{id:m.id,createdAt:m.createdAt,sealed:await seal(m)} satisfies QueueRecord);emit();return m}
export async function queuedCount():Promise<number>{try{return(await getAll<QueueRecord>('queue')).length}catch{return 0}}
export async function listQueued():Promise<OfflineMutation[]>{const rows=(await getAll<QueueRecord>('queue')).sort((a,b)=>a.createdAt-b.createdAt),out:OfflineMutation[]=[];for(const r of rows){try{out.push(await unseal<OfflineMutation>(r.sealed))}catch{}}return out}
export async function removeQueued(id:string):Promise<void>{await deleteKeys('queue',[id]);emit()}
export async function updateQueued(m:OfflineMutation):Promise<void>{await putOne('queue',{id:m.id,createdAt:m.createdAt,sealed:await seal(m)} satisfies QueueRecord);emit()}
export async function purgePrivateOfflineData():Promise<void>{await Promise.all([clearStore('cache'),clearStore('queue')]);emit()}
export async function requestPersistentStorage():Promise<boolean>{return Boolean(navigator.storage?.persist&&await navigator.storage.persist())}
export async function bindOfflinePrincipal(userId:string|number):Promise<void>{
 const next=String(userId),current=await getOne<string>('meta','principal-id');
 if(current&&current!==next)await Promise.all([clearStore('cache'),clearStore('queue')]);
 await putOne('meta',next,'principal-id');emit();
}
export async function clearOfflinePrincipal():Promise<void>{await deleteKeys('meta',['principal-id']);}

async function trimCache(){const rows=(await getAll<CacheRecord>('cache')).sort((a,b)=>a.touchedAt-b.touchedAt);await deleteKeys('cache',rows.slice(0,Math.max(0,rows.length-MAX_CACHE_RECORDS)).map(x=>x.key))}
function emit(){if(typeof window!=='undefined')window.dispatchEvent(new CustomEvent('lodgeflow:offline-state'))}
