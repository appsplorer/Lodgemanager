'use client';

import Link from 'next/link';
import {useState} from 'react';
import {api} from '@/lib/api';

export default function ForgotPasswordPage(){
 const[message,setMessage]=useState(''),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 async function submit(event:React.FormEvent<HTMLFormElement>){event.preventDefault();setBusy(true);setError('');setMessage('');const form=new FormData(event.currentTarget);try{await api('/auth/password-reset/request',{method:'POST',body:JSON.stringify({email:form.get('email')})},'');setMessage('If that account exists, a single-use password-reset link has been sent. Check your inbox and spam folder.')}catch(reason){setError(reason instanceof Error?reason.message:'The request could not be processed.')}finally{setBusy(false)}}
 return <main className="auth-page"><form className="auth-card" onSubmit={submit}><div className="brand-mark">LF</div><span className="eyebrow">Account recovery</span><h1>Reset your password</h1><p>Enter your account email. For privacy, the response is the same whether or not an account exists.</p><label>Email<input type="email" name="email" autoComplete="email" required disabled={busy}/></label><button className="primary large" disabled={busy}>{busy?'Sending securely…':'Send reset link'}</button>{message&&<div className="alert success" role="status">{message}</div>}{error&&<div className="alert error" role="alert">{error}</div>}<div className="auth-links"><Link href="/login">Return to sign in</Link></div></form></main>
}
