"use strict";
/* ---------- Werkstatt: Jarvis baut ---------- */
let bauten=ls.get("jv_bauten",[]),bau=null;IDB.get("bauten").then(b=>{if(b?.length)bauten=b;else if(bauten.length)IDB.set("bauten",bauten)}).catch(()=>{});
function bauListe(){$("#bAlt").innerHTML=`<option value="">Frühere Bauten (${bauten.length})</option>`+bauten.map((b,i)=>`<option value="${i}">${esc(b.titel.slice(0,40))}</option>`).join("")}
const SHIM=`<script>try{localStorage.length}catch(e){const m=()=>{const d={};return{getItem:k=>k in d?d[k]:null,setItem:(k,v)=>{d[k]=String(v)},removeItem:k=>{delete d[k]},clear:()=>{for(const k in d)delete d[k]},key:i=>Object.keys(d)[i]??null,get length(){return Object.keys(d).length}}};Object.defineProperty(window,"localStorage",{value:m()});Object.defineProperty(window,"sessionStorage",{value:m()})}<\/script>`;
function bauZeigen(b){bau=b;$("#bFrame").hidden=false;$("#bFrame").srcdoc=SHIM+b.html;$("#bMehr").hidden=$("#bDl").hidden=false;$("#bInfo").textContent=`„${b.titel}“ · ${Math.round(b.html.length/1024)} KB`}
async function bauen(wunsch,alt){$("#bGo").disabled=$("#bMehr").disabled=true;$("#bInfo").textContent=alt?"Ich verbessere …":"Ich baue … (dauert 10–40 Sekunden)";
  const sys=`Du bist ein Spitzen-Frontend-Entwickler. Liefere GENAU EINE vollständige, lauffähige HTML-Datei (<!doctype html> … </html>) mit eingebettetem CSS und JavaScript, sonst nichts – kein Text davor oder danach.
Regeln: läuft offline und ohne externe Dateien; einzig erlaubte Fremdquelle: https://cdn.jsdelivr.net (z. B. three.js als ES-Modul). Keine Formulare, die Daten verschicken. Deutsche Texte. Dunkles, modernes Design mit Rot/Orange-Akzenten, mobil bedienbar (Touch).`;
  const msgs=[{role:"system",content:sys},...(alt?[{role:"user",content:alt.titel},{role:"assistant",content:alt.html},{role:"user",content:"Verbessere die Datei: "+wunsch+". Gib wieder die komplette Datei aus."}]:[{role:"user",content:wunsch}])];
  try{let t=(await llm(msgs)).text.replace(/<think>[\s\S]*?<\/think>/g,"");const m=t.match(/```(?:html)?\s*([\s\S]*?)```/);if(m)t=m[1];
    const a=t.search(/<!doctype html|<html/i),z=t.toLowerCase().lastIndexOf("</html>");if(a<0)throw new Error("Jarvis hat keinen Bauplan geliefert – bitte nochmal.");
    const html=t.slice(a,z>a?z+7:undefined);const b={titel:alt?alt.titel+" (verbessert)":wunsch.slice(0,80),html,t:Date.now()};
    bauten=[b,...bauten].slice(0,50);IDB.set("bauten",bauten);try{localStorage.removeItem("jv_bauten")}catch(e){}
    bauListe();bauZeigen(b);toast("Fertig gebaut.")}
  catch(e){$("#bInfo").textContent=e.message}$("#bGo").disabled=$("#bMehr").disabled=false}
$("#tBau").onclick=()=>{bauListe();$("#dlgBau").showModal()};
$("#bGo").onclick=()=>{const w=$("#bWas").value.trim();if(w)bauen(w)};
$("#bMehr").onclick=()=>{const w=$("#bWas").value.trim();if(!bau)return;if(!w)return toast("Schreib oben, was besser werden soll.");bauen(w,bau)};
$("#bAlt").onchange=e=>{const b=bauten[e.target.value];if(b)bauZeigen(b)};
$("#bDl").onclick=()=>{if(!bau)return;const u=URL.createObjectURL(new Blob([bau.html],{type:"text/html"})),l=document.createElement("a");l.href=u;l.download=bau.titel.replace(/[^\wäöüÄÖÜß -]/g,"").slice(0,40)+".html";l.click()};

let archivCache=null;
async function archiv(){return archivCache||(archivCache=await IDB.all())}
function archivieren(role,content){const e={role,content,t:Date.now()};IDB.add(e);archivCache?.push(e)}
const worte=t=>[...new Set(String(t).toLowerCase().match(/[a-zäöüß0-9]{4,}/g)||[])];
async function erinnern(frage,n=4){const w=worte(frage);if(!w.length)return[];const a=await archiv(),alt=a.slice(0,-16);
  return alt.map(e=>({e,s:w.reduce((p,x)=>p+(e.content.toLowerCase().includes(x)?1:0),0)})).filter(x=>x.s>=1).sort((a,b)=>b.s-a.s||b.e.t-a.e.t).slice(0,n).map(x=>x.e)}
function relevanteMem(frage){const m=brain.mem;if(m.length<=60)return m;const w=worte(frage);
  const score=x=>w.reduce((p,y)=>p+(x.x.toLowerCase().includes(y)?1:0),0);return[...m.slice(-20),...m.slice(0,-20).sort((a,b)=>score(b)-score(a)).slice(0,40)]}
