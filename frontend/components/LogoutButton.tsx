'use client';
import {api} from '@/lib/api';
import {clearOfflinePrincipal,purgePrivateOfflineData,queuedCount} from '@/lib/offline';
import {useConfirmDialog} from '@/components/AppDialog';

export function LogoutButton(){
 const confirmDialog=useConfirmDialog();
 async function logout(){
  const pending=await queuedCount();
  if(pending>0){
   const ok=await confirmDialog.ask(`You have ${pending} unsynced offline change(s). Signing out will discard them from this device. Sign out anyway?`,{title:'Unsynced changes',danger:true,confirmLabel:'Sign out'});
   if(!ok)return;
  }
  try{await api('/auth/logout',{method:'POST',body:'{}'},'')}
  finally{await purgePrivateOfflineData();await clearOfflinePrincipal();location.assign('/login')}
 }
 return <><button className="sidebar-logout" onClick={()=>void logout()}>Sign out</button>{confirmDialog.dialog}</>;
}
