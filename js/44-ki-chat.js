"use strict";
/* ---------- Gehirn: KI ---------- */
function context(frage=""){
  const P=D.paper,A=D.agents,S=D.status,now=new Date();
  return `Du bist JARVIS, die persönliche rechte Hand von Lucas. Antworte immer auf Deutsch, kurz, direkt und warm (Butler-Ton, gern mit trockenem Humor). Beträge immer in Euro.
Heute: ${now.toLocaleString("de-DE",{dateStyle:"full",timeStyle:"short"})} (Europe/Berlin).
Lucas: Schichtdienst in Oschersleben, wohnt in Halberstadt (ab 01.01.2027 Oschersleben), ca. 15 h/Woche für eigene Geschäfte (TikTok-KI-Videos, Etsy-Finanzvorlagen, Social Media für Handwerker, YouTube-Kanäle), fährt BMW E46.
Deine Regeln: Was du selbst kannst, erledigst du sofort und meldest danach kurz. Kein echtes Geld bewegen, nichts kaufen, nichts veröffentlichen, keine Nachrichten an Fremde ohne Lucas' Ja. Trading nur Spielgeld.

GEDÄCHTNIS (was du über Lucas weißt):
${relevanteMem(frage).map(m=>"- "+m.x).join("\n")||"- (noch leer)"}
KUNDEN: ${(brain.kunden||[]).map(k=>`${k.firma} (${k.leist}, ${eur(k.preis)})`).join("; ")||"(noch keine)"}
WELTLAGE: ${D.lage?.lagebild||(D.lage?.orte||[]).slice(0,4).map(o=>o.land+": "+(o.meldungen[0]?.titel||"")).join("; ")||"?"}
PROJEKTE:
${brain.proj.map(p=>`- ${p.titel}: `+p.schritte.map(s=>(s.ok?"✓ ":"○ ")+s.x).join("; ")).join("\n")||"- (keine)"}
LIVE-DATEN: Krypto-Spielgeld ${P?eur(P.value):"?"}; Memecoin-Spielgeld ${A?eur((A.equity?.at(-1)||[0,A.cash])[1]):"?"}; Wächter: ${S?(S.ok?"alles ok":S.checks.filter(c=>!c.ok).map(c=>c.name+": "+c.info).join("; ")):"?"}.
DEINE BOTS (Workflow-Datei = Name): ${D.bots.map(b=>`${b.wf}=${b.name} (${b.job})`).join("; ")}

AKTIONEN – schreibe sie als eigene Zeilen ans Ende deiner Antwort, nur wenn sinnvoll:
[[MERKEN: Fakt]]  → wenn Lucas dir etwas Dauerhaftes über sich, seine Pläne oder Vorlieben erzählt (auch ohne „merk dir“).
[[PROJEKT: Titel | Schritt 1; Schritt 2; Schritt 3]] → wenn Lucas ein Vorhaben plant (3–8 konkrete Schritte).
[[STARTE: datei.yml]] → wenn ein Bot jetzt arbeiten soll (Lucas bestätigt per Knopf).
[[BAUEN: Beschreibung]] → wenn Lucas eine kleine App, ein Spiel, einen Rechner oder eine Ansicht sofort sehen will (du baust sie selbst in der Werkstatt).
[[AUFTRAG: was in Jarvis eingebaut/programmiert werden soll]] → wenn Lucas eine neue Funktion für dich will (geht an Claude, Lucas bestätigt).
[[HINTERGRUND: genauer Auftrag]] → für alles, was länger dauert oder gründliche Recherche braucht, oder wenn Lucas „im Hintergrund“ sagt. Ein Helfer der Leibgarde (Ben, Lea, Kai) erledigt es parallel; sag in 1 Satz, wer dran ist.
Erwähne die Aktionszeilen nicht im Text.
GENAUIGKEIT: Erfinde nie Zahlen, Preise, Links oder Namen. Bist du unsicher oder ist es aktuell, sag das offen oder nutze die Websuche. Bei Rechnungen rechne Schritt für Schritt nach.${frage&&erinnern.cache?.length?"\nFRÜHERE GESPRÄCHE ZUM THEMA:\n"+erinnern.cache.map(e=>`(${new Date(e.t).toLocaleDateString("de-DE")}, ${e.role==="user"?"Lucas":"Jarvis"}) ${e.content.slice(0,300)}`).join("\n"):""}`}
const needsWeb=t=>/aktuell|heute|gestern|morgen|neueste|news|nachrichten|preis|kostet|kosten|kurs|wetter|wer ist|was gibt es neu|trend|202[5-9]|recherchier|such|google|öffnungszeit|adresse|in der nähe|vergleich|test|bewertung|wie viel|wieviel|gesetz|regel|steuer/i.test(t);
const GESPERRT=new Set(ls.get("jv_gesperrt",[]));
async function llm(messages,web,onDelta){
  if(!cfg.groq)throw new Error("Trag in ⚙️ deinen kostenlosen Groq-Schlüssel ein – das ist mein Denkmotor.");
  const search={tools:[{type:"browser_search"}],tool_choice:"auto"};
  const list=web?[["openai/gpt-oss-120b",{...search,reasoning_effort:"medium"}],["openai/gpt-oss-20b",{...search,reasoning_effort:"medium"}],["groq/compound",{}]]
                :[["openai/gpt-oss-120b",{reasoning_effort:"low"}],["openai/gpt-oss-20b",{reasoning_effort:"low"}],["qwen/qwen3.8-27b",{}]];
  let letzter="";
  for(const[m,extra]of list){if(GESPERRT.has(m))continue;const stream=!!onDelta&&!web; // Websuche ohne Streaming, damit die Quellen sicher mitkommen
    for(const x of [extra,{}]){ // bei 400 einmal ohne Zusatz-Optionen
      let r;try{r=await fetch("https://api.groq.com/openai/v1/chat/completions",{method:"POST",headers:{"Content-Type":"application/json",Authorization:"Bearer "+cfg.groq},body:JSON.stringify({model:m,messages,stream,...x})})}catch(e){letzter="Netz";break}
      if(r.status===400&&Object.keys(x).length&&!x.tools)continue;
      if(r.status===401)throw new Error("Groq-Schlüssel ungültig – bitte in ⚙️ prüfen.");
      if(r.status===404||r.status===403){GESPERRT.add(m);ls.set("jv_gesperrt",[...GESPERRT]);break}
      if(!r.ok){letzter=r.status===429?"Limit erreicht":String(r.status);break}
      if(!stream){const j=await r.json(),msg=j.choices[0].message;return{text:msg.content||"",web,quellen:quellenAus(msg)}}
      const rd=r.body.getReader(),dec=new TextDecoder();let buf="",text="",q=[];
      for(;;){const{done,value}=await rd.read();if(done)break;buf+=dec.decode(value,{stream:true});const zeilen=buf.split("\n");buf=zeilen.pop();
        for(const z of zeilen){if(!z.startsWith("data:"))continue;const d=z.slice(5).trim();if(d==="[DONE]")continue;
          try{const j=JSON.parse(d),c=j.choices?.[0];if(c?.delta?.content){text+=c.delta.content;onDelta(text)}if(c?.delta?.executed_tools)q.push(...quellenAus(c.delta))}catch(e){}}}
      if(text.trim())return{text,web,quellen:q};letzter="leer";break}}
  throw new Error("Keine KI erreichbar ("+letzter+"). Versuch es gleich nochmal.")}
