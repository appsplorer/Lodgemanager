'use client';
import {useEffect,useState} from 'react';
import {api,selectedLodge,setSelectedLodge} from '@/lib/api';
import {bindOfflinePrincipal} from '@/lib/offline';

type Tenant={id:string;name:string;lodge_number?:string;role?:string};
type Impersonation={active:boolean;id?:string;actor?:string;target?:string;expires_at?:string};
type Bootstrap={tenant:Tenant;tenants:Tenant[];user:{id:string|number;username:string;role:string};impersonation?:Impersonation};

export function WorkspaceIdentity(){
 const[data,setData]=useState<Bootstrap|null>(null),[stopping,setStopping]=useState(false),[error,setError]=useState('');
 useEffect(()=>{let alive=true;api<Bootstrap>('/workspace/bootstrap',{},selectedLodge()).then(x=>{if(!alive)return;setData(x);void bindOfflinePrincipal(x.user.id);if(!selectedLodge()&&x.tenant?.id)localStorage.setItem('lodgeflow:selected-lodge',x.tenant.id)}).catch(()=>{if(navigator.onLine)location.assign('/login')});return()=>{alive=false}},[]);
 function change(id:string){if(!id||id===selectedLodge())return;setSelectedLodge(id);location.reload()}
 async function stop(){setStopping(true);setError('');try{await api('/platform/impersonation/stop',{method:'POST',body:'{}'});location.reload()}catch(e){setError(e instanceof Error?e.message:'Could not end impersonation');setStopping(false)}}
 return <>{data?.impersonation?.active&&<div className="impersonation-banner" role="status" aria-live="polite"><div><strong>Support impersonation active</strong><span>{data.impersonation.actor} is viewing this workspace as {data.impersonation.target}. {data.impersonation.expires_at?`Ends ${new Date(data.impersonation.expires_at).toLocaleTimeString()}.`:''}</span>{error&&<small>{error}</small>}</div><button className="secondary" disabled={stopping} onClick={()=>void stop()}>{stopping?'Ending…':'End impersonation'}</button></div>}<div className="workspace-identity"><div><small>{data?.tenant?.lodge_number?`Lodge ${data.tenant.lodge_number}`:'Private lodge'}</small><b>{data?.tenant?.name||'LodgeFlow workspace'}</b></div>{(data?.tenants?.length||0)>1&&!data?.impersonation?.active&&<select aria-label="Switch lodge" value={data?.tenant?.id||selectedLodge()} onChange={e=>change(e.target.value)}>{data?.tenants.map(t=><option value={t.id} key={t.id}>{t.name}</option>)}</select>}</div></>
}
