const $=s=>document.querySelector(s);
let channels=[], groups=[], sections=[], epg={}, activeGroup=null, current=null, hls=null;
let virtualMode=null;
const favs=new Set(JSON.parse(localStorage.getItem('mastertv:favs')||'[]'));
let recent=JSON.parse(localStorage.getItem('mastertv:recent')||'[]');
const RECENT_LIMIT=50;
const ua=navigator.userAgent.toLowerCase();
if(ua.includes('tesla')) $('#teslaNotice').classList.remove('hidden');
if('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(()=>{});

function saveFavs(){localStorage.setItem('mastertv:favs',JSON.stringify([...favs]))}
function saveRecent(){recent=recent.slice(0,RECENT_LIMIT);localStorage.setItem('mastertv:recent',JSON.stringify(recent))}
function addRecent(id){recent=[id,...recent.filter(x=>x!==id)];saveRecent()}
function toggleFav(id){favs.has(id)?favs.delete(id):favs.add(id);saveFavs();render();syncNowFav()}
function syncNowFav(){if(!current)return;$('#nowFav').textContent=(favs.has(current.tvg_id)?'★':'☆')+' Favorite'}
function esc(s=''){return String(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]))}
function fmtTime(iso){if(!iso)return'';try{return new Intl.DateTimeFormat(undefined,{hour:'numeric',minute:'2-digit'}).format(new Date(iso))}catch{return''}}
function groupCount(g){return channels.filter(c=>c.groups?.includes(g)).length}
function virtualCount(g){if(g==='⭐ FAVORITES')return channels.filter(c=>favs.has(c.tvg_id)).length;if(g==='🕘 RECENTLY WATCHED')return recent.filter(id=>channels.some(c=>c.tvg_id===id)).length;return 0}

function selectGroup(g){activeGroup=null;virtualMode=null;if(g==='⭐ FAVORITES'||g==='🕘 RECENTLY WATCHED')virtualMode=g;else activeGroup=g;render()}

function renderGroups(){
  const el=$('#groups');el.innerHTML='';
  const all=document.createElement('button');all.className='group '+(!activeGroup&&!virtualMode?'active':'');all.innerHTML=`<span>📺 ALL CHANNELS</span><span class="count">${channels.length}</span>`;all.onclick=()=>selectGroup(null);el.appendChild(all);
  sections.forEach(sec=>{
    const h=document.createElement('div');h.className='section-label';h.textContent=sec.title;el.appendChild(h);
    sec.groups.forEach(g=>{
      const n=g==='⭐ FAVORITES'||g==='🕘 RECENTLY WATCHED'?virtualCount(g):groupCount(g);
      const b=document.createElement('button');b.className='group '+((activeGroup===g||virtualMode===g)?'active':'')+(n===0?' empty':'');
      b.innerHTML=`<span>${esc(g)}</span><span class="count">${n}</span>`;b.onclick=()=>selectGroup(g);el.appendChild(b);
    });
  });
}

function filtered(){
  const q=$('#search').value.trim().toLowerCase();
  let arr=channels.filter(c=>{
    if(virtualMode==='⭐ FAVORITES'&&!favs.has(c.tvg_id))return false;
    if(activeGroup&&!c.groups?.includes(activeGroup))return false;
    if(q&&!`${c.name} ${c.country} ${(c.languages||[]).join(' ')} ${(c.groups||[]).join(' ')}`.toLowerCase().includes(q))return false;
    return true;
  });
  if(virtualMode==='🕘 RECENTLY WATCHED'){
    const map=new Map(channels.map(c=>[c.tvg_id,c]));arr=recent.map(id=>map.get(id)).filter(Boolean);
    if(q)arr=arr.filter(c=>`${c.name} ${c.country} ${(c.groups||[]).join(' ')}`.toLowerCase().includes(q));
  }
  return arr;
}

function miniEPG(c){const e=epg[c.tvg_id]?.now;if(!e)return c.has_guide_metadata?'Guide available':'Guide fallback';return `${fmtTime(e.start)}  ${e.title||''}`.trim()}
function render(){
  renderGroups();const arr=filtered();$('#resultCount').textContent=`${arr.length} channels`;$('#viewTitle').textContent=virtualMode||activeGroup||'📺 ALL CHANNELS';
  const el=$('#grid');el.innerHTML='';const tpl=$('#cardTpl');
  if(!arr.length){el.innerHTML='<div class="empty-state">No channels in this section yet.</div>';return}
  for(const c of arr){
    const node=tpl.content.firstElementChild.cloneNode(true);node.querySelector('.name').textContent=c.name;
    node.querySelector('.meta').textContent=[c.country,c.quality,(c.languages||[]).join('/')].filter(Boolean).join(' • ');
    node.querySelector('.epg-mini').textContent=miniEPG(c);
    const im=node.querySelector('.logo');if(c.logo){im.src=c.logo;im.onerror=()=>im.remove()}else im.remove();
    node.querySelector('.star').textContent=favs.has(c.tvg_id)?'★':'☆';node.querySelector('.star').onclick=e=>{e.stopPropagation();toggleFav(c.tvg_id)};
    node.onclick=()=>play(c);el.appendChild(node);
  }
}

function renderEPG(c){
  const d=epg[c.tvg_id]||{};const n=d.now;const nx=d.next;
  $('#epgNowTitle').textContent=n?.title||'Live programming — schedule unavailable';$('#epgNowTime').textContent=n?`${fmtTime(n.start)} – ${fmtTime(n.stop)}`:'No reliable programme-level guide data';
  $('#epgNextTitle').textContent=nx?.title||'—';$('#epgNextTime').textContent=nx?`${fmtTime(nx.start)} – ${fmtTime(nx.stop)}`:'';
}

function play(c){
  current=c;addRecent(c.tvg_id);$('#playerCard').classList.remove('hidden');$('#nowName').textContent=c.name;
  $('#nowMeta').textContent=[c.country,c.quality,(c.labels||[]).join(' • ')].filter(Boolean).join(' • ');const im=$('#nowLogo');im.src=c.logo||'';im.style.display=c.logo?'block':'none';syncNowFav();renderEPG(c);
  const v=$('#video');if(hls){hls.destroy();hls=null}v.pause();v.removeAttribute('src');
  if(v.canPlayType('application/vnd.apple.mpegurl')){v.src=c.url;v.play().catch(()=>{})}
  else if(window.Hls&&Hls.isSupported()){hls=new Hls({enableWorker:true,lowLatencyMode:true});hls.loadSource(c.url);hls.attachMedia(v);hls.on(Hls.Events.MANIFEST_PARSED,()=>v.play().catch(()=>{}));}
  else{v.src=c.url;v.play().catch(()=>{})}
  renderGroups();window.scrollTo({top:0,behavior:'smooth'});
}

$('#search').addEventListener('input',render);$('#clearSearch').onclick=()=>{$('#search').value='';render()};$('#nowFav').onclick=()=>current&&toggleFav(current.tvg_id);
const DATA_BASE=location.pathname.includes('/static/')?'../output/':'./output/';
Promise.all([
  fetch(DATA_BASE+'channels.json').then(r=>r.json()),
  fetch(DATA_BASE+'groups.json').then(r=>r.json()),
  fetch(DATA_BASE+'group_sections.json').then(r=>r.json()),
  fetch(DATA_BASE+'epg_index.json').then(r=>r.json()).catch(()=>({}))
]).then(([c,g,s,e])=>{channels=c;groups=g;sections=s;epg=e;render()}).catch(err=>{$('#grid').innerHTML='<p>Run update_master.py first, then serve the project root over HTTP.</p>'});
