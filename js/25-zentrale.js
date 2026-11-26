"use strict";
/* ---------- Kommandozentrale: alles an einem Ort (Startseite) ----------
   Kacheln zu allen Bereichen, Leistungs-Anzeige, Heute-Liste zum Abhaken,
   Content-Studio (Videos auf Zuruf) und Lead-System (Aufträge + Firmen-Leads).
   Nutzt beim Klicken show() (01), hintergrund() (42), speak() (45), toast()/gh() (01). */
const ZT_LINKS={
  kalender:"https://calendar.google.com/", mail:"https://mail.google.com/", drive:"https://drive.google.com/",
  github:`https://github.com/${REPO}/actions`, tiktok:"https://www.tiktok.com/tiktokstudio",
  youtube:"https://studio.youtube.com/", insta:"https://www.instagram.com/"};
const ztHeute=()=>new Date().toLocaleDateString("de-DE");
const ztId=s=>{let h=0;for(const c of s)h=(h*31+c.charCodeAt(0))|0;return"z"+(h>>>0).toString(36)};

/* Leistung: Anteil grüner Wächter-Checks (0–100) */
function ztLeistung(){const c=D.status?.checks||[];return c.length?Math.round(100*c.filter(x=>x.ok).length/c.length):null}
function ztAktiv(){return(D.runs||[]).filter(r=>r.status==="in_progress"||r.status==="queued").length}
function ztLauf(wf){return(D.runs||[]).find(r=>(r.path||"").endsWith("/"+wf))}

/* Heute-Liste: automatisch aus Briefing, Calls, Aufträgen, Wächter + eigene Punkte */
function ztAufgaben(){
  const L=[],b=D.briefing,heute=new Date().toDateString();
  const w=(b?.fazit||"").match(/Wichtig:\s*(.+)$/);if(w)L.push({icon:"⭐",text:w[1].trim()});
  for(const c of ls.get("jv_calls",[]))if(c.wann&&new Date(c.wann).toDateString()===heute)
    L.push({icon:"📞",text:`${new Date(c.wann).toLocaleTimeString("de-DE",{hour:"2-digit",minute:"2-digit"})} Call mit ${c.wer}`});
  for(const a of(D.auftr?.auftraege||[]).filter(a=>a.datum===ztHeute()).slice(0,2))L.push({icon:"🔭",text:`Auftrag prüfen: ${a.titel}`});
  for(const c of(D.status?.checks||[]).filter(c=>!c.ok).slice(0,2))L.push({icon:"🛡️",text:`Prüfen: ${c.name}`});
  for(const t of ls.get("jv_zt_eigen",[]))L.push({icon:"✏️",text:t,eigen:1});
  return L.map(x=>({...x,id:ztId(x.text)}));
}
function ztErledigt(){const d=ls.get("jv_zt_done",{tag:"",ids:[]});return d.tag===ztHeute()?d:{tag:ztHeute(),ids:[]}}

function ztGauge(p){ // Halbkreis-Tacho
  const v=p??0,a=Math.PI*(1-v/100),x=50+38*Math.cos(a),y=50-38*Math.sin(a);
  return`<svg viewBox="0 0 100 58" class="zgauge" role="img" aria-label="Leistung ${p??"unbekannt"} Prozent">
    <path d="M12 50 A38 38 0 0 1 88 50" fill="none" stroke="var(--line)" stroke-width="9" stroke-linecap="round"/>
    <path d="M12 50 A38 38 0 0 1 88 50" fill="none" stroke="url(#zg)" stroke-width="9" stroke-linecap="round" pathLength="100" stroke-dasharray="${v} 100"/>
    <defs><linearGradient id="zg"><stop offset="0" stop-color="var(--ok)"/><stop offset=".6" stop-color="var(--warn)"/><stop offset="1" stop-color="var(--red)"/></linearGradient></defs>
    <line x1="50" y1="50" x2="${x.toFixed(1)}" y2="${y.toFixed(1)}" stroke="var(--text)" stroke-width="3" stroke-linecap="round"/><circle cx="50" cy="50" r="4" fill="var(--text)"/></svg>`}

