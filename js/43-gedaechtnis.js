"use strict";
/* ---------- Gedächtnis ---------- */
function saveBrain(){brain.t=Date.now();ls.set("jv_brain",brain);renderBrain();clearTimeout(saveBrain.t);saveBrain.t=setTimeout(pushBrain,4000)}
function remember(text){text=text.trim();if(!text||brain.mem.some(m=>m.x.toLowerCase()===text.toLowerCase()))return false;brain.mem.push({x:text,t:Date.now()});saveBrain();return true}
function renderBrain(){
  $("#memList").innerHTML=brain.mem.map((m,i)=>`<div class="mem"><span>${esc(m.x)}</span><button class="x" data-dm="${i}" aria-label="Vergessen">✕</button></div>`).join("")||`<p class="muted small">Noch nichts. Sag einfach „Merk dir …“.</p>`;
  $("#projList").innerHTML=brain.proj.map((p,i)=>`<div class="panel" style="margin:8px 0"><div class="row" style="justify-content:space-between"><b>${esc(p.titel)}</b><button class="x" data-dp="${i}" aria-label="Projekt entfernen">✕</button></div>
    ${p.schritte.map((s,j)=>`<div class="mem"><input type="checkbox" data-ps="${i}:${j}" ${s.ok?"checked":""} aria-label="erledigt"><span>${esc(s.x)}</span><button class="btn" data-run="${i}:${j}" style="padding:4px 10px">Machen</button></div>`).join("")}</div>`).join("")||`<p class="muted small">Sag „Plane …“ und Jarvis legt ein Projekt an.</p>`;
  $$("[data-dm]").forEach(b=>b.onclick=()=>{brain.mem.splice(b.dataset.dm,1);saveBrain()});
  $$("[data-dp]").forEach(b=>b.onclick=()=>{brain.proj.splice(b.dataset.dp,1);saveBrain()});
  $$("[data-ps]").forEach(c=>c.onchange=()=>{const[i,j]=c.dataset.ps.split(":");brain.proj[i].schritte[j].ok=c.checked;saveBrain()});
  $$("[data-run]").forEach(b=>b.onclick=()=>{const[i,j]=b.dataset.run.split(":"),p=brain.proj[i];$("#dlgBrain").close();show("jarvis");
    ask(`Projekt „${p.titel}“, Schritt: ${p.schritte[j].x}. Erledige diesen Schritt jetzt so weit du kannst und liefere das Ergebnis.`)});
  $("#brainSync").textContent=cfg.gh&&cfg.pass?"Wird verschlüsselt in GitHub gesichert und auf allen Geräten abgeglichen.":"Nur auf diesem Gerät. Für Sicherung + Abgleich: GitHub-Token und Gedächtnis-Passwort eintragen.";
}
$("#memAdd").onclick=()=>{if(remember($("#memNew").value))$("#memNew").value=""};
// Verschlüsselte Sicherung: data/gehirn.enc (AES-GCM, Schlüssel aus deinem Passwort)
const te=new TextEncoder(),td=new TextDecoder(),b64=u=>btoa(String.fromCharCode(...u)),ub64=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
async function key(salt){const k=await crypto.subtle.importKey("raw",te.encode(cfg.pass),"PBKDF2",false,["deriveKey"]);
  return crypto.subtle.deriveKey({name:"PBKDF2",salt,iterations:200000,hash:"SHA-256"},k,{name:"AES-GCM",length:256},false,["encrypt","decrypt"])}
async function pushBrain(){if(!cfg.gh||!cfg.pass)return;try{
  const salt=crypto.getRandomValues(new Uint8Array(16)),iv=crypto.getRandomValues(new Uint8Array(12));
  const ct=new Uint8Array(await crypto.subtle.encrypt({name:"AES-GCM",iv},await key(salt),te.encode(JSON.stringify(brain))));
  const body=JSON.stringify({v:1,salt:b64(salt),iv:b64(iv),data:b64(ct)});let sha;
  try{sha=(await gh("/contents/data/gehirn.enc"))?.sha}catch(e){}
  await gh("/contents/data/gehirn.enc",{message:"Gedächtnis gesichert (verschlüsselt)",content:btoa(body),sha},"PUT")}catch(e){console.warn("Sicherung",e)}}
async function pullBrain(){if(!cfg.gh||!cfg.pass)return;try{
  const f=await gh("/contents/data/gehirn.enc"),j=JSON.parse(atob(f.content.replace(/\n/g,"")));
  const pt=await crypto.subtle.decrypt({name:"AES-GCM",iv:ub64(j.iv)},await key(ub64(j.salt)),ub64(j.data));
  const remote=JSON.parse(td.decode(pt));if((remote.t||0)>(brain.t||0)){brain=remote;ls.set("jv_brain",brain);renderBrain()}}
  catch(e){if(!/404/.test(e.message))console.warn("Abgleich",e)}}
