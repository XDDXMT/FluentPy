"""Animated page switching preserves layout, effect ownership and lifetime."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import unittest

from fluentpy import AnimatedStackedWidget, ElevatedCardWidget
from fluentpy.qt import QtCore, QtGui, QtWidgets


class AnimatedStackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors, self.messages = [], []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, value, tb: self.errors.append(str(value))
        def capture_message(kind, context, message):
            if self.app.platformName() == "offscreen" and (
                message == "This plugin does not support propagateSizeHints()"
                or message.startswith("QFontDatabase: Cannot find font directory")
            ):
                return
            self.messages.append(message)
        self.old_message_handler = QtCore.qInstallMessageHandler(capture_message)
        self.host = QtWidgets.QWidget()
        self.host.resize(640, 420)
        layout = QtWidgets.QVBoxLayout(self.host)
        self.stack = AnimatedStackedWidget(self.host)
        self.stack.setContentsMargins(7, 9, 11, 13)
        layout.addWidget(self.stack)
        self.pages = []
        for index in range(4):
            page = QtWidgets.QWidget()
            page.setObjectName(str(index))
            body = QtWidgets.QVBoxLayout(page)
            body.addWidget(QtWidgets.QLabel(f"页面 {index} 😀", page))
            if index == 1:
                self.card = ElevatedCardWidget(page)
                self.card.setMinimumHeight(80)
                content = QtWidgets.QVBoxLayout(self.card)
                content.addWidget(QtWidgets.QPushButton("保留阴影", self.card))
                body.addWidget(self.card)
                self.shadow = self.card.graphicsEffect()
            body.addStretch()
            self.stack.addWidget(page)
            self.pages.append(page)
        self.host.show()
        self.app.processEvents()

    def flush(self):
        self.app.processEvents()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()

    def finish(self):
        animation = self.stack._animation
        if animation is not None:
            animation.setCurrentTime(animation.duration())
        self.flush()

    def assert_settled(self):
        self.assertIsNone(self.stack._animation)
        self.assertIsNone(self.stack._transition_widget)
        self.assertEqual(self.stack.currentWidget().geometry(), self.stack.contentsRect())

    def tearDown(self):
        self.host.close()
        self.host.deleteLater()
        self.flush()
        QtCore.qInstallMessageHandler(self.old_message_handler)
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])
        self.assertEqual(self.messages, [])

    def test_default_fade_and_slide_finish_at_layout_origin(self):
        self.stack.setCurrentIndex(1)
        animation = self.stack._animation
        self.assertEqual(animation.duration(), 180)
        self.assertEqual(animation.animationCount(), 2)
        effect = self.pages[1].graphicsEffect()
        self.assertEqual(effect.opacity(), 0.0)
        self.assertEqual(self.pages[1].pos(), self.stack.contentsRect().topLeft() + QtCore.QPoint(22, 0))
        animation.setCurrentTime(90)
        self.assertGreater(effect.opacity(), 0.0)
        self.assertLess(effect.opacity(), 1.0)
        self.assertGreater(self.pages[1].x(), self.stack.contentsRect().x())
        self.finish()
        self.assert_settled()
        self.assertIsNone(self.pages[1].graphicsEffect())
        self.assertIs(self.card.graphicsEffect(), self.shadow)

    def test_rapid_return_and_revisit_clear_every_old_effect_and_offset(self):
        for index in (1, 2, 1, 0, 3, 1, 0, 2, 0):
            self.stack.setCurrentIndex(index)
            self.stack._animation.setCurrentTime(35)
        self.finish()
        self.assert_settled()
        for page in self.pages:
            self.assertEqual(page.pos(), self.stack.contentsRect().topLeft())
            self.assertIsNone(page.graphicsEffect())
        self.assertEqual(self.stack.findChildren(QtCore.QParallelAnimationGroup), [])

    def test_same_page_does_not_restart_in_flight_animation(self):
        changes = []
        self.stack.currentAboutToChange.connect(lambda old, new: changes.append((old, new)))
        self.stack.setCurrentIndex(1)
        animation = self.stack._animation
        animation.setCurrentTime(60)
        self.stack.setCurrentWidget(self.pages[1])
        self.assertIs(self.stack._animation, animation)
        self.assertEqual(animation.currentTime(), 60)
        self.assertEqual(changes, [(0, 1)])
        self.finish()
        self.assert_settled()

    def test_resize_cleans_transition_and_uses_new_layout_geometry(self):
        self.stack.setCurrentIndex(1)
        self.stack._animation.setCurrentTime(40)
        self.host.resize(790, 510)
        self.flush()
        self.assert_settled()
        self.assertIsNone(self.pages[1].graphicsEffect())
        self.stack.setContentsMargins(15, 17, 19, 21)
        self.stack.setCurrentIndex(2)
        self.finish()
        self.assert_settled()

    def test_existing_opacity_effect_is_restored_on_interrupt_and_finish(self):
        effect = QtWidgets.QGraphicsOpacityEffect(self.pages[2])
        effect.setOpacity(0.8)
        self.pages[2].setGraphicsEffect(effect)
        self.stack.setCurrentIndex(2)
        self.assertIs(self.pages[2].graphicsEffect(), effect)
        self.stack._animation.setCurrentTime(90)
        self.assertGreater(effect.opacity(), 0)
        self.assertLess(effect.opacity(), 0.8)
        self.stack.setCurrentIndex(0)
        self.assertIs(self.pages[2].graphicsEffect(), effect)
        self.assertEqual(effect.opacity(), 0.8)
        self.stack.setCurrentIndex(2)
        self.finish()
        self.assert_settled()
        self.assertIs(self.pages[2].graphicsEffect(), effect)
        self.assertEqual(effect.opacity(), 0.8)

    def test_other_page_effects_are_not_replaced_or_deleted(self):
        effect = QtWidgets.QGraphicsColorizeEffect(self.pages[2])
        effect.setStrength(0.4)
        self.pages[2].setGraphicsEffect(effect)
        self.stack.setCurrentIndex(2)
        self.assertEqual(self.stack._animation.animationCount(), 1)
        self.assertIs(self.pages[2].graphicsEffect(), effect)
        self.finish()
        self.assert_settled()
        self.assertIs(self.pages[2].graphicsEffect(), effect)
        self.assertEqual(effect.strength(), 0.4)

    def test_base_nonanimated_switch_cleans_old_transition_immediately(self):
        self.stack.setCurrentIndex(1)
        self.stack._animation.setCurrentTime(45)
        QtWidgets.QStackedWidget.setCurrentIndex(self.stack, 3)
        self.assert_settled()
        self.assertIsNone(self.pages[1].graphicsEffect())
        self.assertEqual(self.pages[1].pos(), self.stack.contentsRect().topLeft())

    def test_remove_and_delete_current_animation_page_then_continue(self):
        self.stack.setCurrentIndex(1)
        self.stack._animation.setCurrentTime(45)
        page = self.pages[1]
        destroyed = []
        page.destroyed.connect(lambda *_: destroyed.append(True))
        self.stack.removeWidget(page)
        page.deleteLater()
        self.flush()
        self.assertEqual(destroyed, [True])
        self.assert_settled()
        self.stack.setCurrentWidget(self.pages[2])
        self.finish()
        self.assert_settled()

    def test_delete_current_page_without_remove_does_not_use_dead_effect(self):
        self.stack.setCurrentIndex(1)
        self.stack._animation.setCurrentTime(45)
        self.pages[1].deleteLater()
        self.flush()
        self.assert_settled()
        self.stack.setCurrentWidget(self.pages[2])
        self.finish()
        self.assert_settled()

    def test_remove_previously_interrupted_page_keeps_current_animation(self):
        self.stack.setCurrentIndex(1)
        self.stack._animation.setCurrentTime(45)
        self.stack.setCurrentIndex(2)
        animation = self.stack._animation
        self.stack.removeWidget(self.pages[1])
        self.pages[1].deleteLater()
        self.flush()
        self.assertIs(self.stack._animation, animation)
        self.finish()
        self.assert_settled()

    def test_hide_or_disable_animation_settles_page_and_effect(self):
        self.stack.setCurrentIndex(1)
        self.stack._animation.setCurrentTime(45)
        self.stack.hide()
        self.assertIsNone(self.stack._animation)
        self.assertIsNone(self.pages[1].graphicsEffect())
        self.stack.show()
        self.stack.setCurrentIndex(2)
        self.stack.setAnimationDuration(0)
        self.assert_settled()
        self.stack.setCurrentIndex(3)
        self.assert_settled()

    def test_reentrant_navigation_does_not_leave_or_reapply_old_effect(self):
        def redirect(_old, new):
            if new == 1:
                self.stack.setCurrentIndex(2)
        self.stack.currentAboutToChange.connect(redirect)
        self.stack.setCurrentIndex(1)
        self.finish()
        self.assertEqual(self.stack.currentIndex(), 2)
        self.assert_settled()
        self.assertIsNone(self.pages[1].graphicsEffect())

    def test_delete_stack_during_transition_has_no_late_callbacks(self):
        self.stack.setCurrentIndex(1)
        self.stack._animation.setCurrentTime(45)
        self.host.deleteLater()
        self.flush()
        # The ordinary tearDown cannot dereference the retired native host.
        self.host = QtWidgets.QWidget()
        self.flush()
        self.assertEqual(self.errors, [])


if __name__ == "__main__":
    unittest.main()
