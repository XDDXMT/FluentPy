"""The real workbench paints its startup surface before doing page setup."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples'))
from showcase import Showcase, PAGES, text_backend
from fluentpy import theme
from fluentpy.qt import QtCore, QtGui, QtWidgets, QT_API
if QT_API == 'PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class WorkbenchStartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.windows = []
        self.old_mode = theme.mode
        self.old_palette = self.app.palette()
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, error, tb: self.errors.append(str(error))

    def tearDown(self):
        for window in self.windows:
            window.close()
            window.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.app.setPalette(self.old_palette)
        theme.set_mode(self.old_mode)
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def window(self, kind=Showcase, **kwargs):
        window = kind(restore_preferences=False, **kwargs)
        self.windows.append(window)
        return window

    def until(self, predicate, timeout=6000):
        elapsed = QtCore.QElapsedTimer()
        elapsed.start()
        while not predicate() and elapsed.elapsed() < timeout:
            QTest.qWait(10)
        self.assertTrue(predicate(), 'startup did not reach the expected state')

    def test_first_frame_precedes_backend_checks_and_page_construction(self):
        before = {w for w in self.app.topLevelWidgets() if w.isVisible()}
        with patch.object(text_backend, 'backend_name', wraps=text_backend.backend_name) as backend:
            window = self.window()
            self.assertFalse(window._initialized)
            self.assertFalse(hasattr(window, 'navigation'))
            self.assertEqual(backend.call_count, 0)
            frames = []
            def first_frame():
                bar = window.title_bar()
                frames.append((len(window._page_indexes), backend.call_count,
                               bar.title_label.isVisible(), bar._actions.isVisible(),
                               [button.isVisible() for button in
                                (bar.minimize_button, bar.maximize_button, bar.close_button)]))
            window.startup_splash.firstFramePainted.connect(first_frame)
            window.show()
            self.until(lambda: window.startup_splash.isHidden())
            self.assertEqual(frames, [(0, 0, False, False, [True, True, True])])
            self.assertEqual(backend.call_count, 1)
        visible = {w for w in self.app.topLevelWidgets() if w.isVisible()} - before
        self.assertEqual(visible, {window})
        self.assertEqual(len(window._page_indexes), len(PAGES))
        self.assertTrue(window.title_bar().title_label.isVisible())
        self.assertTrue(window.theme_toggle.isVisible())

    def test_initialization_is_batched_and_finish_is_tied_to_actual_completion(self):
        checkpoints = []
        class Observed(Showcase):
            def _advance_startup(self):
                checkpoints.append((len(self._page_indexes), self.startup_splash.isVisible()))
                super()._advance_startup()
        window = self.window(Observed, page='sliders', dark=True)
        ready, initialized = [], []
        window.ready.connect(lambda: ready.append(True))
        window.initialized.connect(lambda: initialized.append(len(window._page_indexes)))
        window.show()
        self.until(lambda: bool(ready))
        self.assertEqual(initialized, [len(PAGES)])
        self.assertEqual(ready, [True])
        self.assertEqual([count for count, _ in checkpoints], [0, *range(len(PAGES) + 1)])
        self.assertTrue(all(visible for _, visible in checkpoints))
        self.assertEqual(window.current_route(), 'sliders')
        self.assertEqual(theme.mode.value, 'dark')
        self.assertFalse(window._startup_timer.isActive())
        self.assertFalse(window._note_timer.isActive())

    def test_close_before_first_paint_never_runs_initialization(self):
        window = self.window()
        window.close()
        self.app.processEvents()
        self.assertIsNone(window._startup_steps)
        self.assertFalse(hasattr(window, 'navigation'))
        self.assertFalse(window._initialized)

    def test_close_between_pages_cancels_remaining_work_and_ready(self):
        ready = []
        class Closed(Showcase):
            def _advance_startup(self):
                super()._advance_startup()
                if len(self._page_indexes) == 2:
                    self.close()
        window = self.window(Closed)
        window.ready.connect(lambda: ready.append(True))
        window.show()
        self.until(lambda: window._startup_cancelled)
        QTest.qWait(30)
        self.assertEqual(len(window._page_indexes), 2)
        self.assertFalse(window._initialized)
        self.assertIsNone(window._startup_steps)
        self.assertEqual(ready, [])

    def test_failure_remains_on_startup_surface_with_real_error(self):
        class Failed(Showcase):
            def _inputs_page(self):
                raise RuntimeError('test page failed')
        window = self.window(Failed)
        failed, ready = [], []
        window.startupFailed.connect(failed.append)
        window.ready.connect(lambda: ready.append(True))
        with patch('traceback.print_exc'):
            window.show()
            self.until(lambda: bool(failed))
        self.assertEqual(failed, ['test page failed'])
        self.assertIn('test page failed', window.startup_splash.text())
        self.assertTrue(window.startup_splash.isVisible())
        self.assertFalse(window.title_bar().title_label.isVisible())
        self.assertFalse(window._initialized)
        self.assertFalse(window._startup_timer.isActive())
        self.assertEqual(ready, [])

    def test_resize_and_minimize_during_initialization_keep_one_owned_surface(self):
        class Resized(Showcase):
            def _advance_startup(self):
                super()._advance_startup()
                if len(self._page_indexes) == 2:
                    self.resize(940, 700)
                    self.showMinimized()
                    self.showNormal()
        window = self.window(Resized, page='navigation')
        window.show()
        self.until(lambda: window.startup_splash.isHidden())
        self.assertTrue(window._initialized)
        self.assertIs(window.startup_splash.parentWidget(), window)
        self.assertEqual(window.startup_splash.width(), window.width())
        self.assertEqual(window.current_route(), 'navigation')
        self.assertTrue(window.theme_toggle.isVisible())

    def check_opposite_system_palette(self, dark):
        palette = self.app.palette()
        for role, color in (
                (QtGui.QPalette.ColorRole.Window, '#eeeeee' if dark else '#1f1f1f'),
                (QtGui.QPalette.ColorRole.WindowText, '#111111' if dark else '#ffffff'),
                (QtGui.QPalette.ColorRole.Text, '#111111' if dark else '#ffffff'),
                (QtGui.QPalette.ColorRole.Base, '#ffffff' if dark else '#2b2b2b')):
            palette.setColor(role, QtGui.QColor(color))
        self.app.setPalette(palette)
        window = self.window(dark=dark)
        initial_palettes = []
        window.initialized.connect(lambda: initial_palettes.append(
            window.current_page().widget().palette().color(QtGui.QPalette.ColorRole.Window)))
        window.show()
        self.until(lambda: window.startup_splash.isHidden())
        self.assertEqual(initial_palettes, [QtGui.QColor(theme.tokens.background)])
        for route, _title, _icon in PAGES:
            with self.subTest(route=route, dark=dark):
                window.set_page(route, animated=False)
                self.app.processEvents()
                page = window.current_page().widget()
                self.assertEqual(page.palette().color(QtGui.QPalette.ColorRole.Window),
                                 QtGui.QColor(theme.tokens.background))
                for item in page.findChildren(QtWidgets.QLabel):
                    role = item.foregroundRole()
                    if item.isVisible() and item.objectName() in ('pageTitle', 'smallTitle', 'muted'):
                        expected = theme.tokens.text_muted if role == QtGui.QPalette.ColorRole.PlaceholderText else theme.tokens.text
                        self.assertEqual(item.palette().color(role), QtGui.QColor(expected),
                                         (route, item.text()))
                image = window.grab().toImage()
                viewport = window.current_page().viewport()
                point = viewport.mapTo(window, QtCore.QPoint(viewport.width() - 10, 10))
                self.assertEqual(image.pixelColor(point), QtGui.QColor(theme.tokens.background))
        window.set_page('overview', animated=False)
        for mode in ('light' if dark else 'dark', 'dark' if dark else 'light'):
            window.theme_toggle.setChecked(mode == 'dark')
            self.until(lambda: not window._theme_transition.is_running())
            self.assertEqual(theme.mode.value, mode)
            page = window.current_page().widget()
            self.assertEqual(page.palette().color(QtGui.QPalette.ColorRole.Window),
                             QtGui.QColor(theme.tokens.background))

    def test_light_startup_ignores_dark_system_palette(self):
        self.check_opposite_system_palette(False)

    def test_dark_startup_ignores_light_system_palette(self):
        self.check_opposite_system_palette(True)


if __name__ == '__main__':
    unittest.main()
