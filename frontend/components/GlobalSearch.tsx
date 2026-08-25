'use client';

import Link from 'next/link';
import {useEffect,useState} from 'react';
import {api,selectedLodge} from '@/lib/api';

type SearchResult={type:string;id:string;title:string;subtitle:string;path:string};
const destination:Record<string,string>={member:'/members',candidate:'/candidates',meeting:'/meetings',document:'/documents'};

export function GlobalSearch(){
 const[query,setQuery]=useState(''),[rows,setRows]=useState<SearchResult[]>([]),[open,setOpen]=useState(false),[error,setError]=useState('');
 useEffect(()=>{if(query.trim().length<2){setRows([]);setOpen(false);return}const timer=window.setTimeout(()=>{api<{results:SearchResult[]}>(`/search?q=${encodeURIComponent(query.trim())}&limit=8`,{},selectedLodge()).then(result=>{setRows(result.results||[]);setOpen(true);setError('')}).catch(reason=>{setRows([]);setOpen(true);setError(reason instanceof Error?reason.message:'Search unavailable')})},250);return()=>window.clearTimeout(timer)},[query]);
 return <div className="global-search"><label><span className="sr-only">Search authorized lodge records</span><input type="search" value={query} onChange={event=>setQuery(event.target.value)} onFocus={()=>query.length>=2&&setOpen(true)} placeholder="Search members, candidates, meetings, documents…" aria-expanded={open} aria-controls="global-search-results"/></label>{open&&<div id="global-search-results" className="global-search-results">{error&&<div className="alert error">{error}</div>}{rows.map(row=><Link href={destination[row.type]||'/dashboard'} key={`${row.type}-${row.id}`} onClick={()=>setOpen(false)}><span className="report-badge">{row.type}</span><div><b>{row.title}</b><small>{row.subtitle||'Authorized record'}</small></div></Link>)}{!error&&!rows.length&&<small>No authorized results.</small>}<button className="link-button" onClick={()=>setOpen(false)}>Close search</button></div>}</div>
}
