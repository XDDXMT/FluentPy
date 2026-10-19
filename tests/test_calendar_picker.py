"""Calendar arithmetic parity and real Qt interaction/lifetime coverage."""

import os
import random
import unittest
from unittest.mock import patch

os.environ["QT_QPA_PLATFORM"] = "offscreen"
from fluentpy import QT_API, CalendarPicker, DateRangePicker, DateTimePicker, TimePicker, theme
from fluentpy.backends import _calendar_python
from fluentpy.backends import calendar as policy
from fluentpy.qt import QtCore, QtWidgets

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


def outcome(call):
    try:
        return "value", call()
    except Exception as error:
        return "error", type(error)


class CalendarPolicyTests(unittest.TestCase):
    def test_grid_gregorian_boundaries_and_first_weekday(self):
        cells = policy.month_cells(2024, 2)
        self.assertEqual(len(cells), 42)
        self.assertEqual(cells[0], (2024, 1, 29, True))
        self.assertEqual(cells[-1], (2024, 3, 10, True))
        self.assertIn((2024, 2, 29, True), cells)
        self.assertFalse(any(c and c[:3] == (1900, 2, 29) for c in policy.month_cells(1900, 2)))
        self.assertEqual(policy.month_cells(1, 1, first_weekday=6)[0], None)
        self.assertEqual(policy.month_cells(9999, 12)[-1], None)
        self.assertEqual(policy.month_cells(2024, 2, first_weekday=6)[0][:3], (2024, 1, 28))

    def test_shift_and_datetime_clamp(self):
        self.assertEqual(policy.shift_date((2024, 1, 31), months=1), (2024, 2, 29))
        self.assertEqual(policy.shift_date((2024, 2, 29), months=12), (2025, 2, 28))
        self.assertEqual(policy.shift_date((1, 1, 1), days=-2_000_000_000), (1, 1, 1))
        self.assertEqual(policy.shift_date((9999, 12, 31), days=2_000_000_000), (9999, 12, 31))
        self.assertEqual(policy.shift_date((2024, 2, 29), days=1), (2024, 3, 1))
        lo, hi = (2026, 2, 10, 9, 30, 15), (2026, 2, 10, 20, 0, 0)
        self.assertEqual(policy.clamp_datetime((2026, 2, 10, 8, 0, 0), lo, hi), lo)
        self.assertEqual(policy.clamp_datetime((2026, 2, 10, 23, 0, 0), lo, hi), hi)
        self.assertEqual(policy.step_time(23, 59, 59, 2, 1), (23, 59, 0))
        self.assertEqual(policy.step_time(23, 59, 59, 0, 1), (0, 59, 59))

    def test_endpoint_rules_and_range_crossing_disabled_interior(self):
        rules = policy.validate_rules((2024, 1, 1), (2024, 12, 31), (6, 5, 5), ((2024, 3, 12),))
        self.assertEqual(rules[2], (5, 6))
        self.assertFalse(policy.is_selectable((2024, 3, 16), *rules))
        self.assertFalse(policy.is_selectable((2024, 3, 12), *rules))
        self.assertEqual(
            policy.normalize_range((2024, 3, 21), (2024, 3, 13), *rules),
            ((2024, 3, 13), (2024, 3, 21)),
        )
        with self.assertRaises(ValueError):
            policy.normalize_range((2024, 3, 16), (2024, 3, 21), *rules)
        with self.assertRaises(ValueError):
            policy.validate_rules((2025, 1, 1), (2024, 1, 1))

    def test_invalid_types_and_dates_are_rejected(self):
        for name, args in (
            ("month_cells", (True, 1)),
            ("month_cells", (2024, 13)),
            ("shift_date", ((2023, 2, 29),)),
            ("shift_date", ((2024, 1, 1), False)),
            ("is_selectable", ((2024, 1, 0),)),
            ("validate_rules", ((1, 1, 1), (9999, 12, 31), (7,))),
            ("time_values", (0, 0, 0, 2, 101)),
            ("step_time", (0, 0, 60, 0, 1)),
            ("clamp_datetime", ((2024, 1, 1, 24, 0, 0),)),
        ):
            with self.subTest(name=name, args=args):
                self.assertEqual(outcome(lambda: getattr(policy, name)(*args))[0], "error")

    @unittest.skipUnless(policy.native_available(), "Optional calendar C extension required")
    def test_native_matches_python_random_cases_and_errors(self):
        rng = random.Random(20261017)
        for i in range(240):
            y, m = rng.randint(1, 9999), rng.randint(1, 12)
            value = (y, m, 1)
            args = (y, m, (1, 1, 1), (9999, 12, 31), (5, 6), ((2024, 2, 29),), i % 7)
            self.assertEqual(
                policy._extension.calendar_month_cells(*args), _calendar_python.month_cells(*args)
            )
            days, months = rng.randint(-4000000, 4000000), rng.randint(-140000, 140000)
            self.assertEqual(
                policy._extension.calendar_shift_date(value, days, months),
                _calendar_python.shift_date(value, days, months),
            )
            args = (
                rng.randrange(24),
                rng.randrange(60),
                rng.randrange(60),
                rng.randrange(3),
                10**200 * (-1 if i % 2 else 1),
            )
            self.assertEqual(
                policy._extension.calendar_step_time(*args), _calendar_python.step_time(*args)
            )
        for name, args in (
            ("month_cells", (True, 1)),
            ("month_cells", (10**200, 1)),
            ("month_cells", (2024, 1, None)),
            ("shift_date", ((2023, 2, 29),)),
            ("shift_date", ((2024, 1, 1), 10**100)),
            ("normalize_range", ((2024, 1, 1), (2024, 1, 2), (2024, 1, 1), (2024, 12, 31), (0,))),
            ("time_values", (0, 0, 0, 2, None)),
            ("step_time", (True, 0, 0, 0, 1)),
            ("validate_rules", ((1, 1, 1), (9999, 12, 31), (True,))),
        ):
            self.assertEqual(
                outcome(lambda: getattr(policy._extension, "calendar_" + name)(*args)),
                outcome(lambda: getattr(_calendar_python, name)(*args)),
            )

    def test_feature_fallback_and_explicit_native(self):
        with patch.object(policy, "_extension", None):
            with patch.dict(os.environ, FLUENTPY_BACKEND="auto"):
                self.assertEqual(policy.backend_name(), "python")
                self.assertEqual(len(policy.month_cells(2024, 2)), 42)
            with patch.dict(os.environ, FLUENTPY_BACKEND="native"):
                with self.assertRaises(RuntimeError):
                    policy.month_cells(2024, 2)


class CalendarWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.owner = QtWidgets.QWidget()
        self.owner.resize(900, 650)
        self.picker = CalendarPicker(self.owner)
        self.picker.setGeometry(30, 30, 230, 36)
        self.owner.show()
        QTest.qWait(10)

    def tearDown(self):
        self.owner.close()
        self.owner.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def replace(self, kind):
        self.picker.hide()
        self.picker = kind(self.owner)
        self.picker.setGeometry(30, 30, 300, 36)
        self.picker.show()

    def open(self):
        self.picker.show_popup()
        QTest.qWait(240)
        return self.picker._popup.calendar

    def click_day(self, cal, value):
        index = next(i for i, c in enumerate(cal.cells) if c and c[:3] == value)
        QTest.mouseClick(
            cal.grid, QtCore.Qt.MouseButton.LeftButton, pos=cal.grid._cell(index).center().toPoint()
        )

    def test_single_date_pointer_commit_and_signal_once(self):
        self.picker.set_date(QtCore.QDate(2024, 2, 26))
        changed = []
        accepted = []
        self.picker.dateChanged.connect(changed.append)
        self.picker.dateAccepted.connect(accepted.append)
        QTest.mouseClick(self.picker, QtCore.Qt.MouseButton.LeftButton)
        QTest.qWait(240)
        cal = self.picker._popup.calendar
        self.click_day(cal, (2024, 2, 29))
        QTest.qWait(170)
        self.assertEqual(self.picker.date(), QtCore.QDate(2024, 2, 29))
        self.assertEqual(len(changed), 1)
        self.assertEqual(len(accepted), 1)
        self.assertFalse(self.picker._popup.isVisible())
        self.assertFalse(self.picker._popup.isWindow())

    def test_range_first_click_draft_escape_reverse_then_commit(self):
        self.replace(DateRangePicker)
        self.picker.set_range(QtCore.QDate(2024, 3, 13), QtCore.QDate(2024, 3, 21))
        cal = self.open()
        self.click_day(cal, (2024, 3, 22))
        self.assertEqual(self.picker.start_date(), QtCore.QDate(2024, 3, 13))
        self.assertIsNone(cal.end)
        QTest.keyClick(cal.grid, QtCore.Qt.Key.Key_Escape)
        QTest.qWait(170)
        cal = self.open()
        self.click_day(cal, (2024, 3, 22))
        self.click_day(cal, (2024, 3, 11))
        QTest.qWait(170)
        self.assertEqual(
            (self.picker.start_date(), self.picker.end_date()),
            (QtCore.QDate(2024, 3, 11), QtCore.QDate(2024, 3, 22)),
        )

    def test_disabled_endpoints_and_invalid_configuration_atomic(self):
        self.picker.set_date(QtCore.QDate(2024, 3, 13))
        self.picker.set_disabled_weekdays((5, 6))
        cal = self.open()
        self.click_day(cal, (2024, 3, 16))
        self.assertEqual(self.picker.date(), QtCore.QDate(2024, 3, 13))
        self.assertTrue(self.picker._popup._opened)
        rules = self.picker._rules
        with self.assertRaises(ValueError):
            self.picker.set_date_bounds(QtCore.QDate(2025, 1, 1), QtCore.QDate(2024, 1, 1))
        self.assertEqual(self.picker._rules, rules)
        self.picker.set_disabled_dates((QtCore.QDate(2024, 3, 13),))
        self.assertFalse(self.picker.date().isValid())
        self.assertFalse(self.picker._popup._opened)

    def test_keyboard_cross_month_leap_day_zoom_and_tab(self):
        self.picker.set_date(QtCore.QDate(2024, 1, 31))
        cal = self.open()
        QTest.keyClick(cal.grid, QtCore.Qt.Key.Key_PageDown)
        self.assertEqual(cal.focused, (2024, 2, 29))
        QTest.keyClick(cal.grid, QtCore.Qt.Key.Key_Return)
        QTest.qWait(170)
        self.assertEqual(self.picker.date(), QtCore.QDate(2024, 2, 29))
        cal = self.open()
        cal.heading.click()
        self.assertEqual(cal.level, "months")
        cal.activate(11)
        self.assertEqual(cal.month, (2024, 12))
        self.assertEqual(cal.level, "days")
        cal.heading.click()
        cal.heading.click()
        self.assertEqual(cal.level, "years")
        cal.activate(6)
        self.assertEqual(cal.month[0], 2026)
        self.assertEqual(cal.level, "months")
        cal.grid.setFocus()
        QTest.keyClick(cal.grid, QtCore.Qt.Key.Key_Tab)
        self.assertIs(self.app.focusWidget(), cal.heading)

    def test_datetime_seconds_confirm_cancel_and_same_day_bounds(self):
        self.replace(DateTimePicker)
        value = QtCore.QDateTime(QtCore.QDate(2026, 2, 10), QtCore.QTime(20, 0, 0))
        self.picker.set_date_time(value)
        events = []
        self.picker.dateTimeChanged.connect(events.append)
        cal = self.open()
        self.click_day(cal, (2026, 2, 12))
        self.picker._popup.seconds.step(2, 5)
        self.assertEqual(self.picker.date_time(), value)
        self.picker._popup.cancel_button.click()
        QTest.qWait(170)
        self.assertEqual(self.picker.date_time(), value)
        self.assertEqual(events, [])
        cal = self.open()
        self.click_day(cal, (2026, 2, 12))
        self.picker._popup.seconds.step(2, 5)
        self.picker._popup.confirm_button.click()
        QTest.qWait(170)
        self.assertEqual(
            self.picker.date_time().toString("yyyy-MM-dd HH:mm:ss"), "2026-02-12 20:00:05"
        )
        self.assertEqual(len(events), 1)
        lo = QtCore.QDateTime(QtCore.QDate(2026, 2, 10), QtCore.QTime(9, 30, 15))
        hi = QtCore.QDateTime(QtCore.QDate(2026, 2, 10), QtCore.QTime(20, 0, 0))
        self.picker.set_date_time_bounds(lo, hi)
        self.picker.set_date_time(lo)
        cal = self.open()
        self.picker._popup.seconds.step(0, -1)
        self.assertEqual(self.picker._popup.seconds.value, (9, 30, 15))
        self.picker._popup.confirm_button.click()
        self.assertEqual(self.picker.date_time(), lo)

    def test_in_window_lifetime_switching_themes_owner_resize_and_destroy(self):
        self.picker.set_date(QtCore.QDate(2024, 2, 26))
        self.open()
        popup = self.picker._popup
        self.owner.resize(420, 400)
        self.app.processEvents()
        self.assertTrue(popup.rect().contains(popup.surface.geometry()))
        theme.set_mode("dark")
        self.app.processEvents()
        theme.set_mode("light")
        other = TimePicker(self.owner)
        other.setGeometry(30, 350, 200, 36)
        other.show()
        other.show_popup()
        self.assertFalse(popup._opened)
        other.hide()
        self.picker.show_popup()
        self.picker.setEnabled(False)
        self.assertFalse(popup._opened)
        self.picker.setEnabled(True)
        self.picker.show_popup()
        self.picker.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def test_datetime_narrow_layout_remains_inside_window(self):
        self.replace(DateTimePicker)
        self.owner.resize(390, 620)
        self.open()
        popup = self.picker._popup
        self.assertTrue(popup.rect().contains(popup.surface.geometry()))
        self.assertLessEqual(popup.seconds.geometry().bottom(), popup.body.height())
        self.assertGreater(popup.calendar.grid.height(), 150)

    def test_range_band_reaches_circle_edges_and_clips_circular_corners(self):
        self.replace(DateRangePicker)
        self.picker.set_range(QtCore.QDate(2024, 3, 13), QtCore.QDate(2024, 3, 21))
        cal = self.open()
        grid = cal.grid
        path = grid.range_path()
        for value, is_start in (((2024, 3, 13), True), ((2024, 3, 21), False)):
            index = next(i for i, c in enumerate(cal.cells) if c and c[:3] == value)
            cell = grid._cell(index)
            center = cell.center()
            radius = min(36.0, cell.width() - 6, cell.height() - 5) / 2
            direction = -1 if is_start else 1
            # The midline reaches the outer circle, while its square corner stays empty.
            self.assertTrue(
                path.contains(QtCore.QPointF(center.x() + direction * (radius - 1), center.y()))
            )
            self.assertFalse(
                path.contains(
                    QtCore.QPointF(center.x() + direction * (radius - 1), center.y() - radius + 1)
                )
            )

    def test_range_hover_interpolates_and_same_day_is_one_round_cap(self):
        self.replace(DateRangePicker)
        self.picker.set_range(QtCore.QDate(2024, 3, 13), QtCore.QDate(2024, 3, 21))
        cal = self.open()
        grid = cal.grid
        cal.choose((2024, 3, 13))
        QTest.qWait(220)
        before = grid._range_state
        index = next(i for i, c in enumerate(cal.cells) if c and c[:3] == (2024, 3, 15))
        grid._set_hover(index)
        grid.range_motion.setCurrentTime(80)
        self.assertGreater(grid._range_state[1], before[1])
        self.assertLess(grid._range_state[1], index)
        QTest.qWait(220)
        self.assertEqual(grid._range_state[1], float(index))
        self.assertEqual(self.picker.end_date(), QtCore.QDate(2024, 3, 21))
        grid._set_hover(-1)
        QTest.qWait(220)
        bounds = grid.range_path().boundingRect()
        self.assertAlmostEqual(bounds.width(), bounds.height(), places=4)

    def test_reparented_anchor_can_recreate_flyout_after_old_owner_deleted(self):
        self.open()
        replacement = QtWidgets.QWidget()
        replacement.resize(800, 600)
        replacement.show()
        picker = self.picker
        picker.setParent(replacement)
        picker.show()
        self.owner.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.owner = replacement
        picker.show_popup()
        QTest.qWait(240)
        self.assertTrue(picker._popup._opened)
        self.assertIs(picker._popup.parentWidget(), replacement)

    def test_locale_week_start_and_partial_year_bounds_in_zoom(self):
        self.picker.set_date_bounds(QtCore.QDate(2024, 6, 1), QtCore.QDate(2026, 3, 1))
        self.picker.set_date(QtCore.QDate(2024, 12, 31))
        self.picker.set_locale("en_US")
        self.picker.set_first_weekday(6)
        cal = self.open()
        self.assertEqual(cal.cells[0][:3], (2024, 12, 1))
        self.assertIn("December", cal.heading.text())
        cal.zoom_out()
        cal.zoom_out()
        cal.activate(6)
        self.assertEqual(cal.month, (2026, 3))
        self.assertEqual(cal.level, "months")
        QTest.keyClick(cal.grid, QtCore.Qt.Key.Key_Down)
        self.assertLessEqual(cal.focused, (2026, 3, 1))

    def test_focus_does_not_draw_a_second_ring_inside_selection(self):
        self.replace(DateRangePicker)
        self.picker.set_range(QtCore.QDate(2024, 3, 13), QtCore.QDate(2024, 3, 21))
        cal = self.open()
        cal.grid.setFocus()
        self.app.processEvents()
        self.assertTrue(cal.grid.hasFocus())
        focused = cal.grid.grab().toImage()
        cal.heading.setFocus()
        self.app.processEvents()
        self.assertFalse(cal.grid.hasFocus())
        self.assertEqual(focused, cal.grid.grab().toImage())
        # Removing the painted focus marker does not remove keyboard navigation.
        cal.grid.setFocus()
        QTest.keyClick(cal.grid, QtCore.Qt.Key.Key_Right)
        self.assertEqual(cal.focused, (2024, 3, 14))


if __name__ == "__main__":
    unittest.main()
