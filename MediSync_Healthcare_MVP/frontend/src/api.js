const BASE=import.meta.env.VITE_API_BASE_URL||'http://127.0.0.1:8000/api'
export async function api(path,options={}){
 const headers={'Content-Type':'application/json',...(options.headers||{})}
 const token=localStorage.getItem('medisync_token'); if(token) headers.Authorization=`Bearer ${token}`
 const r=await fetch(BASE+path,{...options,headers}); const t=await r.text(); let d=null
 try{d=t?JSON.parse(t):null}catch{d=t}
 if(!r.ok) throw new Error(d?.detail||`Request failed (${r.status})`)
 return d
}
export const login=(email,password)=>api('/auth/login',{method:'POST',body:JSON.stringify({email,password})})
