"""Native preview wiring, task states and cleanup in the feedback playground."""

import os
import sys
import unittest
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from workbench_feedback import FeedbackPlayground

from fluentpy import ColorToast, InfoBar, ProgressInfoBar, ProgressToast, Toast
from fluentpy.qt import QT_API, QtCore, QtWidgets

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class FeedbackPlaygroundTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, error, tb: self.errors.append(error)
        self.dialog_calls = []
        self.owner = QtWidgets.QWidget()
        self.owner.resize(1000, 800)
        layout = QtWidgets.QVBoxLayout(self.owner)
        self.play = FeedbackPlayground(
            lambda: self.dialog_calls.append("masked"),
            lambda: self.dialog_calls.append("frameless"),
        )
        layout.addWidget(self.play)
        self.owner.show()
        QTest.qWait(190)

    def tearDown(self):
        self.owner.close()
        self.owner.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def settle(self, message):
        message._reveal.setCurrentTime(message.SHOW_DURATION)
        message._stack_motion.setCurrentTime(240)
        self.app.processEvents()

    def test_initial_view_is_one_native_inline_preview_without_spawned_notifications(self):
        self.assertIs(type(self.play._preview), InfoBar)
        self.assertEqual(self.play._messages, {})
        self.assertFalse(self.play.advanced.is_expanded())
        self.assertTrue(self.play.embedded_page.isHidden())
        self.assertTrue(self.play.dialog_page.isHidden())
        self.assertIsNone(self.play._preview._stack)
        self.assertEqual(self.play.inline_body.indexOf(self.play._preview), 0)
        self.assertFalse(self.play.stack_button.isVisible())

    def test_editing_updates_real_widget_and_custom_action_is_usable(self):
        self.play.title_input.setText("修改后的标题")
        self.play.detail_input.setText("现在可以点击自己的操作。")
        self.play.action_check.setChecked(True)
        self.play.action_input.setText("立即重试")
        QTest.qWait(220)
        self.assertEqual(self.play._preview.title(), "修改后的标题")
        self.assertEqual(self.play._preview.action_button.text(), "立即重试")
        self.play._preview.action_button.click()
        self.assertIn("立即重试", self.play.result.text())
        self.assertTrue(self.play._preview.isVisible())
        self.play.component.setCurrentIndex(1)
        self.play.tone.setCurrentIndex(1)
        self.play.refresh_preview()
        green = self.play._preview.color()
        self.play.tone.setCurrentIndex(3)
        self.play.refresh_preview()
        self.assertNotEqual(green, self.play._preview.color())
        self.play.color_picker.set_color("#8b54bd")
        self.play.refresh_preview()
        self.assertEqual(self.play._preview.color().name(), "#8b54bd")

    def test_each_component_selects_its_existing_class_and_valid_placement(self):
        for index, cls in enumerate((InfoBar, ColorToast, ProgressInfoBar, ProgressToast, Toast)):
            self.play.component.setCurrentIndex(index)
            self.play.refresh_preview()
            self.app.processEvents()
            self.assertIs(type(self.play._preview), cls)
            self.assertFalse(self.play._preview.isWindow())
            if index not in (0, 2):
                self.assertIn(self.play.placement(), Toast.PLACEMENTS)
        self.assertEqual({w for w in self.app.topLevelWidgets() if w.isVisible()}, {self.owner})
        self.play.position.setCurrentIndex(len(self.play._positions) - 1)
        message = self.play.test_current()
        self.assertIs(message._target, self.play.test_button)
        self.assertFalse(self.play.stack_button.isVisible())

    def test_task_slider_unknown_and_terminal_choice_drive_task_state(self):
        self.play.component.setCurrentIndex(4)
        self.play.refresh_preview()
        self.play.component.setCurrentIndex(2)
        self.play.progress.setValue(11)
        for index in (2, 3):
            self.play.component.setCurrentIndex(index)
            self.play.task_state.setCurrentIndex(0)
            self.play.refresh_preview()
            self.play.progress.setValue(63)
            self.assertEqual(self.play._preview.value(), 63)
            self.play.unknown.setChecked(True)
            self.play.refresh_preview()
            self.assertTrue(self.play._preview.is_indeterminate())
            self.assertFalse(self.play.progress.isEnabled())
            self.play.unknown.setChecked(False)
            self.play.task_state.setCurrentIndex(1)
            self.play.refresh_preview()
            self.assertEqual(self.play._preview.state(), "success")
            self.assertEqual(self.play._preview.value(), 100)
            self.play.task_state.setCurrentIndex(2)
            self.play.refresh_preview()
            self.assertEqual(self.play._preview.state(), "error")

    def test_window_test_and_three_message_stack_use_real_notification_manager(self):
        self.play.component.setCurrentIndex(1)
        self.play.auto_close.setChecked(False)
        self.play.refresh_preview()
        self.play.test_stack()
        self.assertEqual(len(self.play._messages), 3)
        messages = list(self.play._messages.values())
        for message in messages:
            self.settle(message)
        self.assertIs(messages[0]._stack, messages[2]._stack)
        self.assertIsNot(messages[0]._stack, self.play._preview._stack)
        self.assertTrue(all(m.parentWidget() is self.owner for m in messages))
        self.play.clear_messages()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(self.play._messages, {})
        self.assertIsNone(self.play._preview)

    def test_switching_sections_retains_embedded_state_and_closes_window_messages(self):
        self.play.component.setCurrentIndex(3)
        self.play.refresh_preview()
        message = self.play.test_current()
        self.play.tabs.set_current_item("embedded")
        self.app.processEvents()
        self.assertFalse(message.isVisible())
        self.assertTrue(self.play.embedded_page.isVisible())
        self.assertFalse(self.play.editor.isVisible())
        self.play.embedded_examples.note_input.setText("保留我的备注")
        self.play.tabs.set_current_item("dialogs")
        self.play.tabs.set_current_item("embedded")
        self.assertEqual(self.play.embedded_examples.note_input.text(), "保留我的备注")
        self.play.tabs.set_current_item("playground")
        QTest.qWait(190)
        self.assertIsInstance(self.play._preview, ProgressToast)

    def test_dialog_selector_opens_only_the_selected_style(self):
        self.assertEqual(self.dialog_calls, [])
        self.play.tabs.set_current_item("dialogs")
        self.play.dialog_button.click()
        self.play.dialog_choice.setCurrentIndex(1)
        self.play.dialog_button.click()
        self.assertEqual(self.dialog_calls, ["masked", "frameless"])

    def test_reset_and_hide_stop_notifications_and_task_animation(self):
        self.play.component.setCurrentIndex(2)
        self.play.unknown.setChecked(True)
        self.play.action_check.setChecked(True)
        self.play.advanced.set_expanded(True, animated=False)
        self.play.reset_options()
        self.play.refresh_preview()
        self.assertFalse(self.play.advanced.is_expanded())
        self.assertFalse(self.play.unknown.isChecked())
        self.assertFalse(self.play.action_check.isChecked())
        self.play.component.setCurrentIndex(3)
        self.play.refresh_preview()
        message = self.play.test_current()
        removed = []
        message.destroyed.connect(lambda: removed.append(True))
        self.play.hide()
        self.assertFalse(message.isVisible())
        self.assertFalse(self.play._refresh.isActive())
        self.assertIsNone(self.play._preview)
        self.assertEqual(message._activity.state(), QtCore.QAbstractAnimation.State.Stopped)
        self.app.processEvents()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(removed, [True])


if __name__ == "__main__":
    unittest.main()
