# Licensing Boundaries

FluentPy should remain an independent MIT-licensed implementation.

## Allowed References

- Public Microsoft Fluent Design and WinUI behavior guidelines.
- Public source repositories whose files are explicitly licensed under MIT or another compatible license.
- Microsoft Fluent System Icons when used according to their MIT license.
- Microsoft official open-source assets, styles, examples, and reference files when the specific repository and file are clearly covered by MIT or another compatible license.
- General UI behavior patterns such as hover, pressed, disabled, checked, focus, and theme states.

When vendoring or adapting files from an official MIT repository, keep a source note near the asset or in a third-party notice file. The note should include the repository URL, license, and the date/version/commit used.

## Avoid

- Extracting images, XAML resources, templates, binaries, fonts, or screenshots from Windows, Office, Microsoft Store apps, or other installed software.
- Assuming every Microsoft-looking resource is reusable. The project must rely on the license of the exact source repository or file.
- Copying qfluentwidgets source code, QSS files, resources, documentation, screenshots, examples, module layout, or API signatures.
- Marketing FluentPy as a clone, replacement build, cracked version, or source-compatible copy of another library.

## Preferred Implementation

Controls should usually be drawn with Qt painting and theme tokens instead of bitmap slices. This keeps the widgets DPI-aware and themeable. MIT-licensed Microsoft assets can still be used where they are genuinely assets, such as icons, sample illustrations, screenshots used with permission, or reference imagery.
