"use strict";
/* ---------- Jarvis-Kern (Partikel-Kugel) ---------- */
(function orb(){const btn=$("#core"),cv=document.createElement("canvas");cv.className="orbcv";btn.append(cv);const g=cv.getContext("2d");
  const RM=matchMedia("(prefers-reduced-motion: reduce)").matches,N=520,P=[];
  for(let i=0;i<N;i++){const y=1-2*(i+.5)/N,r=Math.sqrt(1-y*y),a=i*2.39996;P.push([Math.cos(a)*r,y,Math.sin(a)*r])}
  let S=0,lvl=0;function size(){const d=devicePixelRatio||1;S=btn.clientWidth;cv.width=cv.height=S*1.6*d;g.setTransform(d,0,0,d,0,0)}size();new ResizeObserver(size).observe(btn);
  function frame(t){const st=btn.className,busy=st.includes("busy"),talk=st.includes("talk"),lis=st.includes("listen");
    const ziel=talk?.55+.45*Math.abs(Math.sin(t/140)):busy?.35:lis?.5+.3*Math.sin(t/200):.12;lvl+=(ziel-lvl)*.08;
    const W=S*1.6,c=W/2,R=S*.36*(1+lvl*.18),rot=t/(busy?900:2600),ca=Math.cos(rot),sa=Math.sin(rot),tl=.35;
    g.clearRect(0,0,W,W);const gl=g.createRadialGradient(c,c,0,c,c,R*1.7);gl.addColorStop(0,`rgba(255,80,90,${.35+lvl*.4})`);gl.addColorStop(.45,"rgba(255,46,58,.12)");gl.addColorStop(1,"rgba(255,46,58,0)");g.fillStyle=gl;g.fillRect(0,0,W,W);
    g.globalCompositeOperation="lighter";
    for(let i=0;i<N;i++){let[x,y,z]=P[i];const w=1+lvl*.25*Math.sin(t/180+i);let X=x*ca-z*sa,Z=x*sa+z*ca,Y=y*Math.cos(tl)-Z*Math.sin(tl);Z=y*Math.sin(tl)+Z*Math.cos(tl);
      const k=(Z+1)/2,px=c+X*R*w,py=c+Y*R*w;g.fillStyle=`rgba(255,${110+k*120|0},${120+k*80|0},${.15+k*.75})`;const s=.6+k*1.6;g.fillRect(px-s/2,py-s/2,s,s)}
    const cg=g.createRadialGradient(c,c,0,c,c,R*.5);cg.addColorStop(0,"rgba(255,255,255,.95)");cg.addColorStop(.25,"rgba(255,170,160,.6)");cg.addColorStop(1,"rgba(255,46,58,0)");g.fillStyle=cg;g.beginPath();g.arc(c,c,R*.5,0,7);g.fill();
    g.globalCompositeOperation="source-over";g.strokeStyle=`rgba(255,122,69,${.25+lvl*.5})`;g.lineWidth=1;
    for(let j=0;j<3;j++){g.beginPath();g.arc(c,c,R*(1.18+j*.1),rot*(j%2?-1.5:1)+j,rot*(j%2?-1.5:1)+j+1.6+lvl*2);g.stroke()}
    if(!RM&&!document.hidden)requestAnimationFrame(frame)}
  requestAnimationFrame(frame);document.addEventListener("visibilitychange",()=>{if(!document.hidden&&!RM)requestAnimationFrame(frame)});
  new MutationObserver(()=>{if(RM)frame(performance.now())}).observe(btn,{attributes:true})})();
