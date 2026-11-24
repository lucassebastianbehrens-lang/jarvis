"use strict";
/* ---------- Markdown für Antworten ---------- */
function md(t){const blocks=[];t=String(t).replace(/```(\w*)\n?([\s\S]*?)```/g,(_,l,c)=>{blocks.push(`<pre class="code">${esc(c.trim())}</pre>`);return`\u0000${blocks.length-1}\u0000`});
  const inl=s=>esc(s).replace(/`([^`]+)`/g,"<code>$1</code>").replace(/\*\*(.+?)\*\*/g,"<b>$1</b>").replace(/(^|[^*])\*([^*\s][^*]*?)\*/g,"$1<i>$2</i>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>').replace(/(^|[\s(])(https?:\/\/[^\s)<]+)/g,(_,a,u)=>`${a}<a href="${u}" target="_blank" rel="noopener">${u.replace(/^https?:\/\/(www\.)?/,"").slice(0,40)}${u.length>48?"…":""}</a>`);
  let h="",list=null;const close=()=>{if(list){h+=`</${list}>`;list=null}};
  for(const raw of t.split("\n")){const l=raw.trimEnd(),b=l.match(/^\u0000(\d+)\u0000$/);
    if(b){close();h+=blocks[b[1]];continue}
    const hd=l.match(/^(#{1,4})\s+(.*)/),ul=l.match(/^\s*[-*•]\s+(.*)/),ol=l.match(/^\s*\d+[.)]\s+(.*)/);
    if(hd){close();h+=`<p class="mh">${inl(hd[2])}</p>`}
    else if(ul){if(list!=="ul"){close();h+="<ul>";list="ul"}h+=`<li>${inl(ul[1])}</li>`}
    else if(ol){if(list!=="ol"){close();h+="<ol>";list="ol"}h+=`<li>${inl(ol[1])}</li>`}
    else if(/^\s*\|/.test(l)){close();h+=`<p class="small">${inl(l)}</p>`}
    else if(!l.trim()){close();h+=`<div class="gap"></div>`}
    else{close();h+=`<p>${inl(l)}</p>`}}
  close();return h}
