"use strict";
const REPO="lucassebastianbehrens-lang/jarvis", RAW=`https://raw.githubusercontent.com/${REPO}/main/data/`, API="https://api.github.com/repos/"+REPO;
const $=s=>document.querySelector(s), $$=s=>[...document.querySelectorAll(s)];
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const eur=n=>(n??0).toLocaleString("de-DE",{style:"currency",currency:"EUR"});
const ls={get:(k,d)=>{try{return JSON.parse(localStorage.getItem(k))??d}catch(e){return d}},set:(k,v)=>{try{localStorage.setItem(k,JSON.stringify(v))}catch(e){}}};
let cfg=ls.get("jv_cfg",{talk:false}), brain=ls.get("jv_brain",{mem:[],proj:[],t:0}), hist=ls.get("jv_hist",[]);
const D={bots:[],runs:[],status:null,briefing:null,paper:null,agents:null,rech:null,lage:null,auto:null,auftr:null};
/* ---------- Speicher: Archiv (IndexedDB, praktisch unbegrenzt) ---------- */
const IDB=(()=>{let db;const open=()=>db||(db=new Promise((ok,no)=>{const r=indexedDB.open("jarvis",1);r.onupgradeneeded=()=>{r.result.createObjectStore("archiv",{autoIncrement:true});r.result.createObjectStore("kv")};r.onsuccess=()=>ok(r.result);r.onerror=()=>no(r.error)}));
  const tx=async(st,mode,fn)=>{const d=await open();return new Promise((ok,no)=>{const t=d.transaction(st,mode),s=t.objectStore(st),r=fn(s);t.oncomplete=()=>ok(r&&r.result);t.onerror=()=>no(t.error)})};
  return{add:v=>tx("archiv","readwrite",s=>s.add(v)).catch(()=>{}),all:()=>tx("archiv","readonly",s=>s.getAll()).catch(()=>[]),
    get:k=>tx("kv","readonly",s=>s.get(k)).catch(()=>undefined),set:(k,v)=>tx("kv","readwrite",s=>s.put(v,k)).catch(()=>{})}})();
function toast(t,ms=3200){const e=document.createElement("div");e.className="toast";e.setAttribute("role","status");e.textContent=t;($$("dialog[open]").at(-1)||document.body).append(e);setTimeout(()=>e.remove(),ms)}
function ago(ts){const m=Math.round((Date.now()/1000-ts)/60);if(m<1)return"gerade";if(m<60)return`vor ${m} Min`;const h=Math.round(m/60);return h<48?`vor ${h} h`:`vor ${Math.round(h/24)} T`}

/* ---------- Tabs ---------- */
function show(t){$$("nav button").forEach(b=>b.setAttribute("aria-selected",b.dataset.t===t));$$("section.tab").forEach(s=>s.classList.toggle("on",s.id==="t-"+t));location.hash=t;scrollTo(0,0);if(t==="stadt")try{cityStart()}catch(e){}if(t==="lage")try{globeStart()}catch(e){}}
$$("nav button").forEach(b=>b.onclick=()=>show(b.dataset.t));
if(location.hash&&$("#t-"+location.hash.slice(1)))show(location.hash.slice(1));

/* ---------- Daten (stündlich + beim Öffnen) ---------- */
async function getJSON(f){const r=await fetch(RAW+f+"?t="+Math.floor(Date.now()/60000));if(!r.ok)throw new Error(f+": "+r.status);return r.json()}
function ghHead(){return cfg.gh?{Authorization:"Bearer "+cfg.gh}:{}}
async function gh(path,body,method){const r=await fetch(API+path,{method:method||(body?"POST":"GET"),headers:{Accept:"application/vnd.github+json",...ghHead(),...(body?{"Content-Type":"application/json"}:{})},body:body?JSON.stringify(body):undefined});
  if(!r.ok)throw new Error("GitHub "+r.status+(r.status===401||r.status===403?" – Token prüfen":""));const t=await r.text();return t?JSON.parse(t):{}}
let lastLoad=0;
async function loadAll(){
  lastLoad=Date.now();$("#stamp").textContent="aktualisiere …";
  const jobs={bots:"bots.json",status:"status.json",briefing:"briefing.json",paper:"paper.json",agents:"agents.json",rech:"recherche.json",lage:"lage.json",auto:"automaton.json",auftr:"auftraege.json"};
  await Promise.all(Object.entries(jobs).map(async([k,f])=>{try{D[k]=await getJSON(f)}catch(e){console.warn(e)}}));
  try{D.runs=(await gh("/actions/runs?per_page=100")).workflow_runs||[]}catch(e){console.warn(e)}
  try{const{runs,...rest}=D;localStorage.setItem("jv_cache",JSON.stringify(rest))}catch(e){}
  $("#stamp").textContent="Stand "+new Date().toLocaleTimeString("de-DE",{hour:"2-digit",minute:"2-digit"});
  const st=D.status;$("#pulse").className="pulse "+(st?(st.ok?"ok":"bad"):"");
  renderTown();renderBriefing();renderTrading();renderAutomaton();renderNeu();renderLage();renderZentrale();
}
setInterval(loadAll,60*60*1000);
document.addEventListener("visibilitychange",()=>{if(!document.hidden&&Date.now()-lastLoad>10*60*1000)loadAll()});
