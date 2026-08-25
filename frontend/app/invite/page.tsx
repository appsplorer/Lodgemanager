'use client';

import Link from 'next/link';
import {Suspense, useState} from 'react';
import {useSearchParams} from 'next/navigation';
import {api} from '@/lib/api';
import {bindOfflinePrincipal} from '@/lib/offline';

function InvitationForm(){
 const params=useSearchParams(),token=params.get('token')||'';
 const[message,setMessage]=useState(token?'':'This invitation link is incomplete. Ask your lodge administrator for a new invitation.');
 const[busy,setBusy]=useState(false);
 async function submit(event:React.FormEvent<HTMLFormElement>){
  event.preventDefault();setBusy(true);setMessage('');const form=new FormData(event.currentTarget),password=String(form.get('password')||''),confirm=String(form.get('confirm')||'');
  if(password!==confirm){setMessage('The passwords do not match.');setBusy(false);return}
  try{const result=await api<{user:{id:string|number}}>('/auth/invitation',{method:'POST',body:JSON.stringify({token,password})},'');await bindOfflinePrincipal(result.user.id);location.assign('/dashboard')}
  catch(error){setMessage(error instanceof Error?error.message:'The invitation could not be accepted. Ask your administrator for a new link.')}
  finally{setBusy(false)}
 }
 return <main className="auth-page"><form className="auth-card" onSubmit={submit}><div className="brand-mark">LF</div><span className="eyebrow">Secure invitation</span><h1>Set up your account</h1><p>Create a strong password to activate your lodge access. Invitation links work once and expire automatically.</p><label>New password<input type="password" name="password" autoComplete="new-password" minLength={12} required disabled={!token||busy}/></label><label>Confirm password<input type="password" name="confirm" autoComplete="new-password" minLength={12} required disabled={!token||busy}/></label><small className="password-guidance">Use at least 12 characters and avoid common or entirely numeric passwords.</small><button className="primary large" disabled={!token||busy}>{busy?'Activating account…':'Activate secure account'}</button>{message&&<div className="alert error" role="alert">{message}</div>}<div className="auth-links"><Link href="/login">Return to sign in</Link></div></form></main>
}

export default function InvitePage(){return <Suspense fallback={<main className="auth-page"><div className="auth-card">Loading invitation…</div></main>}><InvitationForm/></Suspense>}
