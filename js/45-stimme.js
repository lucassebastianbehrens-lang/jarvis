"use strict";
/* ---------- Stimme: sprechen ---------- */
let voices=[];
function loadVoices(){voices=speechSynthesis.getVoices().filter(v=>v.lang.startsWith("de"));
  const rank=v=>(/natural|online|neural|premium|enhanced/i.test(v.name)?0:/google/i.test(v.name)?1:2);voices.sort((a,b)=>rank(a)-rank(b));
  $("#cVoice").innerHTML=voices.map(v=>`<option ${v.name===cfg.voice?"selected":""}>${esc(v.name)}</option>`).join("")||"<option>Standard</option>"}
if("speechSynthesis"in window){loadVoices();speechSynthesis.onvoiceschanged=loadVoices}
const clean=t=>t.replace(/https?:\/\/\S+/g,"").replace(/[*_#>`|]/g,"").replace(/\p{Extended_Pictographic}/gu,"").slice(0,2500);
let audio;
async function speak(text){
  text=clean(text);if(!text)return;$("#core").className="core talk";const done=()=>$("#core").className="core";
  if(cfg.el&&cfg.elv){try{const r=await fetch(`https://api.elevenlabs.io/v1/text-to-speech/${cfg.elv}?output_format=mp3_44100_128`,{method:"POST",headers:{"xi-api-key":cfg.el,"Content-Type":"application/json"},body:JSON.stringify({text,model_id:"eleven_multilingual_v2"})});
    if(r.ok){audio?.pause();audio=new Audio(URL.createObjectURL(await r.blob()));audio.onended=done;audio.play();return}}catch(e){console.warn(e)}}
  if(!("speechSynthesis"in window))return done();
  speechSynthesis.cancel();const sentences=text.match(/[^.!?]+[.!?]*/g)||[text];
  sentences.forEach((s,i)=>{const u=new SpeechSynthesisUtterance(s.trim());u.lang="de-DE";u.voice=voices.find(v=>v.name===cfg.voice)||voices[0]||null;u.rate=1.03;u.pitch=.92;if(i===sentences.length-1)u.onend=done;speechSynthesis.speak(u)});
}

/* ---------- Stimme: zuhören ---------- */
const SR=window.SpeechRecognition||window.webkitSpeechRecognition;let rec,recording=false,mr,chunks=[];
function setListen(on){recording=on;$("#btnMic").classList.toggle("rec",on);$("#core").classList.toggle("listen",on);$("#coreHint").textContent=on?"Ich höre zu …":"Tipp auf den Kern und sprich – oder schreib unten."}
async function listen(){
  if(recording){rec?.stop();mr?.state==="recording"&&mr.stop();return}
  speechSynthesis?.cancel();audio?.pause();
  if(SR){rec=new SR();rec.lang="de-DE";rec.interimResults=true;rec.continuous=false;let final="";
    rec.onresult=e=>{final=[...e.results].map(r=>r[0].transcript).join(" ");$("#inp").value=final;grow()};
    rec.onend=()=>{setListen(false);if(final.trim()){ask.voice=true;ask(final)}};rec.onerror=e=>{setListen(false);if(e.error!=="no-speech")toast("Mikrofon: "+e.error)};
    rec.start();setListen(true);return}
  if(!cfg.groq)return toast("Spracheingabe braucht hier den Groq-Schlüssel (⚙️).");
  try{const st=await navigator.mediaDevices.getUserMedia({audio:true});mr=new MediaRecorder(st);chunks=[];mr.ondataavailable=e=>chunks.push(e.data);
    mr.onstop=async()=>{st.getTracks().forEach(t=>t.stop());setListen(false);const fd=new FormData();fd.append("file",new Blob(chunks,{type:mr.mimeType}),"sprache.webm");fd.append("model","whisper-large-v3-turbo");fd.append("language","de");
      try{const r=await fetch("https://api.groq.com/openai/v1/audio/transcriptions",{method:"POST",headers:{Authorization:"Bearer "+cfg.groq},body:fd});const j=await r.json();if(j.text){ask.voice=true;ask(j.text)}}catch(e){toast("Spracherkennung fehlgeschlagen")}};
    mr.start();setListen(true);setTimeout(()=>mr.state==="recording"&&mr.stop(),30000)}catch(e){toast("Kein Mikrofon-Zugriff")}
}
$("#btnMic").onclick=listen;$("#core").onclick=listen;
