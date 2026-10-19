"""Behavioral tests for the native-calendar, confirmed date wheel flyout."""

import os

# A Qt.Popup must never appear on the user's desktop while this file runs.
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fluentpy import QT_API, DatePicker, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.widgets import date_picker as picker_module

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class DatePickerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.previous_mode = theme.mode
        self.errors = []
        self.previous_excepthook = sys.excepthook
        sys.excepthook = lambda _type, error, _tb: self.errors.append(error)
        theme.set_mode("light")
        self.host = QtWidgets.QWidget()
        self.host.resize(640, 600)
        layout = QtWidgets.QVBoxLayout(self.host)
        self.view = DatePicker(self.host)
        layout.addWidget(self.view)
        layout.addStretch()
        self.host.show()
        self.app.processEvents()

    def tearDown(self):
        try:
            if self.host is not None:
                self.host.close()
                self.host.deleteLater()
            self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
            theme.set_mode(self.previous_mode)
            self.app.processEvents()
        finally:
            sys.excepthook = self.previous_excepthook
        self.assertEqual(self.errors, [], "Qt callback raised during widget lifetime")

    def open_popup(self, date=None, column=0):
        if date is not None:
            self.view.set_date(QtCore.QDate(*date))
        position = QtCore.QPoint(
            int((column + 0.5) * self.view.width() / 3), self.view.height() // 2
        )
        QTest.mouseClick(self.view, QtCore.Qt.MouseButton.LeftButton, pos=position)
        self.app.processEvents()
        self.assertIsNotNone(self.view._popup)
        self.assertTrue(self.view._popup.isVisible())
        return self.view._popup

    def send_wheel(self, wheel, column, *, angle=0, pixels=0):
        position = QtCore.QPoint(int((column + 0.5) * wheel.width() / 3), wheel.height() // 2)
        event = QtGui.QWheelEvent(
            QtCore.QPointF(position),
            QtCore.QPointF(wheel.mapToGlobal(position)),
            QtCore.QPoint(0, pixels),
            QtCore.QPoint(0, angle),
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
            QtCore.Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        self.app.sendEvent(wheel, event)
        self.app.processEvents()

    def test_initial_value_is_empty_with_default_range(self):
        self.assertFalse(self.view.date().isValid())
        self.assertEqual(self.view.toolTip(), "")
        self.assertEqual(self.view.minimum_date(), QtCore.QDate(1900, 1, 1))
        self.assertEqual(self.view.maximum_date(), QtCore.QDate(2100, 12, 31))
        self.assertEqual(self.view.sizeHint(), QtCore.QSize(300, 38))

    def test_set_date_clamps_range_and_emits_only_changed_values(self):
        changed, accepted = [], []
        self.view.dateChanged.connect(lambda value: changed.append(value.getDate()))
        self.view.dateAccepted.connect(lambda value: accepted.append(value.getDate()))
        self.view.set_date_range(QtCore.QDate(2024, 2, 10), QtCore.QDate(2024, 3, 20))
        self.assertFalse(self.view.date().isValid())
        self.view.set_date(QtCore.QDate(2020, 1, 1))
        self.assertEqual(self.view.date(), QtCore.QDate(2024, 2, 10))
        self.view.setDate(QtCore.QDate(2024, 2, 10))
        self.view.set_date(QtCore.QDate(2025, 1, 1))
        self.assertEqual(self.view.date(), QtCore.QDate(2024, 3, 20))
        self.assertEqual(changed, [(2024, 2, 10), (2024, 3, 20)])
        self.assertEqual(accepted, [])
        self.assertEqual(self.view.toolTip(), "2024-03-20")
        self.view.clear()
        self.view.set_date(QtCore.QDate())
        self.assertFalse(self.view.date().isValid())
        self.assertEqual(len(changed), 3)
        self.assertEqual(changed[-1], (0, 0, 0))

    def test_invalid_range_and_input_do_not_modify_committed_state(self):
        self.view.set_date(QtCore.QDate(2024, 6, 15))
        popup = self.open_popup(column=2)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Down)
        self.assertEqual(popup.wheel.value, (2024, 6, 16))
        before = (self.view.date(), self.view.minimum_date(), self.view.maximum_date())
        changed = []
        self.view.dateChanged.connect(changed.append)
        for minimum, maximum, error in (
            (QtCore.QDate(2025, 1, 1), QtCore.QDate(2024, 1, 1), ValueError),
            (QtCore.QDate(), QtCore.QDate(2024, 1, 1), ValueError),
            (QtCore.QDate(2024, 1, 1), QtCore.QDate(), ValueError),
            ((2024, 1, 1), QtCore.QDate(2025, 1, 1), TypeError),
        ):
            with self.subTest(minimum=minimum, maximum=maximum):
                with self.assertRaises(error):
                    self.view.set_date_range(minimum, maximum)
                self.assertEqual(
                    (self.view.date(), self.view.minimum_date(), self.view.maximum_date()), before
                )
                self.assertEqual(popup.wheel.value, (2024, 6, 16))
        with self.assertRaises(TypeError):
            self.view.set_date("2024-06-15")
        self.assertEqual(changed, [])

    def test_range_changes_clamp_current_value_once_and_update_open_wheel(self):
        popup = self.open_popup((2024, 6, 15))
        changed = []
        self.view.dateChanged.connect(lambda value: changed.append(value.getDate()))
        self.view.set_date_range(QtCore.QDate(2024, 7, 1), QtCore.QDate(2024, 7, 31))
        self.assertEqual(self.view.date(), QtCore.QDate(2024, 7, 1))
        self.assertEqual(popup.wheel.value, (2024, 7, 1))
        self.assertEqual(changed, [(2024, 7, 1)])
        self.view.setMinimumDate(QtCore.QDate(2024, 7, 10))
        self.view.setMaximumDate(QtCore.QDate(2024, 7, 20))
        self.assertEqual(self.view.date(), QtCore.QDate(2024, 7, 10))
        self.assertEqual(popup.wheel.minimum, (2024, 7, 10))
        self.assertEqual(popup.wheel.maximum, (2024, 7, 20))
        self.assertEqual(changed, [(2024, 7, 1), (2024, 7, 10)])

    def test_confirm_commits_once_and_reconfirm_does_not_emit_changed(self):
        popup = self.open_popup((2024, 6, 15), column=2)
        changed, accepted = [], []
        self.view.dateChanged.connect(lambda value: changed.append(value.getDate()))
        self.view.dateAccepted.connect(lambda value: accepted.append(value.getDate()))
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Down)
        self.assertEqual(self.view.date(), QtCore.QDate(2024, 6, 15))
        self.assertEqual(popup.wheel.value, (2024, 6, 16))
        QTest.mouseClick(popup.confirm_button, QtCore.Qt.MouseButton.LeftButton)
        self.app.processEvents()
        self.assertFalse(popup.isVisible())
        self.assertEqual(self.view.date(), QtCore.QDate(2024, 6, 16))
        self.assertEqual(changed, [(2024, 6, 16)])
        self.assertEqual(accepted, [(2024, 6, 16)])
        self.open_popup(column=2)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Return)
        self.assertEqual(changed, [(2024, 6, 16)])
        self.assertEqual(accepted, [(2024, 6, 16), (2024, 6, 16)])

    def test_cancel_and_escape_discard_pending_changes(self):
        self.view.set_date(QtCore.QDate(2024, 6, 15))
        changed, accepted = [], []
        self.view.dateChanged.connect(changed.append)
        self.view.dateAccepted.connect(accepted.append)
        for action in ("cancel", "wheel_escape", "popup_escape"):
            with self.subTest(action=action):
                popup = self.open_popup(column=2)
                QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Down)
                self.assertEqual(popup.wheel.value, (2024, 6, 16))
                if action == "cancel":
                    QTest.mouseClick(popup.cancel_button, QtCore.Qt.MouseButton.LeftButton)
                else:
                    QTest.keyClick(
                        popup.wheel if action == "wheel_escape" else popup, QtCore.Qt.Key.Key_Escape
                    )
                self.app.processEvents()
                self.assertFalse(popup.isVisible())
                self.assertEqual(self.view.date(), QtCore.QDate(2024, 6, 15))
        self.assertEqual(changed, [])
        self.assertEqual(accepted, [])

    def test_cancel_from_empty_value_keeps_it_empty(self):
        popup = self.open_popup()
        self.assertTrue(QtCore.QDate(*popup.wheel.value).isValid())
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Down)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Escape)
        self.assertFalse(self.view.date().isValid())

    def test_click_outside_native_popup_cancels_without_committing(self):
        popup = self.open_popup((2024, 6, 15), column=2)
        changed, accepted = [], []
        self.view.dateChanged.connect(changed.append)
        self.view.dateAccepted.connect(accepted.append)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Down)
        outside = QtCore.QPoint(self.host.width() - 8, self.host.height() - 8)
        self.assertFalse(popup.frameGeometry().contains(self.host.mapToGlobal(outside)))
        # QWidget-targeted synthetic events bypass native popup redirection.
        # Deliver through the host's actual QWindow input path instead.
        QTest.mouseClick(self.host.windowHandle(), QtCore.Qt.MouseButton.LeftButton, pos=outside)
        self.app.processEvents()
        self.assertFalse(popup.isVisible(), "A real click outside the popup must cancel its draft")
        self.assertEqual(self.view.date(), QtCore.QDate(2024, 6, 15))
        self.assertEqual(changed, [])
        self.assertEqual(accepted, [])

    def test_year_and_month_changes_clamp_leap_and_short_month_days(self):
        popup = self.open_popup((2024, 2, 29), column=0)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Down)
        self.assertEqual(popup.wheel.value, (2025, 2, 28))
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Return)
        self.assertEqual(self.view.date(), QtCore.QDate(2025, 2, 28))
        popup = self.open_popup((2024, 1, 31), column=1)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Down)
        self.assertEqual(popup.wheel.value, (2024, 2, 29))
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Return)
        popup = self.open_popup((2024, 3, 31), column=1)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Down)
        self.assertEqual(popup.wheel.value, (2024, 4, 30))

    def test_clicking_each_field_opens_the_corresponding_reused_column(self):
        first = None
        for column in range(3):
            with self.subTest(column=column):
                popup = self.open_popup((2024, 6, 15), column=column)
                first = first or popup
                self.assertIs(popup, first)
                self.assertEqual(popup.wheel.column, column)
                self.assertEqual(len(popup.wheel._values[column]), 11)
                QTest.mouseClick(popup.cancel_button, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(len(self.view.findChildren(picker_module._DatePopup)), 1)

    def test_clicking_visible_rows_selects_each_of_the_three_columns(self):
        popup = self.open_popup((2024, 6, 15))
        wheel = popup.wheel
        expected = [(2025, 6, 15), (2025, 7, 15), (2025, 7, 16)]
        for column, date in enumerate(expected):
            with self.subTest(column=column):
                point = QtCore.QPoint(
                    int((column + 0.5) * wheel.width() / 3),
                    int((wheel.RADIUS + 1.5) * wheel.ROW_HEIGHT),
                )
                QTest.mouseClick(wheel, QtCore.Qt.MouseButton.LeftButton, pos=point)
                self.assertEqual(wheel.value, date)
                self.assertEqual(wheel.column, column)
        self.assertEqual(self.view.date(), QtCore.QDate(2024, 6, 15))

    def test_small_angle_wheel_deltas_accumulate_per_column(self):
        popup = self.open_popup((2024, 6, 15))
        for _ in range(3):
            self.send_wheel(popup.wheel, 2, angle=30)
        self.assertEqual(popup.wheel.value, (2024, 6, 15))
        self.send_wheel(popup.wheel, 1, angle=30)
        self.send_wheel(popup.wheel, 2, angle=30)
        self.assertEqual(popup.wheel.value, (2024, 6, 14))
        for _ in range(3):
            self.send_wheel(popup.wheel, 1, angle=30)
        self.assertEqual(popup.wheel.value, (2024, 5, 14))
        self.assertEqual(self.view.date(), QtCore.QDate(2024, 6, 15))

    def test_small_touchpad_pixel_deltas_accumulate_without_early_steps(self):
        popup = self.open_popup((2024, 6, 15), column=2)
        for _ in range(3):
            self.send_wheel(popup.wheel, 2, pixels=11)
        self.assertEqual(popup.wheel.value, (2024, 6, 15))
        self.send_wheel(popup.wheel, 2, pixels=11)
        self.assertEqual(popup.wheel.value, (2024, 6, 14))
        self.send_wheel(popup.wheel, 2, pixels=-22)
        self.send_wheel(popup.wheel, 2, pixels=-22)
        self.assertEqual(popup.wheel.value, (2024, 6, 15))

    def test_switching_wheel_delta_modes_discards_incompatible_remainders(self):
        popup = self.open_popup((2024, 6, 15), column=2)
        self.send_wheel(popup.wheel, 2, angle=60)
        self.send_wheel(popup.wheel, 2, pixels=22)
        self.assertEqual(popup.wheel.value, (2024, 6, 15))
        self.send_wheel(popup.wheel, 2, pixels=22)
        self.assertEqual(popup.wheel.value, (2024, 6, 14))
        self.send_wheel(popup.wheel, 2, pixels=22)
        self.send_wheel(popup.wheel, 2, angle=60)
        self.assertEqual(popup.wheel.value, (2024, 6, 14))
        self.send_wheel(popup.wheel, 2, angle=60)
        self.assertEqual(popup.wheel.value, (2024, 6, 13))

    def test_keyboard_opens_navigates_columns_and_confirms(self):
        self.view.set_date(QtCore.QDate(2024, 6, 15))
        self.view.setFocus()
        QTest.keyClick(self.view, QtCore.Qt.Key.Key_Space)
        self.app.processEvents()
        popup = self.view._popup
        self.assertTrue(popup.isVisible())
        self.assertEqual(popup.wheel.column, 0)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Right)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Down)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Right)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Up)
        self.assertEqual(popup.wheel.value, (2024, 7, 14))
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Left)
        self.assertEqual(popup.wheel.column, 1)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Enter)
        self.assertFalse(popup.isVisible())
        self.assertEqual(self.view.date(), QtCore.QDate(2024, 7, 14))

    def test_repeated_opening_reuses_popup_and_resets_canceled_draft(self):
        first = self.open_popup((2024, 6, 15), column=2)
        for _ in range(5):
            QTest.keyClick(first.wheel, QtCore.Qt.Key.Key_Down)
            QTest.mouseClick(first.cancel_button, QtCore.Qt.MouseButton.LeftButton)
            reopened = self.open_popup(column=2)
            self.assertIs(reopened, first)
            self.assertEqual(reopened.wheel.value, (2024, 6, 15))
        self.view.show_popup()
        self.assertFalse(first.isVisible())
        self.assertEqual(len(self.view.findChildren(picker_module._DatePopup)), 1)

    def test_hiding_or_disabling_closes_popup_without_commit(self):
        self.view.set_date(QtCore.QDate(2024, 6, 15))
        changed, accepted = [], []
        self.view.dateChanged.connect(changed.append)
        self.view.dateAccepted.connect(accepted.append)
        popup = self.open_popup(column=2)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Down)
        self.view.hide()
        self.app.processEvents()
        self.assertFalse(popup.isVisible())
        self.view.show()
        self.open_popup(column=2)
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Down)
        self.view.setEnabled(False)
        self.app.processEvents()
        self.assertFalse(popup.isVisible())
        self.view.show_popup()
        self.assertFalse(popup.isVisible())
        self.assertEqual(self.view.date(), QtCore.QDate(2024, 6, 15))
        self.assertEqual(changed, [])
        self.assertEqual(accepted, [])

    def test_destroying_parent_destroys_popup_and_disconnects_theme(self):
        popup = self.open_popup((2024, 6, 15))
        QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Down)
        destroyed = []
        popup.destroyed.connect(lambda *_: destroyed.append("popup"))
        popup.wheel.destroyed.connect(lambda *_: destroyed.append("wheel"))
        self.host.deleteLater()
        self.host = None
        self.view = None
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertCountEqual(destroyed, ["popup", "wheel"])
        for mode in ("dark", "light"):
            theme.set_mode(mode)
            self.app.processEvents()
        self.assertEqual(self.errors, [])

    def test_font_fallback_and_theme_switch_update_live_picker_and_popup(self):
        popup = self.open_popup((2024, 6, 15))
        self.assertIn("Microsoft YaHei UI", self.view.font().families())
        self.assertIn("Microsoft YaHei UI", popup.wheel.font().families())
        self.assertEqual(self.view.font().pixelSize(), theme.tokens.font_size)
        self.assertEqual(popup.wheel.font().pixelSize(), 16)
        available = set(QtGui.QFontDatabase.families())
        if available.intersection({"Microsoft YaHei UI", "Noto Sans CJK SC"}):
            layout = QtGui.QTextLayout("年月日", popup.wheel.font())
            layout.beginLayout()
            layout.createLine()
            layout.endLayout()
            runs = layout.glyphRuns()
            self.assertTrue(runs, "Chinese date labels must produce visible glyphs")
            self.assertTrue(all(index != 0 for run in runs for index in run.glyphIndexes()))
            self.assertNotIn("SimSun", {run.rawFont().familyName() for run in runs})
        images = {}
        for mode in ("light", "dark", "light"):
            theme.set_mode(mode)
            self.app.processEvents()
            images[mode] = self.view.grab().toImage()
            panel = popup.panel.grab().toImage()
            self.assertEqual(panel.pixelColor(3, panel.height() // 2).name(), theme.tokens.surface)
            self.assertEqual(self.view.date(), QtCore.QDate(2024, 6, 15))
            self.assertEqual(popup.wheel.value, (2024, 6, 15))
        point = QtCore.QPoint(8, self.view.height() // 2)
        self.assertNotEqual(images["light"].pixelColor(point), images["dark"].pixelColor(point))

    def test_focused_selected_row_has_no_extra_underline_in_either_theme(self):
        popup = self.open_popup((2024, 6, 15))
        wheel = popup.wheel
        for mode in ("light", "dark"):
            theme.set_mode(mode)
            for column in range(3):
                with self.subTest(mode=mode, column=column):
                    position = QtCore.QPoint(
                        int((column + 0.5) * wheel.width() / 3),
                        int((wheel.RADIUS + 0.5) * wheel.ROW_HEIGHT),
                    )
                    QTest.mouseClick(wheel, QtCore.Qt.MouseButton.LeftButton, pos=position)
                    self.app.processEvents()
                    self.assertTrue(
                        wheel.hasFocus(), "Visual regression must exercise actual focus"
                    )
                    self.assertEqual(wheel.column, column)
                    image = wheel.grab().toImage()
                    ratio = image.devicePixelRatio()
                    start = int(column * wheel.width() / 3) + 28
                    end = int((column + 1) * wheel.width() / 3) - 28
                    bottom = (wheel.RADIUS + 1) * wheel.ROW_HEIGHT
                    for y in range(bottom - 6, bottom - 3):
                        colors = {
                            image.pixelColor(round(x * ratio), round(y * ratio)).name()
                            for x in range(start, end)
                        }
                        self.assertEqual(colors, {QtGui.QColor(theme.tokens.accent).name()})

    def test_popup_disables_system_shadow_and_keeps_rounded_panel_shadow(self):
        popup = self.open_popup((2024, 6, 15))
        self.assertTrue(popup.windowFlags() & QtCore.Qt.WindowType.NoDropShadowWindowHint)
        effect = popup.panel.graphicsEffect()
        self.assertIsInstance(effect, QtWidgets.QGraphicsDropShadowEffect)
        self.assertTrue(effect.isEnabled())
        self.assertGreater(effect.blurRadius(), 0)
        image = popup.panel.grab().toImage()
        # The custom panel remains rounded: its corner has lower coverage than
        # the solid surface a little further inside the same top edge.
        self.assertLess(image.pixelColor(0, 0).alpha(), image.pixelColor(12, 4).alpha())

    def test_date_calls_follow_the_selected_backend_without_changing_ui_behavior(self):
        calendar = picker_module.calendar
        for mode in ("python", "native"):
            if mode == "native" and not calendar.native_available():
                continue
            with (
                self.subTest(text_backend=mode),
                patch.dict(os.environ, {"FLUENTPY_BACKEND": mode}),
            ):
                with patch.object(calendar, "clamp_date", wraps=calendar.clamp_date) as clamp:
                    self.view.set_date(QtCore.QDate(2024, 2, 29))
                    self.assertTrue(clamp.called)
                self.assertEqual(self.view.acceleration_backend(), mode)
                popup = self.open_popup(column=0)
                with patch.object(calendar, "step_date", wraps=calendar.step_date) as step:
                    QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Down)
                    self.assertTrue(step.called)
                    self.assertEqual(popup.wheel.value, (2025, 2, 28))
                QTest.keyClick(popup.wheel, QtCore.Qt.Key.Key_Escape)

    def test_missing_calendar_extension_is_actionable_without_breaking_import(self):
        message = "DatePicker requires the compiled fluentpy._native C extension"
        with patch.object(picker_module.calendar, "clamp_date", side_effect=RuntimeError(message)):
            import fluentpy

            self.assertIs(fluentpy.DatePicker, DatePicker)
            with self.assertRaisesRegex(RuntimeError, "compiled.*C extension"):
                DatePicker(self.host)
        self.assertFalse(self.view.date().isValid())

    def test_fresh_import_still_succeeds_when_native_module_cannot_load(self):
        source = str(Path(__file__).resolve().parents[1] / "src")
        probe = r"""
import importlib.abc, json, sys
sys.path.insert(0, sys.argv[1])
class BlockNative(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'fluentpy._native':
            raise ImportError('isolated missing native extension test')
sys.meta_path.insert(0, BlockNative())
import fluentpy
from fluentpy.qt import QtWidgets
app = QtWidgets.QApplication([])
from fluentpy.qt import QtCore
picker = fluentpy.DatePicker()
picker.set_date(QtCore.QDate(2024, 2, 29))
assert picker.acceleration_backend() == 'python'
assert picker.date().getDate() == (2024, 2, 29)
picker.set_date_range(QtCore.QDate(2025, 2, 1), QtCore.QDate(2025, 2, 28))
assert picker.date().getDate() == (2025, 2, 1)
print(json.dumps({'imported': True, 'backend': picker.acceleration_backend()}))
"""
        env = os.environ.copy()
        env["QT_QPA_PLATFORM"] = "offscreen"
        env["FLUENTPY_BACKEND"] = "auto"
        result = subprocess.run(
            [sys.executable, "-I", "-B", "-X", "utf8", "-c", probe, source],
            cwd=Path(__file__).resolve().parents[1],
            env=env,
            text=True,
            encoding="utf-8",
            capture_output=True,
            timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(json.loads(result.stdout)["imported"])


if __name__ == "__main__":
    unittest.main()
