# Icon Sources

Files named `ic_fluent_*` in this directory come from Microsoft Fluent UI System Icons.

- Source: https://github.com/microsoft/fluentui-system-icons
- License: MIT
- Asset pattern: `assets/*/SVG/ic_fluent_*_24_regular.svg`

2624 regular 24px SVG icons are bundled, including localized variants. Copyright (c) 2020 Microsoft Corporation.
The complete MIT license is included in [Microsoft-Fluent-System-Icons-LICENSE.txt](../../../../licenses/Microsoft-Fluent-System-Icons-LICENSE.txt).
See also [third-party notices](../../../../THIRD_PARTY_NOTICES.md). Built distributions include these notices in their license metadata.

## Complete 24px Regular catalog

- Pinned official commit: `9eb184e96268d3293462f9d9d19225b4c7b07774`.
- Inventory and each retained file's SHA-256: [UPSTREAM.json](UPSTREAM.json).
- 2478 default symbols and 146 localized variants. Localized filenames add their locale before `_24_regular.svg`, e.g. `ic_fluent_text_bold_ru_24_regular.svg` / `FluentIcon.TEXT_BOLD_RU`; their SVG bytes are unchanged.
- All missing symbols from this size/style were imported. Other sizes and Filled/Color styles are outside this catalog.
- Existing public names and assets are retained, including earlier versions of CODE and COPY. These two entries have `matches_snapshot: false` in the inventory; newly imported SVGs match the pinned upstream Git blobs.
- Upstream Mail Rewind has a `0 0 25 24` viewBox despite its 24px filename; it is retained unchanged.
- Reproducible import: `python scripts/sync_icons.py --commit 9eb184e96268d3293462f9d9d19225b4c7b07774`.
- The full upstream MIT license and NOTICE are included in `licenses/`. No upstream scripts, fonts or build tools are shipped with these SVGs.

## FluentPy Leaf

- Bundled file: `fluentpy_leaf_24_regular.svg`; public enum: `FluentIcon.LEAF`.
- Independently drawn FluentPy vector paths, distributed under this project's MIT license.
- This asset is part of FluentPy, separate from the Microsoft assets listed above. Microsoft also provides `FluentIcon.LEAF_ONE`, `LEAF_TWO` and `LEAF_THREE`, without changing the existing `FluentIcon.LEAF` name.
- The public loader works in library installations and has no dependency on workbench examples.

## Music Note 2

- Bundled file: `ic_fluent_music_note_2_24_regular.svg`; public enum: `FluentIcon.MUSIC_NOTE_2`.
- Official asset: https://github.com/microsoft/fluentui-system-icons/blob/main/assets/Music%20Note%202/SVG/ic_fluent_music_note_2_24_regular.svg
- Downloaded original SVG without path or byte changes from https://raw.githubusercontent.com/microsoft/fluentui-system-icons/a347af95478f989038cccbf085978865264c048a/assets/Music%20Note%202/SVG/ic_fluent_music_note_2_24_regular.svg
- Upstream repository commit resolved at download: `a347af95478f989038cccbf085978865264c048a`.
- SHA-256: `6dacdfca1f1d955e41ef48412b3fb9e8567120ee17cee6f3ed1c4563170e34aa` (1,076 bytes).
- License: the same Microsoft MIT license linked above; its complete text is retained unchanged.

## Eyedropper

- Bundled file: `ic_fluent_eyedropper_24_regular.svg`; public enum: `FluentIcon.EYEDROPPER`.
- Official unchanged SVG: https://raw.githubusercontent.com/microsoft/fluentui-system-icons/main/assets/Eyedropper/SVG/ic_fluent_eyedropper_24_regular.svg
- Downloaded 2026-10-17; SHA-256: `760f2318a6cca80a85e254428b843d97e4f3c974c2293c80ea1a11836e8b42ec` (1,774 bytes).
- License: Microsoft MIT; complete license retained at the link above.
