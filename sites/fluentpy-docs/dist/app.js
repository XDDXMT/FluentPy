(() => {
  'use strict';
  const {pages, groups, api, icons, sourceDate, previewVersion, animatedPreviews={}} = window.DOCS_DATA;
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
      const paused=reducedMotion.matches;
      return `<figure class="preview-box animation-preview" data-animated-preview="${escape(type)}" data-animation="${escape(animation)}" data-poster="${escape(poster)}" data-paused="${paused}"><div class="preview-stage preview-animation"><img class="qt-shot" src="${escape(paused?poster:animation)}" width="${item.width}" height="${item.height}" alt="${escape(item.alt)}" loading="lazy"></div><figcaption class="preview-caption"><span>Qt 控件实录 · 亮色 GIF</span><div class="animation-controls"><button type="button" data-preview-toggle>${paused?'播放动画':'暂停动画'}</button><a href="${escape(animation)}" target="_blank" rel="noopener">查看动图 ↗</a></div></figcaption></figure>`;
    }
    return `<div class="preview-box"><div class="preview-stage${type==='code-editor'?' preview-code':''}"><img class="qt-shot" src="assets/previews/${escape(type)}-light.png?v=${previewVersion}" alt="${escape(type)} Qt 控件亮色截图" loading="lazy"></div><div class="preview-caption"><span>Qt 控件亮色截图${type==='code-editor'?' · 可横向滚动':''}</span>${type==='code-editor'?`<a href="assets/previews/code-editor-light.png?v=${previewVersion}" target="_blank" rel="noopener">查看原图 ↗</a>`:'<span>FLUENTPY · PYSIDE6</span>'}</div></div>`;
  }
  function apiClass(name){
    const item=api[name];if(!item)return '';
    const methods=item.methods.map(method=>`<div class="method" id="api-${escape(name)}-${escape(method.name)}"><div class="signature">${escape(method.signature)}</div>${method.description?`<p>${escape(method.description)}</p>`:''}</div>`).join('');
    const signals=item.signals.length?`<div class="api-signals">信号 ${item.signals.map(signal=>`<code>${escape(signal.name)}</code>`).join(' ')}</div>`:'';
    return `<div class="api-class" id="api-${escape(name)}"><div class="api-class-head"><strong>${escape(name)}</strong><span class="api-base">${escape(item.alias?'alias → '+item.alias:item.base||'')}</span></div><p class="api-description">${escape(item.description)}</p>${methods||`<div class="api-empty">${item.alias?'导出别名，与 '+escape(item.alias)+' 使用同一实现。':item.base?'构造与基础接口继承自 '+escape(item.base)+'。':'此项为公开数据或枚举入口。'}</div>`}${signals}</div>`;
  }
  function buildNavigation(){
    $('#navigation').innerHTML=groups.map(group=>`<div class="nav-group"><div class="nav-group-title">${escape(group.name)}<span>⌄</span></div>${group.pages.map(id=>{const page=pages.find(p=>p.id===id);return `<a class="nav-link" href="${route(id)}" data-page="${id}">${escape(page.title)}${id==='code-editor'?'<span class="new">NEW</span>':''}</a>`}).join('')}</div>`).join('');
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
  function introCover(cover){
    if(!cover)return '';
    const tags=`<div class="intro-tags">${cover.tags.map(tag=>`<span>${escape(tag)}</span>`).join('')}</div>`;
    const source=`assets/previews/${escape(cover.image)}-light.png?v=${previewVersion}`;
    return `${tags}<figure class="intro-cover"><div class="intro-cover-top"><span>FLUENTPY · 组件组合示例</span><a href="${source}" target="_blank" rel="noopener">查看大图 ↗</a></div><img src="${source}" width="${cover.width||920}" height="${cover.height||400}" alt="FluentPy 示例工作台，包含侧栏导航、应用卡片和分组设置"><figcaption>${escape(cover.caption)}</figcaption></figure>`;
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
    const migration=section.migration?`<div class="migration-visual" aria-label="QPushButton 到 FluentPy Button 的常用 API 对照"><div class="migration-panel"><span class="migration-label">原生 Qt</span><code>button = <strong>${escape(section.migration.before)}</strong>(<span class="tok-string">"保存"</span>)</code></div><span class="migration-arrow" aria-hidden="true">→</span><div class="migration-panel migration-after"><span class="migration-label">FluentPy</span><code>button = <strong>${escape(section.migration.after)}</strong>(<span class="tok-string">"保存"</span>)</code></div><div class="migration-shared"><span>沿用常用方法与信号</span><code>setText()</code><code>setEnabled()</code><code>clicked</code></div></div>`:'';
    const steps=section.steps?`<div class="intro-steps">${section.steps.map((step,index)=>`<a class="intro-step" href="${route(step.page)}"><span class="intro-step-number">${index+1}</span><h3>${escape(step.title)}</h3><p>${escape(step.text)}</p><span class="intro-step-link">${escape(step.label)} →</span></a>`).join('')}</div>`:'';
    const callout=section.callout?`<aside class="license-callout" aria-label="${escape(section.callout.title)} 许可说明"><h3><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v6m0-10v1"/></svg>${escape(section.callout.title)}</h3><p>${escape(section.callout.text)}</p></aside>`:'';
    return paragraphs+nativeFlow+architecture+items+metrics+table+gallery+migration+steps+links+callout;
  }
  function render(){
    const parts=location.hash.replace(/^#\/?/,'').split('/');
    let page=pages.find(p=>p.id===parts[0]);
    if(!page){page=pages.find(p=>p.id==='inputs');history.replaceState(null,'',route(page.id));}
    const anchor=parts[1];
    if(currentPage===page.id){closeMenu();if(anchor)document.getElementById(anchor)?.scrollIntoView({behavior:reducedMotion.matches?'auto':'smooth'});else window.scrollTo({top:0});return;}
    nativeFlowCleanup?.();nativeFlowCleanup=null;
    observer?.disconnect();codeSnippets=[];currentPage=page.id;
    document.title=`${page.title} · FluentPy 文档`;
    $$('.nav-link').forEach(link=>{link.classList.toggle('active',link.dataset.page===page.id);if(link.dataset.page===page.id)link.setAttribute('aria-current','page');else link.removeAttribute('aria-current');});
    const sections=page.sections.map(s=>`<section id="${s.id}"${s.callout?' class="license-section"':''}><h2>${escape(s.title)}<a class="anchor" href="${route(page.id,s.id)}" aria-label="链接到 ${escape(s.title)}">#</a>${page.id==='code-editor'&&s.id==='codeedit'?'<span class="new-badge">本地开发新增</span>':''}</h2><p>${escape(s.text)}</p>${sectionContent(s)}${s.preview?preview(s.preview):''}${s.code?codeBlock(s.code,s.language):''}${s.note?`<div class="note">${escape(s.note)}</div>`:''}</section>`).join('');
    const apiSection=page.classes.length?`<section class="api-section" id="api"><h2>接口参考 <span class="class-tag">API</span><a class="anchor" href="${route(page.id,'api')}" aria-label="链接到接口参考">#</a></h2><p class="api-intro">以下签名来自当前本地源码。继承自 Qt 的通用方法未逐项展开。</p>${page.classes.map(apiClass).join('')}</section>`:'';
    const order=groups.flatMap(g=>g.pages);const idx=order.indexOf(page.id);const previous=pages.find(p=>p.id===order[idx-1]);const next=pages.find(p=>p.id===order[idx+1]);
    main.innerHTML=`<div class="breadcrumb"><span>文档</span><span>›</span><b>${escape(page.group)}</b></div><h1>${escape(page.title)}<span>${escape(page.english)}</span></h1><p class="lead">${escape(page.intro)}</p>${introCover(page.cover)}<div class="page-tabs"><a href="${route(page.id,page.sections[0].id)}">${page.id==='introduction'?'项目概览':'预览与用法'}</a>${page.classes.length?`<a href="${route(page.id,'api')}">接口参考</a>`:''}</div>${sections}${apiSection}<div class="page-footer"><span>FluentPy · 独立实现 · <a href="assets/FluentPy-LICENSE.txt" target="_blank">MIT 许可</a></span><span>源码接口快照 · ${sourceDate}</span></div><nav class="pager" aria-label="前后文档">${previous?`<a href="${route(previous.id)}"><small>← 上一页</small>${escape(previous.title)}</a>`:''}${next?`<a href="${route(next.id)}"><small>下一页 →</small>${escape(next.title)}</a>`:''}</nav>`;
    const nativeRoot=$('[data-native-flow]',main);
    if(nativeRoot&&window.FluentNativeFlow)nativeFlowCleanup=window.FluentNativeFlow.mount(nativeRoot);
    const tocEntries=[...page.sections.map(s=>({id:s.id,title:s.title})),...(page.classes.length?[{id:'api',title:'接口参考'}]:[])];
    $('#toc').innerHTML=tocEntries.map(entry=>`<a href="${route(page.id,entry.id)}" data-anchor="${entry.id}">${escape(entry.title)}</a>`).join('');
    observer=new IntersectionObserver(entries=>{const visible=entries.filter(e=>e.isIntersecting).sort((a,b)=>a.boundingClientRect.top-b.boundingClientRect.top);if(visible.length)$$('#toc a').forEach(a=>a.classList.toggle('active',a.dataset.anchor===visible[0].target.id));},{rootMargin:'-85px 0px -65% 0px',threshold:0});
    $$('main section[id]').forEach(section=>observer.observe(section));
    if($('#icon-grid'))renderIcons();
    if($('#api-index-grid'))renderIndex();
    closeMenu();
    requestAnimationFrame(()=>{if(anchor)document.getElementById(anchor)?.scrollIntoView();else window.scrollTo({top:0,behavior:'instant'});});
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
    for(const name of page.classes){
      const item=api[name];if(!item)continue;
      searchEntries.push({title:name,detail:page.title+' · '+item.description,url:route(page.id,'api-'+name),haystack:name+' '+item.description});
      for(const method of item.methods){if(method.name==='__init__')continue;searchEntries.push({title:`${name}.${method.name}`,detail:page.title+' · '+method.description,url:route(page.id,'api-'+name+'-'+method.name),haystack:name+' '+method.name+' '+method.description});}
    }
  }
  function search(){
    const query=$('#search-input').value.trim().toLowerCase();searchIndex=0;
    const results=query?searchEntries.filter(entry=>entry.haystack.toLowerCase().includes(query)).slice(0,18):searchEntries.filter(entry=>!entry.title.includes('.')).slice(0,8);
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
  buildNavigation();setTheme(themePreference);render();
  window.addEventListener('hashchange',render);
})();
