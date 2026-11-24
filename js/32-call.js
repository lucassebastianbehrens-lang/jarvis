"use strict";
/* ---------- Call-Vorbereitung ---------- */
let calls=ls.get("jv_calls",[]);
$("#tCall").onclick=()=>{$("#cForm").hidden=false;$("#cOut").hidden=true;const d=new Date(Date.now()+36e5);d.setMinutes(0,0,0);$("#cWann").value=dtLocal(d);$("#dlgCall").showModal()};
$("#cGo").onclick=async e=>{const wer=$("#cWer").value.trim(),web=$("#cWeb").value.trim(),was=$("#cWas").value.trim(),wann=$("#cWann").value;if(!wer)return toast("Mit wem ist der Call?");
  e.target.disabled=true;e.target.textContent="Recherchiere …";
  try{const r=await llm([{role:"system",content:context()},{role:"user",content:`Ich habe gleich einen Call mit ${wer}${web?" ("+web+")":""}. Thema: ${was||"Erstgespräch"}.
Recherchiere im Internet und schreib mir: „Alles, was du vor dem Gespräch wissen musst“ – kurz, auf Deutsch, in diesen Abschnitten:
1. Wer ist das? (3 Stichpunkte, nur belegbare Fakten, sonst „nicht gefunden“)
2. Was die wollen / wo der Schuh drückt (2–3 Punkte)
3. Mein Ziel für den Call (1 Satz)
4. 3 gute Fragen
5. Mögliche Einwände + kurze Antwort
Keine Aktionszeilen.`}],true);
    const t=r.text.replace(/<think>[\s\S]*?<\/think>/g,"").replace(/\[\[[\s\S]*?\]\]/g,"").trim();
    const c={wer,was,wann,text:t,id:Date.now()};calls=[c,...calls.filter(x=>new Date(x.wann)>Date.now())].slice(0,10);ls.set("jv_calls",calls);planCalls();
    $("#cText").textContent=t;$("#cForm").hidden=true;$("#cOut").hidden=false;
    $("#cIcs").onclick=()=>{if(!wann)return toast("Bitte eine Uhrzeit angeben.");ics(`Call: ${wer}`,new Date(wann),30,t,5);toast("Termin mit Wecker 5 Min vorher – in deinem Kalender speichern.")};
    $("#cRead").onclick=()=>speak(t);$("#cCopy").onclick=()=>navigator.clipboard.writeText(t).then(()=>toast("Kopiert."));
    if("Notification"in window&&Notification.permission==="default")Notification.requestPermission().catch(()=>{})}
  catch(x){toast(x.message)}e.target.disabled=false;e.target.textContent="Vorbereiten"};
const callTimers=[];
function planCalls(){callTimers.splice(0).forEach(clearTimeout);
  for(const c of calls){const ms=new Date(c.wann).getTime()-5*60000-Date.now();if(ms<0||ms>864e5)continue;
    callTimers.push(setTimeout(()=>{feiern("CALL IN 5 MIN",c.wer);
      try{if(Notification.permission==="granted")new Notification("Jarvis: Call in 5 Minuten",{body:c.wer+" – "+(c.was||""),icon:"icon-192.png"})}catch(e){}
      setTimeout(()=>speak(`Lucas, in fünf Minuten ist dein Call mit ${c.wer}. Hier das Wichtigste. ${c.text}`),1500)},ms))}}
planCalls();
