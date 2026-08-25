'use client';

import Link from 'next/link';
import {Suspense, useState} from 'react';
import {useSearchParams} from 'next/navigation';
import {api} from '@/lib/api';

function ResetForm(){
 const params=useSearchParams(),token=params.get('token')||'';
 const[message,setMessage]=useState(token?'':'This reset link is incomplete. Request a new password-reset email.');
 const[complete,setComplete]=useState(false),[busy,setBusy]=useState(false);
 async function submit(event:React.FormEvent<HTMLFormElement>){event.preventDefault();setBusy(true);setMessage('');const form=new FormData(event.currentTarget),password=String(form.get('password')||''),confirm=String(form.get('confirm')||'');if(password!==confirm){setMessage('The passwords do not match.');setBusy(false);return}try{await api('/auth/password-reset/confirm',{method:'POST',body:JSON.stringify({token,password})},'');setComplete(true);setMessage('Your password has been changed. Existing authenticated sessions will be rejected automatically.')}catch(reason){setMessage(reason instanceof Error?reason.message:'The reset link is invalid or expired. Request another link.')}finally{setBusy(false)}}
 return <main className="auth-page"><form className="auth-card" onSubmit={submit}><div className="brand-mark">LF</div><span className="eyebrow">Secure recovery</span><h1>Choose a new password</h1>{complete?<><div className="alert success" role="status">{message}</div><Link className="button-link" href="/login">Sign in with the new password</Link></>:<><p>Reset links are single-use and expire automatically.</p><label>New password<input type="password" name="password" autoComplete="new-password" minLength={12} required disabled={!token||busy}/></label><label>Confirm password<input type="password" name="confirm" autoComplete="new-password" minLength={12} required disabled={!token||busy}/></label><small className="password-guidance">Use at least 12 characters and avoid common or entirely numeric passwords.</small><button className="primary large" disabled={!token||busy}>{busy?'Changing password…':'Change password'}</button>{message&&<div className="alert error" role="alert">{message}</div>}<div className="auth-links"><Link href="/forgot-password">Request another link</Link><Link href="/login">Return to sign in</Link></div></>}</form></main>
}

export default function ResetPasswordPage(){return <Suspense fallback={<main className="auth-page"><div className="auth-card">Loading secure reset…</div></main>}><ResetForm/></Suspense>}
