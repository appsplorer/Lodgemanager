'use client';
import {useCallback,useState} from 'react';

type ConfirmRequest={title:string;message:string;danger:boolean;confirmLabel:string;resolve:(value:boolean)=>void};
type PromptRequest={title:string;message:string;value:string;secret:boolean;confirmLabel:string;resolve:(value:string|null)=>void};

export function useConfirmDialog(){
 const[request,setRequest]=useState<ConfirmRequest|null>(null);
 const ask=useCallback((message:string,options:{title?:string;danger?:boolean;confirmLabel?:string}={})=>new Promise<boolean>(resolve=>setRequest({title:options.title||'Confirm action',message,danger:Boolean(options.danger),confirmLabel:options.confirmLabel||'Confirm',resolve})),[]);
 function finish(value:boolean){if(!request)return;request.resolve(value);setRequest(null)}
 const dialog=request?<div className="dialog-backdrop" role="presentation" onMouseDown={e=>{if(e.target===e.currentTarget)finish(false)}}><section className="app-dialog" role="dialog" aria-modal="true" aria-labelledby="confirm-title"><span className="eyebrow">Confirmation</span><h3 id="confirm-title">{request.title}</h3><p>{request.message}</p><div className="console-actions"><button className="secondary" onClick={()=>finish(false)}>Cancel</button><button className={request.danger?'primary danger':'primary'} onClick={()=>finish(true)} autoFocus>{request.confirmLabel}</button></div></section></div>:null;
 return {ask,dialog};
}

export function useTextPromptDialog(){
 const[request,setRequest]=useState<PromptRequest|null>(null);const[input,setInput]=useState('');
 const ask=useCallback((message:string,options:{title?:string;value?:string;secret?:boolean;confirmLabel?:string}={})=>new Promise<string|null>(resolve=>{setInput(options.value||'');setRequest({title:options.title||'Provide value',message,value:options.value||'',secret:Boolean(options.secret),confirmLabel:options.confirmLabel||'Continue',resolve})}),[]);
 function finish(value:string|null){if(!request)return;request.resolve(value);setRequest(null);setInput('')}
 const dialog=request?<div className="dialog-backdrop" role="presentation"><form className="app-dialog" role="dialog" aria-modal="true" aria-labelledby="prompt-title" onSubmit={e=>{e.preventDefault();finish(input)}}><span className="eyebrow">Secure action</span><h3 id="prompt-title">{request.title}</h3><p>{request.message}</p><textarea className="json-editor" rows={6} value={input} onChange={e=>setInput(e.target.value)} autoFocus spellCheck={false}/><div className="console-actions"><button type="button" className="secondary" onClick={()=>finish(null)}>Cancel</button><button className="primary">{request.confirmLabel}</button></div></form></div>:null;
 return {ask,dialog};
}

type StepUpValue={password:string;code:string};
type StepUpRequest={title:string;message:string;resolve:(value:StepUpValue|null)=>void};

export function useStepUpDialog(){
 const[request,setRequest]=useState<StepUpRequest|null>(null);const[password,setPassword]=useState('');const[code,setCode]=useState('');
 const ask=useCallback((message='Re-enter your password. If MFA is enrolled, enter the current authenticator code too.',options:{title?:string}={})=>new Promise<StepUpValue|null>(resolve=>{setPassword('');setCode('');setRequest({title:options.title||'Verify your identity',message,resolve})}),[]);
 function finish(value:StepUpValue|null){if(!request)return;request.resolve(value);setRequest(null);setPassword('');setCode('')}
 const dialog=request?<div className="dialog-backdrop" role="presentation"><form className="app-dialog" role="dialog" aria-modal="true" aria-labelledby="step-up-title" onSubmit={e=>{e.preventDefault();finish({password,code})}}><span className="eyebrow">Step-up authentication</span><h3 id="step-up-title">{request.title}</h3><p>{request.message}</p><label><span>Password</span><input type="password" autoComplete="current-password" value={password} onChange={e=>setPassword(e.target.value)} required autoFocus/></label><label><span>Authenticator code <small>(when MFA is enrolled)</small></span><input inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{6}" maxLength={6} value={code} onChange={e=>setCode(e.target.value.replace(/\D/g,'').slice(0,6))}/></label><div className="console-actions"><button type="button" className="secondary" onClick={()=>finish(null)}>Cancel</button><button className="primary">Verify & continue</button></div></form></div>:null;
 return {ask,dialog};
}
