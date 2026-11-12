/* MedCommodities chart window — TradingView-style, built on TradingView Lightweight Charts v5 (Apache-2.0, vendored).
   Opened by any element with class .ck and data-sym / data-name (futures rows, macro snapshot, EUR/USD, 6E, palm).
   12 Nov 2026. Loader is pluggable: window.MC_CHART_LOADER(sym, tf, src) -> Promise<payload> (static Pages build). */
(function(){
'use strict';
const LW=window.LightweightCharts;
const TZ='Europe/Paris', TZL='CET';
const TFS=[['15m','15m','Intraday 15m'],['60m','1H','Intraday 1 hour'],['1d','D','Daily'],['1wk','W','Weekly'],['1mo','M','Monthly']];
const TFNAME={'15m':'Intraday 15m','60m':'1 hour','1d':'Daily','1wk':'Weekly','1mo':'Monthly'};
const COL={up:'#26c281',dn:'#f0505f',acc:'#29ABFF',acc2:'#0A6CFF',grid:'rgba(42,58,78,0.38)',tx:'#c9d4e0',bg:'#0f141b'};
const MA_COL=['#29ABFF','#ffb000','#c58cff','#ff6fb1'],EC=['#7ee0c3','#ff8a4c','#e7d36b','#f5f5f5'];
const LS='mcchart.v1', LSW='mcchart.win.v1', LSD='mcchart.draw.v1.';
const DEF={tf:'1d',type:'candle',log:false,side:true,vol:true,
 sma:[{p:20,on:false},{p:50,on:true},{p:100,on:false},{p:200,on:true}],
 ema:[{p:20,on:false},{p:50,on:false},{p:100,on:false},{p:200,on:false}],
 bb:{on:false,p:20,k:2},rsi:{on:false,p:14},macd:{on:false,f:12,s:26,g:9}};
const clone=o=>JSON.parse(JSON.stringify(o));
let ST;try{ST=Object.assign(clone(DEF),JSON.parse(localStorage.getItem(LS)||'{}'))}catch(e){ST=clone(DEF)}
const save=()=>{try{localStorage.setItem(LS,JSON.stringify(ST))}catch(e){}};
const $=(s,r=document)=>r.querySelector(s);
const esc=s=>String(s==null?'':s).replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const IC={
 cursor:'<svg viewBox="0 0 16 16"><path d="M3 2l9 5.2-4 1 2.4 4.3-1.6.9L6.4 9l-3 3z"/></svg>',
 trend:'<svg viewBox="0 0 16 16"><path d="M2.5 13.5l11-11"/><circle cx="2.5" cy="13.5" r="1.4"/><circle cx="13.5" cy="2.5" r="1.4"/></svg>',
 hline:'<svg viewBox="0 0 16 16"><path d="M1 8h14"/><circle cx="8" cy="8" r="1.5"/></svg>',
 fib:'<svg viewBox="0 0 16 16"><path d="M1.5 2.5h13M1.5 6h13M1.5 9.5h13M1.5 13.5h13"/><path d="M3 13.5L13 2.5" stroke-dasharray="1.5 1.5"/></svg>',
 trash:'<svg viewBox="0 0 16 16"><path d="M2.5 4h11M6 4V2.5h4V4M4 4l.7 9.5h6.6L12 4"/></svg>',
 del:'<svg viewBox="0 0 16 16"><path d="M3 3l10 10M13 3L3 13"/></svg>',
 auto:'<svg viewBox="0 0 16 16"><path d="M8 1.5v13M5.5 4L8 1.5 10.5 4M5.5 12L8 14.5 10.5 12"/></svg>',
 reset:'<svg viewBox="0 0 16 16"><path d="M2.5 8a5.5 5.5 0 1 0 1.7-4"/><path d="M2.5 2v3.5H6"/></svg>',
 ind:'<svg viewBox="0 0 16 16"><path d="M1.5 12.5l3.5-4 3 2.5 5.5-7"/><path d="M11 4h2.5v2.5"/></svg>',
 side:'<svg viewBox="0 0 16 16"><rect x="1.5" y="2.5" width="13" height="11" rx="1.5"/><path d="M10 2.5v11"/></svg>',
 max:'<svg viewBox="0 0 16 16"><rect x="2.5" y="2.5" width="11" height="11" rx="1.5"/></svg>',
 full:'<svg viewBox="0 0 16 16"><path d="M2 6V2h4M10 2h4v4M14 10v4h-4M6 14H2v-4"/></svg>',
 close:'<svg viewBox="0 0 16 16"><path d="M3.5 3.5l9 9M12.5 3.5l-9 9"/></svg>',
 shot:'<svg viewBox="0 0 16 16"><rect x="1.5" y="4" width="13" height="9.5" rx="1.5"/><circle cx="8" cy="8.7" r="2.5"/><path d="M5.5 4l1-1.5h3l1 1.5"/></svg>'};

/* ---------- time helpers: daily bars at 00:00 UTC; intraday shifted to Paris wall-clock so axis reads CET ---------- */
const _off={};
function tzOffset(ts){const h=Math.floor(ts/3600);if(_off[h]!=null)return _off[h];
 const p={};new Intl.DateTimeFormat('en-US',{timeZone:TZ,hourCycle:'h23',year:'numeric',month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit',second:'2-digit'}).formatToParts(new Date(ts*1000)).forEach(x=>p[x.type]=x.value);
 const loc=Date.UTC(+p.year,+p.month-1,+p.day,+p.hour%24,+p.minute,+p.second)/1000;return _off[h]=Math.round((loc-ts)/60)*60}
const toT=(t,intra)=>intra?t+tzOffset(t):Date.UTC(+t.slice(0,4),+t.slice(5,7)-1,+t.slice(8,10))/1000;
const fmtDate=(t,intra)=>{const d=new Date(t*1000),o={timeZone:'UTC',day:'2-digit',month:'short',year:'numeric'};if(intra){o.hour='2-digit';o.minute='2-digit';o.hourCycle='h23'}return d.toLocaleString('en-GB',o)};

/* ---------- indicator math ---------- */
function sma(v,p){const o=new Array(v.length).fill(null);let s=0;for(let i=0;i<v.length;i++){s+=v[i];if(i>=p)s-=v[i-p];if(i>=p-1)o[i]=s/p}return o}
function ema(v,p){const o=new Array(v.length).fill(null),k=2/(p+1);let e=null,s=0;for(let i=0;i<v.length;i++){if(i<p){s+=v[i];if(i===p-1){e=s/p;o[i]=e}continue}e=v[i]*k+e*(1-k);o[i]=e}return o}
function bbands(v,p,k){const m=sma(v,p),u=[],l=[];for(let i=0;i<v.length;i++){if(m[i]==null){u.push(null);l.push(null);continue}let s=0;for(let j=i-p+1;j<=i;j++)s+=(v[j]-m[i])**2;const sd=Math.sqrt(s/p);u.push(m[i]+k*sd);l.push(m[i]-k*sd)}return{m,u,l}}
function rsi(v,p){const o=new Array(v.length).fill(null);let g=0,l=0;for(let i=1;i<v.length;i++){const d=v[i]-v[i-1],G=Math.max(d,0),L=Math.max(-d,0);
 if(i<=p){g+=G;l+=L;if(i===p){g/=p;l/=p;o[i]=l===0?100:100-100/(1+g/l)}}else{g=(g*(p-1)+G)/p;l=(l*(p-1)+L)/p;o[i]=l===0?100:100-100/(1+g/l)}}return o}
function macd(v,f,s,g){const a=ema(v,f),b=ema(v,s),m=v.map((_,i)=>a[i]==null||b[i]==null?null:a[i]-b[i]);const i0=m.findIndex(x=>x!=null);
 const sg=new Array(v.length).fill(null);if(i0>=0){const e=ema(m.slice(i0),g);e.forEach((x,i)=>sg[i0+i]=x)}return{m,sg,h:m.map((x,i)=>x==null||sg[i]==null?null:x-sg[i])}}

/* ---------- DOM ---------- */
let W,win,cw,chartEl,ov,lg,msg,side,hint,menu,stEl;
function build(){
 if(W)return;
 W=document.createElement('div');W.id='mcw';
 W.innerHTML=`<div class="mcwin" role="dialog" aria-label="Chart">
 <div class="mc-hd"><img src="assets/logo.png" alt="MedCommodities" onerror="this.style.display='none'"><div class="mc-title"><b class="t1"></b><span class="t2"></span></div>
  <div class="mc-hq"><span class="px"></span><span class="ch"></span></div><div class="mc-sp"></div>
  <div class="mc-wb"><button data-a="side" title="Details panel">${IC.side}</button><button data-a="shot" title="Save chart image (PNG)">${IC.shot}</button><button data-a="max" title="Maximize / restore">${IC.max}</button><button data-a="full" title="Full screen">${IC.full}</button><button data-a="close" class="x" title="Close (Esc)">${IC.close}</button></div></div>
 <div class="mc-tb">
  <div class="mc-grp mc-src"></div><div class="mc-sep sep-src"></div>
  <div class="mc-grp mc-tf">${TFS.map(([k,l,t])=>`<button data-tf="${k}" title="${t}">${l}</button>`).join('')}</div><div class="mc-sep"></div>
  <div class="mc-grp mc-ty"><button data-ty="candle" title="Candles"><svg viewBox="0 0 16 16"><path d="M5 1.5v13M11 1.5v13"/><rect x="3" y="4" width="4" height="7" rx=".5"/><rect x="9" y="6" width="4" height="5" rx=".5" fill="currentColor"/></svg></button><button data-ty="bar" title="OHLC bars"><svg viewBox="0 0 16 16"><path d="M5 2v12M3 5h2M5 11h2M11 3v11M9 6h2M11 12h2"/></svg></button><button data-ty="line" title="Line"><svg viewBox="0 0 16 16"><path d="M1.5 12l4-5 3 3 6-7"/></svg></button><button data-ty="area" title="Area"><svg viewBox="0 0 16 16"><path d="M1.5 12l4-5 3 3 6-7v11.5h-13z" fill="currentColor" fill-opacity=".25"/></svg></button></div><div class="mc-sep"></div>
  <div class="mc-dd"><button data-a="ind" title="Indicators">${IC.ind}&nbsp;Indicators</button><div class="mc-menu"></div></div><div class="mc-sep"></div>
  <div class="mc-grp mc-dr"><button class="ic" data-dr="cursor" title="Cursor / select (click a drawing, Del to remove)">${IC.cursor}</button><button class="ic" data-dr="trend" title="Trend line (click start, click end)">${IC.trend}</button><button class="ic" data-dr="hline" title="Horizontal line (click a price)">${IC.hline}</button><button class="ic" data-dr="fib" title="Fibonacci retracement (click swing start, click swing end)">${IC.fib}</button><button class="ic" data-a="delsel" title="Delete selected drawing (Del)">${IC.del}</button><button class="ic" data-a="clear" title="Clear all drawings">${IC.trash}</button></div><div class="mc-sep"></div>
  <div class="mc-grp"><button data-a="auto" title="Autoscale price axis">${IC.auto}&nbsp;Auto</button><button data-a="log" title="Logarithmic price scale">Log</button><button data-a="reset" title="Reset view">${IC.reset}&nbsp;Reset</button></div>
 </div>
 <div class="mc-body"><div class="mc-cw"><div class="mc-chart"></div><canvas class="mc-ov"></canvas><div class="mc-lg"></div><div class="mc-hint"></div><div class="mc-msg"></div></div><div class="mc-side"></div></div>
 <div class="mc-ft"><div class="mc-grp mc-rg"></div><span class="st"></span></div>
 ${['n','s','e','w','ne','nw','se','sw'].map(d=>`<div class="mc-rs ${d}" data-rs="${d}"></div>`).join('')}<div class="mc-grip"></div>
 </div>`;
 document.body.appendChild(W);
 win=$('.mcwin',W);cw=$('.mc-cw',W);chartEl=$('.mc-chart',W);ov=$('.mc-ov',W);lg=$('.mc-lg',W);msg=$('.mc-msg',W);side=$('.mc-side',W);hint=$('.mc-hint',W);menu=$('.mc-menu',W);stEl=$('.mc-ft .st',W);
 placeWin();wireWin();wireToolbar();
 new ResizeObserver(()=>{const nw=win.offsetWidth<880;if(nw!==win.classList.contains('narrow')){win.classList.toggle('narrow',nw);win.classList.remove('sideopen');if(!nw)win.classList.toggle('noside',!ST.side);syncButtons()}sizeOverlay();drawOverlay()}).observe(cw);
}
function placeWin(){let s=null;try{s=JSON.parse(localStorage.getItem(LSW)||'null')}catch(e){}
 const w=Math.min(s&&s.w||1320,innerWidth-16),h=Math.min(s&&s.h||780,innerHeight-16);
 win.style.width=w+'px';win.style.height=h+'px';win.style.left=Math.max(8,(innerWidth-w)/2)+'px';win.style.top=Math.max(8,(innerHeight-h)/2)+'px';
 win.classList.toggle('noside',!ST.side)}
function saveWin(){try{localStorage.setItem(LSW,JSON.stringify({w:win.offsetWidth,h:win.offsetHeight}))}catch(e){}}
function wireWin(){
 let down=false;W.addEventListener('pointerdown',e=>{down=e.target===W});W.addEventListener('click',e=>{if(e.target===W&&down)close()});
 const hd=$('.mc-hd',W);let drag=null;
 hd.addEventListener('pointerdown',e=>{if(e.target.closest('button')||win.classList.contains('max')||document.fullscreenElement)return;drag={x:e.clientX-win.offsetLeft,y:e.clientY-win.offsetTop};hd.setPointerCapture(e.pointerId)});
 hd.addEventListener('pointermove',e=>{if(!drag)return;win.style.left=Math.min(Math.max(-win.offsetWidth+120,e.clientX-drag.x),innerWidth-120)+'px';win.style.top=Math.min(Math.max(0,e.clientY-drag.y),innerHeight-44)+'px'});
 hd.addEventListener('pointerup',()=>drag=null);
 hd.addEventListener('dblclick',e=>{if(!e.target.closest('button'))toggleMax()});
 W.querySelectorAll('.mc-rs').forEach(h=>{let r=null;
  h.addEventListener('pointerdown',e=>{r={d:h.dataset.rs,x:e.clientX,y:e.clientY,l:win.offsetLeft,t:win.offsetTop,w:win.offsetWidth,h:win.offsetHeight};h.setPointerCapture(e.pointerId);e.preventDefault()});
  h.addEventListener('pointermove',e=>{if(!r)return;const dx=e.clientX-r.x,dy=e.clientY-r.y,mw=420,mh=300;let{l,t,w,h:hh}=r;
   if(r.d.includes('e'))w=Math.max(mw,r.w+dx);if(r.d.includes('s'))hh=Math.max(mh,r.h+dy);
   if(r.d.includes('w')){w=Math.max(mw,r.w-dx);l=r.l+r.w-w}if(r.d.includes('n')){hh=Math.max(mh,r.h-dy);t=Math.max(0,r.t+r.h-hh)}
   Object.assign(win.style,{left:l+'px',top:t+'px',width:w+'px',height:hh+'px'})});
  h.addEventListener('pointerup',()=>{if(r){r=null;saveWin()}})});
 document.addEventListener('keydown',e=>{if(!W.classList.contains('on'))return;if(e.target.matches&&e.target.matches('input'))return;
  if(e.key==='Escape'){if(menu.classList.contains('on')){menu.classList.remove('on');return}if(pending){pending=null;setTool('cursor');drawOverlay();return}if(tool!=='cursor'){setTool('cursor');return}if(document.fullscreenElement)return;close()}
  else if((e.key==='Delete'||e.key==='Backspace')&&sel!=null){removeDrawing(sel);e.preventDefault()}
  else if(e.altKey&&e.key.toLowerCase()==='r'){resetView()}});
 document.addEventListener('fullscreenchange',()=>setTimeout(drawOverlay,50));
 document.addEventListener('pointerdown',e=>{if(menu.classList.contains('on')&&!e.target.closest('.mc-dd'))menu.classList.remove('on')});
}
function toggleMax(){win.classList.toggle('max')}

/* ---------- state for the open chart ---------- */
let chart=null,main=null,volS=null,ind=[],D=null,cur={sym:null,name:null,src:'auto'},lastLoad=0,timer=null,pane0Lines=[];
let tool='cursor',pending=null,hover=null,sel=null,drawings=[],hlines=[];

function wireToolbar(){
 W.addEventListener('click',e=>{const b=e.target.closest('button');if(!b||!W.contains(b))return;
  if(b.dataset.tf){if(b.disabled)return;ST.tf=b.dataset.tf;save();load(true);return}
  if(b.dataset.ty){ST.type=b.dataset.ty;save();buildMain();syncButtons();return}
  if(b.dataset.dr){setTool(b.dataset.dr);return}
  if(b.dataset.src){cur.src=b.dataset.src;load(true);return}
  if(b.dataset.rg){setRange(b.dataset.rg);return}
  const a=b.dataset.a;
  if(a==='close')close();else if(a==='max')toggleMax();
  else if(a==='full'){document.fullscreenElement?document.exitFullscreen():win.requestFullscreen&&win.requestFullscreen().catch(()=>toggleMax())}
  else if(a==='side'){if(win.classList.contains('narrow')){win.classList.remove('noside');win.classList.toggle('sideopen')}else{ST.side=!ST.side;save();win.classList.toggle('noside',!ST.side)}syncButtons()}
  else if(a==='ind'){renderMenu();menu.classList.toggle('on')}
  else if(a==='auto'){chart&&chart.priceScale('right').applyOptions({autoScale:true});syncButtons()}
  else if(a==='log'){ST.log=!ST.log;save();chart&&chart.priceScale('right').applyOptions({mode:ST.log?LW.PriceScaleMode.Logarithmic:LW.PriceScaleMode.Normal});syncButtons();setTimeout(drawOverlay,30)}
  else if(a==='reset')resetView();
  else if(a==='clear'){drawings=[];sel=null;pending=null;saveDraw();renderHlines();drawOverlay()}
  else if(a==='delsel'){if(sel!=null)removeDrawing(sel)}
  else if(a==='shot')snapshot()});
}
function syncButtons(){if(!W)return;
 W.querySelectorAll('[data-tf]').forEach(b=>b.classList.toggle('on',b.dataset.tf===ST.tf));
 W.querySelectorAll('[data-ty]').forEach(b=>b.classList.toggle('on',b.dataset.ty===ST.type));
 W.querySelectorAll('[data-dr]').forEach(b=>b.classList.toggle('on',b.dataset.dr===tool));
 W.querySelectorAll('[data-src]').forEach(b=>b.classList.toggle('on',b.dataset.src===(D&&D.continuous?'cont':'contract')));
 $('[data-a=log]',W).classList.toggle('on',!!ST.log);$('[data-a=side]',W).classList.toggle('on',win.classList.contains('narrow')?win.classList.contains('sideopen'):!!ST.side);
 const as=chart?chart.priceScale('right').options().autoScale:true;$('[data-a=auto]',W).classList.toggle('on',!!as);
 $('[data-a=delsel]',W).disabled=sel==null;$('[data-a=clear]',W).disabled=!drawings.length;
 const lt=(window.MC_CHART_TFS||TFS.map(x=>x[0]));W.querySelectorAll('[data-tf]').forEach(b=>b.disabled=!lt.includes(b.dataset.tf));
 win.classList.toggle('drawing',tool!=='cursor');
}

/* ---------- indicator menu ---------- */
function renderMenu(){
 const row=(id,label,on,inputs,color)=>`<div class="mc-mi"><label><input type="checkbox" data-k="${id}" ${on?'checked':''}>${color?`<span class="sw" style="background:${color}"></span>`:''}${label}</label>${inputs||''}</div>`;
 const num=(k,v,min,max,step)=>`<input type="number" data-n="${k}" value="${v}" min="${min}" max="${max}" step="${step||1}">`;
 menu.innerHTML=`<h4>Moving averages</h4>${ST.sma.map((m,i)=>row('sma.'+i,'SMA',m.on,num('sma.'+i,m.p,2,500),MA_COL[i])).join('')}
 ${ST.ema.map((m,i)=>row('ema.'+i,'EMA',m.on,num('ema.'+i,m.p,2,500),EC[i])).join('')}
 <h4>Bands &amp; oscillators</h4>${row('bb','Bollinger Bands',ST.bb.on,num('bb.p',ST.bb.p,2,200)+num('bb.k',ST.bb.k,0.5,5,0.5),'#8ab4ff')}
 ${row('rsi','RSI (sub-pane)',ST.rsi.on,num('rsi.p',ST.rsi.p,2,100),'#c58cff')}
 ${row('macd','MACD (sub-pane)',ST.macd.on,num('macd.f',ST.macd.f,2,100)+num('macd.s',ST.macd.s,2,200)+num('macd.g',ST.macd.g,2,100),'#29ABFF')}
 ${row('vol','Volume',ST.vol,'','#5b6b7f')}
 <div class="mc-mi" style="justify-content:space-between;margin-top:6px"><span style="color:#6b7d92;font-size:11px">Saved on this browser</span><button data-a="indreset">Defaults</button></div>`;
 menu.onchange=e=>{const t=e.target;
  if(t.dataset.k){const[k,i]=t.dataset.k.split('.');if(i!=null)ST[k][+i].on=t.checked;else if(k==='vol')ST.vol=t.checked;else ST[k].on=t.checked}
  if(t.dataset.n){const[k,i]=t.dataset.n.split('.'),v=+t.value;if(!(v>0))return;if(k==='sma'||k==='ema')ST[k][+i].p=Math.round(v);else ST[k][i]=k==='bb'&&i==='k'?v:Math.round(v)}
  save();buildIndicators()};
 menu.onclick=e=>{const b=e.target.closest('[data-a=indreset]');if(!b)return;e.stopPropagation();const k=['sma','ema','bb','rsi','macd','vol'];k.forEach(x=>ST[x]=clone(DEF[x]));save();renderMenu();buildIndicators()};
}

/* ---------- chart ---------- */
function makeChart(){
 if(chart){chart.remove();chart=null}
 chart=LW.createChart(chartEl,{autoSize:true,
  layout:{background:{type:'solid',color:COL.bg},textColor:COL.tx,fontSize:11.5,fontFamily:'Inter,"Segoe UI",-apple-system,Roboto,Arial,sans-serif',attributionLogo:false,
   panes:{separatorColor:'#243142',separatorHoverColor:'rgba(41,171,255,0.25)',enableResize:true}},
  grid:{vertLines:{color:COL.grid},horzLines:{color:COL.grid}},
  crosshair:{mode:LW.CrosshairMode.Normal,vertLine:{color:'rgba(159,176,195,0.55)',width:1,style:LW.LineStyle.Dashed,labelBackgroundColor:'#0A6CFF'},horzLine:{color:'rgba(159,176,195,0.55)',width:1,style:LW.LineStyle.Dashed,labelBackgroundColor:'#0A6CFF'}},
  rightPriceScale:{borderColor:'#243142',scaleMargins:{top:0.08,bottom:0.22},mode:ST.log?LW.PriceScaleMode.Logarithmic:LW.PriceScaleMode.Normal},
  timeScale:{borderColor:'#243142',rightOffset:8,barSpacing:7,minBarSpacing:0.5,timeVisible:D.intraday,secondsVisible:false,fixLeftEdge:false},
  localization:{priceFormatter:p=>fmt(p),timeFormatter:t=>fmtDate(t,D.intraday)},
  handleScale:{axisPressedMouseMove:{time:true,price:true},mouseWheel:true,pinch:true,axisDoubleClickReset:{time:true,price:true}},
  handleScroll:{mouseWheel:false,pressedMouseMove:true,horzTouchDrag:true,vertTouchDrag:true}});
 try{LW.createTextWatermark(chart.panes()[0],{horzAlign:'center',vertAlign:'center',lines:[{text:wmText(),color:'rgba(41,171,255,0.055)',fontSize:Math.max(34,Math.min(72,Math.round(560/Math.max(1,wmText().length)))),fontStyle:'bold'},{text:'MedCommodities',color:'rgba(255,255,255,0.04)',fontSize:22}]})}catch(e){}
 chart.subscribeCrosshairMove(onCross);
 chart.timeScale().subscribeVisibleLogicalRangeChange(()=>drawOverlay());
 chart.timeScale().subscribeSizeChange(()=>{sizeOverlay();drawOverlay()});
 cw.onmousemove=onMove;wireClicks();cw.onmouseleave=()=>{hover=null;if(pending)drawOverlay()};
 // keep the overlay glued during price-axis drags/wheel (no event for price-range changes)
 let raf=0;const tick=()=>{if(!chart)return;const k=keyState();if(k!==tick.k){tick.k=k;drawOverlay();syncButtons()}raf=requestAnimationFrame(tick)};tick.k='';raf=requestAnimationFrame(tick);
}
function wmText(){const d=D.details;if(d.contract&&!/continuous/.test(d.contract))return d.contract;return(d.name||D.symbol).split(' (')[0].toUpperCase()}
function keyState(){if(!main)return'';const a=main.priceToCoordinate(D.c[D.c.length-1]),b=main.coordinateToPrice(0);return a+'|'+b+'|'+chart.panes().map(p=>p.getHeight()).join(',')}
function fmt(p){if(p==null||!isFinite(p))return'—';const d=D?D.details.decimals:2;return(+p).toLocaleString('en-US',{minimumFractionDigits:d,maximumFractionDigits:d})}
function fmtV(v){if(v==null)return'—';return v>=1e9?(v/1e9).toFixed(2)+'B':v>=1e6?(v/1e6).toFixed(2)+'M':v>=1e4?(v/1e3).toFixed(1)+'K':Math.round(v).toLocaleString('en-US')}

function buildMain(){
 if(!chart||!D)return;if(main){chart.removeSeries(main);main=null}
 const dec=D.details.decimals,pf={type:'price',precision:dec,minMove:1/Math.pow(10,dec)};
 const ohlc=D.T.map((t,i)=>({time:t,open:D.o[i],high:D.h[i],low:D.l[i],close:D.c[i]}));
 const line=D.T.map((t,i)=>({time:t,value:D.c[i]}));
 if(ST.type==='line')main=chart.addSeries(LW.LineSeries,{color:COL.acc,lineWidth:2,priceFormat:pf,lastValueVisible:true,priceLineVisible:true,priceLineColor:COL.acc},0);
 else if(ST.type==='area')main=chart.addSeries(LW.AreaSeries,{lineColor:COL.acc,topColor:'rgba(41,171,255,0.38)',bottomColor:'rgba(10,108,255,0.02)',lineWidth:2,priceFormat:pf},0);
 else if(ST.type==='bar')main=chart.addSeries(LW.BarSeries,{upColor:COL.up,downColor:COL.dn,thinBars:false,priceFormat:pf},0);
 else main=chart.addSeries(LW.CandlestickSeries,{upColor:COL.up,downColor:COL.dn,borderUpColor:COL.up,borderDownColor:COL.dn,wickUpColor:COL.up,wickDownColor:COL.dn,priceFormat:pf},0);
 main.setData(ST.type==='line'||ST.type==='area'?line:ohlc);
 renderHlines();
}
function paneSizes(){if(!chart)return;const P=chart.panes();P.forEach((p,i)=>{try{p.setStretchFactor(i?1:(P.length>2?4:4.5))}catch(e){}})}
function buildIndicators(){
 if(!chart||!D)return;
 ind.forEach(s=>{try{chart.removeSeries(s.s)}catch(e){}});ind=[];
 if(volS){chart.removeSeries(volS);volS=null}
 while(chart.panes().length>1)chart.removePane(chart.panes().length-1);
 const T=D.T,c=D.c,pts=a=>a.map((v,i)=>v==null?{time:T[i]}:{time:T[i],value:v}),dec=D.details.decimals,pf={type:'price',precision:dec,minMove:1/Math.pow(10,dec)};
 const add=(type,opt,data,pane,name,col)=>{const s=chart.addSeries(type,Object.assign({lastValueVisible:false,priceLineVisible:false,crosshairMarkerVisible:false},opt),pane);s.setData(data);ind.push({s,name,col,data});return s};
 if(ST.vol&&D.v){volS=chart.addSeries(LW.HistogramSeries,{priceScaleId:'vol',priceFormat:{type:'volume'},lastValueVisible:false,priceLineVisible:false},0);
  chart.priceScale('vol').applyOptions({scaleMargins:{top:0.82,bottom:0},visible:false});
  volS.setData(T.map((t,i)=>({time:t,value:D.v[i],color:c[i]>=D.o[i]?'rgba(38,194,129,0.38)':'rgba(240,80,95,0.38)'})))}
 chart.priceScale('right').applyOptions({scaleMargins:{top:0.08,bottom:ST.vol&&D.v?0.2:0.06}});
 ST.sma.forEach((m,i)=>{if(m.on&&m.p<c.length)add(LW.LineSeries,{color:MA_COL[i],lineWidth:1.6,priceFormat:pf},pts(sma(c,m.p)),0,'SMA '+m.p,MA_COL[i])});
 ST.ema.forEach((m,i)=>{if(m.on&&m.p<c.length)add(LW.LineSeries,{color:EC[i],lineWidth:1.6,lineStyle:LW.LineStyle.Solid,priceFormat:pf},pts(ema(c,m.p)),0,'EMA '+m.p,EC[i])});
 if(ST.bb.on&&ST.bb.p<c.length){const b=bbands(c,ST.bb.p,ST.bb.k),bc='#8ab4ff';
  add(LW.LineSeries,{color:'rgba(138,180,255,0.9)',lineWidth:1,priceFormat:pf},pts(b.u),0,`BB ${ST.bb.p},${ST.bb.k} U`,bc);
  add(LW.LineSeries,{color:'rgba(255,176,0,0.75)',lineWidth:1,lineStyle:LW.LineStyle.Dashed,priceFormat:pf},pts(b.m),0,'BB basis','#ffb000');
  add(LW.LineSeries,{color:'rgba(138,180,255,0.9)',lineWidth:1,priceFormat:pf},pts(b.l),0,'BB L',bc);D.bb=b}else D.bb=null;
 let pane=1;
 if(ST.rsi.on){const r=add(LW.LineSeries,{color:'#c58cff',lineWidth:1.5,priceFormat:{type:'price',precision:1,minMove:0.1},lastValueVisible:true},pts(rsi(c,ST.rsi.p)),pane,'RSI '+ST.rsi.p,'#c58cff');
  [70,50,30].forEach(v=>r.createPriceLine({price:v,color:v===50?'rgba(159,176,195,0.3)':'rgba(197,140,255,0.45)',lineWidth:1,lineStyle:LW.LineStyle.Dashed,axisLabelVisible:v!==50,title:''}));pane++}
 if(ST.macd.on){const m=macd(c,ST.macd.f,ST.macd.s,ST.macd.g),p2={type:'price',precision:dec+1,minMove:1/Math.pow(10,dec+1)};
  add(LW.HistogramSeries,{priceFormat:p2},m.h.map((v,i)=>v==null?{time:T[i]}:{time:T[i],value:v,color:v>=0?(i&&m.h[i-1]!=null&&v<m.h[i-1]?'rgba(38,194,129,0.45)':'rgba(38,194,129,0.85)'):(i&&m.h[i-1]!=null&&v>m.h[i-1]?'rgba(240,80,95,0.45)':'rgba(240,80,95,0.85)')}),pane,'Hist','#5b6b7f');
  add(LW.LineSeries,{color:'#29ABFF',lineWidth:1.5,priceFormat:p2},pts(m.m),pane,`MACD ${ST.macd.f},${ST.macd.s},${ST.macd.g}`,'#29ABFF');
  add(LW.LineSeries,{color:'#ff8a4c',lineWidth:1.2,priceFormat:p2},pts(m.sg),pane,'Signal','#ff8a4c');pane++}
 paneSizes();
 setTimeout(()=>{sizeOverlay();drawOverlay()},0);legend(null);
}

/* ---------- legend ---------- */
function onCross(p){let i=null;if(p&&p.time!=null){i=idxOf(p.time)}legend(i)}
function idxOf(t){let lo=0,hi=D.T.length-1;while(lo<=hi){const m=(lo+hi)>>1;if(D.T[m]===t)return m;if(D.T[m]<t)lo=m+1;else hi=m-1}return null}
function legend(i){if(!D)return;const n=D.T.length;if(i==null)i=n-1;const o=D.o[i],h=D.h[i],l=D.l[i],c=D.c[i],pc=i>0?D.c[i-1]:null,ch=pc!=null?c-pc:null,pct=pc?ch/pc*100:null,cls=ch>0?'up2':ch<0?'dn2':'';
 const k=(a,b,cl)=>`<span><span class="k">${a}</span><span class="${cl||cls}">${b}</span></span>`;
 const det=D.details;
 let s=`<div class="r1"><span class="sym">${esc(det.contract&&!/continuous/.test(det.contract)?det.contract:(det.name||D.symbol))} · ${esc(TFNAME[ST.tf])}${D.continuous&&det.contract&&/continuous/.test(det.contract)?' · continuous':''}</span>${k('O',fmt(o))}${k('H',fmt(h))}${k('L',fmt(l))}${k('C',fmt(c))}${ch!=null?`<span class="${cls}">${ch>0?'+':''}${fmt(ch)} (${pct>0?'+':''}${pct.toFixed(2)}%)</span>`:''}${D.v?k('Vol',fmtV(D.v[i]),''):''}</div>`;
 const items=ind.filter(x=>x.name!=='Hist').map(x=>{const d=x.data[i];return d&&d.value!=null?`<span style="color:${x.col}">${esc(x.name)} ${x.name.startsWith('RSI')?d.value.toFixed(1):x.name.startsWith('MACD')||x.name==='Signal'?d.value.toFixed(det.decimals+1):fmt(d.value)}</span>`:''}).filter(Boolean);
 if(items.length)s+=`<div class="ind">${items.join('')}</div>`;
 lg.innerHTML=s}

/* ---------- details card (top-right side panel: never covers the latest candles, which sit on the right edge) ---------- */
function card(){const d=D.details,q=d.quote||{},cls=q.chg>0?'up2':q.chg<0?'dn2':'',sg=v=>v>0?'+':'';
 const kv=(k,v)=>v==null||v===''?'':`<span class="k">${k}</span><span class="v">${v}</span>`;
 const rng=(t,lo,hi,a,b)=>{if(lo==null||hi==null||hi<=lo)return'';const p=Math.max(0,Math.min(100,(q.last-lo)/(hi-lo)*100));return `<div class="mc-rng"><div class="t"><span>${t}</span><span>${p.toFixed(0)}% of range</span></div><div class="bar"><div class="dot" style="left:${p}%"></div></div><div class="v"><span class="dn2" title="${esc(a||'')}">${fmt(lo)}</span><span class="up2" title="${esc(b||'')}">${fmt(hi)}</span></div></div>`};
 const asof=q.time?new Date(q.time*1000).toLocaleString('en-GB',{timeZone:TZ,day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',hourCycle:'h23'})+' '+TZL:q.date||'';
 const isC=d.contract&&!/continuous/.test(d.contract);
 const exp=d.expiry?`${new Date(d.expiry+'T00:00:00Z').toLocaleDateString('en-GB',{timeZone:'UTC',day:'2-digit',month:'short',year:'numeric'})}${d.expiry_est?' (est.)':''}${d.days_to_expiry!=null?` · ${d.days_to_expiry}d`:''}`:null;
 const since=q.life_from?new Date(q.life_from+'T00:00:00Z').getUTCFullYear():'';
 side.innerHTML=`<div class="mc-card"><div class="c1"><div><div class="code">${esc(isC?d.contract:(d.name||D.symbol))}</div><div class="nm">${esc(isC?d.name:(d.contract||D.symbol))}</div></div><span class="mc-badge">${esc(d.exchange||'')}</span></div>
 <div class="last">${fmt(q.last)}<span class="unit">${esc(d.unit||'')}</span></div>
 <div class="chg ${cls}">${q.chg!=null?`${sg(q.chg)}${fmt(q.chg)} &nbsp;(${sg(q.pct)}${q.pct.toFixed(2)}%)`:''}</div><div class="asof">Last ${esc(asof)}</div>
 <div class="mc-kv">${kv('Units',esc(d.unit))}${kv('Currency',esc(d.currency))}${isC?kv('Contract month',esc(d.month)):''}${exp?kv('Last trade',exp):''}<div class="hr"></div>
 ${kv('Open',fmt(q.open))}${kv('High',`<span class="up2">${fmt(q.high)}</span>`)}${kv('Low',`<span class="dn2">${fmt(q.low)}</span>`)}${kv('Prev. settle',fmt(q.prev))}
 ${q.volume?kv('Volume',fmtV(q.volume)):''}${q.oi?kv('Open interest',fmtV(q.oi)):''}</div>
 ${rng('Day range',q.low,q.high)}${rng('52-week range',q.wk52_low,q.wk52_high)}${rng(isC?'Life of contract (since '+since+')':'Series range (since '+since+')',q.life_low,q.life_high,q.life_low_date,q.life_high_date)}
 <div class="mc-src">${D.fallback?esc(D.note||'')+'<br>':''}${esc(TFNAME[ST.tf])} · ${D.n.toLocaleString('en-US')} bars from ${esc(fmtDate(D.T[0],D.intraday))}${D.intraday?' ('+TZL+')':''}${D.v?'':' · no volume reported'}</div></div>`;
 const hq=$('.mc-hq',W);hq.querySelector('.px').textContent=fmt(q.last)+' '+(d.unit||'');const ch=hq.querySelector('.ch');ch.className='ch '+cls;ch.textContent=q.chg!=null?`${sg(q.chg)}${fmt(q.chg)} (${sg(q.pct)}${q.pct.toFixed(2)}%)`:'';
}

/* ---------- ranges ---------- */
const RANGES=[['1D',1],['5D',5],['1M',30],['3M',91],['6M',182],['YTD','ytd'],['1Y',365],['5Y',1826],['All','all']];
function renderRanges(){const intra=D&&D.intraday,span=D?(D.T[D.T.length-1]-D.T[0])/86400:0;
 $('.mc-rg',W).innerHTML=RANGES.filter(([l,d])=>d==='all'||d==='ytd'||(intra?d<=span+1:d>=30&&d<=span*1.2)||(intra&&d===1)).map(([l])=>`<button data-rg="${l}">${l}</button>`).join('')}
function setRange(l){if(!D||!chart)return;const r=RANGES.find(x=>x[0]===l);if(!r)return;const n=D.T.length,last=D.T[n-1];
 if(r[1]==='all'){chart.timeScale().setVisibleLogicalRange({from:-2,to:n+6})}
 else{let from;if(r[1]==='ytd'){const y=new Date(last*1000).getUTCFullYear();from=Date.UTC(y,0,1)/1000}else from=last-r[1]*86400;
  let i=D.T.findIndex(t=>t>=from);if(i<0)i=0;chart.timeScale().setVisibleLogicalRange({from:i-0.5,to:n-1+Math.max(3,(n-i)*0.06)})}
 chart.priceScale('right').applyOptions({autoScale:true});W.querySelectorAll('[data-rg]').forEach(b=>b.classList.toggle('on',b.dataset.rg===l))}
const DEFR={'15m':'5D','60m':'1M','1d':'1Y','1wk':'5Y','1mo':'All'};
function resetView(){if(!chart)return;chart.priceScale('right').applyOptions({autoScale:true});paneSizes();setRange(DEFR[ST.tf]||'1Y');syncButtons()}

/* ---------- drawings (trend line, horizontal line, Fibonacci retracement) on an overlay canvas, anchored in time/price ---------- */
function drawKey(){return LSD+(D?D.symbol:'')+'@'+ST.tf}   // drawings are per symbol AND timeframe
let _dk=null;function loadDraw(){_dk=drawKey();try{drawings=JSON.parse(localStorage.getItem(_dk)||'[]')}catch(e){drawings=[]}sel=null;pending=null}
function saveDraw(){try{localStorage.setItem(drawKey(),JSON.stringify(drawings))}catch(e){}syncButtons()}
function removeDrawing(i){drawings.splice(i,1);sel=null;saveDraw();renderHlines();drawOverlay()}
function setTool(t){tool=t;pending=null;hint.classList.toggle('on',t!=='cursor');hint.textContent={trend:'Trend line: click the start point, then the end point',hline:'Horizontal line: click a price level',fib:'Fibonacci: click the swing start, then the swing end',cursor:''}[t];
 chart&&chart.applyOptions({handleScroll:{pressedMouseMove:t==='cursor'}});syncButtons();drawOverlay()}
// time <-> logical index (fractional; extrapolates past both ends so lines can extend into the future)
function t2l(t){const T=D.T,n=T.length;if(n<2)return 0;if(t<=T[0])return(t-T[0])/(T[1]-T[0]);if(t>=T[n-1]){const st=(T[n-1]-T[Math.max(0,n-21)])/Math.min(20,n-1);return n-1+(t-T[n-1])/st}
 let lo=0,hi=n-1;while(hi-lo>1){const m=(lo+hi)>>1;if(T[m]<=t)lo=m;else hi=m}return lo+(t-T[lo])/(T[hi]-T[lo])}
function l2t(l){const T=D.T,n=T.length;if(l<=0)return T[0]+l*(T[1]-T[0]);if(l>=n-1){const st=(T[n-1]-T[Math.max(0,n-21)])/Math.min(20,n-1);return T[n-1]+(l-(n-1))*st}const i=Math.floor(l);return T[i]+(l-i)*(T[i+1]-T[i])}
function xOf(t){const x=chart.timeScale().logicalToCoordinate(t2l(t));return x}
function yOf(v){return main.priceToCoordinate(v)}
function ptAt(x,y){const l=chart.timeScale().coordinateToLogical(x);const v=main.coordinateToPrice(y);if(l==null||v==null)return null;
 // magnet: snap to the nearest OHLC value of the bar under the cursor when within 8px
 const i=Math.round(l);let val=v;if(i>=0&&i<D.T.length){let best=8;for(const c of [D.o[i],D.h[i],D.l[i],D.c[i]]){const dy=Math.abs(yOf(c)-y);if(dy<best){best=dy;val=c}}}
 return{t:l2t(l),v:val}}
function pane0(){const ts=chart.timeScale();return{w:ts.width(),h:chart.panes()[0].getHeight()}}
function sizeOverlay(){if(!chart)return;const{w,h}=pane0(),dpr=devicePixelRatio||1;ov.width=Math.round(w*dpr);ov.height=Math.round(h*dpr);ov.style.width=w+'px';ov.style.height=h+'px'}
const FIBL=[[0,'#9fb0c3'],[0.236,'#f0505f'],[0.382,'#ff8a4c'],[0.5,'#26c281'],[0.618,'#29ABFF'],[0.786,'#0A6CFF'],[1,'#9fb0c3'],[1.618,'#c58cff']];
function drawOverlay(){if(!chart||!main||!D)return;const ctx=ov.getContext('2d'),dpr=devicePixelRatio||1,{w,h}=pane0();
 if(Math.round(w*dpr)!==ov.width||Math.round(h*dpr)!==ov.height)sizeOverlay();
 ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,w,h);ctx.save();ctx.beginPath();ctx.rect(0,0,w,h);ctx.clip();
 // Bollinger fill
 if(D.bb){const r=chart.timeScale().getVisibleLogicalRange();if(r){const a=Math.max(0,Math.floor(r.from)-1),b=Math.min(D.T.length-1,Math.ceil(r.to)+1),up=[],dn=[];
  for(let i=a;i<=b;i++){if(D.bb.u[i]==null)continue;const x=chart.timeScale().logicalToCoordinate(i);up.push([x,yOf(D.bb.u[i])]);dn.push([x,yOf(D.bb.l[i])])}
  if(up.length>1){ctx.beginPath();up.forEach(([x,y],j)=>j?ctx.lineTo(x,y):ctx.moveTo(x,y));for(let j=dn.length-1;j>=0;j--)ctx.lineTo(dn[j][0],dn[j][1]);ctx.closePath();ctx.fillStyle='rgba(138,180,255,0.07)';ctx.fill()}}}
 const all=drawings.map((d,i)=>({d,i}));if(pending&&hover)all.push({d:{type:pending.type,p:[pending.p,hover]},i:-1,pre:true});
 for(const{d,i,pre}of all){const S=i===sel;
  if(d.type==='trend'){const[a,b]=d.p,x1=xOf(a.t),y1=yOf(a.v),x2=xOf(b.t),y2=yOf(b.v);if([x1,y1,x2,y2].some(v=>v==null))continue;
   ctx.strokeStyle=S?'#ffffff':'#29ABFF';ctx.lineWidth=S?2.2:1.8;ctx.setLineDash(pre?[5,4]:[]);ctx.beginPath();ctx.moveTo(x1,y1);ctx.lineTo(x2,y2);ctx.stroke();ctx.setLineDash([]);
   for(const[x,y]of[[x1,y1],[x2,y2]]){ctx.beginPath();ctx.arc(x,y,S?4.5:3,0,7);ctx.fillStyle=COL.bg;ctx.fill();ctx.strokeStyle='#29ABFF';ctx.lineWidth=1.5;ctx.stroke()}
   if(S||pre){const ch=b.v-a.v,pc=ch/a.v*100;label(ctx,x2+8,y2,`${ch>0?'+':''}${fmt(ch)} (${pc.toFixed(2)}%)`,'#0A6CFF')}}
  else if(d.type==='fib'){const[a,b]=d.p,x1=xOf(a.t),x2=xOf(b.t);if(x1==null||x2==null)continue;const xl=Math.min(x1,x2),xr=w;
   let prev=null;FIBL.forEach(([r,c],k)=>{const v=b.v+(a.v-b.v)*r,y=yOf(v);if(y==null)return;
    if(prev!=null&&r<=1){ctx.fillStyle=hexA(c,S?0.12:0.08);ctx.fillRect(xl,Math.min(prev,y),xr-xl,Math.abs(y-prev))}
    ctx.strokeStyle=hexA(c,r===1.618?0.6:0.95);ctx.lineWidth=S?1.6:1.1;ctx.setLineDash(r===1.618?[4,4]:[]);ctx.beginPath();ctx.moveTo(xl,y);ctx.lineTo(xr,y);ctx.stroke();ctx.setLineDash([]);
    ctx.font='11px Inter,Segoe UI,Arial,sans-serif';ctx.fillStyle=c;ctx.textBaseline='bottom';ctx.fillText(`${r} (${fmt(v)})`,xl+4,y-2);if(r<=1)prev=y});
   ctx.strokeStyle='rgba(159,176,195,0.55)';ctx.setLineDash([3,3]);ctx.lineWidth=1;ctx.beginPath();ctx.moveTo(x1,yOf(a.v));ctx.lineTo(x2,yOf(b.v));ctx.stroke();ctx.setLineDash([])}
  else if(d.type==='hline'){const y=yOf(d.p[0].v);if(y==null)continue;if(S){ctx.strokeStyle='rgba(255,255,255,0.9)';ctx.lineWidth=3;ctx.globalAlpha=0.35;ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(w,y);ctx.stroke();ctx.globalAlpha=1}}}
 if(pending&&pending.type==='hline'&&hover){}
 ctx.restore()}
function label(ctx,x,y,t,bg){ctx.font='600 11px Inter,Segoe UI,Arial,sans-serif';const m=ctx.measureText(t).width+10;ctx.fillStyle=bg;ctx.beginPath();ctx.roundRect?ctx.roundRect(x,y-10,m,20,4):ctx.rect(x,y-10,m,20);ctx.fill();ctx.fillStyle='#fff';ctx.textBaseline='middle';ctx.fillText(t,x+5,y)}
function hexA(h,a){const n=parseInt(h.slice(1),16);return`rgba(${n>>16&255},${n>>8&255},${n&255},${a})`}
function renderHlines(){if(!main)return;hlines.forEach(l=>{try{main.removePriceLine(l)}catch(e){}});hlines=[];
 drawings.forEach((d,i)=>{if(d.type==='hline')hlines.push(main.createPriceLine({price:d.p[0].v,color:i===sel?'#ffffff':'#ffb000',lineWidth:i===sel?2:1,lineStyle:LW.LineStyle.Solid,axisLabelVisible:true,title:''}))})}
function onMove(e){if(!chart||tool==='cursor'||!pending)return;const b=cw.getBoundingClientRect();hover=ptAt(e.clientX-b.left,e.clientY-b.top);drawOverlay()}
// own click detection (pointerdown/up with <5px travel): reliable for fast consecutive clicks, unlike a click callback
let _cl=null;function wireClicks(){if(cw._wired)return;cw._wired=1;
 cw.addEventListener('pointerdown',e=>{if(e.button===0&&!e.target.closest('.mc-side'))_cl={x:e.clientX,y:e.clientY}},true);
 cw.addEventListener('pointerup',e=>{if(!_cl||e.button!==0)return;const m=Math.hypot(e.clientX-_cl.x,e.clientY-_cl.y);_cl=null;if(m>5||!chart)return;const b=chartEl.getBoundingClientRect();onClick({point:{x:e.clientX-b.left,y:e.clientY-b.top}})},true)}
function onClick(p){if(!p||!p.point||!D)return;const{x,y}=p.point;if(y>pane0().h||x>pane0().w||x<0||y<0)return;
 if(tool==='cursor'){sel=hit(x,y);renderHlines();drawOverlay();syncButtons();return}
 const pt=ptAt(x,y);if(!pt)return;
 if(tool==='hline'){drawings.push({type:'hline',p:[pt]});sel=drawings.length-1;saveDraw();renderHlines();setTool('cursor');return}
 if(!pending){pending={type:tool,p:pt};hover=pt;return}
 drawings.push({type:pending.type,p:[pending.p,pt]});sel=drawings.length-1;pending=null;saveDraw();setTool('cursor');renderHlines();drawOverlay()}
function hit(x,y){let best=null,bd=7;drawings.forEach((d,i)=>{let dist=1e9;
  if(d.type==='hline'){dist=Math.abs(yOf(d.p[0].v)-y)}
  else if(d.type==='trend'){const x1=xOf(d.p[0].t),y1=yOf(d.p[0].v),x2=xOf(d.p[1].t),y2=yOf(d.p[1].v);dist=segDist(x,y,x1,y1,x2,y2)}
  else if(d.type==='fib'){const[a,b]=d.p,xl=Math.min(xOf(a.t),xOf(b.t));if(x>=xl-6)FIBL.forEach(([r])=>{const yy=yOf(b.v+(a.v-b.v)*r);dist=Math.min(dist,Math.abs(yy-y))})}
  if(dist<bd){bd=dist;best=i}});return best}
function segDist(px,py,x1,y1,x2,y2){const dx=x2-x1,dy=y2-y1,L=dx*dx+dy*dy;let t=L?((px-x1)*dx+(py-y1)*dy)/L:0;t=Math.max(0,Math.min(1,t));return Math.hypot(px-x1-t*dx,py-y1-t*dy)}

function snapshot(){if(!chart)return;const c=chart.takeScreenshot(),cv=document.createElement('canvas');cv.width=c.width;cv.height=c.height;const x=cv.getContext('2d');x.drawImage(c,0,0);
 const dpr=c.width/chartEl.clientWidth;x.drawImage(ov,0,0,ov.width,ov.height,0,0,ov.width*dpr/(devicePixelRatio||1),ov.height*dpr/(devicePixelRatio||1));
 const a=document.createElement('a');a.download=`MedCommodities_${(D.details.contract||D.symbol).replace(/\W+/g,'_')}_${ST.tf}.png`;a.href=cv.toDataURL('image/png');a.click()}

/* ---------- data ---------- */
async function fetchData(sym,tf,src){
 if(window.MC_CHART_LOADER)return window.MC_CHART_LOADER(sym,tf,src);
 const r=await fetch(`/api/chart?sym=${encodeURIComponent(sym)}&tf=${tf}&src=${src}`);const j=await r.json();if(!r.ok||j.error)throw new Error(j.error||('HTTP '+r.status));return j}
function prep(j){const b=j.bars,intra=!!j.intraday;const d={...j,T:b.t.map(t=>toT(t,intra)),o:b.o,h:b.h,l:b.l,c:b.c,v:b.v};
 // de-duplicate / sort guard (LWC needs strictly increasing times)
 const keep=[];for(let i=0;i<d.T.length;i++){if(keep.length&&d.T[i]<=d.T[keep[keep.length-1]]){keep[keep.length-1]=i;continue}keep.push(i)}
 if(keep.length!==d.T.length){for(const k of['T','o','h','l','c'])d[k]=keep.map(i=>d[k][i]);if(d.v)d.v=keep.map(i=>d.v[i]);d.n=d.T.length}return d}
function showMsg(t,err){msg.className='mc-msg'+(err?' err':'');msg.innerHTML=t?(err?'':'<div class="mc-spin"></div>')+esc(t):''}
async function load(fresh){
 const sym=cur.sym,tf=ST.tf;syncButtons();showMsg('Loading '+(TFNAME[tf]||tf)+' …');
 let j;try{j=await fetchData(sym,tf,cur.src)}catch(e){if(cur.sym===sym){showMsg('Chart data unavailable for '+sym+' ('+TFNAME[tf]+'): '+e.message,true)}return}
 if(cur.sym!==sym||ST.tf!==tf)return;
 const keepView=!fresh&&D&&D.symbol===j.symbol&&D.tf===j.tf,lr=keepView?chart.timeScale().getVisibleLogicalRange():null,oldN=D?D.T.length:0;
 D=prep(j);showMsg('');lastLoad=Date.now();
 if(drawKey()!==_dk)loadDraw();
 if(!keepView){makeChart();main=null;volS=null;ind=[];hlines=[]}
 buildMain();buildIndicators();card();renderRanges();
 if(keepView&&lr){const dn=D.T.length-oldN;chart.timeScale().setVisibleLogicalRange({from:lr.from+dn,to:lr.to+dn})}else resetView();
 const det=D.details,isC=det.contract&&!/continuous/.test(det.contract);
 $('.t1',W).textContent=(cur.name||det.name||sym);
 $('.t2',W).textContent=[det.exchange,isC?det.month:det.contract,det.unit].filter(Boolean).join(' · ');
 const p=window.MC_CHART_SRC!==false&&/^(ZS|ZM|ZL|ZC|ZW|KE|CL|BZ|HO|RB|NG|TTF|6E)[FGHJKMNQUVXZ]\d{2}(\.[A-Z]{3})?$/.test(sym);
 $('.mc-src',W).innerHTML=p?`<button data-src="contract" title="This contract only (life of contract)">Contract</button><button data-src="cont" title="Continuous front month — long history">Continuous</button>`:'';$('.sep-src',W).style.display=p?'':'none';
 stEl.textContent=`${TFNAME[ST.tf]} · ${D.n.toLocaleString('en-US')} bars · ${fmtDate(D.T[0],D.intraday)} → ${fmtDate(D.T[D.T.length-1],D.intraday)}${D.intraday?' '+TZL:''} · wheel = zoom, drag axes = scale, dbl-click axis = reset`;
 syncButtons();
}
function open(sym,name,opt){build();opt=opt||{};
 if(opt.tf&&TFS.some(x=>x[0]===opt.tf))ST.tf=opt.tf;
 if(!(window.MC_CHART_TFS||TFS.map(x=>x[0])).includes(ST.tf))ST.tf='1d';
 const same=cur.sym===sym;cur={sym,name,src:opt.src||'auto'};W.classList.add('on');if(!same){D=null;lg.innerHTML='';side.innerHTML='';if(chart){chart.remove();chart=null;main=null}}
 setTool('cursor');load(true);
 clearInterval(timer);timer=setInterval(()=>{if(W.classList.contains('on')&&!document.hidden&&!pending)load(false)},60000)}
function close(){if(!W)return;W.classList.remove('on');clearInterval(timer);menu.classList.remove('on');if(document.fullscreenElement)document.exitFullscreen().catch(()=>{});
 if(chart){chart.remove();chart=null;main=null;volS=null;ind=[]}D=null;cur={sym:null}}

window.MCChart={open,close,
 setTF:tf=>{ST.tf=tf;save();load(true)},
 setIndicators:o=>{Object.assign(ST,o);save();buildIndicators()},
 addDrawing:d=>{drawings.push(d);saveDraw();renderHlines();drawOverlay()},
 clearDrawings:()=>{drawings=[];saveDraw();renderHlines();drawOverlay()},
 state:()=>({ST,sym:cur.sym,n:D&&D.n,drawings,tool}),
 coords:(t,v)=>({x:xOf(t),y:yOf(v)}),data:()=>D,ready:()=>!!(D&&main&&chart)};
window.openChart=(sym,name,opt)=>open(sym,name,opt);
document.addEventListener('click',e=>{const t=e.target.closest('.ck');if(t&&!e.target.closest('a')&&!(W&&W.contains(t)))open(t.dataset.sym,t.dataset.name)});
{const q=new URLSearchParams(location.search);if(q.get('chart'))setTimeout(()=>open(q.get('chart'),q.get('name')||q.get('chart'),{tf:q.get('tf')||undefined,src:q.get('src')||undefined}),600)}
})();
