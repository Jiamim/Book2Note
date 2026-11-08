(()=>{
 'use strict';
 const slides=[...document.querySelectorAll('.slide')];
 const stage=document.querySelector('.stage');
 const overview=document.querySelector('#overview');
 const help=document.querySelector('#help');
 const noteReader=document.querySelector('#note-reader');
 const notesPanel=document.querySelector('#notes-panel');
 const notesTitle=document.querySelector('#notes-title');
 const notesCopy=document.querySelector('#notes-copy');
 const notesSources=document.querySelector('#notes-sources');
 const isPresenter=new URLSearchParams(location.search).get('presenter')==='1';
 let index=0,peer=null,touch=null,toastTimer=null;
 let routeMode=new URLSearchParams(location.search).get('route')==='complete'?'complete':'sharing';
 const sharingIndices=slides.map((s,i)=>s.dataset.detail==='true'?null:i).filter(i=>i!==null);
 function routeIndices(){return routeMode==='complete'?slides.map((s,i)=>i):sharingIndices}
 function routePosition(){return routeIndices().indexOf(index)}
 function routeStep(step){const r=routeIndices();go(r[Math.max(0,Math.min(r.length-1,routePosition()+step))])}
 function applyRoute(mode){routeMode=mode;document.body.dataset.route=mode;document.querySelector('#route-select').value=mode;slides.forEach((s,i)=>s.classList.toggle('route-hidden',mode==='sharing'&&!sharingIndices.includes(i)))}
 function chooseRoute(mode,sync=true){applyRoute(mode);if(!routeIndices().includes(index))index=sharingIndices[sharingIndices.length-1];go(index,{sync})}
 let timerRunning=false,timerStarted=0,timerElapsed=0;
 function fromHash(){const m=location.hash.match(/^#slide-(\d+)$/);return m?Math.min(slides.length-1,Math.max(0,Number(m[1])-1)):0}
 function fit(){if(matchMedia('(max-width:760px) and (orientation:portrait)').matches){document.documentElement.style.setProperty('--scale',1);return}const r=stage.getBoundingClientRect();document.documentElement.style.setProperty('--scale',Math.min((r.width-32)/1600,(r.height-24)/900))}
 function updateNotes(){const s=slides[index];notesTitle.textContent=`${routePosition()+1}. ${s.dataset.title}`;document.querySelector('#notes-meta').textContent=`${s.dataset.group}　${s.dataset.time||'按需展开'}`;notesCopy.innerHTML=s.querySelector('.speaker-note .notes-text')?.innerHTML||'';notesSources.innerHTML=s.querySelector('.speaker-note .notes-citations')?.innerHTML||''}
 function sendState(){const data={type:'protocols-slide',index,routeMode};if(peer&&!peer.closed)peer.postMessage(data,'*');if(isPresenter&&window.opener)window.opener.postMessage(data,'*')}
 let embeddedNotes=null,currentNote='';
const embedded=document.getElementById('embedded-notes');
if(embedded){try{embeddedNotes=JSON.parse(embedded.textContent)}catch{embeddedNotes=null}}
const esc=t=>t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;').replace(/'/g,'&#39;');
function inline(t){return esc(t).replace(/\[([^\]]+)\]\(([^)]+)\)/g,(m,label,href)=>{if(!/^(https?:\/\/|(?:\.\.\/)*[^:]+\.md(?:#[^\s]+)?$)/.test(href))return label;return `<a href="${href}">${label}</a>`}).replace(/`([^`]+)`/g,'<code>$1</code>').replace(/\*\*([^*]+)\*\*/g,'<strong>$1</strong>').replace(/\*([^*]+)\*/g,'<em>$1</em>')}
function renderMarkdown(source){const lines=source.split('\n');const out=[];let i=0;const isTable=x=>/^\s*\|/.test(x);const cells=x=>x.trim().replace(/^\||\|$/g,'').split('|').map(c=>inline(c.trim()));while(i<lines.length){const line=lines[i];if(!line.trim()){i++;continue}if(line.startsWith('```')){i++;const code=[];while(i<lines.length&&!lines[i].startsWith('```'))code.push(lines[i++]);i++;out.push('<pre><code>'+esc(code.join('\n'))+'</code></pre>');continue}const head=line.match(/^(#{1,4})\s+(.+)/);if(head){out.push(`<h${head[1].length}>${inline(head[2])}</h${head[1].length}>`);i++;continue}if(isTable(line)&&i+1<lines.length&&/^\s*\|[\s:|\-]+$/.test(lines[i+1])){const rows=[];out.push('<table><thead><tr>'+cells(line).map(c=>'<th>'+c+'</th>').join('')+'</tr></thead><tbody>');i+=2;while(i<lines.length&&isTable(lines[i]))rows.push('<tr>'+cells(lines[i++]).map(c=>'<td>'+c+'</td>').join('')+'</tr>');out.push(rows.join('')+'</tbody></table>');continue}if(/^\s*(?:- |\d+\. )/.test(line)){const ordered=/^\s*\d+\./.test(line),tag=ordered?'ol':'ul';out.push('<'+tag+'>');while(i<lines.length&&/^\s*(?:- |\d+\. )/.test(lines[i]))out.push('<li>'+inline(lines[i++].replace(/^\s*(?:- |\d+\. )/,''))+'</li>');out.push('</'+tag+'>');continue}const para=[line];i++;while(i<lines.length&&lines[i].trim()&&!/^(?:#{1,4}\s|```|\s*- |\s*\d+\. |\s*\|)/.test(lines[i]))para.push(lines[i++]);out.push('<p>'+inline(para.join(' '))+'</p>')}return out.join('\n')}
function openNote(name){if(!embeddedNotes?.[name])return false;currentNote=name;document.querySelector('#note-reader-title').textContent=name.replace(/\.md$/,'');document.querySelector('#note-reader-body').innerHTML=renderMarkdown(embeddedNotes[name]);if(!noteReader.open)noteReader.showModal();noteReader.scrollTop=0;return true}
document.addEventListener('click',e=>{const a=e.target.closest('a');if(!a||!embeddedNotes)return;let name;try{name=decodeURIComponent(a.getAttribute('href').split('#')[0].split('/').pop())}catch{return}if(embeddedNotes[name]){e.preventDefault();openNote(name)}});
document.querySelector('#download-note').addEventListener('click',()=>{if(!currentNote||!embeddedNotes)return;const u=URL.createObjectURL(new Blob([embeddedNotes[currentNote]],{type:'text/markdown;charset=utf-8'}));const a=document.createElement('a');a.href=u;a.download=currentNote;a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)});

 function go(next,{sync=true,hash=true}={}){index=Math.max(0,Math.min(slides.length-1,next));if(!routeIndices().includes(index))applyRoute('complete');const currentRoute=routeIndices();const position=routePosition();slides.forEach((s,i)=>{s.classList.toggle('active',i===index);s.inert=i!==index;s.setAttribute('aria-hidden',String(i!==index))});document.querySelector('#page-input').max=currentRoute.length;document.querySelector('#page-input').value=position+1;document.querySelector('#page-total').textContent=`/ ${currentRoute.length}`;document.querySelector('#prev-btn').disabled=position===0;document.querySelector('#next-btn').disabled=position===currentRoute.length-1;slides.forEach((s,i)=>{s.querySelector('.page-number').textContent=currentRoute.includes(i)?`${String(currentRoute.indexOf(i)+1).padStart(2,'0')} / ${currentRoute.length}`:''});document.querySelector('.progress').style.width=`${(position+1)/currentRoute.length*100}%`;document.title=`${position+1}/${currentRoute.length} · ${slides[index].dataset.title} · Protocols`;document.querySelector('#live-status').textContent=`第 ${position+1} 页，共 ${currentRoute.length} 页。${slides[index].dataset.title}`;updateNotes();if(hash){const url=new URL(location.href);url.hash=`slide-${index+1}`;url.searchParams.set('route',routeMode);try{history.replaceState(null,'',url.href)}catch{location.hash=`slide-${index+1}`}}overview.querySelectorAll('[data-slide]').forEach(b=>{b.classList.toggle('current',Number(b.dataset.slide)===index);if(Number(b.dataset.slide)===index)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current')});if(sync)sendState();fit();if(matchMedia('(max-width:760px) and (orientation:portrait)').matches)window.scrollTo(0,0)}
 function toast(msg){const el=document.querySelector('#toast');el.textContent=msg;el.hidden=false;clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.hidden=true,3500)}
 function toggleNotes(){if(isPresenter)return;const show=notesPanel.hidden;notesPanel.hidden=!show;document.body.classList.toggle('notes-open',show);document.querySelector('#notes-btn').setAttribute('aria-pressed',String(show));fit()}
 function toggleBlackout(){const b=document.querySelector('#blackout');b.hidden=!b.hidden;document.querySelector('#blackout-btn').setAttribute('aria-pressed',String(!b.hidden))}
 function openOverview(){overview.showModal();const current=overview.querySelector('.current');if(current){current.focus();current.scrollIntoView({block:'center'})}}
 function openPresenter(){if(isPresenter)return;const u=new URL(location.href);u.searchParams.set('presenter','1');peer=window.open(u.href,'protocols-presenter','width=1440,height=860');if(!peer)toast('浏览器拦截了新窗口，可以按 N 在本页查看备注')}
 async function fullscreen(){try{if(document.fullscreenElement)await document.exitFullscreen();else if(document.documentElement.requestFullscreen)await document.documentElement.requestFullscreen();else toast('请使用浏览器菜单进入全屏')}catch{toast('请使用浏览器菜单进入全屏')}}
 slides.forEach((s,i)=>{s.querySelector('.page-number').textContent=`${String(i+1).padStart(2,'0')} / ${slides.length}`;const b=document.createElement('button');b.type='button';b.dataset.slide=i;const no=document.createElement('span');no.className='num';no.textContent=String(i+1).padStart(2,'0');const text=document.createElement('span');text.className='title';text.textContent=s.dataset.title;const group=document.createElement('span');group.className='group';group.textContent=s.dataset.group+(s.dataset.detail==='true'?'　深入阅读':'');text.append(group);b.append(no,text);b.addEventListener('click',()=>{overview.close();go(i)});overview.querySelector('.overview-grid').append(b)});
 document.querySelector('#route-select').addEventListener('change',e=>chooseRoute(e.target.value));
 document.querySelector('#library-btn').addEventListener('click',()=>document.querySelector('#library').showModal());
 const noteNames=['README.md','00-导读与全书框架.md','01-睡眠.md','02-运动.md','03-压力控制.md','04-营养.md','05-光照.md','06-专注动机与学习.md','07-个人成长.md','08-全书速查与实践记录.md','09-研究资料.md'];
 noteNames.forEach(name=>{const a=document.createElement('a');a.href='../../Notes/Protocols/'+name;a.textContent=name==='README.md'?'阅读目录':name.replace(/\.md$/,'');if(embeddedNotes?.[name])a.addEventListener('click',e=>{e.preventDefault();document.querySelector('#library').close();openNote(name)});else{a.target='_blank';a.rel='noopener'}document.querySelector('#library-list').append(a)});
 document.querySelector('#prev-btn').addEventListener('click',()=>routeStep(-1));
 document.querySelector('#next-btn').addEventListener('click',()=>routeStep(1));
 document.querySelector('#overview-btn').addEventListener('click',openOverview);
 document.querySelector('#notes-btn').addEventListener('click',toggleNotes);
 document.querySelector('#presenter-btn').addEventListener('click',openPresenter);
 document.querySelector('#fullscreen-btn').addEventListener('click',fullscreen);
 document.querySelector('#blackout-btn').addEventListener('click',toggleBlackout);
 document.querySelector('#blackout').addEventListener('click',toggleBlackout);
 document.querySelector('#help-btn').addEventListener('click',()=>help.showModal());
 document.querySelector('#print-btn').addEventListener('click',()=>{document.querySelectorAll('dialog').forEach(d=>{if(d.open)d.close()});window.print()});
 document.querySelectorAll('[data-close]').forEach(b=>b.addEventListener('click',()=>b.closest('dialog').close()));
 document.querySelector('#page-input').addEventListener('change',e=>{const n=Number(e.target.value);if(Number.isInteger(n)){const r=routeIndices();go(r[Math.max(0,Math.min(r.length-1,n-1))])}else e.target.value=routePosition()+1});
 document.querySelector('#page-input').addEventListener('keydown',e=>{if(e.key==='Enter'){e.target.blur();e.preventDefault()}});
 document.querySelectorAll('[data-reveal]').forEach(b=>b.addEventListener('click',()=>{const answer=document.getElementById(b.dataset.reveal);const visible=answer.hidden;answer.hidden=!visible;b.setAttribute('aria-expanded',String(visible));b.textContent=visible?'收起解释':'查看解释'}));
 document.addEventListener('keydown',e=>{if(overview.open||help.open||noteReader.open||document.querySelector('#library').open)return;if(e.target.closest('input,textarea,select,[contenteditable="true"]'))return;if(e.target.closest('button,a')&&[' ','Enter'].includes(e.key))return;if(!document.querySelector('#blackout').hidden){if(['b','B','Escape',' '].includes(e.key)){e.preventDefault();toggleBlackout()}return}if(['ArrowRight','ArrowDown','PageDown',' '].includes(e.key)){e.preventDefault();routeStep(1)}else if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key)){e.preventDefault();routeStep(-1)}else if(e.key==='Home'){e.preventDefault();go(routeIndices()[0])}else if(e.key==='End'){e.preventDefault();go(routeIndices().at(-1))}else if(e.key.toLowerCase()==='n')toggleNotes();else if(e.key.toLowerCase()==='o')openOverview();else if(e.key.toLowerCase()==='f')fullscreen();else if(e.key.toLowerCase()==='p')openPresenter();else if(e.key.toLowerCase()==='l')document.querySelector('#library').showModal();else if(e.key.toLowerCase()==='b')toggleBlackout();else if(e.key==='?')help.showModal()});
 stage.addEventListener('touchstart',e=>{if(e.target.closest('button,a,input'))return;touch={x:e.changedTouches[0].clientX,y:e.changedTouches[0].clientY}},{passive:true});
 stage.addEventListener('touchend',e=>{if(!touch)return;const dx=e.changedTouches[0].clientX-touch.x,dy=e.changedTouches[0].clientY-touch.y;touch=null;if(Math.abs(dx)>70&&Math.abs(dx)>Math.abs(dy)*1.5)routeStep(dx<0?1:-1)},{passive:true});
 window.addEventListener('resize',fit);window.addEventListener('hashchange',()=>go(fromHash(),{hash:false}));
 window.addEventListener('message',e=>{if(e.data?.type!=='protocols-slide')return;if(e.source!==peer&&e.source!==window.opener)return;if(Number.isInteger(e.data.index)){applyRoute(e.data.routeMode==='complete'?'complete':'sharing');go(e.data.index,{sync:false})}});
 const timerValue=document.querySelector('#timer-value');
 function renderTimer(){const elapsed=timerElapsed+(timerRunning?Date.now()-timerStarted:0);const seconds=Math.floor(elapsed/1000);timerValue.textContent=`${String(Math.floor(seconds/60)).padStart(2,'0')}:${String(seconds%60).padStart(2,'0')}`}
 document.querySelector('#timer-start').addEventListener('click',e=>{if(timerRunning){timerElapsed+=Date.now()-timerStarted;timerRunning=false;e.target.textContent='继续'}else{timerStarted=Date.now();timerRunning=true;e.target.textContent='暂停'}renderTimer()});
 document.querySelector('#timer-reset').addEventListener('click',()=>{timerRunning=false;timerElapsed=0;timerStarted=0;document.querySelector('#timer-start').textContent='开始';renderTimer()});setInterval(renderTimer,1000);
 if(isPresenter){document.body.classList.add('presenter','notes-open');notesPanel.hidden=false}
 applyRoute(routeMode);go(fromHash());
 if(isPresenter&&window.opener)sendState();
 document.fonts.ready.then(fit);
})();
