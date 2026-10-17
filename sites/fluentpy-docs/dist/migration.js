(function () {
  'use strict';

  const escape = value => String(value).replace(/[&<>"']/g, character => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[character]));
  const pauseIcon = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M7 4v12M13 4v12"/></svg>';
  const playIcon = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m7 4 8 6-8 6Z"/></svg>';
  const replayIcon = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 8a6 6 0 1 1 .3 5M4 3v5h5"/></svg>';

  function labels() {
    return '<span class="mg-label" aria-hidden="true"><span data-mg-old>原生 Qt</span><span data-mg-new>FluentPy</span></span>';
  }

  function markup(config, version) {
    const image = key => 'assets/previews/' + escape(config[key]) + '?v=' + escape(version);
    return '<figure class="api-migration" data-api-migration data-mg-phase="qt" data-mg-running="false" aria-label="从原生 Qt 到 FluentPy 的输入框迁移动画">' +
      '<div class="mg-heading"><span>熟悉的写法，新的界面</span><span class="mg-status" data-mg-status>准备演示</span></div>' +
      '<div class="mg-columns"><div class="mg-panel mg-code-panel"><span class="mg-panel-title">PYTHON 代码</span>' + labels() +
        '<div class="mg-code-stage"><code data-mg-code role="img" aria-label="edit = QLineEdit(); edit.setText(把灵感写下来)"><span aria-hidden="true"><span class="mg-code-line">edit = <span class="mg-class" data-mg-class><span data-mg-old>' + escape(config.before) + '</span><span data-mg-new>' + escape(config.after) + '</span></span>()</span><span class="mg-code-line mg-code-setting">edit.setText(<span class="tok-string">"把灵感写下来"</span>)</span></span></code></div>' +
        '<span class="mg-panel-note">替换类名，沿用常用 API</span></div>' +
      '<div class="mg-panel mg-preview-panel"><span class="mg-panel-title">输入框外观</span>' + labels() +
        '<div class="mg-preview-stage"><div class="mg-control-images" role="img" data-mg-preview aria-label="原生 Qt 输入框，内容为把灵感写下来"><img src="' + image('beforeImage') + '" width="260" height="58" alt="" decoding="async"><div class="mg-new-control" data-mg-control><img src="' + image('afterImage') + '" width="260" height="58" alt="" decoding="async"><img class="mg-focus-image" data-mg-focus src="' + image('focusImage') + '" width="260" height="58" alt="" decoding="async"></div></div></div>' +
        '<span class="mg-panel-note" data-mg-preview-note>实际 Qt 控件 · 亮色截图</span></div></div>' +
      '<div class="mg-bottom"><div class="mg-shared"><span>常用方法与信号</span><code>setText()</code><code>setPlaceholderText()</code><code>textChanged</code></div>' +
        '<div class="mg-controls"><button type="button" data-mg-toggle aria-label="暂停迁移动画">' + pauseIcon + '<span>暂停</span></button><button type="button" data-mg-replay aria-label="重播迁移动画">' + replayIcon + '<span>重播</span></button></div></div>' +
      '<figcaption class="mg-caption">代码与输入框同步过渡，再展示焦点强调线 · 网页动画示意</figcaption></figure>';
  }

  function mount(root) {
    const find = selector => root.querySelector(selector);
    const oldLayers = [...root.querySelectorAll('[data-mg-old]')];
    const newLayers = [...root.querySelectorAll('[data-mg-new]')];
    const classSlot = find('[data-mg-class]');
    const before = classSlot.querySelector('[data-mg-old]').textContent;
    const after = classSlot.querySelector('[data-mg-new]').textContent;
    const code = find('[data-mg-code]');
    const preview = find('[data-mg-preview]');
    const control = find('[data-mg-control]');
    const focusImage = find('[data-mg-focus]');
    const previewNote = find('[data-mg-preview-note]');
    const toggleButton = find('[data-mg-toggle]');
    const replayButton = find('[data-mg-replay]');
    const status = find('[data-mg-status]');
    const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const duration = 7600;
    let elapsed = motion.matches ? 4100 : 0;
    let playing = !motion.matches;
    let visible = false;
    let ready = false;
    let destroyed = false;
    let frame = 0;
    let lastTime = null;
    let phase = '';
    const smooth = (time, start, end) => {
      const progress = Math.max(0, Math.min(1, (time - start) / (end - start)));
      return progress * progress * (3 - 2 * progress);
    };
    const canRun = () => !destroyed && playing && visible && ready && !document.hidden;

    function render(time) {
      const reversing = time >= 5900;
      const blend = reversing ? 1 - smooth(time, 5900, 6900) : smooth(time, 1500, 2500);
      const oldOpacity = reversing ? smooth(time, 6390, 6900) : 1 - smooth(time, 1500, 1940);
      const newOpacity = reversing ? 1 - smooth(time, 5900, 6340) : smooth(time, 1990, 2500);
      oldLayers.forEach(layer => { layer.style.opacity = String(oldOpacity); });
      newLayers.forEach(layer => { layer.style.opacity = String(newOpacity); });
      classSlot.style.width = (before.length + (after.length - before.length) * blend) + 'ch';
      // The opaque Qt frame stays underneath: the transition never fades to black.
      control.style.opacity = String(blend);
      const focus = smooth(time, 2850, 3450) * (1 - smooth(time, 5250, 5600));
      focusImage.style.clipPath = 'inset(0 ' + ((1 - focus) * 50) + '%)';
      root.dataset.mgFocus = focus === 0 ? 'idle' : focus === 1 ? 'focused' : 'transition';
      previewNote.textContent = focus > 0 ? 'FluentPy 焦点反馈 · 强调线展开' : '实际 Qt 控件 · 亮色截图';
      const nextPhase = blend === 0 ? 'qt' : blend === 1 ? 'fluent' : 'transition';
      if (nextPhase !== phase) {
        phase = nextPhase;
        root.dataset.mgPhase = phase;
        const fluent = blend >= 0.5;
        code.setAttribute('aria-label', 'edit = ' + (fluent ? after : before) + '(); edit.setText("把灵感写下来")');
        preview.setAttribute('aria-label', (fluent ? 'FluentPy' : '原生 Qt') + ' 输入框，内容为把灵感写下来');
      }
    }

    function controls() {
      root.dataset.mgRunning = String(canRun());
      toggleButton.innerHTML = (playing ? pauseIcon : playIcon) + '<span>' + (playing ? '暂停' : '播放') + '</span>';
      toggleButton.setAttribute('aria-label', playing ? '暂停迁移动画' : '播放迁移动画');
      status.textContent = !ready ? '载入控件截图…' : canRun() ? '同步演示中' : playing ? '已自动暂停' : motion.matches ? '静态示意' : '已暂停';
    }

    function tick(now) {
      frame = 0;
      if (!canRun()) { lastTime = null; return; }
      if (lastTime !== null) elapsed = (elapsed + Math.min(now - lastTime, 80)) % duration;
      lastTime = now;
      render(elapsed);
      frame = window.requestAnimationFrame(tick);
    }

    function sync() {
      if (destroyed) return;
      if (canRun()) {
        if (!frame) { lastTime = null; frame = window.requestAnimationFrame(tick); }
      } else {
        window.cancelAnimationFrame(frame);
        frame = 0;
        lastTime = null;
      }
      controls();
    }

    function toggle() { playing = !playing; sync(); }
    function replay() { elapsed = 0; lastTime = null; playing = true; render(elapsed); sync(); }
    function motionChanged() {
      if (motion.matches) { playing = false; elapsed = 4100; render(elapsed); }
      sync();
    }
    const observer = new IntersectionObserver(entries => { visible = entries[0].isIntersecting; sync(); });
    observer.observe(root);
    toggleButton.addEventListener('click', toggle);
    replayButton.addEventListener('click', replay);
    document.addEventListener('visibilitychange', sync);
    motion.addEventListener('change', motionChanged);
    render(elapsed);
    controls();
    // Decode every Qt state before starting so no transition reveals missing media.
    Promise.all([...root.querySelectorAll('img')].map(image => image.decode())).then(() => {
      if (destroyed) return;
      ready = true;
      sync();
    }).catch(() => {
      if (destroyed) return;
      playing = false;
      sync();
      status.textContent = '控件截图未能加载，请刷新重试';
    });

    return function () {
      destroyed = true;
      window.cancelAnimationFrame(frame);
      observer.disconnect();
      toggleButton.removeEventListener('click', toggle);
      replayButton.removeEventListener('click', replay);
      document.removeEventListener('visibilitychange', sync);
      motion.removeEventListener('change', motionChanged);
    };
  }

  window.FluentMigration = {markup, mount};
})();
