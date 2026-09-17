# Visual Research Notes

These notes summarize observed design patterns from the locally downloaded PyQt-Fluent-Widgets-Gallery executable. They are used as visual direction only; FluentPy should keep its own implementation and not copy qfluentwidgets source, QSS, or bundled resources.

## Observed Patterns

- Dark mode uses a cool blue-black page background rather than neutral gray.
- Light mode uses a very pale cool gray page background rather than pure white.
- Example panels are split into two bands:
  - preview area: slightly darker in light mode, darker blue-gray in dark mode
  - source area: subtly different surface color
- Cards have small corner radius, thin borders, and soft shadows.
- Accent color leans cyan/teal, not default Windows blue.
- Buttons are compact and quiet; the page gains richness from surrounding surfaces and layout.
- A narrow left navigation rail adds an app-shell feeling even with simple content.
- Hero imagery/material gives the page depth before individual controls appear.
- Mica/Acrylic material is not only transparency: it needs tint, soft shadow, subtle highlight, and a little texture/noise.
- Focused and unfocused windows should not share exactly the same background tint; inactive windows should feel flatter and less chromatic.

## FluentPy Direction

- Keep controls self-drawn or token-driven.
- Use MIT Fluent System Icons where icons are useful.
- Build a theme token layer around background, surface-high, surface-low, borders, shadows, and accent.
- Use native Windows Mica where available, with Qt-painted acrylic cards as the portable fallback.
- Treat Gallery as a visual validation tool, not just a demo.
