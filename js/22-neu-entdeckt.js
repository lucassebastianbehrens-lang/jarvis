"use strict";
/* ---------- Neu entdeckt ---------- */
function renderNeu(){
  const R=D.rech,no=new Set(ls.get("jv_nein",[])),ja=new Set(ls.get("jv_ja",[]));
  if(!R){$("#neu").innerHTML=`<p class="empty">Die erste Nacht-Recherche läuft heute Nacht um 2 Uhr.</p>`;return}
  $("#neuInfo").textContent="zuletzt "+ago(R.updated);
  const items=R.items.filter(i=>!no.has(i.id));
  $("#neu").innerHTML=(R.fazit?`<div class="panel"><p class="fazit">${esc(R.fazit)}</p></div>`:"")+items.map(i=>`<div class="panel card"><span class="score">${i.punkte??""}</span>
    <h3><a href="${esc(i.url)}" target="_blank" rel="noopener">${esc(i.titel)}</a></h3><p class="muted small">${esc(i.quelle||"")} · ${ago(i.t)}${R.neu?.includes(i.id)?" · neu":""}</p>
    <p>${esc(i.was||"")}</p>${i.nutzen?`<p><b>Nutzen:</b> ${esc(i.nutzen)}</p>`:""}${i.vorschlag?`<p><b>Einbau:</b> ${esc(i.vorschlag)}</p>`:""}
    <div class="row">${ja.has(i.id)?`<span class="chip done">An Claude übergeben ✓</span>`:`<button class="btn go" data-ja="${i.id}">Einbauen</button><button class="btn ghost" data-nein="${i.id}">Nein danke</button>`}</div></div>`).join("")||`<p class="empty">Alles gesichtet – heute Nacht kommt Neues.</p>`;
  $$("[data-nein]").forEach(b=>b.onclick=()=>{no.add(b.dataset.nein);ls.set("jv_nein",[...no]);renderNeu()});
  $$("[data-ja]").forEach(b=>b.onclick=async()=>{const i=R.items.find(x=>x.id===b.dataset.ja);b.disabled=true;
    try{await auftrag(`Einbauen: ${i.titel}`,`**Fund:** ${i.url}\n\n${i.was||""}\n\n**Nutzen:** ${i.nutzen||""}\n\n**Vorschlag:** ${i.vorschlag||""}`);ja.add(i.id);ls.set("jv_ja",[...ja]);renderNeu()}catch(e){toast(e.message);b.disabled=false}});
}
async function auftrag(titel,text){
  if(!cfg.gh){await navigator.clipboard?.writeText(`${titel}\n\n${text}`).catch(()=>{});throw new Error("Kein GitHub-Token – Auftrag wurde kopiert, gib ihn Claude.")}
  const r=await gh("/issues",{title:"Jarvis: "+titel,body:text+"\n\n_Freigegeben von Lucas in der Jarvis-App._",labels:["jarvis-auftrag"]});
  toast("Auftrag angelegt – Claude baut es ein.");return r}
