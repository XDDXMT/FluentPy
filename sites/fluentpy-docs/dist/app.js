(() => {
  'use strict';
  const {pages, groups, api, icons, sourceDate, version, previewVersion, animatedPreviews={}} = window.DOCS_DATA;
  const $ = (s, root=document) => root.querySelector(s);
  const $$ = (s, root=document) => [...root.querySelectorAll(s)];
  const escape = value => String(value).replace(/[&<>"']/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const route = (page, anchor='') => `#/${page}${anchor?'/'+anchor:''}`;
  const copyIcon='<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="8" y="8" width="12" height="13" rx="2"/><path d="M15 8V4a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1v11a1 1 0 0 0 1 1h4"/></svg>';
  const main=$('#main');
  let currentPage='';
  let codeSnippets=[];
  let observer;
  let nativeFlowCleanup;
  let migrationCleanup;
  let toastTimer;
  let searchIndex=0;
  let themePreference=document.documentElement.dataset.preference||'system';
  const systemTheme=window.matchMedia('(prefers-color-scheme: dark)');
  const reducedMotion=window.matchMedia('(prefers-reduced-motion: reduce)');

  function notify(message){
    $('#toast').textContent=message;
    $('#toast').classList.add('visible');
    clearTimeout(toastTimer);
    toastTimer=setTimeout(()=>$('#toast').classList.remove('visible'),2200);
  }
  async function copyText(text){
    try{await navigator.clipboard.writeText(text);notify('已复制到剪贴板');return true;}
    catch{notify('浏览器未允许复制，请选中文字后复制');return false;}
  }
  function highlight(text){
    const pattern=/(#[^\n]*|"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|\b(?:from|import|as|if|else|def|class|return|lambda|for|in|True|False|None|print)\b|\b\d+(?:\.\d+)?\b|\b[A-Za-z_]\w*(?=\())/g;
    let result='',start=0;
    for(const match of text.matchAll(pattern)){
      result+=escape(text.slice(start,match.index));
      const token=match[0];
      const type=token.startsWith('#')?'comment':/^['"]/.test(token)?'string':/^\d/.test(token)?'number':/^(from|import|as|if|else|def|class|return|lambda|for|in|True|False|None|print)$/.test(token)?'keyword':'call';
      result+=`<span class="tok-${type}">${escape(token)}</span>`;
      start=match.index+token.length;
    }
    return result+escape(text.slice(start));
  }
  function codeBlock(code,language){
    const index=codeSnippets.push(code)-1;
    const label=language||(code.startsWith('git ')||code.startsWith('python ')?'PowerShell':'Python');
    return `<div class="code-block"><div class="code-top"><span>${escape(label)}</span><button class="copy-button" data-copy="${index}" aria-label="复制代码">${copyIcon}复制</button></div><div class="code-body">${highlight(code).split('\n').map(line=>`<span class="code-line">${line||' '}</span>`).join('')}</div></div>`;
  }
  function preview(type){
    if(type==='icons')return `<input class="icon-search" id="icon-filter" placeholder="搜索图标名称，例如 add、home、arrow" aria-label="搜索图标"><div class="icon-grid" id="icon-grid"></div><a href="assets/icons-LICENSE.txt" target="_blank" class="api-intro">查看 Microsoft Fluent System Icons 完整许可 ↗</a>`;
    if(type==='api-index')return `<input class="icon-search index-filter" id="api-filter" placeholder="按名称或说明过滤接口" aria-label="过滤接口"><div class="api-index" id="api-index-grid"></div>`;
    if(animatedPreviews[type]){
      const item=animatedPreviews[type];
      const animation=`assets/previews/${item.image}?v=${previewVersion}`;
      const poster=`assets/previews/${item.poster}?v=${previewVersion}`;
      const paused=true;
      return `<details class="sample-code motion-details"><summary>查看交互动画 · Qt 录制</summary><figure class="preview-box animation-preview" data-animated-preview="${escape(type)}" data-animation="${escape(animation)}" data-poster="${escape(poster)}" data-paused="${paused}"><div class="preview-stage preview-animation"><img class="qt-shot" src="${escape(paused?poster:animation)}" width="${item.width}" height="${item.height}" alt="${escape(item.alt)}" loading="lazy"></div><figcaption class="preview-caption"><span>Qt 控件实录 · 亮色 GIF</span><div class="animation-controls"><button type="button" data-preview-toggle>${paused?'播放动画':'暂停动画'}</button><a href="${escape(animation)}" target="_blank" rel="noopener">查看动图 ↗</a></div></figcaption></figure></details>`;
    }
    return `<div class="preview-box"><div class="preview-stage${type==='code-editor'?' preview-code':''}"><img class="qt-shot" src="assets/previews/${escape(type)}-light.png?v=${previewVersion}" alt="${escape(type)} Qt 控件亮色截图" loading="lazy"></div><div class="preview-caption"><span>Qt 控件亮色截图${type==='code-editor'?' · 可横向滚动':''}</span>${type==='code-editor'?`<a href="assets/previews/code-editor-light.png?v=${previewVersion}" target="_blank" rel="noopener">查看原图 ↗</a>`:'<span>FLUENTPY · PYSIDE6</span>'}</div></div>`;
  }
  function apiClass(name){
    const item=api[name];if(!item)return '';
    const methods=item.methods.map(method=>`<div class="method" id="api-${escape(name)}-${escape(method.name)}"><div class="signature">${escape(method.signature)}</div>${method.description?`<p>${escape(method.description)}</p>`:''}</div>`).join('');
    const signals=item.signals.length?`<div class="api-signals">信号 ${item.signals.map(signal=>`<code>${escape(signal.name)}</code>`).join(' ')}</div>`:'';
    return `<div class="api-class" id="api-${escape(name)}"><div class="api-class-head"><strong>${escape(name)}</strong><span class="api-base">${escape(item.alias?'alias → '+item.alias:(item.base||'').startsWith('_')?'':item.base||'')}</span></div><p class="api-description">${escape(item.description)}</p>${methods||`<div class="api-empty">${item.alias?'导出别名，与 '+escape(item.alias)+' 使用同一实现。':item.base?'构造与基础接口继承自 '+escape(item.base)+'。':'此项为公开数据或枚举入口。'}</div>`}${signals}</div>`;
  }
  function pageForClass(name){return pages.find(page=>page.classes.includes(name));}
  function renderIndex(filter=''){
    const query=filter.toLowerCase();
    const entries=Object.values(api).filter(item=>(item.name+' '+item.description).toLowerCase().includes(query));
    $('#api-index-grid').innerHTML=entries.length?entries.map(item=>{
      const page=pageForClass(item.name)||pages.find(p=>p.id==='themes');
      const anchor=page.classes.includes(item.name)?'api-'+item.name:page.sections[0].id;
      return `<a class="index-card" href="${route(page.id,anchor)}"><code>${escape(item.name)}</code><small>${escape(item.description)}</small></a>`;
    }).join(''):'<p>没有匹配的接口。</p>';
  }
  function renderIcons(filter=''){
    const matches=icons.filter(icon=>icon.name.toLowerCase().includes(filter.toLowerCase()));
    $('#icon-grid').innerHTML=matches.length?matches.map(icon=>`<button class="icon-cell" data-icon="${escape(icon.name)}" aria-label="复制 FluentIcon.${escape(icon.name)}"><img src="${escape(icon.file)}" alt="" loading="lazy"><span>${escape(icon.name)}</span></button>`).join(''):'<p>没有匹配的图标。</p>';
  }
  function closeMenu(){$('#sidebar').classList.remove('open');$('#sidebar-shade').classList.remove('visible');$('#menu-toggle').setAttribute('aria-expanded','false');}
  function setPreviewPaused(box,paused,manual=false){
    if(manual)box.dataset.motionOverride=paused?'pause':'play';
    box.dataset.paused=String(paused);
    $('img',box).src=paused?box.dataset.poster:box.dataset.animation;
    $('[data-preview-toggle]',box).textContent=paused?'播放动画':'暂停动画';
  }
  function sectionContent(section){
    const paragraphs=(section.paragraphs||[]).map(text=>`<p>${escape(text)}</p>`).join('');
    const nativeFlow=section.nativeFlow&&window.FluentNativeFlow?window.FluentNativeFlow.markup():'';
    const architecture=section.architecture?`<ol class="backend-layers" aria-label="Python、C 与 Qt 的职责分工">${section.architecture.map(layer=>`<li><div class="backend-layer-head"><span>${escape(layer.name)}</span><strong>${escape(layer.role)}</strong></div><p>${escape(layer.text)}</p></li>`).join('')}</ol>`:'';
    const metrics=section.metrics?`<dl class="native-metrics" aria-label="一万行 JSON 的本机 C 后端实测">${section.metrics.map(metric=>`<div><dt>${escape(metric.label)}</dt><dd><strong>${escape(metric.value)}</strong><span>${escape(metric.detail)}</span></dd></div>`).join('')}</dl>`:'';
    const table=section.table?`<div class="native-table" role="region" aria-label="${escape(section.table.caption)}" tabindex="0"><table><caption>${escape(section.table.caption)}</caption><thead><tr>${section.table.headers.map(label=>`<th scope="col">${escape(label)}</th>`).join('')}</tr></thead><tbody>${section.table.rows.map(row=>`<tr>${row.map((cell,index)=>index===0?`<th scope="row">${escape(cell)}</th>`:`<td>${escape(cell)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`:'';
    const items=section.items?`<ul class="doc-list">${section.items.map(item=>`<li><strong>${escape(item.title)}</strong>：${escape(item.text)}</li>`).join('')}</ul>`:'';
    const links=section.links?`<div class="doc-links">${section.links.map(link=>`<a href="${escape(link.page?route(link.page):link.href)}"${link.page?'':' target="_blank" rel="noopener"'}>${escape(link.label)}</a>`).join('')}</div>`:'';
    const gallery=section.gallery?`<div class="intro-gallery">${section.gallery.map((card,index)=>`<a class="intro-card" href="${route(card.page)}"><div class="intro-card-image"><img src="assets/previews/${escape(card.image)}-light.png?v=${previewVersion}" alt="${escape(card.title)}的 FluentPy 亮色控件截图" loading="lazy"></div><div class="intro-card-copy"><span class="intro-card-number">0${index+1}</span><h3>${escape(card.title)}<span aria-hidden="true">↗</span></h3><p>${escape(card.text)}</p><small>${escape(card.tag)}</small></div></a>`).join('')}</div>`:'';
    const migration=section.migration&&window.FluentMigration?window.FluentMigration.markup(section.migration,previewVersion):'';
    const steps=section.steps?`<div class="intro-steps">${section.steps.map((step,index)=>`<a class="intro-step" href="${route(step.page)}"><span class="intro-step-number">${index+1}</span><h3>${escape(step.title)}</h3><p>${escape(step.text)}</p><span class="intro-step-link">${escape(step.label)} →</span></a>`).join('')}</div>`:'';
    const callout=section.callout?`<aside class="license-callout" aria-label="${escape(section.callout.title)} 许可说明"><h3><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/></svg>${escape(section.callout.title)}</h3><p>${escape(section.callout.text)}</p></aside>`:'';
    return paragraphs+nativeFlow+architecture+items+metrics+table+gallery+migration+steps+links+callout;
  }
  function setTheme(preference){
    themePreference=preference;
    const mode=preference==='system'?(systemTheme.matches?'dark':'light'):preference;
    document.documentElement.dataset.theme=mode;
    document.documentElement.dataset.preference=preference;
    try{localStorage.setItem('fluentpy-theme-mode',preference);}catch{}
    const light=mode==='light';
    const next=preference==='system'?'浅色':preference==='light'?'深色':'跟随系统';
    const name=preference==='system'?'跟随系统':light?'浅色':'深色';
    $('#theme-toggle').setAttribute('aria-label',`当前主题：${name}；点击切换为${next}`);
    $('#theme-toggle').setAttribute('title',`主题：${name}，点击切换为${next}`);
    $('#theme-toggle').innerHTML=preference==='system'?'<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="13" rx="2"/><path d="M8 21h8m-4-4v4"/></svg>':light?'<svg viewBox="0 0 24 24"><path d="M20 15.5A8.5 8.5 0 0 1 8.5 4 8.5 8.5 0 1 0 20 15.5Z"/></svg>':'<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1.5 1.5m11 11L19 19M5 19l1.5-1.5m11-11L19 5"/></svg>';
    $('meta[name="theme-color"]').content=light?'#ffffff':'#161616';
  }
  const searchEntries=[];
  for(const page of pages){
    searchEntries.push({title:page.title,detail:page.english+' · '+page.group,url:route(page.id),haystack:page.title+' '+page.english+' '+page.intro});
    if(page.id==='faq')for(const section of page.sections){
      searchEntries.push({title:section.title,detail:'常见问题 · '+section.text,url:route(page.id,section.id),haystack:section.title+' '+section.text+' '+(section.paragraphs||[]).join(' ')});
    }
    for(const name of page.classes){
      const item=api[name];if(!item)continue;
      searchEntries.push({title:name,detail:page.title+' · '+item.description,url:route(page.id,'api-'+name),haystack:name+' '+item.description});
      for(const method of item.methods){if(method.name==='__init__')continue;searchEntries.push({title:`${name}.${method.name}`,detail:page.title+' · '+method.description,url:route(page.id,'api-'+name+'-'+method.name),haystack:name+' '+method.name+' '+method.description});}
    }
  }
  function search(){
    const query=$('#search-input').value.trim().toLowerCase();searchIndex=0;
    const terms=query.split(/\s+/).filter(Boolean);
    const results=query?searchEntries.filter(entry=>terms.every(term=>(entry.title+' '+entry.haystack).toLowerCase().includes(term))).slice(0,18):searchEntries.filter(entry=>!entry.title.includes('.')).slice(0,8);
    $('#search-results').innerHTML=results.length?results.map((entry,i)=>`<a class="search-result${i===0?' active':''}" href="${entry.url}"><code>${escape(entry.title)}</code><small>${escape(entry.detail)}</small></a>`).join(''):`<div class="search-empty">没有找到「${escape(query)}」相关内容</div>`;
  }
  function openSearch(){$('#search-dialog').showModal();$('#search-input').value='';search();$('#search-input').focus();}
  $('#search-trigger').addEventListener('click',openSearch);
  $('#search-close').addEventListener('click',()=>$('#search-dialog').close());
  $('#search-input').addEventListener('input',search);
  $('#search-results').addEventListener('click',e=>{if(e.target.closest('a'))$('#search-dialog').close();});
  $('#search-dialog').addEventListener('click',e=>{if(e.target===$('#search-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
  document.addEventListener('keydown',e=>{
    if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==='k'){e.preventDefault();if(!$('#search-dialog').open)openSearch();return;}
    if(!$('#search-dialog').open)return;
    const results=$$('.search-result');
    if((e.key==='ArrowDown'||e.key==='ArrowUp')&&results.length){e.preventDefault();searchIndex=(searchIndex+(e.key==='ArrowDown'?1:-1)+results.length)%results.length;results.forEach((r,i)=>r.classList.toggle('active',i===searchIndex));results[searchIndex].scrollIntoView({block:'nearest'});}
    if(e.key==='Enter'&&results.length){e.preventDefault();results[searchIndex].click();}
  });
  $('#theme-toggle').addEventListener('click',()=>setTheme(themePreference==='system'?'light':themePreference==='light'?'dark':'system'));
  systemTheme.addEventListener('change',()=>{if(themePreference==='system')setTheme('system');});
  reducedMotion.addEventListener('change',()=>$$('[data-animated-preview]').filter(box=>!box.dataset.motionOverride).forEach(box=>setPreviewPaused(box,reducedMotion.matches)));
  $('#menu-toggle').addEventListener('click',()=>{const open=$('#sidebar').classList.toggle('open');$('#sidebar-shade').classList.toggle('visible',open);$('#menu-toggle').setAttribute('aria-expanded',String(open));});
  $('#sidebar-shade').addEventListener('click',closeMenu);
  main.addEventListener('input',e=>{
    if(e.target.id==='icon-filter')renderIcons(e.target.value);
    if(e.target.id==='api-filter')renderIndex(e.target.value);
  });
  main.addEventListener('click',async e=>{
    const button=e.target.closest('button');if(!button)return;
    if(button.hasAttribute('data-preview-toggle')){const box=button.closest('[data-animated-preview]');setPreviewPaused(box,box.dataset.paused!=='true',true);return;}
    if(button.hasAttribute('data-copy')){if(await copyText(codeSnippets[Number(button.dataset.copy)])){button.innerHTML=copyIcon+'已复制';setTimeout(()=>{if(button.isConnected)button.innerHTML=copyIcon+'复制';},1800);}}
    if(button.dataset.icon)await copyText('FluentIcon.'+button.dataset.icon);
  });
  $('#sidebar').addEventListener('click',e=>{if(e.target.closest('a'))closeMenu();});
  $('.skip').addEventListener('click',e=>{e.preventDefault();main.focus();main.scrollIntoView();});
  function buildNavigation(){
    $('#navigation').innerHTML=groups.map((group,index)=>`<details class="nav-group" data-nav-group="${index}"${index===0?' open':''}><summary>${escape(group.name)}</summary><div class="nav-group-links">${group.pages.map(id=>{const page=pages.find(p=>p.id===id);return `<a class="nav-link" href="${route(id)}" data-page="${id}">${escape(page.title)}</a>`}).join('')}</div></details>`).join('');
  }

  function introCover(cover){
    if(!cover)return '';
    const source=`assets/previews/${escape(cover.image)}-light.png?v=${previewVersion}`;
    return `<figure class="intro-cover"><div class="intro-cover-top"><span>FluentPy 组件示例 · Qt 原生界面</span><a href="${source}" target="_blank" rel="noopener">查看原图 ↗</a></div><img src="${source}" width="${cover.width||1120}" height="${cover.height||780}" alt="${escape(cover.alt||'FluentPy 组件示例程序')}" fetchpriority="high"><figcaption>${escape(cover.caption)}</figcaption></figure>`;
  }

  const catalogIcons={'buttons':'TOOLBOX','inputs':'TEXT_FONT','selection':'CHECKBOX_CHECKED','date-picker':'CALENDAR_LTR','time-picker':'CLOCK','calendar-picker':'CALENDAR_LTR','drag-drop':'FOLDER_OPEN','shortcut-picker':'KEY','navigation':'NAVIGATION','navigation-controls':'LAYOUT_ROW_THREE','cards':'TABLE','dialogs':'CHAT','feedback':'ALERT','code-editor':'CODE','note-timeline':'MUSIC_NOTE_2','icons':'ICONS'};
  const componentGroups=groups.map(group=>({...group,pages:group.pages.map(id=>pages.find(p=>p.id===id)).filter(page=>page.classes.length&&page.id!=='themes')})).filter(group=>group.pages.length);
  let catalogCategory='all';
  function catalogMarkup(){
    return `<div class="catalog-toolbar"><input class="catalog-search" id="catalog-filter" aria-label="搜索组件" placeholder="按组件名称、类名或用途查找"><span class="catalog-count" id="catalog-count" aria-live="polite"></span></div><div class="catalog-filters" aria-label="组件分类"><button type="button" class="catalog-filter" data-catalog-group="all" aria-pressed="true">全部</button>${componentGroups.map(group=>`<button type="button" class="catalog-filter" data-catalog-group="${escape(group.name)}" aria-pressed="false">${escape(group.name)}</button>`).join('')}</div><div id="component-catalog"></div>`;
  }
  function renderCatalog(){
    const query=($('#catalog-filter')?.value||'').trim().toLowerCase();let count=0;
    $('#component-catalog').innerHTML=componentGroups.filter(group=>catalogCategory==='all'||catalogCategory===group.name).map(group=>{
      const matches=group.pages.filter(page=>(page.title+' '+page.english+' '+page.intro+' '+page.classes.join(' ')).toLowerCase().includes(query));count+=matches.length;
      return matches.length?`<section class="catalog-category"><h2>${escape(group.name)}</h2><div class="catalog-grid">${matches.map(page=>{const icon=icons.find(item=>item.name===catalogIcons[page.id]);return `<a class="catalog-card" href="${route(page.id)}"><div class="catalog-card-head">${icon?`<img class="catalog-icon" src="${escape(icon.file)}" alt="">`:''}<h3>${escape(page.title)}</h3></div><p>${escape(page.catalogDescription||page.intro)}</p><code>${escape(page.classes.slice(0,3).join(' · '))}${page.classes.length>3?' …':''}</code></a>`;}).join('')}</div></section>`:'';
    }).join('')||'<p class="catalog-empty">没有匹配的组件，请调整关键词或分类。</p>';
    $('#catalog-count').textContent=`${count} 个组件主题`;
    $$('[data-catalog-group]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.catalogGroup===catalogCategory)));
  }

  function renderSection(page,section){
    const content=sectionContent(section);
    const media=section.preview?preview(section.preview):'';
    const sample=section.code?codeBlock(section.code,section.language):'';
    const code=(section.preview||section.migration)&&section.code?`<details class="sample-code"><summary>查看示例代码</summary>${sample}</details>`:sample;
    const note=section.note?`<div class="note">${escape(section.note)}</div>`:'';
    if(page.id==='faq')return `<details class="faq-item" id="${escape(section.id)}"><summary><h2>${escape(section.title)}</h2></summary><div class="faq-answer"><p>${escape(section.text)}</p>${content}${code}${note}</div></details>`;
    return `<section id="${escape(section.id)}"><h2>${escape(section.title)}<a class="anchor" href="${route(page.id,section.id)}" aria-label="链接到 ${escape(section.title)}">#</a></h2>${section.text?`<p>${escape(section.text)}</p>`:''}${content}${media}${code}${note}</section>`;
  }

  function updateDocumentView(page,anchor){
    const apiView=page.classes.length>0&&Boolean(anchor&&(anchor==='api'||anchor.startsWith('api-')));
    const examples=$('#examples-pane');const reference=$('#reference-pane');
    if(examples)examples.hidden=apiView;
    if(reference)reference.hidden=!apiView;
    $$('.page-tabs [role=tab]').forEach(tab=>tab.setAttribute('aria-selected',String(tab.dataset.view===(apiView?'api':'examples'))));
    const entries=apiView?page.classes.map(name=>({id:'api-'+name,title:name})):page.sections.map(section=>({id:section.id,title:section.title}));
    $('#toc').innerHTML=entries.map(entry=>`<a href="${route(page.id,entry.id)}" data-anchor="${escape(entry.id)}">${escape(entry.title)}</a>`).join('');
    observer?.disconnect();
    observer=new IntersectionObserver(changes=>{const visible=changes.filter(item=>item.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top);if(visible.length)$$('#toc a').forEach(link=>link.classList.toggle('active',link.dataset.anchor===visible[0].target.id));},{rootMargin:'-90px 0px -60% 0px',threshold:0});
    entries.forEach(entry=>{const target=document.getElementById(entry.id);if(target)observer.observe(target);});
    requestAnimationFrame(()=>{
      const target=anchor&&anchor!=='api'?document.getElementById(anchor):null;
      if(target){let node=target;while(node&&node!==main){if(node.tagName==='DETAILS')node.open=true;node=node.parentElement;}target.scrollIntoView({behavior:'instant',block:'start'});}
      else window.scrollTo({top:0,behavior:'instant'});
    });
  }

  function render(){
    let parts=location.hash.replace(/^#\/?/,'').split('/');
    const moved={'introduction/features':'components','introduction/next':'getting-started','introduction/more':'themes'};
    const destination=moved[parts.join('/')];
    if(destination){parts=destination.split('/');history.replaceState(null,'','#/'+destination);}
    let page=pages.find(item=>item.id===parts[0]);
    if(!page){page=pages.find(item=>item.id==='introduction');history.replaceState(null,'',route(page.id));}
    const anchor=parts[1];
    if(currentPage===page.id){closeMenu();updateDocumentView(page,anchor);return;}
    nativeFlowCleanup?.();nativeFlowCleanup=null;migrationCleanup?.();migrationCleanup=null;
    observer?.disconnect();codeSnippets=[];currentPage=page.id;document.body.dataset.page=page.id;
    document.title=page.id==='introduction'?'FluentPy · Qt for Python 组件库':`${page.title} · FluentPy 文档`;
    $$('.nav-link').forEach(link=>{const active=link.dataset.page===page.id;link.classList.toggle('active',active);if(active){link.setAttribute('aria-current','page');link.closest('details').open=true;}else link.removeAttribute('aria-current');});
    const sections=page.sections.map(section=>renderSection(page,section)).join('');
    const apiSection=page.classes.length?`<section id="api"><h2>API 参考</h2><p class="api-intro">签名来自当前源码。Qt 的通用继承接口请查阅 Qt 文档。</p>${page.classes.map(apiClass).join('')}</section>`:'';
    const order=groups.flatMap(group=>group.pages);const index=order.indexOf(page.id);const previous=pages.find(item=>item.id===order[index-1]);const next=pages.find(item=>item.id===order[index+1]);
    const footer=`<div class="page-footer"><span>FluentPy ${escape(version)} · <a href="assets/FluentPy-LICENSE.txt" target="_blank">MIT License</a></span><span>文档更新 ${sourceDate}</span></div>`;
    const pager=page.id==='introduction'||page.catalog?'':`<nav class="pager" aria-label="前后文档">${previous?`<a href="${route(previous.id)}"><small>← 上一页</small>${escape(previous.title)}</a>`:''}${next?`<a href="${route(next.id)}"><small>下一页 →</small>${escape(next.title)}</a>`:''}</nav>`;
    if(page.id==='introduction'){
      main.innerHTML=`<header class="home-head"><div class="home-title"><h1>FluentPy</h1><p>用于 Qt for Python 的 Fluent 风格桌面组件库。</p><div class="home-meta"><span>Python 3.10+</span><span>PySide6 / Qt 6</span><span>MIT License</span></div></div><div class="home-actions"><a class="button-link primary" href="${route('getting-started')}">快速开始</a><a class="button-link" href="${route('components')}">浏览组件</a></div></header>${introCover(page.cover)}<div class="home-facts"><div><h2>原生 Qt 组件</h2><p>控件、布局与信号由 Qt 驱动，保留常用的 Qt 使用方式。</p></div><div><h2>统一外观</h2><p>支持明暗主题、强调色与交互状态，按需组合到现有应用。</p></div><div><h2>C 可选加速</h2><p>已接入的后端优先使用 C，扩展不可用时自动回退 Python。</p></div></div><div id="examples-pane">${sections}</div>${footer}`;
    }else{
      const header=`<div class="breadcrumb"><a href="${route('introduction')}">文档</a><span>/</span><b>${escape(page.group)}</b></div><h1>${escape(page.title)}<span>${escape(page.english)}</span></h1><p class="lead">${escape(page.intro)}</p>`;
      const tabs=page.classes.length?`<div class="page-tabs" role="tablist" aria-label="文档内容"><a role="tab" aria-controls="examples-pane" aria-selected="true" data-view="examples" href="${route(page.id)}">示例与用法</a><a role="tab" aria-controls="reference-pane" aria-selected="false" data-view="api" href="${route(page.id,'api')}">API 参考</a></div>`:page.catalog?'':'<div style="height:28px"></div>';
      main.innerHTML=header+tabs+(page.catalog?catalogMarkup():`<div id="examples-pane"${page.classes.length?' role="tabpanel"':''}>${sections}</div>${apiSection?`<div id="reference-pane" role="tabpanel" hidden>${apiSection}</div>`:''}`)+footer+pager;
    }
    const nativeRoot=$('[data-native-flow]',main);if(nativeRoot&&window.FluentNativeFlow)nativeFlowCleanup=window.FluentNativeFlow.mount(nativeRoot);
    const migrationRoot=$('[data-api-migration]',main);if(migrationRoot&&window.FluentMigration)migrationCleanup=window.FluentMigration.mount(migrationRoot);
    if($('#icon-grid'))renderIcons();if($('#api-index-grid'))renderIndex();
    if(page.catalog){catalogCategory='all';renderCatalog();}
    closeMenu();updateDocumentView(page,anchor);
  }

  main.addEventListener('input',event=>{if(event.target.id==='catalog-filter')renderCatalog();});
  main.addEventListener('click',event=>{const button=event.target.closest('[data-catalog-group]');if(button){catalogCategory=button.dataset.catalogGroup;renderCatalog();}});
  main.addEventListener('keydown',event=>{if(event.target.matches('.page-tabs [role=tab]')&&['ArrowLeft','ArrowRight'].includes(event.key)){event.preventDefault();const tabs=$$('.page-tabs [role=tab]');const next=tabs[(tabs.indexOf(event.target)+1)%tabs.length];next.click();next.focus();}});
  main.addEventListener('toggle',event=>{if(event.target.matches('.motion-details')){const box=$('[data-animated-preview]',event.target);if(box)setPreviewPaused(box,!event.target.open||reducedMotion.matches||box.dataset.motionOverride==='pause');}},true);

  buildNavigation();setTheme(themePreference);render();
  window.addEventListener('hashchange',render);
})();
