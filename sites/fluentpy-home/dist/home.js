(() => {
  'use strict';
  // Preserve links to the documentation's previous root-level hash routes.
  function redirectLegacyHash() {
    if (!location.hash.startsWith('#/')) return false;
    location.replace(new URL(`docs/${location.hash}`, document.baseURI));
    return true;
  }
  if (redirectLegacyHash()) return;
  addEventListener('hashchange', redirectLegacyHash);
  const root = document.documentElement;
  const assetVersion = new URL(document.currentScript.src).searchParams.get('v') || 'source';
  const scenes = {
    buttons: {
      image: 'assets/buttons.png',
      width: 460,
      height: 138,
      caption: '基础按钮、切换状态与下拉操作，沿用熟悉的 Qt 信号。',
      alt: 'FluentPy 按钮与操作控件的真实 Qt 截图',
    },
    tables: {
      image: 'assets/tables.png',
      width: 1000,
      height: 760,
      caption: '连接 Qt 模型，编辑、排序、筛选和多选复制。',
      alt: 'FluentPy 表格与数据操作的真实 Qt 截图',
    },
    window: {
      image: 'assets/window.png',
      width: 1040,
      height: 720,
      caption: '使用导航、标题栏和页面历史，组合自己的桌面应用。',
      alt: 'FluentPy 窗口和页面导航的真实 Qt 截图',
    },
    editor: {
      image: 'assets/editor.png',
      width: 760,
      height: 540,
      caption: '保留原生文本编辑接口，提供行号、缩进辅助线和语法着色。',
      alt: 'FluentPy 代码编辑器的真实 Qt 截图',
    },
  };
  function syncTheme() {
    const dark = root.dataset.theme === 'dark';
    document.querySelector('#hero-image').src =
      `assets/workbench-${dark ? 'dark' : 'light'}.png?v=${assetVersion}`;
    document
      .querySelector('#theme')
      .setAttribute('aria-label', dark ? '切换到浅色主题' : '切换到深色主题');
    document.querySelector('meta[name="theme-color"]').content = dark ? '#151c26' : '#f7f9fc';
  }
  document.querySelector('#theme').addEventListener('click', () => {
    root.dataset.theme = root.dataset.theme === 'dark' ? 'light' : 'dark';
    try {
      localStorage.setItem('fluentpy-home-theme', root.dataset.theme);
    } catch {}
    syncTheme();
  });
  syncTheme();
  for (const button of document.querySelectorAll('[data-preview]')) {
    button.addEventListener('click', () => {
      const scene = scenes[button.dataset.preview];
      for (const other of document.querySelectorAll('[data-preview]')) {
        const selected = other === button;
        other.classList.toggle('active', selected);
        other.setAttribute('aria-pressed', String(selected));
      }
      const image = document.querySelector('#preview-image');
      image.width = scene.width;
      image.height = scene.height;
      image.src = `${scene.image}?v=${assetVersion}`;
      image.alt = scene.alt;
      document.querySelector('#preview-caption').textContent = scene.caption;
    });
  }
  let timer;
  document.querySelector('#copy').addEventListener('click', async () => {
    const command = document.querySelector('#install-command').textContent;
    const status = document.querySelector('#status');
    try {
      await navigator.clipboard.writeText(command);
      status.textContent = '安装命令已复制';
    } catch {
      const selection = getSelection();
      const range = document.createRange();
      range.selectNodeContents(document.querySelector('#install-command'));
      selection.removeAllRanges();
      selection.addRange(range);
      status.textContent = '已选中安装命令，可使用 Ctrl+C 复制';
    }
    status.classList.add('visible');
    clearTimeout(timer);
    timer = setTimeout(() => status.classList.remove('visible'), 2200);
  });
})();
