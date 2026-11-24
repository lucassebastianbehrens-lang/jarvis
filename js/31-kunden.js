"use strict";
/* ---------- Kunden-Onboarding ---------- */
$("#tKunde").onclick=()=>{$("#kForm").hidden=false;$("#kRun").hidden=true;const d=new Date(Date.now()+2*864e5);d.setHours(10,0,0,0);$("#kStart").value=dtLocal(d);$("#dlgKunde").showModal()};
$("#kForm").onsubmit=e=>{e.preventDefault();onboarding({firma:$("#kFirma").value.trim(),name:$("#kName").value.trim(),leist:$("#kLeist").value,preis:+$("#kPreis").value||0,start:$("#kStart").value,tel:$("#kTel").value.trim()})};
async function onboarding(k){if(!k.firma)return toast("Bitte die Firma eintragen.");
  $("#kForm").hidden=true;$("#kRun").hidden=false;$("#kTitel").textContent=k.firma;
  brain.kunden=brain.kunden||[];const nr=`RE-${new Date().getFullYear()}-${String(brain.kunden.length+1).padStart(3,"0")}`;
  const S=[["👤","Kunde anlegen"],["🧾","Rechnungsentwurf"],["📋","Projekt-Board"],["📅","Kick-off-Termin"],["💬","Willkommensnachricht"]];
  $("#kSteps").innerHTML=S.map(([i,t],j)=>`<li id="ks${j}"><b>${i}</b><div style="flex:1"><b>${t}</b><div class="out"></div></div></li>`).join("");
  const step=async(j,fn)=>{const li=$("#ks"+j);li.classList.add("on");li.querySelector("b").textContent="…";try{await fn(li.querySelector(".out"))}catch(x){li.querySelector(".out").textContent="✕ "+x.message}
    li.classList.add("ok");li.querySelector("b").textContent="✓";const p=Math.round((j+1)/S.length*100);$("#kPct").textContent=p+" %";$("#kBar").style.width=p+"%";await new Promise(r=>setTimeout(r,450))};
  const anrede=k.name||"Team "+k.firma, start=k.start?new Date(k.start):null;
  await step(0,async o=>{brain.kunden.push({...k,nr,t:Date.now()});saveBrain();o.textContent=`${k.firma} · ${k.leist} · ${k.preis?eur(k.preis):"Preis offen"}`});
  await step(1,async o=>{const txt=`Rechnung ${nr}\nAn: ${k.firma}${k.name?", "+k.name:""}\nLeistung: ${k.leist}\nBetrag: ${eur(k.preis)}\nZahlbar innerhalb von 14 Tagen.\n(Steuerangaben je nach deinem Status ergänzen.)`;
    o.innerHTML=`${esc(txt)}\n<span class="row" style="margin-top:6px"><a class="btn" href="https://www.paypal.com/invoice/create" target="_blank" rel="noopener">In PayPal anlegen</a><button class="btn" type="button" data-cp>Kopieren</button></span>`;
    o.querySelector("[data-cp]").onclick=()=>navigator.clipboard.writeText(txt).then(()=>toast("Kopiert."))});
  await step(2,async o=>{const s=["Zugänge & Logo vom Kunden holen","Kick-off-Gespräch führen","Ziele & Zielgruppe festhalten","Ersten Inhaltsplan (2 Wochen) erstellen","Erste Lieferung an den Kunden","Rechnung "+nr+" bezahlt? prüfen"];
    brain.proj.push({titel:"Kunde: "+k.firma,schritte:s.map(x=>({x,ok:false})),t:Date.now()});saveBrain();o.textContent=s.length+" Schritte angelegt (🧠 → Projekte)."});
  await step(3,async o=>{if(!start){o.textContent="Kein Termin angegeben – übersprungen.";return}
    o.innerHTML=`${start.toLocaleString("de-DE",{dateStyle:"full",timeStyle:"short"})}\n<button class="btn" type="button" style="margin-top:6px">📅 In Kalender eintragen</button>`;
    o.querySelector("button").onclick=()=>ics(`Kick-off: ${k.firma}`,start,45,`${k.leist}\nAnsprechpartner: ${k.name||"-"}\nTel: ${k.tel||"-"}`,30)});
  await step(4,async o=>{let msg=`Hallo ${anrede},\n\nwillkommen an Bord! Ich freue mich auf die Zusammenarbeit bei ${k.leist}.${start?` Unser Kick-off ist am ${start.toLocaleString("de-DE",{weekday:"long",day:"numeric",month:"long",hour:"2-digit",minute:"2-digit"})} Uhr.`:""} Bis dahin schicken Sie mir gern Ihr Logo und ein paar Fotos Ihrer Arbeit.\n\nViele Grüße\nLucas`;
    try{const r=await llm([{role:"system",content:"Schreib eine kurze, herzliche, professionelle WhatsApp-Willkommensnachricht auf Deutsch (Sie-Form, max. 5 Sätze, ohne Emojis-Flut, Absender Lucas). Nur die Nachricht."},{role:"user",content:`Kunde: ${k.firma}, Ansprechpartner: ${k.name||"unbekannt"}, Leistung: ${k.leist}, Kick-off: ${start?start.toLocaleString("de-DE"):"noch offen"}. Bitte um Logo und Fotos.`}]);
      const t=r.text.replace(/<think>[\s\S]*?<\/think>/g,"").trim();if(t.length>40)msg=t}catch(e){}
    const tel=k.tel.replace(/[^\d+]/g,"").replace(/^00/,"+").replace(/^0/,"+49").replace(/^\+/,"");
    o.innerHTML=`${esc(msg)}\n<span class="row" style="margin-top:6px">${tel?`<a class="btn go" href="https://wa.me/${tel}?text=${encodeURIComponent(msg)}" target="_blank" rel="noopener">Per WhatsApp senden</a>`:""}<button class="btn" type="button" data-cp>Kopieren</button></span>`;
    o.querySelector("[data-cp]").onclick=()=>navigator.clipboard.writeText(msg).then(()=>toast("Kopiert."))});
  feiern("KUNDE AN BORD",k.firma+(k.preis?" · "+eur(k.preis):""));speak(`Neuer Kunde an Bord: ${k.firma}. Rechnung, Projekt und Willkommensnachricht liegen bereit.`)}
