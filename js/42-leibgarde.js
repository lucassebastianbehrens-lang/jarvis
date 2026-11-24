"use strict";
/* ---------- Leibgarde: Hintergrund-Bots nur für Lucas ---------- */
let jobs=ls.get("jv_jobs",[]);const GARDE=["Ben","Lea","Kai"];
function saveJobs(){ls.set("jv_jobs",jobs.slice(0,30));renderJobs()}
function freierBot(){const b=new Set(jobs.filter(j=>j.status==="läuft").map(j=>j.bot));return GARDE.find(n=>!b.has(n))||GARDE[jobs.length%3]}
async function hintergrund(aufgabe){aufgabe=aufgabe.trim();if(!aufgabe)return;
  const j={id:"j"+Date.now().toString(36),aufgabe,bot:freierBot(),t:Date.now(),status:"läuft",wo:cfg.gh?"github":"app"};jobs.unshift(j);saveJobs();
  if(j.wo==="github"){try{await gh("/actions/workflows/hintergrund.yml/dispatches",{ref:"main",inputs:{aufgabe:aufgabe.slice(0,900),id:j.id,bot:j.bot}});pollJobs()}
    catch(e){j.wo="app";toast("GitHub nicht erreichbar – "+j.bot+" arbeitet in der App weiter.")}}
  if(j.wo==="app")lokalArbeiten(j);
  return j}
async function lokalArbeiten(j){try{const r=await llm([{role:"system",content:context(j.aufgabe)+"\nDu bist "+j.bot+", ein Hintergrund-Helfer. Liefere ein fertiges Ergebnis in Markdown: zuerst die Antwort fett in 1–2 Sätzen, dann Details als Liste mit Quellen-Links, am Ende **Nächster Schritt:**. Keine Aktionszeilen."},{role:"user",content:j.aufgabe}],true);
    fertig(j,{antwort:r.text.replace(/\[\[[\s\S]*?\]\]/g,""),quellen:(r.quellen||[]).map(q=>q.url)})}catch(e){fertig(j,{antwort:"Hat nicht geklappt: "+e.message,ok:false})}}
function fertig(j,res){Object.assign(j,{status:res.ok===false?"fehler":"fertig",antwort:res.antwort,quellen:res.quellen||[],ende:Date.now()});saveJobs();if(res.ok!==false)archivieren("assistant",`Ergebnis von ${j.bot} zu „${j.aufgabe}“: ${res.antwort}`);
  toast(`🛡️ ${j.bot} ist fertig: ${j.aufgabe.slice(0,40)}`,5000);try{if(document.hidden&&Notification.permission==="granted")new Notification(`${j.bot} ist fertig`,{body:j.aufgabe.slice(0,80),icon:"icon-192.png"})}catch(e){}
  if(cfg.talk)speak(`${j.bot} ist fertig mit: ${j.aufgabe.slice(0,60)}`)}
let pollT;async function pollJobs(){clearTimeout(pollT);const offen=jobs.filter(j=>j.status==="läuft"&&j.wo==="github");if(!offen.length)return;
  for(const j of offen){try{const f=await gh(`/contents/data/hintergrund/${j.id}.json`);const d=JSON.parse(td.decode(ub64(f.content.replace(/\n/g,""))));fertig(j,d)}
    catch(e){if(Date.now()-j.t>20*60000){j.status="fehler";j.antwort="Keine Rückmeldung nach 20 Minuten. Protokoll: https://github.com/"+REPO+"/actions/workflows/hintergrund.yml";saveJobs()}}}
  if(jobs.some(j=>j.status==="läuft"&&j.wo==="github"))pollT=setTimeout(pollJobs,20000)}
function renderJobs(){const el=$("#jobs");if(!el)return;const l=jobs.slice(0,6);$("#garde").hidden=!l.length;
  el.innerHTML=l.map((j,i)=>`<details class="job ${j.status==="läuft"?"run":""}" ${i===0&&j.status!=="läuft"&&!j.gelesen?"open":""} data-j="${j.id}"><summary><b>${j.status==="läuft"?"⚙️":j.status==="fertig"?"✅":"⛔"} ${esc(j.bot)}</b> <span>${esc(j.aufgabe.slice(0,70))}</span><span class="muted small"> · ${j.status==="läuft"?"arbeitet …":ago(j.t/1000)}</span></summary>
    ${j.antwort?`<div class="md">${md(j.antwort)}</div>${j.quellen?.length?`<p class="small muted">Quellen: ${j.quellen.slice(0,6).map((u,k)=>`<a href="${esc(u)}" target="_blank" rel="noopener">[${k+1}]</a>`).join(" ")}</p>`:""}<div class="row"><button class="btn" data-weiter="${j.id}">Im Chat weitermachen</button><button class="x" data-weg="${j.id}" aria-label="Entfernen">✕</button></div>`:""}</details>`).join("");
  $$("[data-weg]").forEach(b=>b.onclick=()=>{jobs=jobs.filter(j=>j.id!==b.dataset.weg);saveJobs()});
  $$("[data-weiter]").forEach(b=>b.onclick=()=>{const j=jobs.find(x=>x.id===b.dataset.weiter);hist.push({role:"user",content:"Hintergrund-Auftrag: "+j.aufgabe},{role:"assistant",content:j.antwort});ls.set("jv_hist",hist);$("#inp").focus();toast("Ergebnis ist im Chat-Gedächtnis – frag einfach nach.")});
  $$("details.job").forEach(d=>d.ontoggle=()=>{const j=jobs.find(x=>x.id===d.dataset.j);if(j&&d.open&&!j.gelesen){j.gelesen=1;ls.set("jv_jobs",jobs)}})}
$("#tGarde").onclick=()=>{const a=prompt("Was soll ein Hintergrund-Helfer für dich erledigen?\n(z. B. „Recherchiere die 5 günstigsten Steuerberater in Oschersleben“)");if(a)hintergrund(a).then(j=>j&&toast(`🛡️ ${j.bot} legt los – du kannst weiter mit mir reden.`))};
renderJobs();pollJobs();
