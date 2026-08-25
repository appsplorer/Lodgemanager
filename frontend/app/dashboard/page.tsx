'use client';
import Link from 'next/link';
import {useEffect,useState} from 'react';
import {AppShell} from '@/components/AppShell';
import {api} from '@/lib/api';

type DashboardData={
 kpis:{members_total:number;members_active:number;average_attendance:number;dues_collection_rate:number;outstanding_dues:string;candidates_active:number;candidates_overdue:number;lodge_energy_score:number};
 attendance_trend:Array<{meeting:string;date:string;present:number}>;
 recent_activity:Array<{id?:string;occurred_at?:string;action?:string;object_type?:string}>;
};

export default function Dashboard(){
 const[data,setData]=useState<DashboardData|null>(null),[error,setError]=useState('');
 useEffect(()=>{let mounted=true;api<DashboardData>('/dashboard').then(x=>{if(mounted){setData(x);setError('')}}).catch(e=>{if(mounted)setError(e instanceof Error?e.message:'Dashboard failed to load')});return()=>{mounted=false}},[]);
 const kpis=data?[['Active members',String(data.kpis.members_active),`${data.kpis.members_total} total`],['Dues collected',`${Number(data.kpis.dues_collection_rate).toFixed(1)}%`,`Outstanding ${data.kpis.outstanding_dues}`],['Average attendance',String(data.kpis.average_attendance),'Recent meetings'],['Candidates',String(data.kpis.candidates_active),`${data.kpis.candidates_overdue} overdue`],['Lodge energy',String(data.kpis.lodge_energy_score),'Operational score']]:[];
 return <AppShell><div className="page-heading"><div><span className="eyebrow">Lodge health</span><h1>Dashboard</h1><p>Live tenant-scoped membership, meetings, finance and candidate progress.</p></div><Link className="primary button-link" href="/meetings">Create meeting</Link></div>
 {!data&&!error&&<section className="panel" aria-live="polite"><h3>Loading dashboard…</h3><p>Retrieving the latest lodge data.</p></section>}
 {error&&<section className="panel error-panel" role="alert"><h3>Dashboard unavailable</h3><p>{error}</p><button className="secondary" onClick={()=>location.reload()}>Retry</button></section>}
 {data&&<><div className="kpi-grid">{kpis.map(([a,b,c])=><article className="panel kpi" key={a}><small>{a}</small><strong>{b}</strong><span>{c}</span></article>)}</div><div className="dashboard-grid"><section className="panel"><span className="eyebrow">Attendance trend</span><h3>Recent meetings</h3>{data.attendance_trend.length?<div className="activity-list">{data.attendance_trend.map(x=><div className="activity-row" key={`${x.date}-${x.meeting}`}><b>{x.meeting}</b><span>{x.date} · {x.present} present</span></div>)}</div>:<p>No completed meetings yet. Create a meeting to begin attendance reporting.</p>}</section><section className="panel"><span className="eyebrow">Recent activity</span><h3>Audited changes</h3>{data.recent_activity.length?<div className="activity-list">{data.recent_activity.slice(0,6).map((x,i)=><div className="activity-row" key={x.id||`${x.occurred_at}-${i}`}><b>{(x.action||'Activity').replaceAll('.',' · ')}</b><span>{x.object_type||'System'}{x.occurred_at?` · ${new Date(x.occurred_at).toLocaleString()}`:''}</span></div>)}</div>:<p>No audited activity has been recorded for this lodge yet.</p>}</section></div></>}
 </AppShell>;
}
