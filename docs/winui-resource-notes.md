# WinUI Resource Notes

FluentPy uses Microsoft WinUI's MIT-licensed resource dictionaries as a reference for control state naming and behavior.

- Source: https://github.com/microsoft/microsoft-ui-xaml
- License: MIT
- Reference file: `controls/dev/CommonStyles/Button_themeresources.xaml`

The button resource mapping in WinUI separates state into:

- `ButtonBackground`
- `ButtonBackgroundPointerOver`
- `ButtonBackgroundPressed`
- `ButtonBackgroundDisabled`
- `ButtonForeground`
- `ButtonForegroundPointerOver`
- `ButtonForegroundPressed`
- `ButtonForegroundDisabled`
- `ButtonBorderBrush`
- `ButtonBorderBrushPointerOver`
- `ButtonBorderBrushPressed`
- `ButtonBorderBrushDisabled`

FluentPy implements these concepts through Python theme tokens and Qt painting instead of copying XAML styles directly.
