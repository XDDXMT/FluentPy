(function () {
  'use strict';

  const scenes = {
    json: {
      eyebrow: 'JSON HIGHLIGHTING',
      inputTitle: '一份 JSON 文本',
      inputNote: 'Python 接收内容，调用扩展接口。',
      input: '<span>{</span><span>  "name": "FluentPy",</span><span>  "items": 10000,</span><span>  "ready": true</span><span>}</span>',
      coreTitle: '扫描与分类',
      coreNote: 'C 识别文本片段，返回位置与类型。',
      coreTags: ['字符串', '数字', '关键字'],
      outputTitle: 'Qt 绘制高亮',
      outputNote: 'Qt 使用计算结果，为文字着色。',
      output: '<div class="nf-code nf-code-result"><span>{</span><span>  <b class="nf-key">"name"</b>: <b class="nf-string">"FluentPy"</b>,</span><span>  <b class="nf-key">"items"</b>: <b class="nf-number">10000</b>,</span><span>  <b class="nf-key">"ready"</b>: <b class="nf-keyword">true</b></span><span>}</span></div>',
      explanations: [
        ['01 · 接收文本', '仍然使用熟悉的 Python 接口。把需要处理的文本交给 C 扩展。'],
        ['02 · 进入 C 扩展', '调用跨过语言边界，文本进入已经接入的 C 计算路径。'],
        ['03 · 集中完成计算', 'C 扫描字符并标记字符串、数字和关键字的位置。'],
        ['04 · 返回轻量结果', '只把位置与类型交还给 Python，再传给 Qt 控件。'],
        ['05 · 呈现到界面', 'Qt 根据结果绘制语法颜色。界面交互与绘制仍由 Qt 负责。']
      ],
      evidence: '<span class="nf-proof-label">本机历史实测 · 万行 JSON 扫描</span><span class="nf-proof-values"><span>原始版本 <b>25.28 ms</b></span><span class="nf-proof-arrow" aria-hidden="true">→</span><span>C <b>1.91 ms</b></span><strong>13.21×</strong></span>',
      evidenceNote: '仅为原始版本与 C 扫描路径的历史对照，不代表整个组件库的提速倍数。'
    },
    date: {
      eyebrow: 'DATE CALCULATION',
      inputTitle: '一次日期选择',
      inputNote: 'Python 接收选择的年、月与日。',
      input: '<span>year  = 2028</span><span>month = 2</span><span>day   = 29</span><span class="nf-code-comment"># 交给日期计算接口</span>',
      coreTitle: '日期规则计算',
      coreNote: 'C 处理闰年、天数与日期边界。',
      coreTags: ['闰年判断', '月份天数', '边界校验'],
      outputTitle: 'Qt 更新日期',
      outputNote: '有效日期返回，控件更新选择。',
      output: '<div class="nf-calendar"><div class="nf-calendar-title"><span>2028 年 2 月</span><span class="nf-calendar-ok">有效日期</span></div><div class="nf-calendar-grid" aria-hidden="true"><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span><span>日</span><span>21</span><span>22</span><span>23</span><span>24</span><span>25</span><span>26</span><span>27</span><span>28</span><span class="nf-calendar-selected">29</span><span class="nf-calendar-dim">1</span><span class="nf-calendar-dim">2</span><span class="nf-calendar-dim">3</span><span class="nf-calendar-dim">4</span><span class="nf-calendar-dim">5</span></div></div>',
      explanations: [
        ['01 · 接收选择', '日期控件接收 2028 年 2 月 29 日，Python 调用计算接口。'],
        ['02 · 进入 C 扩展', '年、月、日交给 C；Python 的公开使用方式保持一致。'],
        ['03 · 检查日期规则', '判断闰年、计算月份天数，并校验日期是否在有效范围内。'],
        ['04 · 返回有效日期', '计算结果回到 Python，供日期控件使用。'],
        ['05 · 更新选择状态', 'Qt 呈现合法的 2 月 29 日。弹层、动画和交互仍由 Qt 负责。']
      ],
      evidence: '<span class="nf-proof-label">日期计算路径</span><span class="nf-proof-values nf-proof-rules"><span>闰年规则</span><span class="nf-proof-arrow" aria-hidden="true">→</span><span>月份天数</span><span class="nf-proof-arrow" aria-hidden="true">→</span><span>有效日期</span></span>',
      evidenceNote: '这里展示职责与数据流，未对日期计算给出性能倍数。'
    }
  };

  const playIcon = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="m7 4 8 6-8 6Z"/></svg>';
  const pauseIcon = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M7 4v12M13 4v12"/></svg>';
  const replayIcon = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M4 8a6 6 0 1 1 .3 5M4 3v5h5"/></svg>';

  function connection(direction) {
    return '<div class="nf-connection" data-nf-connection="' + direction + '" aria-hidden="true"><svg viewBox="0 0 56 30"><path class="nf-wire" d="M0 15h56"/><path class="nf-wire-arrow" d="m26 11 4 4-4 4"/><circle class="nf-particle" r="3" cx="0" cy="15"/><circle class="nf-particle nf-particle-small" r="1.7" cx="0" cy="15"/></svg></div>';
  }

  function markup() {
    const scene = scenes.json;
    return '<section class="native-flow" data-native-flow data-nf-step="4" data-nf-running="false" aria-label="C 扩展工作原理动画">' +
      '<div class="nf-heading"><div><span class="nf-eyebrow">PYTHON + C + QT</span><h2>计算交给 C，界面交给 Qt</h2><p>一个熟悉的调用，经过更高效的计算路径。</p></div><span class="nf-live"><i aria-hidden="true"></i><span data-nf-status>原理示意</span></span></div>' +
      '<div class="nf-toolbar"><div class="nf-scenes" role="group" aria-label="选择演示内容"><button type="button" data-nf-scene="json" aria-pressed="true">JSON 高亮</button><button type="button" data-nf-scene="date" aria-pressed="false">日期计算</button></div><span class="nf-scene-code" data-nf-eyebrow>' + scene.eyebrow + '</span></div>' +
      '<div class="nf-visual" aria-label="Python 调用，C 核心计算，Qt 展示">' +
        '<div class="nf-node nf-input"><div class="nf-node-header"><span class="nf-language nf-language-python">Py</span><div><span class="nf-node-order">01 / INPUT</span><h3 data-nf-input-title>' + scene.inputTitle + '</h3></div></div><div class="nf-code nf-code-input" data-nf-input>' + scene.input + '</div><p data-nf-input-note>' + scene.inputNote + '</p></div>' +
        connection('in') +
        '<div class="nf-node nf-core"><div class="nf-node-header"><span class="nf-language nf-language-c">C</span><div><span class="nf-node-order">02 / NATIVE CORE</span><h3 data-nf-core-title>' + scene.coreTitle + '</h3></div></div><div class="nf-chip-area" aria-hidden="true"><div class="nf-chip-traces nf-chip-traces-left"></div><div class="nf-chip"><span class="nf-chip-ring"></span><span class="nf-chip-letter">C</span><span class="nf-chip-detail">NATIVE</span><span class="nf-chip-scan"></span></div><div class="nf-chip-traces nf-chip-traces-right"></div></div><div class="nf-core-tags" data-nf-tags>' + scene.coreTags.map(function (tag) { return '<span>' + tag + '</span>'; }).join('') + '</div><p data-nf-core-note>' + scene.coreNote + '</p></div>' +
        connection('out') +
        '<div class="nf-node nf-output"><div class="nf-node-header"><span class="nf-language nf-language-qt">Qt</span><div><span class="nf-node-order">03 / RENDER</span><h3 data-nf-output-title>' + scene.outputTitle + '</h3></div></div><div class="nf-output-preview" data-nf-output>' + scene.output + '</div><p data-nf-output-note>' + scene.outputNote + '</p></div>' +
      '</div>' +
      '<div class="nf-explanation"><span class="nf-explanation-step" data-nf-explanation-step>05 · 呈现到界面</span><p data-nf-explanation>' + scene.explanations[4][1] + '</p><div class="nf-progress" aria-hidden="true"><span data-nf-progress></span></div></div>' +
      '<div class="nf-bottom"><div class="nf-controls"><button type="button" data-nf-toggle>' + playIcon + '<span>播放动画</span></button><button type="button" data-nf-replay>' + replayIcon + '<span>重新演示</span></button></div><span class="nf-disclaimer">流程动画 · 非实时测速</span></div>' +
      '<div class="nf-evidence"><div data-nf-evidence>' + scene.evidence + '</div><p data-nf-evidence-note>' + scene.evidenceNote + '</p></div>' +
      '<p class="nf-boundary">C 扩展负责已接入的后端计算；Python 保留组件接口，Qt 负责界面与交互。</p>' +
    '</section>';
  }

  function mount(root) {
    if (!root || !root.matches('[data-native-flow]')) return function () {};

    const find = function (selector) { return root.querySelector(selector); };
    const nodes = {
      status: find('[data-nf-status]'),
      eyebrow: find('[data-nf-eyebrow]'),
      input: find('[data-nf-input]'),
      inputTitle: find('[data-nf-input-title]'),
      inputNote: find('[data-nf-input-note]'),
      coreTitle: find('[data-nf-core-title]'),
      coreNote: find('[data-nf-core-note]'),
      tags: find('[data-nf-tags]'),
      output: find('[data-nf-output]'),
      outputTitle: find('[data-nf-output-title]'),
      outputNote: find('[data-nf-output-note]'),
      step: find('[data-nf-explanation-step]'),
      explanation: find('[data-nf-explanation]'),
      progress: find('[data-nf-progress]'),
      toggle: find('[data-nf-toggle]'),
      replay: find('[data-nf-replay]'),
      evidence: find('[data-nf-evidence]'),
      evidenceNote: find('[data-nf-evidence-note]'),
      chip: find('.nf-chip'),
      scan: find('.nf-chip-scan'),
      ring: find('.nf-chip-ring'),
      particlesIn: Array.from(root.querySelectorAll('[data-nf-connection="in"] circle')),
      particlesOut: Array.from(root.querySelectorAll('[data-nf-connection="out"] circle')),
      sceneButtons: Array.from(root.querySelectorAll('[data-nf-scene]'))
    };
    const motionQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const duration = 9000;
    const boundaries = [0, 1550, 2300, 5350, 6100];
    let sceneKey = 'json';
    let elapsed = motionQuery.matches ? 7600 : 0;
    let userPlaying = !motionQuery.matches;
    let visible = true;
    let destroyed = false;
    let frame = 0;
    let lastTime = 0;
    let previousStep = -1;
    let observer = null;
    let previousRunning = null;

    function canRun() {
      return !destroyed && userPlaying && visible && !document.hidden;
    }

    function updateControls() {
      const running = canRun();
      root.dataset.nfRunning = String(running);
      nodes.toggle.innerHTML = (userPlaying ? pauseIcon : playIcon) + '<span>' + (userPlaying ? '暂停动画' : '播放动画') + '</span>';
      nodes.toggle.setAttribute('aria-label', userPlaying ? '暂停动画' : '播放动画');
      nodes.status.textContent = running ? '正在演示' : (userPlaying ? '已自动暂停' : (motionQuery.matches ? '静态示意' : '已暂停'));
      previousRunning = running;
    }

    function drawParticles(particles, progress, active) {
      particles.forEach(function (particle, index) {
        const offset = (progress * 2.3 - index * 0.31) % 1;
        particle.setAttribute('cx', String(Math.max(0, offset) * 56));
        particle.style.opacity = active && offset >= 0 ? String(Math.sin(offset * Math.PI) * (index ? 0.55 : 1)) : '0';
      });
    }

    function render(time) {
      const scene = scenes[sceneKey];
      let step = 0;
      boundaries.forEach(function (boundary, index) { if (time >= boundary) step = index; });
      if (step !== previousStep) {
        root.dataset.nfStep = String(step);
        nodes.step.textContent = scene.explanations[step][0];
        nodes.explanation.textContent = scene.explanations[step][1];
        previousStep = step;
      }

      nodes.progress.style.transform = 'scaleX(' + Math.min(time / 7900, 1) + ')';
      const scanProgress = Math.max(0, Math.min((time - 2300) / 3050, 1));
      const processing = step === 2;
      const wave = Math.sin(scanProgress * Math.PI * 7);
      nodes.chip.style.setProperty('--nf-chip-energy', processing ? String(0.34 + Math.abs(wave) * 0.46) : '0.12');
      nodes.scan.style.transform = 'translateY(' + (scanProgress * 64 - 32) + 'px)';
      nodes.scan.style.opacity = processing ? '0.8' : '0';
      nodes.ring.style.transform = 'scale(' + (processing ? 1 + Math.abs(wave) * 0.12 : 1) + ')';
      nodes.ring.style.opacity = processing ? String(0.15 + Math.abs(wave) * 0.35) : '0.14';
      drawParticles(nodes.particlesIn, (time - 1550) / 750, step === 1);
      drawParticles(nodes.particlesOut, (time - 5350) / 750, step === 3);

      const inputLines = nodes.input.children;
      const scanIndex = Math.floor((time / 1550) * inputLines.length);
      Array.from(inputLines).forEach(function (line, index) {
        line.classList.toggle('nf-line-active', step === 0 && index === Math.min(scanIndex, inputLines.length - 1));
      });
      Array.from(nodes.tags.children).forEach(function (tag, index) {
        tag.classList.toggle('nf-tag-active', processing && Math.floor(scanProgress * 9) % 3 === index);
      });

      const outputProgress = Math.max(0, Math.min((time - 6100) / 1100, 1));
      nodes.output.style.setProperty('--nf-output-progress', String(outputProgress));
      nodes.output.style.setProperty('--nf-output-sweep', String(outputProgress * 100) + '%');
    }

    function tick(now) {
      frame = 0;
      if (!canRun()) { lastTime = 0; return; }
      if (lastTime) elapsed = (elapsed + Math.min(now - lastTime, 80)) % duration;
      lastTime = now;
      render(elapsed);
      frame = window.requestAnimationFrame(tick);
    }

    function sync() {
      if (canRun()) {
        if (!frame) {
          lastTime = 0;
          frame = window.requestAnimationFrame(tick);
        }
      } else {
        if (frame) window.cancelAnimationFrame(frame);
        frame = 0;
        lastTime = 0;
      }
      if (previousRunning !== canRun()) updateControls();
    }

    function toggle() {
      userPlaying = !userPlaying;
      root.dataset.nfManualMotion = String(userPlaying);
      updateControls();
      sync();
    }

    function replay() {
      elapsed = 0;
      previousStep = -1;
      userPlaying = true;
      root.dataset.nfManualMotion = 'true';
      render(elapsed);
      updateControls();
      sync();
    }

    function selectScene(event) {
      const key = event.currentTarget.dataset.nfScene;
      if (key === sceneKey) return;
      sceneKey = key;
      const scene = scenes[key];
      nodes.eyebrow.textContent = scene.eyebrow;
      nodes.inputTitle.textContent = scene.inputTitle;
      nodes.inputNote.textContent = scene.inputNote;
      nodes.input.innerHTML = scene.input;
      nodes.coreTitle.textContent = scene.coreTitle;
      nodes.coreNote.textContent = scene.coreNote;
      nodes.tags.innerHTML = scene.coreTags.map(function (tag) { return '<span>' + tag + '</span>'; }).join('');
      nodes.outputTitle.textContent = scene.outputTitle;
      nodes.outputNote.textContent = scene.outputNote;
      nodes.output.innerHTML = scene.output;
      nodes.evidence.innerHTML = scene.evidence;
      nodes.evidenceNote.textContent = scene.evidenceNote;
      nodes.sceneButtons.forEach(function (button) { button.setAttribute('aria-pressed', String(button.dataset.nfScene === key)); });
      elapsed = userPlaying ? 0 : 7600;
      previousStep = -1;
      render(elapsed);
      sync();
    }

    function visibilityChanged() { sync(); }
    function motionChanged() {
      if (motionQuery.matches) {
        userPlaying = false;
        elapsed = 7600;
        previousStep = -1;
        render(elapsed);
        updateControls();
        sync();
      }
    }

    nodes.toggle.addEventListener('click', toggle);
    nodes.replay.addEventListener('click', replay);
    nodes.sceneButtons.forEach(function (button) { button.addEventListener('click', selectScene); });
    document.addEventListener('visibilitychange', visibilityChanged);
    if (motionQuery.addEventListener) motionQuery.addEventListener('change', motionChanged);

    if ('IntersectionObserver' in window) {
      visible = false;
      observer = new IntersectionObserver(function (entries) {
        if (destroyed) return;
        visible = entries[0].isIntersecting;
        sync();
      }, { threshold: 0 });
      observer.observe(root);
    }

    render(elapsed);
    updateControls();
    sync();

    return function cleanup() {
      destroyed = true;
      if (frame) window.cancelAnimationFrame(frame);
      if (observer) observer.disconnect();
      nodes.toggle.removeEventListener('click', toggle);
      nodes.replay.removeEventListener('click', replay);
      nodes.sceneButtons.forEach(function (button) { button.removeEventListener('click', selectScene); });
      document.removeEventListener('visibilitychange', visibilityChanged);
      if (motionQuery.removeEventListener) motionQuery.removeEventListener('change', motionChanged);
    };
  }

  window.FluentNativeFlow = Object.freeze({ markup: markup, mount: mount });
}());
