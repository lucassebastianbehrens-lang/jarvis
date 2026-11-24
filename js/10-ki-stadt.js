"use strict";
/* ---------- KI-Stadt ---------- */
const wfOf=r=>(r.path||"").split("/").pop().split("@")[0];
function renderTown(){
  const now=Date.now()/1000,last={},cnt={};
  for(const r of D.runs){const w=wfOf(r);if(!last[w])last[w]=r;const t=Date.parse(r.created_at)/1000;if(now-t<86400)cnt[w]=(cnt[w]||0)+1}
  const bad=new Set((D.status?.checks||[]).filter(c=>!c.ok).map(c=>c.name));
  $("#town").innerHTML=D.bots.map((b,i)=>{const r=last[b.wf],t=r?Date.parse(r.created_at)/1000:0,
    work=r&&r.status!=="completed",err=(r&&["failure","timed_out"].includes(r.conclusion))||bad.has(b.name),
    lit=work||(r&&now-t<(b.max_h||24)*3600);
    return `<button class="house ${lit?"lit":""} ${work?"work":""} ${err?"err":""}" style="--c:${b.farbe}" data-i="${i}" aria-label="${esc(b.name)}, ${esc(b.haus)}${err?", Problem":""}">
      <span class="roof"></span><span class="wall"><i class="win"></i><i class="win"></i><span class="ico">${b.icon}</span></span>
      <span class="n">${esc(b.name)}</span><span class="h">${esc(b.haus)} · ${cnt[b.wf]||0}× heute</span></button>`}).join("")||`<p class="empty">Die Stadt lädt …</p>`;
  $$(".house").forEach(h=>h.onclick=()=>houseInfo(D.bots[h.dataset.i],last[D.bots[h.dataset.i].wf],cnt));
  $$(".house").forEach(h=>h.onfocus=()=>City.sel=+h.dataset.i);
  City.bots=D.bots;City.last=last;City.cnt=cnt;
  City.st=D.bots.map(b=>{const r=last[b.wf],t=r?Date.parse(r.created_at)/1000:0,work=!!r&&r.status!=="completed";
    return{work,err:(!!r&&["failure","timed_out"].includes(r.conclusion))||bad.has(b.name),lit:work||(!!r&&now-t<(b.max_h||24)*3600)}});
  cityStart();
  const active=D.bots.filter(b=>last[b.wf]&&now-Date.parse(last[b.wf].created_at)/1000<86400).length;
  $("#stadtInfo").textContent=`${D.bots.length} Bewohner · ${active} heute aktiv`;
  const names=Object.fromEntries(D.bots.map(b=>[b.wf,b]));
  $("#ticker").innerHTML=D.runs.filter(r=>names[wfOf(r)]).slice(0,10).map(r=>{const b=names[wfOf(r)],s=r.status!=="completed"?"arbeitet gerade …":r.conclusion==="success"?"hat Schicht erledigt ✓":r.conclusion==="failure"?"hatte einen Fehler ✕":r.conclusion;
    return `<li><time>${ago(Date.parse(r.created_at)/1000)}</time><span>${b.icon} <b>${esc(b.name)}</b> ${esc(s)}</span></li>`}).join("")||`<li class="muted">Noch keine Läufe geladen.</li>`;
}
/* ---------- KI-Stadt: 3D-Draufsicht mit laufenden Bots ---------- */
const City={bots:[],st:[],last:{},cnt:{},sel:-1,hov:-1,run:false,key:""};
const cityStart=(()=>{
  const cv=$("#cityCv"),g=cv.getContext("2d"),RM=matchMedia("(prefers-reduced-motion: reduce)").matches;
  const B=3,S=1,M=.42,ZK=.62;let N=4,T=17,W=0,H=0,tw=20,ox=0,oy=0,P=[],blds=[],parks=[],walkers=[],cars=[],last=0,lastDraw=0,tt=0;
  const hash=s=>{let h=7;for(const c of String(s))h=(h*31+c.charCodeAt(0))|0;return Math.abs(h)};
  const iso=(x,y,z=0)=>[ox+(x-y)*tw/2,oy+(x+y)*tw/4-z*tw*ZK];
  function shade(hex,f){const n=parseInt((hex||"#888").slice(1),16),m=f<0?0:255,a=Math.abs(f);
    return`rgb(${[n>>16,n>>8&255,n&255].map(c=>Math.round(c+(m-c)*a)).join(",")})`}
  function poly(pts,fill,stroke,lw=1){g.beginPath();pts.forEach(([x,y],i)=>i?g.lineTo(x,y):g.moveTo(x,y));g.closePath();
    if(fill){g.fillStyle=fill;g.fill()}if(stroke){g.strokeStyle=stroke;g.lineWidth=lw;g.stroke()}}
  const EF='"Apple Color Emoji","Segoe UI Emoji","Noto Color Emoji",sans-serif';
  function emoji(e,x,y,sz){g.font=`${sz}px ${EF}`;g.textAlign="center";g.textBaseline="middle";g.fillText(e,x,y)}
  // Box mit sichtbarer Dach-, Links- (y=y1) und Rechtsseite (x=x1)
  function box(x0,y0,x1,y1,z0,h,top,l,r,edge){
    poly([iso(x0,y1,z0),iso(x1,y1,z0),iso(x1,y1,z0+h),iso(x0,y1,z0+h)],l);
    poly([iso(x1,y1,z0),iso(x1,y0,z0),iso(x1,y0,z0+h),iso(x1,y1,z0+h)],r);
    poly([iso(x0,y0,z0+h),iso(x1,y0,z0+h),iso(x1,y1,z0+h),iso(x0,y1,z0+h)],top,edge,1);
  }
  function build(){
    const n=City.bots.length;N=Math.max(3,Math.ceil(Math.sqrt(n+1)));T=N*B+(N+1)*S;P=[];for(let k=0;k<=N;k++)P.push(k*(B+S)+S/2);
    const c=Math.floor((N-1)/2),lots=[];for(let j=0;j<N;j++)for(let i=0;i<N;i++)if(!(i===c&&j===c))lots.push([i,j]);
    // Häuser nahe der Zentrale zuerst
    lots.sort((a,b)=>(Math.abs(a[0]-c)+Math.abs(a[1]-c))-(Math.abs(b[0]-c)+Math.abs(b[1]-c))||a[1]-b[1]||a[0]-b[0]);
    const lot=(i,j,bi)=>{const x0=P[i]+S/2+M,y0=P[j]+S/2+M,x1=x0+B-2*M,y1=y0+B-2*M,b=City.bots[bi];
      return{i,j,bi,x0,y0,x1,y1,cx:(x0+x1)/2,cy:(y0+y1)/2,col:b?b.farbe:"#ff2e3a",h:bi===-1?5.6:b?1.1+(hash(b.name)%15)/10:0,seed:hash(b?b.name:"jarvis")}};
    blds=[lot(c,c,-1)];parks=[];lots.forEach((l,k)=>k<n?blds.push(lot(l[0],l[1],k)):parks.push(lot(l[0],l[1],-2)));
    const old=Object.fromEntries(walkers.map(w=>[w.bi,w]));
    walkers=City.bots.map((b,bi)=>old[bi]||{bi,k:Math.floor(Math.random()*(N+1)),l:Math.floor(Math.random()*(N+1)),path:[],mode:"walk",
      off:(Math.random()<.5?-1:1)*(.3+Math.random()*.08),spd:.75+Math.random()*.4,ph:Math.random()*6});
    walkers.forEach(w=>{w.k=Math.min(w.k,N);w.l=Math.min(w.l,N);if(w.x==null){w.x=P[w.k]+w.off;w.y=P[w.l]+w.off}});
    cars=[0,1,2].map(()=>newCar());
  }
  function newCar(){const cols=["#ff2e3a","#ff7a45","#ffc04d","#d9d2d0","#3ddc8f"];
    return{ax:Math.random()<.5?"x":"y",k:Math.floor(Math.random()*(N+1)),lane:Math.random()<.5?-.2:.2,pos:-1,spd:2+Math.random()*1.4,col:cols[Math.floor(Math.random()*cols.length)]}}
  function resize(){
    const w=cv.parentElement.clientWidth;if(!w)return false;dpr=Math.min(2,devicePixelRatio||1);W=w;
    tw=Math.min(W*.94/T,52);const c=blds[0]?blds[0].cx+blds[0].cy:T,top=Math.max(8,7*ZK*tw-c*tw/4)+16;H=Math.round(T*tw/2+top+.8*ZK*tw+12);ox=W/2;oy=top;
    cv.width=W*dpr;cv.height=H*dpr;cv.style.height=H+"px";g.setTransform(dpr,0,0,dpr,0,0);return true}
  let dpr=1;
  const want=w=>{const s=City.st[w.bi]||{};return s.err?"stand":s.work?"in":s.lit?"walk":"in"};
  const bOf=bi=>blds.find(b=>b.bi===bi);
  function routeHome(w){const b=bOf(w.bi);if(!b)return;const p=[];let k=w.k,l=w.l;
    while(k!==b.i){k+=Math.sign(b.i-k);p.push([P[k]+w.off,P[l]+w.off,k,l])}
    while(l!==b.j+1){l+=Math.sign(b.j+1-l);p.push([P[k]+w.off,P[l]+w.off,k,l])}
    p.push([b.cx,P[b.j+1]+w.off,k,l],[b.cx,b.y1+.06,k,l,"door"]);w.path=p}
  function step(w,dt){
    const d=want(w);
    if(w.mode!=="walk"){ // im Haus oder vor der Tür
      if(d===w.mode)return;const b=bOf(w.bi);if(!b)return;w.x=b.cx;w.y=b.y1+.06;
      if(d!=="walk"){w.mode=d;return}
      w.mode="walk";w.k=b.i;w.l=b.j+1;w.path=[[b.cx,P[b.j+1]+w.off,b.i,b.j+1],[P[b.i+1]+w.off,P[b.j+1]+w.off,b.i+1,b.j+1]];
      return}
    if(!w.path.length){
      if(d!=="walk"){routeHome(w);if(!w.path.length)return}
      else{const nb=[[1,0],[-1,0],[0,1],[0,-1]].map(([a,c])=>[w.k+a,w.l+c]).filter(([k,l])=>k>=0&&l>=0&&k<=N&&l<=N&&!(k===w.pk&&l===w.pl));
        const [k,l]=nb[Math.floor(Math.random()*nb.length)];w.pk=w.k;w.pl=w.l;w.path=[[P[k]+w.off,P[l]+w.off,k,l]]}}
    const [tx,ty,k,l,tag]=w.path[0],dx=tx-w.x,dy=ty-w.y,dist=Math.hypot(dx,dy),mv=w.spd*dt*(RM?.5:1);
    w.ph+=mv*9;
    if(dist<=mv){w.x=tx;w.y=ty;w.k=k;w.l=l;w.path.shift();if(tag==="door"){w.mode=d==="walk"?"in":d;w.path=[]}}
    else{w.x+=dx/dist*mv;w.y+=dy/dist*mv}
  }
  function stepCar(c,dt){c.pos+=c.spd*dt*(c.lane>0?1:-1)*(RM?.5:1);if(c.pos<-1.5||c.pos>T+1.5){Object.assign(c,newCar());c.pos=c.lane>0?-1:T+1}}
  function drawBld(b){
    const s=b.bi>=0?City.st[b.bi]||{}:{lit:1},tower=b.bi===-1,{x0,y0,x1,y1,h}=b,hot=b.bi>=0&&(City.hov===b.bi||City.sel===b.bi);
    // Schatten
    poly([iso(x0,y1),iso(x1,y1),iso(x1+.5,y1+.35),iso(x1+.5,y0+.35),iso(x1,y0)],"rgba(0,0,0,.35)");
    const wl=tower?"#1d080b":shade(b.col,-.8),wr=tower?"#14060a":shade(b.col,-.87);
    box(x0,y0,x1,y1,0,h,tower?"#2a0c12":b.col,wl,wr,hot?"#fff":tower?"#ff2e3a":shade(b.col,.35));
    // Fenster
    const rows=Math.max(1,Math.floor((h-.3)/.48)),L=x1-x0,cols=Math.max(2,Math.floor(L/.42));
    for(let f=0;f<2;f++)for(let r=0;r<rows;r++)for(let c=0;c<cols;c++){
      const sd=(b.seed+f*131+r*17+c*7)%100,z0=.28+r*.48;
      let on=s.work?((sd+Math.floor(tt*(RM?1:4)+sd))%3!==0):s.lit?sd<72:sd<6;if(tower)on=sd<85;
      const col=on?(s.work&&sd%2?"#fff3c4":"#ffd27a"):"#0b0405",u=x0+(c+.5)*L/cols-.09,v=y0+(c+.5)*L/cols-.09;
      if(f===0)poly([iso(u,y1+.01,z0),iso(u+.18,y1+.01,z0),iso(u+.18,y1+.01,z0+.22),iso(u,y1+.01,z0+.22)],col);
      else poly([iso(x1+.01,v+.18,z0),iso(x1+.01,v,z0),iso(x1+.01,v,z0+.22),iso(x1+.01,v+.18,z0+.22)],col)}
    if(!tower){ // Tür + Dachkante + Symbol
      poly([iso(b.cx-.13,y1+.01,0),iso(b.cx+.13,y1+.01,0),iso(b.cx+.13,y1+.01,.3),iso(b.cx-.13,y1+.01,.3)],s.work||s.lit?"#ffb45a":"#050203");
      poly([iso(x0+.16,y0+.16,h),iso(x1-.16,y0+.16,h),iso(x1-.16,y1-.16,h),iso(x0+.16,y1-.16,h)],shade(b.col,-.22));
      const [ex,ey]=iso(b.cx,b.cy,h);emoji(City.bots[b.bi].icon,ex,ey,tw*.75);
    }else{ // Jarvis-Zentrale: Antenne + Leuchtfeuer
      const [ax,ay]=iso(b.cx,b.cy,h),[bx,by]=iso(b.cx,b.cy,h+.9),p=.55+.45*Math.sin(tt*2.6);
      g.strokeStyle="#ff2e3a";g.lineWidth=2;g.beginPath();g.moveTo(ax,ay);g.lineTo(bx,by);g.stroke();
      const gr=g.createRadialGradient(bx,by,0,bx,by,tw*1.4);gr.addColorStop(0,`rgba(255,46,58,${.7*p})`);gr.addColorStop(1,"rgba(255,46,58,0)");
      g.fillStyle=gr;g.beginPath();g.arc(bx,by,tw*1.4,0,7);g.fill();g.fillStyle="#ff2e3a";g.beginPath();g.arc(bx,by,tw*.16,0,7);g.fill();
      g.font=`700 ${tw*.55}px Chakra Petch,sans-serif`;g.fillStyle="#ff8a8f";g.textAlign="center";g.fillText("JARVIS",ax,ay+tw*.15)}
    const pts=[iso(x0,y0,h),iso(x1,y1,0),iso(x0,y1,0),iso(x1,y0,0)];b.bb=[pts[2][0],pts[0][1]-tw*.4,pts[3][0],pts[1][1]];
  }
  function drawPark(p){
    poly([iso(p.x0-.2,p.y0-.2,.04),iso(p.x1+.2,p.y0-.2,.04),iso(p.x1+.2,p.y1+.2,.04),iso(p.x0-.2,p.y1+.2,.04)],"#0f2418","#1c3a27");
    [[.25,.3],[.7,.25],[.45,.7],[.8,.78]].forEach(([a,c],i)=>{const x=p.x0+a*(p.x1-p.x0),y=p.y0+c*(p.y1-p.y0),[tx,ty]=iso(x,y,0),[cx2,cy2]=iso(x,y,.75);
      g.strokeStyle="#3a2418";g.lineWidth=2;g.beginPath();g.moveTo(tx,ty);g.lineTo(cx2,cy2);g.stroke();
      g.fillStyle=i%2?"#1f5a35":"#17472a";g.beginPath();g.arc(cx2,cy2-tw*.12,tw*.34,0,7);g.fill()});
  }
  function drawWalker(w){
    if(w.mode==="in")return;const b=City.bots[w.bi];if(!b)return;
    const [x,y]=iso(w.x,w.y,0),u=tw,sw=w.mode==="walk"?Math.sin(w.ph)*u*.09:0,bob=w.mode==="stand"?Math.sin(tt*5)*u*.04:Math.abs(Math.sin(w.ph))*u*.03;
    g.fillStyle="rgba(0,0,0,.4)";g.beginPath();g.ellipse(x,y,u*.17,u*.07,0,0,7);g.fill();
    g.strokeStyle=shade(b.farbe,-.5);g.lineWidth=Math.max(1.5,u*.07);g.lineCap="round";
    g.beginPath();g.moveTo(x-u*.05,y-u*.2-bob);g.lineTo(x-u*.05+sw,y);g.moveTo(x+u*.05,y-u*.2-bob);g.lineTo(x+u*.05-sw,y);g.stroke();
    g.fillStyle=b.farbe;g.beginPath();g.roundRect?g.roundRect(x-u*.13,y-u*.5-bob,u*.26,u*.33,u*.08):g.rect(x-u*.13,y-u*.5-bob,u*.26,u*.33);g.fill();
    emoji(b.icon,x,y-u*.68-bob,u*.42);
    if(City.hov===w.bi||City.sel===w.bi){g.strokeStyle="#fff";g.lineWidth=1.5;g.beginPath();g.ellipse(x,y,u*.26,u*.11,0,0,7);g.stroke()}
    w.bb=[x-u*.3,y-u*.95,x+u*.3,y+u*.1];
  }
  function drawCar(c){
    const a=c.ax==="x",o=P[c.k]+c.lane,p=c.pos,L=.36,Wd=.17;
    const [x0,y0,x1,y1]=a?[p-L,o-Wd,p+L,o+Wd]:[o-Wd,p-L,o+Wd,p+L];
    box(x0,y0,x1,y1,0,.26,c.col,shade(c.col,-.45),shade(c.col,-.6));
    box(x0+(a?.12:.03),y0+(a?.03:.12),x1-(a?.12:.03),y1-(a?.03:.12),.26,.14,"#2b1a22",shade(c.col,-.7),"#110a0c");
    const f=c.lane>0?1:-1,[hx,hy]=a?iso(f>0?x1:x0,o,.13):iso(o,f>0?y1:y0,.13);
    g.fillStyle="rgba(255,236,170,.9)";g.beginPath();g.arc(hx,hy,Math.max(1.2,tw*.06),0,7);g.fill();
  }
  function label(b){
    const bot=City.bots[b.bi],s=City.st[b.bi]||{},[x,y]=iso(b.cx,b.cy,b.h+.9),t=`${bot.name} · ${bot.haus}`;
    g.font=`600 ${Math.max(11,tw*.6)}px Chakra Petch,sans-serif`;const w=g.measureText(t).width+16,hh=Math.max(20,tw*1.05);
    g.fillStyle="rgba(12,5,6,.92)";g.strokeStyle=s.err?"#ff2e3a":bot.farbe;g.lineWidth=1.5;g.beginPath();
    g.roundRect?g.roundRect(x-w/2,y-hh,w,hh,8):g.rect(x-w/2,y-hh,w,hh);g.fill();g.stroke();
    g.fillStyle="#f4e7e5";g.textAlign="center";g.textBaseline="middle";g.fillText(t,x,y-hh/2);
  }
  function badges(b){
    const s=City.st[b.bi]||{},[x,y]=iso(b.cx,b.cy,b.h+.35);
    if(s.err){const yy=y-Math.abs(Math.sin(tt*3))*tw*.25;g.fillStyle="#ff2e3a";g.beginPath();g.arc(x,yy,tw*.36,0,7);g.fill();
      g.fillStyle="#fff";g.font=`700 ${tw*.5}px sans-serif`;g.textAlign="center";g.textBaseline="middle";g.fillText("!",x,yy+1)}
    else if(s.work){g.save();g.translate(x,y);g.rotate(tt*2);emoji("⚙️",0,0,tw*.6);g.restore()}
    else if(!s.lit){const k=(tt*.5+b.seed%10/10)%1;g.globalAlpha=1-k;g.fillStyle="#a98d8a";g.font=`600 ${tw*(.4+k*.3)}px sans-serif`;
      g.textAlign="center";g.fillText("z",x+k*tw*.6,y-k*tw);g.globalAlpha=1}
  }
  function draw(){
    g.clearRect(0,0,W,H);
    // Bodenplatte mit Kante
    const dz=-.8;
    poly([iso(0,T,0),iso(T,T,0),iso(T,T,dz),iso(0,T,dz)],"#1a0a0d");poly([iso(T,T,0),iso(T,0,0),iso(T,0,dz),iso(T,T,dz)],"#120609");
    poly([iso(0,0),iso(T,0),iso(T,T),iso(0,T)],"#161014","rgba(255,46,58,.55)",1.5);
    // Gehwege/Blöcke
    for(let j=0;j<N;j++)for(let i=0;i<N;i++){const a=P[i]+S/2,c=P[j]+S/2;poly([iso(a,c,.05),iso(a+B,c,.05),iso(a+B,c+B,.05),iso(a,c+B,.05)],"#2a171b","#3b161b")}
    // Mittellinien
    g.save();g.setLineDash([tw*.28,tw*.32]);g.strokeStyle="rgba(255,192,77,.35)";g.lineWidth=Math.max(1,tw*.05);
    for(const p of P){g.beginPath();g.moveTo(...iso(p,0));g.lineTo(...iso(p,T));g.moveTo(...iso(0,p));g.lineTo(...iso(T,p));g.stroke()}g.restore();
    // Laternen-Licht
    for(const a of P)for(const c of P){const [x,y]=iso(a+.55,c+.55,0),r=tw*1.1,gr=g.createRadialGradient(x,y,0,x,y,r);
      gr.addColorStop(0,"rgba(255,180,90,.22)");gr.addColorStop(1,"rgba(255,180,90,0)");g.fillStyle=gr;g.fillRect(x-r,y-r,2*r,2*r);
      const [lx,ly]=iso(a+.55,c+.55,.7);g.fillStyle="#ffd27a";g.beginPath();g.arc(lx,ly,Math.max(1.2,tw*.07),0,7);g.fill()}
    // Tiefensortierung
    const items=[...blds.map(b=>[b.cx+b.cy,()=>drawBld(b)]),...parks.map(p=>[p.cx+p.cy-1,()=>drawPark(p)]),
      ...walkers.map(w=>[w.x+w.y,()=>drawWalker(w)]),
      ...cars.map(c=>{const o=P[c.k]+c.lane;return[o+c.pos,()=>drawCar(c)]})];
    items.sort((a,b)=>a[0]-b[0]).forEach(i=>i[1]());
    blds.forEach(b=>b.bi>=0&&badges(b));
    const hi=City.hov>=0?City.hov:City.sel,hb=hi>=0&&bOf(hi);if(hb)label(hb);
  }
  function loop(t){
    if(!$("#t-stadt").classList.contains("on")||document.hidden){City.run=false;return}
    const dt=Math.min(.05,(t-last)/1000||0);last=t;tt=t/1000;
    walkers.forEach(w=>step(w,dt));cars.forEach(c=>stepCar(c,dt));
    if(t-lastDraw>=(RM?200:32)){lastDraw=t;draw()}
    requestAnimationFrame(loop)}
  function hit(e){const r=cv.getBoundingClientRect(),x=e.clientX-r.left,y=e.clientY-r.top,inb=b=>b.bb&&x>=b.bb[0]&&x<=b.bb[2]&&y>=b.bb[1]&&y<=b.bb[3];
    const w=walkers.filter(w=>w.mode!=="in"&&inb(w)).sort((a,b)=>b.y+b.x-a.y-a.x)[0];if(w)return w.bi;
    const b=[...blds].sort((a,c)=>c.cx+c.cy-a.cx-a.cy).find(inb);return b?b.bi:null}
  cv.addEventListener("pointermove",e=>{if(e.pointerType!=="mouse")return;const h=hit(e);City.hov=h??-1;cv.style.cursor=h!=null?"pointer":"default"});
  cv.addEventListener("pointerleave",()=>City.hov=-1);
  cv.addEventListener("click",e=>{const h=hit(e);if(h==null)return;if(h===-1){show("jarvis");return}
    City.sel=h;const b=City.bots[h];houseInfo(b,City.last[b.wf],City.cnt)});
  new ResizeObserver(()=>{if(City.run)resize()}).observe(cv.parentElement);
  return function(){
    const key=City.bots.map(b=>b.wf).join();if(key!==City.key){City.key=key;build()}
    if(City.run||!$("#t-stadt").classList.contains("on")||document.hidden)return;
    if(!resize())return;City.run=true;last=performance.now();requestAnimationFrame(loop)}
})();
document.addEventListener("visibilitychange",()=>{if(!document.hidden)cityStart()});
function houseInfo(b,r,cnt){
  const d=document.createElement("dialog");
  const chk=(D.status?.checks||[]).find(c=>c.name===b.name);
  d.innerHTML=`<div class="row" style="justify-content:space-between"><h2>${b.icon} ${esc(b.name)}</h2><button class="x" data-close aria-label="Schließen">✕</button></div>
   <p class="muted">${esc(b.haus)}</p><p>${esc(b.job)}</p>
   <div class="kv small"><span class="muted">Letzte Schicht</span><span>${r?ago(Date.parse(r.created_at)/1000):"–"}</span>
   <span class="muted">Ergebnis</span><span>${r?(r.status!=="completed"?"läuft":r.conclusion==="success"?"✓ ok":"✕ "+r.conclusion):"–"}</span>
   <span class="muted">Schichten in 24 h</span><span>${cnt[b.wf]||0}</span>
   ${chk?`<span class="muted">Wächter sagt</span><span>${esc(chk.info)}</span>`:""}</div>
   <div class="row" style="margin-top:16px"><button class="btn go" id="hStart">Jetzt arbeiten lassen</button>${r?`<a class="btn" href="${r.html_url}" target="_blank" rel="noopener">Protokoll</a>`:""}</div>`;
  document.body.append(d);d.showModal();d.querySelector("[data-close]").onclick=()=>{d.close();d.remove()};
  d.querySelector("#hStart").onclick=async e=>{e.target.disabled=true;try{await startWf(b.wf);toast(`${b.name} legt los.`);d.close();d.remove();setTimeout(loadAll,8000)}catch(x){toast(x.message);e.target.disabled=false}};
}
async function startWf(wf){if(!cfg.gh)throw new Error("Dafür braucht Jarvis den GitHub-Token (⚙️ Einstellungen).");await gh(`/actions/workflows/${wf}/dispatches`,{ref:"main"})}