function renderZentrale(){
  const el=$("#zentrale");if(!el)return;
  const p=ztLeistung(),akt=ztAktiv(),bots=D.bots?.length||0,b=D.briefing;
  const spiel=(D.paper?.value??0)+(D.agents?.value??0);
  const t=(icon,name,info,ziel,extern)=>`<button class="ztile" ${extern?`data-href="${esc(ziel)}"`:`data-show="${ziel}"`}><b aria-hidden="true">${icon}</b><span>${esc(name)}</span><small>${esc(info||"")}</small></button>`;
  const vid=ztLauf("video-auto.yml"),vidInfo=vid?`${vid.status==="completed"?(vid.conclusion==="success"?"✓ zuletzt fertig":"⛔ letzter Lauf fehlgeschlagen"):"⚙️ dreht gerade"} · ${ago(Date.parse(vid.created_at)/1000)}`:"Regisseurin Rita dreht täglich automatisch";
  const auftr=(D.auftr?.auftraege||[]).slice(0,3);
  const done=new Set(ztErledigt().ids),aufg=ztAufgaben(),fertig=aufg.filter(a=>done.has(a.id)).length;
  el.innerHTML=`
  <div class="panel zhead">
    <div>${ztGauge(p)}<div class="zmax">${p==null?"…":p>=90?"MAX":p+" %"}</div></div>
    <div class="zstat"><p class="fazit" style="margin:0">${p==null?"Wächter meldet sich gleich.":p>=90?"Alle Systeme laufen.":"Einige Systeme brauchen Hilfe."}</p>
      <p class="muted small">${bots} Agenten · ${akt} arbeiten gerade · Spielgeld ${eur(spiel)}${D.auto?.modus?` · Modus ${esc(D.auto.modus)}`:""}</p>
      <div class="row"><button class="btn go" id="zPower" aria-label="Alle Agenten starten">⏻ Alle Agenten starten</button></div></div>
  </div>
  <div class="zgrid">
    ${t("💬","Jarvis","Chat & Sprache","jarvis")}
    ${t("☀️","Briefing",b?.datum?.split(",")[0]||"6 Uhr","briefing")}
    ${t("📅","Kalender","Google",ZT_LINKS.kalender,1)}
    ${t("✉️","Mails","Gmail",ZT_LINKS.mail,1)}
    ${t("📈","Trading",eur(spiel),"trading")}
    ${t("🛰️","Lage","Welt & Märkte","lage")}
    ${t("🏙️","KI-Stadt",`${akt} aktiv`,"stadt")}
    ${t("✨","Neu",`${D.rech?.items?.length||0} Funde`,"neu")}
    ${t("📝","Obsidian","Drive-Vault",ZT_LINKS.drive,1)}
    ${t("🐙","GitHub","Bots & Läufe",ZT_LINKS.github,1)}
    ${t("▶️","YouTube","Studio",ZT_LINKS.youtube,1)}
    ${t("🎵","TikTok","Studio",ZT_LINKS.tiktok,1)}
  </div>
  <div class="panel"><div class="row" style="justify-content:space-between"><h3>☀️ Heute erledigen</h3><span class="muted small">${fertig}/${aufg.length} ✓</span></div>
    <ul class="zlist">${aufg.map(a=>`<li><label><input type="checkbox" data-zid="${a.id}" ${done.has(a.id)?"checked":""}> <span>${a.icon} ${esc(a.text)}</span></label>${a.eigen?`<button class="x" data-zweg="${esc(a.text)}" aria-label="Entfernen">✕</button>`:""}</li>`).join("")||`<li class="muted">Nichts offen – genieß den Tag.</li>`}</ul>
    <div class="row" style="margin-top:8px"><input type="text" id="zNeu" placeholder="Eigener Punkt …" style="flex:1"><button class="btn" id="zAdd">+</button><button class="btn" id="zVor" aria-label="Heute-Liste vorlesen">🔊</button></div></div>
  <div class="panel"><h3>🎬 Content-Studio</h3><p class="muted small">${esc(vidInfo)}</p>
    <div class="row"><select id="zModus" style="width:auto"><option value="sim">Simulation</option><option value="tt">Früchte-Drama</option><option value="geld">Kontostand</option><option value="zt">Zeichentrick</option></select>
      <input type="text" id="zIdee" placeholder="Eigene Idee (wird Simulations-Video)" style="flex:1;min-width:150px"></div>
    <div class="row" style="margin-top:8px"><button class="btn go" id="zVideo">🎬 Video drehen lassen</button>
      <a class="btn" href="${ZT_LINKS.tiktok}" target="_blank" rel="noopener">TikTok</a><a class="btn" href="${ZT_LINKS.youtube}" target="_blank" rel="noopener">YouTube</a><a class="btn" href="${ZT_LINKS.insta}" target="_blank" rel="noopener">Instagram</a></div>
    <p class="muted small">Prüfung + Bildcheck laufen automatisch. Veröffentlicht wird nur, was du freigegeben hast.</p></div>
  <div class="panel"><h3>🎯 Lead-System</h3>
    ${auftr.map(a=>`<div class="zlead"><span><b>${esc(a.titel)}</b><br><span class="muted small">${esc(a.quelle||"")}${a.lieferzeit?" · "+esc(a.lieferzeit):""}</span></span><span class="r">${a.preis_eur?eur(a.preis_eur):""}${a.url?`<br><a class="small" href="${esc(a.url)}" target="_blank" rel="noopener">öffnen</a>`:""}</span></div>`).join("")||`<p class="muted small">Scout Sam sucht täglich neue Aufträge.</p>`}
    <div class="row" style="margin-top:10px"><button class="btn go" id="zLeads">🏢 Firmen-Leads suchen (Webseiten)</button></div>
    <p class="muted small">Leads sind Handwerksbetriebe ohne gute Webseite. Kontakt nur per Brief oder Besuch (UWG) – Jarvis schreibt dir den Briefsatz dazu.</p></div>`;

  $$("#zentrale [data-show]").forEach(x=>x.onclick=()=>show(x.dataset.show));
  $$("#zentrale [data-href]").forEach(x=>x.onclick=()=>open(x.dataset.href,"_blank","noopener"));
  $$("#zentrale [data-zid]").forEach(x=>x.onchange=()=>{const d=ztErledigt(),s=new Set(d.ids);x.checked?s.add(x.dataset.zid):s.delete(x.dataset.zid);ls.set("jv_zt_done",{tag:d.tag,ids:[...s]});renderZentrale()});
  $$("#zentrale [data-zweg]").forEach(x=>x.onclick=()=>{ls.set("jv_zt_eigen",ls.get("jv_zt_eigen",[]).filter(t=>t!==x.dataset.zweg));renderZentrale()});
  const add=()=>{const v=$("#zNeu").value.trim();if(!v)return;ls.set("jv_zt_eigen",[...ls.get("jv_zt_eigen",[]),v].slice(-20));renderZentrale()};
  $("#zAdd").onclick=add;$("#zNeu").onkeydown=e=>{if(e.key==="Enter")add()};
  $("#zVor").onclick=()=>{const o=ztAufgaben().filter(a=>!ztErledigt().ids.includes(a.id));speak(o.length?`Heute offen: ${o.map(a=>a.text).join(". ")}`:"Heute ist alles erledigt.")};
  $("#zVideo").onclick=async e=>{if(!cfg.gh)return toast("Dafür braucht Jarvis den GitHub-Token (⚙️).");e.target.disabled=true;
    // Mit Idee: Simulation, landet als nächstes neues Video hinter dem 7-Tage-Vorrat. Ohne Idee: Vorrat der Serie auffüllen.
    const idee=$("#zIdee").value.trim().slice(0,300),inputs=idee?{modus:"sim",idee,tage:"8"}:{modus:$("#zModus").value};
    try{await gh("/actions/workflows/video-auto.yml/dispatches",{ref:"main",inputs});$("#zIdee").value="";
      toast(idee?"🎬 Rita dreht deine Idee als nächstes Simulations-Video – kommt per Telegram.":"🎬 Rita füllt den Video-Vorrat auf.",5000)}catch(x){toast(x.message)}e.target.disabled=false};
  $("#zLeads").onclick=()=>hintergrund("Lead-System (KC, Webseiten für Firmen): Finde 10 Handwerksbetriebe im Raum Oschersleben, Halberstadt und Magdeburg, die keine oder eine veraltete Webseite haben. Je Betrieb: Name, Gewerk, Ort, Geschäftsadresse, aktuelle Webseite (falls vorhanden) und was daran fehlt. Nur öffentliche Firmendaten, keine Privatpersonen. Kontakt nur per Brief oder Besuch (UWG) – schreib zu jedem Betrieb einen passenden Einstiegssatz für den Brief. Als Tabelle mit Quellen.")
    .then(j=>j&&toast(`🛡️ ${j.bot} sucht Leads – Ergebnis unter Jarvis → Im Hintergrund.`,5000));
  $("#zPower").onclick=async e=>{if(!cfg.gh)return toast("Dafür braucht Jarvis den GitHub-Token (⚙️).");e.target.disabled=true;
    try{await gh("/actions/workflows/waechter.yml/dispatches",{ref:"main"});toast("⏻ Wächter Willi prüft alle Agenten und startet Liegengebliebene neu.")}catch(x){toast(x.message)}e.target.disabled=false};
}
