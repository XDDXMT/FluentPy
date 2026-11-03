/* The icon browser is independent of the docs router and never changes SVGs. */
((scope) => {
  'use strict';

  const PAGE_SIZE = 96;
  const escape = (value) =>
    String(value).replace(
      /[&<>"']/g,
      (char) =>
        ({
          '&': '&amp;',
          '<': '&lt;',
          '>': '&gt;',
          '"': '&quot;',
          "'": '&#39;',
        })[char],
    );

  function terms(query) {
    return String(query)
      .normalize('NFKC')
      .toLowerCase()
      .replace(/^fluenticon[.\s:]+/, '')
      .split(/[\s_.\-]+/)
      .filter(Boolean);
  }

  function selectIcons(icons, { category = 'all', query = '', localized = false } = {}) {
    const words = terms(query);
    return icons.filter((icon) => {
      if (!localized && icon.localized) return false;
      if (category !== 'all' && icon.category !== category) return false;
      const haystack = `${icon.name.replaceAll('_', ' ')} ${icon.keywords || ''}`.toLowerCase();
      return words.every((word) => haystack.includes(word));
    });
  }

  function mount(host, { icons, categories, state = {} }) {
    const valid = new Set(categories.map((category) => category.id));
    state.category = valid.has(state.category) ? state.category : 'all';
    state.query = typeof state.query === 'string' ? state.query : '';
    state.localized = Boolean(state.localized);
    state.limit = PAGE_SIZE;
    const localizedCount = icons.filter((icon) => icon.localized).length;
    let frame;
    let shown = 0;
    host.classList.add('icon-browser');
    host.innerHTML = `
      <div class="icon-browser-controls">
        <div class="icon-browser-fields">
          <label class="icon-category-field">用途分类
            <select id="icon-category" aria-label="图标分类"></select>
          </label>
          <label class="icon-query-field">搜索图标
            <input type="search" id="icon-filter" placeholder="音量、文件、speaker…" autocomplete="off">
          </label>
        </div>
        <div class="icon-browser-options">
          <label class="icon-locale-option"><input id="icon-localized" type="checkbox">包含其他语言版本 <span>(${localizedCount})</span></label>
          <button type="button" class="icon-reset" id="icon-reset">清除筛选</button>
        </div>
      </div>
      <div class="icon-browser-summary"><strong id="icon-category-name"></strong><span id="icon-result-count" role="status" aria-live="polite" aria-atomic="true"></span></div>
      <div class="icon-grid" id="icon-grid" aria-label="图标结果"></div>
      <div class="icon-pagination"><span id="icon-shown-count"></span><button type="button" id="icon-more">显示更多图标</button></div>
      <p class="icon-browser-help">点击图标复制 FluentIcon 名称。可在分类内继续搜索；其他语言版本包含不同语言的加粗、斜体等文字样式。</p>`;

    const find = (selector) => host.querySelector(selector);
    const category = find('#icon-category');
    const input = find('#icon-filter');
    const localized = find('#icon-localized');
    const grid = find('#icon-grid');
    const more = find('#icon-more');
    input.value = state.query;
    localized.checked = state.localized;

    function options() {
      const available = icons.filter((icon) => state.localized || !icon.localized);
      const counts = new Map();
      for (const icon of available) counts.set(icon.category, (counts.get(icon.category) || 0) + 1);
      category.innerHTML = `<option value="all">全部分类 · ${available.length}</option>${categories
        .map(
          (item) =>
            `<option value="${escape(item.id)}">${escape(item.label)} · ${counts.get(item.id) || 0}</option>`,
        )
        .join('')}`;
      category.value = state.category;
    }

    function render(append = false) {
      const matches = selectIcons(icons, state);
      const previous = append ? shown : 0;
      shown = Math.min(matches.length, state.limit);
      const cards = matches
        .slice(previous, shown)
        .map(
          (icon) =>
            `<button type="button" class="icon-cell" data-icon="${escape(icon.name)}" aria-label="复制 FluentIcon.${escape(icon.name)}" title="FluentIcon.${escape(icon.name)}"><img src="${escape(icon.file)}" width="25" height="25" alt="" loading="lazy" decoding="async"><span>${escape(icon.name)}</span></button>`,
        )
        .join('');
      if (append) grid.insertAdjacentHTML('beforeend', cards);
      else grid.innerHTML = cards;
      if (!matches.length) {
        const hiddenVariants =
          !state.localized && selectIcons(icons, { ...state, localized: true }).length > 0;
        grid.innerHTML = `<div class="icon-empty"><strong>没有匹配的图标</strong><p>${hiddenVariants ? '匹配项属于其他语言版本，可开启下方选项查看。' : '试试清空关键词，或切换到全部分类。'}</p>${hiddenVariants ? '<button type="button" data-icon-locales>显示其他语言版本</button>' : '<button type="button" data-icon-clear>清空关键词</button>'}${state.category !== 'all' ? '<button type="button" data-icon-all>查看全部分类</button>' : ''}</div>`;
      }
      find('#icon-category-name').textContent =
        categories.find((item) => item.id === state.category)?.label || '全部用途';
      find('#icon-result-count').textContent = `找到 ${matches.length} 个图标`;
      find('#icon-shown-count').textContent = `已显示 ${shown} / ${matches.length}`;
      more.hidden = shown >= matches.length;
      find('#icon-reset').hidden = !state.query && state.category === 'all' && !state.localized;
      if (append) {
        const firstNew = grid.children[previous];
        firstNew?.focus({ preventScroll: true });
        firstNew?.scrollIntoView({
          block: 'nearest',
          behavior: 'instant',
        });
      }
    }

    function refresh() {
      state.query = input.value;
      state.category = category.value;
      state.localized = localized.checked;
      state.limit = PAGE_SIZE;
      render();
    }

    function onInput(event) {
      if (event.target !== input || event.isComposing) return;
      cancelAnimationFrame(frame);
      frame = requestAnimationFrame(refresh);
    }

    function onChange(event) {
      if (event.target !== category && event.target !== localized) return;
      refresh();
      if (event.target === localized) options();
    }

    function onClick(event) {
      const button = event.target.closest('button');
      if (!button) return;
      if (button === more) {
        state.limit += PAGE_SIZE;
        render(true);
      } else if (button.id === 'icon-reset') {
        state.category = 'all';
        state.query = '';
        state.localized = false;
        input.value = '';
        localized.checked = false;
        options();
        refresh();
        input.focus();
      } else if (button.hasAttribute('data-icon-clear')) {
        input.value = '';
        refresh();
        input.focus();
      } else if (button.hasAttribute('data-icon-all')) {
        category.value = 'all';
        refresh();
        category.focus();
      } else if (button.hasAttribute('data-icon-locales')) {
        localized.checked = true;
        refresh();
        options();
      }
    }

    host.addEventListener('input', onInput);
    host.addEventListener('change', onChange);
    host.addEventListener('click', onClick);
    host.addEventListener('compositionend', onInput);
    options();
    render();
    return () => {
      cancelAnimationFrame(frame);
      host.removeEventListener('input', onInput);
      host.removeEventListener('change', onChange);
      host.removeEventListener('click', onClick);
      host.removeEventListener('compositionend', onInput);
    };
  }

  scope.FluentIconCatalog = { mount, selectIcons };
})(globalThis);
