"use strict";
/* ---------- Dialoge ---------- */
$$("dialog [data-close]").forEach(b=>b.onclick=()=>b.closest("dialog").close());
function openBrain(){renderBrain();$("#dlgBrain").showModal();archiv().then(a=>$("#archInfo").textContent=`${a.length} Nachrichten gespeichert – Jarvis erinnert sich automatisch an passende alte Gespräche.`)}
$("#archQ").oninput=async e=>{const q=e.target.value.trim().toLowerCase();if(q.length<3){$("#archRes").innerHTML="";return}const a=await archiv();
  $("#archRes").innerHTML=a.filter(x=>x.content.toLowerCase().includes(q)).slice(-8).reverse().map(x=>`<p><span class="muted">${new Date(x.t).toLocaleString("de-DE",{dateStyle:"short",timeStyle:"short"})} · ${x.role==="user"?"Du":"Jarvis"}:</span> ${esc(x.content.slice(0,220))}</p>`).join("")||`<p class="muted">Nichts gefunden.</p>`};
$("#btnBrain").onclick=openBrain;
$("#btnCfg").onclick=()=>{$("#cGroq").value=cfg.groq||"";$("#cGh").value=cfg.gh||"";$("#cPass").value=cfg.pass||"";$("#cEl").value=cfg.el||"";$("#cElV").value=cfg.elv||"";$("#cTalk").checked=!!cfg.talk;$("#dlgCfg").showModal()};
$("#cSave").onclick=async()=>{cfg={groq:$("#cGroq").value.trim(),gh:$("#cGh").value.trim(),pass:$("#cPass").value,el:$("#cEl").value.trim(),elv:$("#cElV").value.trim(),voice:$("#cVoice").value,talk:$("#cTalk").checked};
  ls.set("jv_cfg",cfg);$("#dlgCfg").close();toast("Gespeichert.");await pullBrain();pushBrain();loadAll()};
$("#cTest").onclick=()=>{cfg.voice=$("#cVoice").value;speak("Guten Abend Lucas. Alle Systeme laufen. Womit kann ich dienen?")};

/* ---------- Start ---------- */
(function greet(){
  const h=new Date().getHours(),g=h<11?"Guten Morgen":h<18?"Hallo":"Guten Abend";
  for(const m of hist.slice(-6))bubble(m.role==="user"?"me":"ai",m.role==="user"?esc(m.content):md(m.content));
  if(!hist.length)bubble("ai",`${g} Lucas. Ich bin Jarvis. Frag mich alles – ich recherchiere im Netz, plane Projekte, merke mir, was dir wichtig ist, und schicke meine Bots los.${cfg.groq?"":"\n\nEinmalig nötig: Trag in ⚙️ deinen kostenlosen Groq-Schlüssel ein – das ist mein Denkmotor."}`);
})();
if("serviceWorker"in navigator)navigator.serviceWorker.register("sw.js").catch(()=>{});
(()=>{const c=ls.get("jv_cache",null);if(c){Object.assign(D,c);for(const f of[renderTown,renderBriefing,renderTrading,renderAutomaton,renderNeu,renderLage])try{f()}catch(e){console.warn(e)}}})(); // Schnellstart mit letztem Stand
pullBrain().then(renderBrain);loadAll();
