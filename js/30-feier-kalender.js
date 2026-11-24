"use strict";
/* ---------- Erfolgs-Feier ---------- */
function feiern(titel,sub){const d=document.createElement("dialog");d.className="fx";d.setAttribute("aria-label",titel);
  d.innerHTML=`<canvas></canvas><div class="orb"></div><div><div class="t">${esc(titel)}</div><div class="s">${esc(sub||"")}</div></div>`;document.body.append(d);d.showModal();d.oncancel=()=>end();
  const cv=d.querySelector("canvas"),g=cv.getContext("2d"),W=cv.width=innerWidth,H=cv.height=innerHeight,P=[];
  for(let i=0;i<160;i++){const a=Math.random()*7,v=1+Math.random()*5;P.push({x:W/2,y:H/2,vx:Math.cos(a)*v,vy:Math.sin(a)*v,l:1})}
  let alive=true;(function f(){if(!alive)return;g.clearRect(0,0,W,H);for(const p of P){p.x+=p.vx;p.y+=p.vy;p.vx*=.985;p.vy*=.985;p.l*=.988;
    g.fillStyle=`rgba(255,${140+Math.random()*80|0},80,${p.l})`;g.fillRect(p.x,p.y,2,2)}requestAnimationFrame(f)})();
  const end=()=>{alive=false;d.remove()};d.onclick=end;setTimeout(end,4200);try{navigator.vibrate?.([60,40,120])}catch(e){}}

/* ---------- Kalender-Datei (.ics) ---------- */
function ics(titel,start,minuten,text,alarm){const z=d=>d.toISOString().replace(/[-:]/g,"").replace(/\.\d+/,""),e=s=>String(s).replace(/\\/g,"\\\\").replace(/\n/g,"\\n").replace(/[,;]/g,m=>"\\"+m);
  const a=new Date(start),b=new Date(a.getTime()+minuten*60000);
  const body=["BEGIN:VCALENDAR","VERSION:2.0","PRODID:-//Jarvis//DE","BEGIN:VEVENT","UID:"+Date.now()+"@jarvis","DTSTAMP:"+z(new Date()),"DTSTART:"+z(a),"DTEND:"+z(b),"SUMMARY:"+e(titel),"DESCRIPTION:"+e(text.slice(0,1800)),
    "BEGIN:VALARM","ACTION:DISPLAY","DESCRIPTION:"+e(titel),"TRIGGER:-PT"+alarm+"M","END:VALARM","END:VEVENT","END:VCALENDAR"].join("\r\n");
  const u=URL.createObjectURL(new Blob([body],{type:"text/calendar"})),l=document.createElement("a");l.href=u;l.download=titel.replace(/[^\wäöüÄÖÜß -]/g,"").slice(0,40)+".ics";l.click();setTimeout(()=>URL.revokeObjectURL(u),5000)}
const dtLocal=d=>{const x=new Date(d.getTime()-d.getTimezoneOffset()*60000);return x.toISOString().slice(0,16)};
