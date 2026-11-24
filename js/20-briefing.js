"use strict";
/* ---------- Briefing ---------- */
function renderBriefing(){
  const b=D.briefing;
  if(!b){$("#briefing").innerHTML=`<p class="empty">Das erste Briefing kommt morgen um 6 Uhr.</p>`;}
  else{$("#bDatum").textContent=b.datum;
    $("#briefing").innerHTML=`<div class="panel"><p class="fazit">${esc(b.fazit||"Hier ist, was über Nacht passiert ist.")}</p><ul class="lines">${b.zeilen.map(z=>`<li>${esc(z)}</li>`).join("")}</ul></div>
    ${b.bots?.length?`<div class="panel"><h3>Wer hat gearbeitet</h3><table><tr><th>Bot</th><th class="r">erledigt</th><th class="r">Fehler</th></tr>${b.bots.map(x=>`<tr><td>${x.icon} ${esc(x.name)}</td><td class="r">${x.ok}</td><td class="r ${x.fehler?"neg":""}">${x.fehler}</td></tr>`).join("")}</table></div>`:""}
    ${b.neu?.length?`<div class="panel"><h3>Neu entdeckt</h3>${b.neu.map(n=>`<p><a href="${esc(n.url)}" target="_blank" rel="noopener">${esc(n.titel)}</a><br><span class="muted small">${esc(n.nutzen||"")}</span></p>`).join("")}</div>`:""}`;
    $("#bAlt").innerHTML=(b.verlauf||[]).map(v=>`<div style="margin-top:12px"><b>${esc(v.datum)}</b><p class="small">${esc(v.fazit||"")}</p><ul class="small">${v.zeilen.map(z=>`<li>${esc(z)}</li>`).join("")}</ul></div>`).join("")||`<p class="muted small">Noch keine.</p>`;}
  const s=D.status;
  $("#checks").innerHTML=s?`<p class="muted">Zuletzt ${ago(s.updated)}${s.repariert?.length?` · selbst repariert: ${esc(s.repariert.join(", "))}`:""}</p>`+s.checks.map(c=>`<div class="check"><b class="${c.ok?"pos":"neg"}">${c.ok?"✓":"✕"}</b><span><b>${esc(c.name)}</b> – ${esc(c.info)}</span></div>`).join(""):`<p class="muted">Der Wächter meldet sich nach seiner ersten Runde.</p>`;
}
$("#btnRead").onclick=()=>{const b=D.briefing;if(b)speak(`Guten Morgen Lucas. ${b.fazit||""} ${b.zeilen.join(" ")}`.replace(/[🤖📈🔭📚🛡️🔧⚠️]/gu,""))};