function quellenAus(msg){const q=[];for(const t of msg?.executed_tools||[]){const sr=t.search_results;for(const r of (sr?.results||sr||[]))if(r?.url)q.push({titel:r.title||"",url:r.url})}
  return q.filter((x,i,a)=>a.findIndex(y=>y.url===x.url)===i).slice(0,8)}
function bubble(cls,html){const d=document.createElement("div");d.className="msg "+cls;d.innerHTML=html;$("#chat").append(d);d.scrollIntoView({block:"end",behavior:"smooth"});return d}
const fmt=t=>esc(t).replace(/\*\*(.+?)\*\*/g,"<b>$1</b>").replace(/(https?:\/\/[^\s)<]+)/g,'<a href="$1" target="_blank" rel="noopener">$1</a>');
async function ask(text){
  text=text.trim();if(!text)return;$("#inp").value="";grow();
  bubble("me",esc(text));hist.push({role:"user",content:text});archivieren("user",text);
  const web=$("#btnWeb").classList.contains("on")||needsWeb(text);
  const wait=bubble("ai",`<span class="muted">${web?"Ich recherchiere im Internet …":"Einen Moment …"}</span>`);$("#core").className="core busy";
  try{
    erinnern.cache=await erinnern(text);
    const sicht=t=>t.replace(/<think>[\s\S]*?(<\/think>|$)/g,"").replace(/\[\[[\s\S]*?(\]\]|$)/g,"").trim();
    let tick=0;const r=await llm([{role:"system",content:context(text)},...hist.slice(-16)],web,t=>{if(++tick%3===0||t.length<40){wait.innerHTML=`<div class="cursor">${md(sicht(t))}</div>`;wait.scrollIntoView({block:"end"})}});
    let out=r.text.replace(/<think>[\s\S]*?<\/think>/g,"").trim();const acts=[];
    out=out.replace(/\[\[(MERKEN|PROJEKT|STARTE|AUFTRAG|BAUEN|HINTERGRUND):\s*([\s\S]*?)\]\]/g,(_,k,v)=>{acts.push([k,v.trim()]);return""}).trim();
    hist.push({role:"assistant",content:out});hist=hist.slice(-40);ls.set("jv_hist",hist);archivieren("assistant",out);
    wait.innerHTML=md(out)+(r.quellen?.length?`<div class="quellen">${r.quellen.map((q,i)=>`<a href="${esc(q.url)}" target="_blank" rel="noopener" title="${esc(q.titel)}">${i+1} · ${esc(new URL(q.url).hostname.replace(/^www\./,""))}</a>`).join("")}</div>`:r.web?`<span class="src">🌐 mit Internet-Recherche</span>`:"");
    const chips=document.createElement("div");chips.className="chips";
    for(const[k,v]of acts){
      if(k==="MERKEN"){if(remember(v))chips.insertAdjacentHTML("beforeend",`<span class="chip done">🧠 gemerkt: ${esc(v)}</span>`)}
      else if(k==="PROJEKT"){const[t,st=""]=v.split("|");brain.proj.push({titel:t.trim(),schritte:st.split(";").map(x=>({x:x.trim(),ok:false})).filter(x=>x.x),t:Date.now()});saveBrain();
        chips.insertAdjacentHTML("beforeend",`<button class="chip done" data-open-brain>📋 Projekt angelegt: ${esc(t.trim())}</button>`)}
      else if(k==="STARTE"){const b=D.bots.find(x=>x.wf===v)||{name:v,wf:v};chips.append(confirmChip(`▶ ${b.name} starten?`,async()=>{await startWf(b.wf);return`${b.name} arbeitet.`}))}
      else if(k==="HINTERGRUND"){const j=await hintergrund(v);if(j)chips.insertAdjacentHTML("beforeend",`<span class="chip done">🛡️ ${esc(j.bot)} arbeitet im Hintergrund daran</span>`)}
      else if(k==="BAUEN"){const c=document.createElement("button");c.className="chip done";c.textContent="🛠 Ich baue: "+v.slice(0,50);c.onclick=()=>{bauListe();$("#dlgBau").showModal()};chips.append(c);$("#bWas").value=v;bauListe();$("#dlgBau").showModal();bauen(v)}
      else if(k==="AUFTRAG"){chips.append(confirmChip(`🛠 Einbauen: ${v.slice(0,60)}?`,async()=>{await auftrag(v.slice(0,80),v);return"An Claude übergeben."}))}
    }
    if(chips.children.length)wait.append(chips);
    $$("[data-open-brain]").forEach(b=>b.onclick=openBrain);
    if(cfg.talk||ask.voice)speak(out);else $("#core").className="core";
  }catch(e){wait.innerHTML=`<span class="neg">${esc(e.message)}</span>`;$("#core").className="core"}
  ask.voice=false;
}
function confirmChip(label,fn){const s=document.createElement("span");s.className="chip";s.innerHTML=`${esc(label)} <button class="btn go" style="padding:2px 10px;margin-left:6px">Ja</button><button class="btn ghost" style="padding:2px 10px">Nein</button>`;
  const[y,n]=s.querySelectorAll("button");y.onclick=async()=>{y.disabled=true;try{const m=await fn();s.className="chip done";s.textContent="✓ "+m}catch(e){toast(e.message);y.disabled=false}};n.onclick=()=>{s.className="chip";s.textContent="Abgelehnt"};return s}
function grow(){const t=$("#inp");t.style.height="auto";t.style.height=Math.min(t.scrollHeight,160)+"px"}
$("#inp").addEventListener("input",grow);
$("#inp").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();ask($("#inp").value)}});
$("#send").onclick=()=>ask($("#inp").value);
$("#btnWeb").onclick=e=>{const on=e.currentTarget.classList.toggle("on");e.currentTarget.setAttribute("aria-pressed",on);toast(on?"Jarvis recherchiert jetzt im Internet.":"Websuche nur bei Bedarf.")};
