(() => {
  'use strict';

  const platforms = [
    { id: 'windows', name: 'Windows', runtime: 'Windows x64' },
    { id: 'linux', name: 'Linux', runtime: 'Ubuntu x64 · X11' },
    { id: 'macos', name: 'macOS', runtime: 'macOS · Apple Silicon' },
  ];

  function markup(assetPath, version) {
    const nodes = platforms.map(({ name }) => `<li>${name}</li>`).join('');
    const examples = platforms
      .map(({ id, name, runtime }) => {
        const screenshots = ['light', 'dark']
          .map((mode) => {
            const src = `${assetPath}/platform-${id}-${mode}.png?v=${encodeURIComponent(version)}`;
            const theme = mode === 'light' ? '浅色' : '深色';
            return `<a class="platform-capture platform-capture-${mode}" href="${src}" target="_blank" rel="noopener">
          <img src="${src}" width="1120" height="780" loading="lazy" decoding="async"
            alt="FluentPy 工作台在 ${runtime} 上的${theme}运行截图">
        </a>`;
          })
          .join('');
        return `<details class="platform-example" name="fluent-platform-example">
        <summary><strong>${name} 运行示例</strong><span>${runtime}</span></summary>
        <figure>${screenshots}<figcaption>0.8.1 工作台 · 点击截图查看原尺寸</figcaption></figure>
      </details>`;
      })
      .join('');

    return `<div class="platform-showcase">
      <div class="platform-diagram" role="img" aria-label="FluentPy 通过 Qt 在 Windows、Linux 和 macOS 上运行">
        <div class="platform-origin"><strong>FluentPy</strong><span>同一套 Qt 控件 API</span></div>
        <ul class="platform-branches">${nodes}</ul>
      </div>
      <div class="platform-examples">${examples}</div>
      <p class="platform-source"><a href="https://github.com/XDDXMT/FluentPy/actions/runs/45631276069">
        查看各平台的截图与构建记录
      </a></p>
    </div>`;
  }

  window.FluentPlatformShowcase = { markup };
  const home = document.querySelector('[data-platform-showcase]');
  if (home) {
    const version = new URL(document.currentScript.src).searchParams.get('v') || 'source';
    home.innerHTML = markup('docs/assets/previews', version);
  }
})();
