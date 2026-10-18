"""Atomic palette changes and the rendered whole-window theme transition."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import unittest
from unittest.mock import patch

from fluentpy import FluentWindow, LineEdit, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets, QT_API
from fluentpy.theme import ThemeManager, ThemeMode
if QT_API == 'PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class ThemeTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.original = theme.tokens
        theme.set_theme('light', accent=None)
        self.window = FluentWindow('Theme transition')
        self.window.set_title_bar_enabled(True)
        self.window.resize(460, 300)
        self.field = LineEdit('保留内容')
        self.field.setText('保留内容')
        self.window.content_layout.addWidget(self.field)
        self.window.content_layout.addStretch()
        self.window.show()
        self.app.processEvents()
        self.window.set_theme_transition_enabled(True)

    def tearDown(self):
        self.window.close()
        self.window.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_theme(self.original.mode, accent=self.original.custom_accent)

    def pixel(self):
        return self.window.grab().toImage().pixelColor(400, 250)

    def test_atomic_mode_and_accent_refresh_once_and_bracket_all_subscribers(self):
        manager = ThemeManager()
        events = []
        manager.modeAboutToChange.connect(lambda tokens: events.append(('before', manager.mode, tokens.custom_accent)))
        manager.changed.connect(lambda tokens: events.append(('refresh', manager.mode, tokens.custom_accent)))
        manager.modeChanged.connect(lambda tokens: events.append(('after', manager.mode, tokens.custom_accent)))
        manager.set_theme('dark', accent='#60cdff')
        self.assertEqual(events, [('before', ThemeMode.LIGHT, '#60cdff'),
                                  ('refresh', ThemeMode.DARK, '#60cdff'),
                                  ('after', ThemeMode.DARK, '#60cdff')])
        manager.set_theme('dark', accent='#60cdff')
        self.assertEqual(len(events), 3)
        manager.set_accent(None)
        self.assertEqual(events[-1], ('refresh', ThemeMode.DARK, None))

    def test_rendered_midpoint_blends_all_backgrounds_and_finishes_at_target(self):
        start = self.pixel()
        self.window.set_dark(True)
        transition = self.window._theme_transition
        self.assertTrue(transition.is_running())
        self.assertEqual(self.pixel(), start)
        transition.animation.setCurrentTime(transition.duration // 2)
        middle = self.pixel()
        transition.animation.setCurrentTime(transition.duration)
        end = self.pixel()
        self.assertLess(end.lightness(), middle.lightness())
        self.assertLess(middle.lightness(), start.lightness())
        self.assertFalse(transition.is_running())
        self.assertTrue(transition.layer.frame.isNull())
        self.assertEqual(end.name(), self.window._resolved_background_color().name())

    def test_reversal_starts_from_current_blended_frame_without_jump(self):
        self.window.set_dark(True)
        transition = self.window._theme_transition
        transition.animation.setCurrentTime(100)
        before = self.pixel()
        self.window.set_dark(False)
        self.assertEqual(self.pixel(), before)
        transition.animation.setCurrentTime(transition.duration)
        self.assertEqual(theme.mode, ThemeMode.LIGHT)
        self.assertFalse(transition.is_running())

    def test_input_and_focus_remain_live_and_do_not_trigger_style_refresh_per_frame(self):
        self.field.setFocus()
        self.field.setCursorPosition(len(self.field.text()))
        self.window.set_dark(True)
        changes = []
        def changed(tokens):
            changes.append(tokens)
        theme.changed.connect(changed)
        try:
            transition = self.window._theme_transition
            self.assertTrue(transition.layer.testAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents))
            for position in (40, 80, 120, 160, 200):
                transition.animation.setCurrentTime(position)
                self.pixel()
            QTest.keyClicks(self.field, 'abc')
            self.assertEqual(self.field.text(), '保留内容abc')
            self.assertIs(self.window.focusWidget(), self.field)
            self.assertEqual(changes, [])
            self.app.processEvents()
            self.assertFalse(transition.is_running(), 'Input reveals live content on the next event turn')
        finally:
            theme.changed.disconnect(changed)

    def test_click_that_reverses_theme_keeps_its_new_transition(self):
        button = QtWidgets.QPushButton('Switch theme', self.window)
        self.window.content_layout.addWidget(button)
        button.clicked.connect(theme.toggle)
        self.app.processEvents()
        self.window.set_dark(True)
        transition = self.window._theme_transition
        transition.animation.setCurrentTime(100)
        QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertEqual(theme.mode, ThemeMode.LIGHT)
        self.assertTrue(transition.is_running())
        self.assertTrue(self.window.updatesEnabled())

    def test_unavailable_target_snapshot_falls_back_without_leaving_updates_disabled(self):
        previous = self.window.grab()
        with patch.object(self.window, 'grab', side_effect=[previous, QtGui.QPixmap()]):
            self.window.set_dark(True)
        transition = self.window._theme_transition
        self.assertFalse(transition.is_running())
        self.assertTrue(self.window.updatesEnabled())
        self.assertTrue(transition.layer.frame.isNull())
        self.assertTrue(transition.layer.target_frame.isNull())

    def test_resize_hide_and_disabling_release_frames_and_leave_updates_enabled(self):
        transition = self.window._theme_transition
        self.window.set_dark(True)
        self.window.resize(500, 320)
        self.app.processEvents()
        self.assertFalse(transition.is_running())
        self.assertTrue(self.window.updatesEnabled())
        self.window.set_dark(False)
        self.window.set_theme_transition_enabled(False)
        self.assertFalse(transition.is_running())
        self.assertTrue(transition.layer.frame.isNull())
        self.window.set_theme_transition_enabled(True)
        self.window.set_dark(True)
        self.window.hide()
        self.assertFalse(transition.is_running())
        self.window.set_dark(False)
        self.assertFalse(transition.is_running())
        self.assertTrue(self.window.updatesEnabled())


if __name__ == '__main__':
    unittest.main()
