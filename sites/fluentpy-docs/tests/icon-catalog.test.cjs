/* Run with node --test sites/fluentpy-docs/tests/icon-catalog.test.cjs. */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

const site = path.resolve(__dirname, '..');
const context = vm.createContext({ window: {} });
vm.runInContext(fs.readFileSync(path.join(site, 'dist/data.js'), 'utf8'), context);
vm.runInContext(fs.readFileSync(path.join(site, 'dist/icon-catalog.js'), 'utf8'), context);
const { icons, iconCategories } = context.window.DOCS_DATA;
const { selectIcons } = context.FluentIconCatalog;

test('every public icon belongs to exactly one named category', () => {
  const ids = new Set(iconCategories.map((category) => category.id));
  assert.equal(ids.size, iconCategories.length);
  assert.equal(icons.length, 2625);
  assert.ok(icons.every((icon) => ids.has(icon.category)));
  const all = iconCategories.flatMap((category) =>
    selectIcons(icons, { category: category.id, localized: true }),
  );
  assert.equal(all.length, icons.length);
  assert.equal(new Set(all.map((icon) => icon.name)).size, icons.length);
});

test('localized letterforms are optional and never removed from the catalog', () => {
  assert.equal(selectIcons(icons).length, 2479);
  assert.equal(selectIcons(icons, { localized: true }).length, 2625);
  assert.equal(selectIcons(icons, { query: 'TEXT_BOLD_RU' }).length, 0);
  const selected = selectIcons(icons, { query: 'TEXT_BOLD_RU', localized: true });
  assert.equal(selected.length, 1);
  assert.equal(selected[0].name, 'TEXT_BOLD_RU');
});

test('category and Chinese/English search intersect without changing public names', () => {
  const volume = selectIcons(icons, { category: 'media', query: '音量' });
  assert.ok(volume.some((icon) => icon.name === 'SPEAKER_2'));
  assert.ok(volume.some((icon) => icon.name === 'DESKTOP_SPEAKER'));
  assert.equal(selectIcons(icons, { category: 'time', query: '音量' }).length, 0);
  const mute = selectIcons(icons, { category: 'media', query: 'speaker mute' });
  assert.equal(mute.length, 1);
  assert.equal(mute[0].name, 'SPEAKER_MUTE');
  const copiedName = selectIcons(icons, { query: 'FluentIcon.SPEAKER_2' });
  assert.equal(copiedName.length, 1);
  assert.equal(copiedName[0].name, 'SPEAKER_2');
  assert.ok(
    selectIcons(icons, { category: 'files', query: '保存' }).some(
      (icon) => icon.name === 'DOCUMENT_SAVE',
    ),
  );
});

test('common families retain their purpose despite action overlays', () => {
  const lookup = new Map(icons.map((icon) => [icon.name, icon]));
  assert.equal(lookup.get('FOLDER_ARROW_RIGHT').category, 'files');
  assert.equal(lookup.get('ARROW_RIGHT').category, 'navigation');
  assert.equal(lookup.get('TABLE').category, 'data');
  assert.equal(lookup.get('LEAF').category, 'nature');
});
