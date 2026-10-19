"""Canonical time policy, C parity, confirmed editing and flyout lifetime."""

import importlib.util
import os
import random
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from fluentpy import QT_API, TimePicker, theme
from fluentpy.backends import _time_python
from fluentpy.backends import time as clock
from fluentpy.qt import QtCore, QtGui, QtWidgets

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


def outcome(call):
    try:
        return "value", call()
    except Exception as error:
        return "error", type(error)


class TimePolicyTests(unittest.TestCase):
    def test_every_minute_round_trips_in_both_presentations(self):
        for hour in range(24):
            for minute in range(60):
                self.assertEqual(clock.validate_time(hour, minute), (hour, minute))
                display = clock.display_time(hour, minute, True)
                self.assertEqual(clock.from_display(*display), (hour, minute))
                self.assertEqual(clock.display_time(hour, minute)[:2], (hour, minute))

    def test_midnight_noon_and_independent_wheel_boundaries(self):
        for value, expected in (
            ((0, 0), (12, 0, 0)),
            ((12, 0), (12, 0, 1)),
            ((23, 59), (11, 59, 1)),
        ):
            self.assertEqual(clock.display_time(*value, True), expected)
        self.assertEqual(clock.step_time(23, 59, 0, 1), (0, 59))
        self.assertEqual(clock.step_time(23, 59, 1, 1), (23, 0))
        self.assertEqual(clock.step_time(11, 20, 0, 1, True), (0, 20))
        self.assertEqual(clock.step_time(23, 20, 0, 1, True), (12, 20))
        self.assertEqual(clock.step_time(2, 20, 2, 1, True), (14, 20))
        self.assertEqual(clock.step_time(14, 20, 2, -1, True), (2, 20))
        self.assertEqual(clock.step_time(14, 20, 2, 10**500, True), (14, 20))

    def test_centered_rows_and_non_repeated_meridiem(self):
        self.assertEqual(clock.column_values(14, 0, 0), tuple(range(10, 19)))
        self.assertEqual(clock.column_values(14, 0, 1), (56, 57, 58, 59, 0, 1, 2, 3, 4))
        self.assertEqual(
            clock.column_values(14, 0, 0, use_12_hour=True), (10, 11, 12, 1, 2, 3, 4, 5, 6)
        )
        self.assertEqual(
            clock.column_values(14, 0, 2, use_12_hour=True),
            (None, None, None, 0, 1, None, None, None, None),
        )

    def test_invalid_input_is_rejected_without_coercion(self):
        for operation, args, error in (
            (clock.validate_time, (True, 0), TypeError),
            (clock.validate_time, (24, 0), ValueError),
            (clock.validate_time, (0, 60), ValueError),
            (clock.validate_time, (10**100, 0), ValueError),
            (clock.display_time, (0, 0, 1), TypeError),
            (clock.from_display, (0, 0, 0), ValueError),
            (clock.from_display, (12, 0, True), TypeError),
            (clock.step_time, (0, 0, 2, 1), ValueError),
            (clock.step_time, (0, 0, 0, 1.5), TypeError),
            (clock.column_values, (0, 0, 0, 101), ValueError),
        ):
            with self.subTest(args=args, operation=operation.__name__):
                with self.assertRaises(error):
                    operation(*args)

    def test_auto_fallback_strict_native_and_old_binary(self):
        with patch.object(clock, "_extension", None):
            with patch.dict(os.environ, FLUENTPY_BACKEND="auto"):
                self.assertEqual(clock.backend_name(), "python")
                self.assertEqual(clock.step_time(23, 59, 1, 1), (23, 0))
            with patch.dict(os.environ, FLUENTPY_BACKEND="native"):
                with self.assertRaises(RuntimeError):
                    clock.backend_name()
        path = Path(clock.__file__)
        for failure in (ImportError("missing"), OSError("ABI mismatch"), object()):
            with patch(
                "importlib.import_module",
                side_effect=failure if isinstance(failure, Exception) else None,
                return_value=failure,
            ):
                spec = importlib.util.spec_from_file_location("fluentpy.backends._time_test", path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                with patch.dict(os.environ, FLUENTPY_BACKEND="auto"):
                    self.assertEqual(module.backend_name(), "python")
                    self.assertEqual(module.display_time(0, 0, True), (12, 0, 0))
                    self.assertIsNotNone(module.native_error())

    @unittest.skipUnless(clock.native_available(), "C parity requires the optional extension")
    def test_native_matches_compatibility_for_values_extremes_and_errors(self):
        rng = random.Random(20261017)
        for _ in range(120):
            hour, minute, twelve = rng.randrange(24), rng.randrange(60), bool(rng.randrange(2))
            for column in range(3 if twelve else 2):
                steps = rng.choice((-(10**500), 10**500, rng.randint(-1000, 1000)))
                radius = rng.choice((0, 4, 100))
                self.assertEqual(
                    _time_python.step_time(hour, minute, column, steps, twelve),
                    clock._extension.time_step_time(hour, minute, column, steps, twelve),
                )
                self.assertEqual(
                    _time_python.column_values(hour, minute, column, radius, twelve),
                    clock._extension.time_column_values(hour, minute, column, radius, twelve),
                )
        for name, args in (
            ("validate_time", (True, 0)),
            ("validate_time", (10**500, 0)),
            ("display_time", (0, 0, 1)),
            ("from_display", (12, 0, 2)),
            ("step_time", (0, 0, False, 1)),
            ("column_values", (0, 0, 0, None)),
            ("step_time", (0, 0, 2, 1)),
        ):
            self.assertEqual(
                outcome(lambda: getattr(_time_python, name)(*args)),
                outcome(lambda: getattr(clock._extension, "time_" + name)(*args)),
            )


class TimePickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda _kind, error, _tb: self.errors.append(error)
        self.old_mode = theme.mode
        theme.set_mode("light")
        self.host = QtWidgets.QWidget()
        self.host.resize(760, 600)
        self.view = TimePicker(self.host)
        self.view.setGeometry(70, 270, 300, 38)
        self.changed, self.accepted = [], []
        self.view.timeChanged.connect(self.changed.append)
        self.view.timeAccepted.connect(self.accepted.append)
        self.host.show()
        self.app.processEvents()

    def tearDown(self):
        try:
            self.host.close()
            self.host.deleteLater()
            self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
            self.app.processEvents()
            theme.set_mode(self.old_mode)
        finally:
            sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [], "Qt callback raised")

    def open(self, value=(14, 0), column=0):
        if value is not None:
            self.view.setTime(QtCore.QTime(*value))
        count = 3 if self.view.is_12_hour_clock() else 2
        QTest.mouseClick(
            self.view,
            QtCore.Qt.MouseButton.LeftButton,
            pos=QtCore.QPoint(round((column + 0.5) * self.view.width() / count), 18),
        )
        self.app.processEvents()
        self.assertTrue(self.view._popup._opened)
        return self.view._popup

    def finish_motion(self, popup):
        popup._reveal.setCurrentTime(popup._reveal.duration())
        self.app.processEvents()

    def test_empty_set_clear_and_minute_precision(self):
        self.assertFalse(self.view.time().isValid())
        self.assertEqual(self.view.sizeHint(), QtCore.QSize(300, 38))
        self.view.setTime(QtCore.QTime(14, 30, 45, 230))
        self.view.setTime(QtCore.QTime(14, 30))
        self.assertEqual(self.view.time(), QtCore.QTime(14, 30))
        self.assertEqual(len(self.changed), 1)
        self.assertEqual(self.view.toolTip(), "14:30")
        with self.assertRaises(TypeError):
            self.view.setTime("14:30")
        self.view.clear()
        self.view.clear()
        self.assertEqual(len(self.changed), 2)
        self.assertFalse(self.view.time().isValid())

    def test_only_confirmation_commits_and_reconfirmation_accepts(self):
        popup = self.open(column=1)
        self.changed.clear()
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Down)
        self.assertEqual(popup.wheel.value, (14, 1))
        self.assertEqual(self.view.time(), QtCore.QTime(14, 0))
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Return)
        self.finish_motion(popup)
        self.assertEqual(self.view.time(), QtCore.QTime(14, 1))
        self.assertEqual(self.changed, [QtCore.QTime(14, 1)])
        self.assertEqual(self.accepted, [QtCore.QTime(14, 1)])
        popup = self.open(value=None)
        QTest.mouseClick(popup.confirm_button, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(len(self.changed), 1)
        self.assertEqual(len(self.accepted), 2)

    def test_cancel_escape_and_outside_click_preserve_committed_value(self):
        for action in ("cancel", "escape", "outside"):
            popup = self.open(column=1)
            self.finish_motion(popup)
            self.changed.clear()
            popup.wheel.step(1, 8)
            if action == "cancel":
                QTest.mouseClick(popup.cancel_button, QtCore.Qt.MouseButton.LeftButton)
            elif action == "escape":
                QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Escape)
            else:
                QTest.mouseClick(
                    popup, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(740, 580)
                )
            self.finish_motion(popup)
            self.assertEqual(self.view.time(), QtCore.QTime(14, 0))
            self.assertEqual(self.changed, [])
            self.assertFalse(popup._opened)
        self.assertEqual(self.accepted, [])

    def test_cancel_empty_picker_keeps_it_empty(self):
        popup = self.open(value=None)
        popup.wheel.step(0, 1)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Escape)
        self.assertFalse(self.view.time().isValid())
        self.assertEqual(self.changed, [])

    def test_two_and_three_columns_and_canonical_meridiem(self):
        for twelve in (False, True):
            self.view.set_12_hour_clock(twelve)
            for column in range(3 if twelve else 2):
                popup = self.open(column=column)
                self.assertEqual(popup.wheel.column, column)
                self.assertEqual(len(popup.wheel._values), 3 if twelve else 2)
                popup.dismiss(immediate=True)
        popup = self.open((0, 0), column=2)
        popup.wheel.step(2, 1)
        QTest.mouseClick(popup.confirm_button, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(self.view.time(), QtCore.QTime(12, 0))
        self.assertEqual(self.view.toolTip(), "12:00 PM")

    def test_presentation_switch_does_not_change_time_or_keep_draft(self):
        popup = self.open((23, 59))
        popup.wheel.step(0, 1)
        self.changed.clear()
        self.view.set12HourClock(True)
        self.assertTrue(self.view.is12HourClock())
        self.assertEqual(self.view.time(), QtCore.QTime(23, 59))
        self.assertEqual(self.view.toolTip(), "11:59 PM")
        self.assertFalse(popup._opened)
        self.assertEqual(self.changed, [])
        with self.assertRaises(TypeError):
            self.view.set_12_hour_clock(1)
        self.assertTrue(self.view.is_12_hour_clock())

    def test_angle_and_pixel_deltas_accumulate_per_column(self):
        popup = self.open()
        for mode, amount in (("angle", 30), ("pixel", 11)):
            popup.wheel.set_value((14, 0))
            pos = QtCore.QPoint(3 * popup.wheel.width() // 4, popup.wheel.height() // 2)
            for index in range(4):
                event = QtGui.QWheelEvent(
                    QtCore.QPointF(pos),
                    QtCore.QPointF(popup.wheel.mapToGlobal(pos)),
                    QtCore.QPoint(0, amount if mode == "pixel" else 0),
                    QtCore.QPoint(0, amount if mode == "angle" else 0),
                    QtCore.Qt.MouseButton.NoButton,
                    QtCore.Qt.KeyboardModifier.NoModifier,
                    QtCore.Qt.ScrollPhase.NoScrollPhase,
                    False,
                )
                self.app.sendEvent(popup.wheel, event)
                self.assertEqual(popup.wheel.value, (14, 59) if index == 3 else (14, 0))

    def test_click_and_drag_use_selected_column(self):
        popup = self.open()
        wheel = popup.wheel
        QTest.mouseClick(
            wheel,
            QtCore.Qt.MouseButton.LeftButton,
            pos=QtCore.QPoint(wheel.width() // 4, (wheel.RADIUS + 1) * 44 + 22),
        )
        self.assertEqual(wheel.value, (15, 0))
        point = QtCore.QPoint(3 * wheel.width() // 4, wheel.height() // 2)
        QTest.mousePress(wheel, QtCore.Qt.MouseButton.LeftButton, pos=point)
        QTest.mouseMove(wheel, point - QtCore.QPoint(0, 88))
        QTest.mouseRelease(
            wheel, QtCore.Qt.MouseButton.LeftButton, pos=point - QtCore.QPoint(0, 88)
        )
        self.assertEqual(wheel.value, (15, 2))

    def test_meridiem_blank_rows_do_not_activate(self):
        self.view.set12HourClock(True)
        popup = self.open((14, 0), column=2)
        wheel = popup.wheel
        QTest.mouseClick(
            wheel, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(5 * wheel.width() // 6, 22)
        )
        self.assertEqual(wheel.value, (14, 0))

    def test_partial_drag_snaps_back_with_animation_and_does_not_commit(self):
        popup = self.open()
        wheel = popup.wheel
        point = QtCore.QPoint(wheel.width() // 4, wheel.height() // 2)
        QTest.mousePress(wheel, QtCore.Qt.MouseButton.LeftButton, pos=point)
        QTest.mouseMove(wheel, point + QtCore.QPoint(0, 15))
        QTest.mouseRelease(
            wheel, QtCore.Qt.MouseButton.LeftButton, pos=point + QtCore.QPoint(0, 15)
        )
        self.assertEqual(wheel.value, (14, 0))
        self.assertEqual(wheel._animations[0].state(), QtCore.QAbstractAnimation.State.Running)
        self.assertEqual(wheel._animations[0].startValue(), 15.0)
        self.assertEqual(self.view.time(), QtCore.QTime(14, 0))

    def test_keyboard_columns_and_tab_cycle(self):
        popup = self.open()
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Right)
        self.assertEqual(popup.wheel.column, 1)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Right)
        self.assertEqual(popup.wheel.column, 0)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Tab)
        self.assertTrue(popup.confirm_button.hasFocus())
        QTest.keyClick(popup.confirm_button, QtCore.Qt.Key.Key_Tab)
        self.assertTrue(popup.cancel_button.hasFocus())
        QTest.keyClick(popup.cancel_button, QtCore.Qt.Key.Key_Tab)
        self.assertTrue(popup.wheel.hasFocus())

    def test_in_window_animation_and_lifetime(self):
        top_levels = set(self.app.topLevelWidgets())
        popup = self.open()
        self.assertFalse(popup.isWindow())
        self.assertEqual(top_levels, set(self.app.topLevelWidgets()))
        self.assertGreater(popup._reveal.duration(), 0)
        popup._reveal.setCurrentTime(110)
        self.assertGreater(popup._progress, 0)
        self.assertLess(popup._progress, 1)
        self.finish_motion(popup)
        self.assertTrue(popup._filter_installed)
        self.view.hide()
        self.assertFalse(popup.isVisible())
        self.assertFalse(popup._filter_installed)
        self.assertEqual(popup._reveal.state(), QtCore.QAbstractAnimation.State.Stopped)

    def test_resize_theme_disable_and_rapid_reopen(self):
        popup = self.open()
        self.host.resize(390, 300)
        self.view.move(50, 130)
        self.app.processEvents()
        self.assertTrue(self.host.rect().contains(popup.surface.geometry()))
        self.assertLess(popup.wheel.RADIUS, 4)
        pending = popup.wheel.value
        theme.set_mode("dark")
        self.assertEqual(popup.wheel.value, pending)
        self.view.setEnabled(False)
        self.assertFalse(popup._opened)
        self.view.setEnabled(True)
        for _ in range(8):
            self.view.show_popup()
        self.app.processEvents()
        self.assertEqual(len(self.host.findChildren(type(popup))), 1)

    def test_only_one_time_flyout_and_owner_deactivation_closes(self):
        popup = self.open()
        other = TimePicker(self.host, use_12_hour=True)
        other.setGeometry(420, 270, 300, 38)
        other.show()
        other.show_popup()
        self.assertFalse(popup._opened)
        self.assertTrue(other._popup._opened)
        self.app.sendEvent(self.host, QtCore.QEvent(QtCore.QEvent.Type.WindowDeactivate))
        self.assertFalse(other._popup._opened)

    def test_destroying_anchor_during_motion_removes_flyout_and_filter(self):
        popup = self.open()
        self.view.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()
        self.assertEqual(self.host.findChildren(type(popup)), [])

    def test_offscreen_anchor_or_tiny_owner_never_leaves_an_overlay(self):
        self.view.move(900, 200)
        self.view.show_popup()
        self.assertFalse(self.view._popup._opened)
        self.assertFalse(self.view._popup.isVisible())
        self.assertFalse(self.view._popup._filter_installed)
        self.host.resize(300, 100)
        self.view.move(0, 20)
        self.view.show_popup()
        self.assertFalse(self.view._popup.isVisible())


if __name__ == "__main__":
    unittest.main()
