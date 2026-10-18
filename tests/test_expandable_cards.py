"""Interaction, layout and ownership of animated expandable setting cards."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import sys
import unittest

from fluentpy import AccordionWidget, Button, ExpandableCardWidget, LineEdit, theme
from fluentpy.qt import QtCore, QtWidgets
if "PySide6" in QtCore.__name__:
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class ExpandableCardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.mode = theme.mode
        self.host = QtWidgets.QWidget()
        self.host.resize(700, 760)
        self.layout = QtWidgets.QVBoxLayout(self.host)
        self.layout.addStretch()
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda _kind, error, _tb: self.errors.append(str(error))

    def tearDown(self):
        self.host.close()
        self.host.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode(self.mode)
        self.app.processEvents()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def show_widget(self, widget):
        self.layout.insertWidget(0, widget)
        self.host.show()
        self.host.activateWindow()
        self.app.processEvents()

    def settle(self):
        QTest.qWait(360)
        self.app.processEvents()

    def test_header_is_the_only_card_toggle_and_controls_keep_their_state(self):
        card = ExpandableCardWidget("混合", expanded=True)
        label = QtWidgets.QLabel("混合模式")
        entry = LineEdit()
        entry.setText("保留的内容")
        button = Button("应用")
        for widget in (label, entry, button):
            card.body_layout.addWidget(widget)
        self.assertIs(card.viewLayout, card.body_layout)
        self.assertIs(entry.parentWidget(), card.view)
        self.show_widget(card)
        clicks = []
        button.clicked.connect(lambda: clicks.append(True))
        QTest.mouseClick(label, QtCore.Qt.MouseButton.LeftButton)
        QTest.mouseClick(card.view, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(2, 2))
        QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
        self.assertTrue(card.is_expanded())
        self.assertEqual(clicks, [True])

        QTest.mouseClick(card.header_button, QtCore.Qt.MouseButton.LeftButton)
        self.settle()
        self.assertFalse(card.is_expanded())
        self.assertFalse(card.view.isVisible())
        QTest.mouseClick(card.header_button, QtCore.Qt.MouseButton.LeftButton)
        self.settle()
        self.assertTrue(card.view.isVisible())
        self.assertEqual(entry.text(), "保留的内容")
        self.assertEqual(card.body_layout.count(), 3)

    def test_keyboard_toggle_and_disabled_header(self):
        card = ExpandableCardWidget("色度")
        card.body_layout.addWidget(LineEdit())
        self.show_widget(card)
        changed = []
        card.expandedChanged.connect(changed.append)
        card.header_button.setFocus()
        for key, expanded in ((QtCore.Qt.Key.Key_Space, True),
                              (QtCore.Qt.Key.Key_Return, False),
                              (QtCore.Qt.Key.Key_Enter, True)):
            QTest.keyClick(card.header_button, key)
            self.settle()
            self.assertEqual(card.isExpanded(), expanded)
        self.assertEqual(changed, [True, False, True])
        card.setEnabled(False)
        QTest.mouseClick(card.header_button, QtCore.Qt.MouseButton.LeftButton)
        QTest.keyClick(card.header_button, QtCore.Qt.Key.Key_Space)
        self.assertTrue(card.is_expanded())

    def test_collapse_returns_focus_to_header_without_losing_input(self):
        card = ExpandableCardWidget("输入", expanded=True)
        entry = LineEdit()
        card.body_layout.addWidget(entry)
        self.show_widget(card)
        entry.setFocus()
        QTest.keyClicks(entry, "project")
        self.assertTrue(entry.hasFocus())
        card.set_expanded(False, animated=False)
        self.app.processEvents()
        self.assertFalse(card.view.isVisible())
        self.assertTrue(card.header_button.hasFocus())
        self.assertEqual(entry.text(), "project")

    def test_open_and_close_animate_and_rapid_reversal_settles(self):
        card = ExpandableCardWidget("混合")
        content = QtWidgets.QWidget()
        content.setFixedHeight(180)
        card.body_layout.addWidget(content)
        self.show_widget(card)
        closed_height = card.height()
        card.set_expanded(True, animated=False)
        self.app.processEvents()
        open_height = card.height()
        self.assertGreater(open_height, closed_height + 150)
        card.set_expanded(False, animated=False)
        self.app.processEvents()

        card.set_expanded(True)
        QTest.qWait(50)
        opening_height = card.height()
        self.assertGreater(opening_height, closed_height)
        self.assertLess(opening_height, open_height)
        card.set_expanded(False)
        QTest.qWait(25)
        card.set_expanded(True)
        self.settle()
        self.assertTrue(card.is_expanded())
        self.assertTrue(card.view.isVisible())
        self.assertAlmostEqual(card.height(), open_height, delta=1)

        card.toggle()
        self.settle()
        self.assertFalse(card.view.isVisible())
        self.assertAlmostEqual(card.height(), closed_height, delta=1)

    def test_dynamic_content_and_wrapped_text_recalculate_expanded_height(self):
        card = ExpandableCardWidget("说明", expanded=True)
        text = QtWidgets.QLabel("这是一段会随着卡片宽度自然换行的设置说明。" * 7)
        text.setWordWrap(True)
        text.setMinimumWidth(0)
        card.body_layout.addWidget(text)
        self.show_widget(card)
        self.settle()
        wide_height = card.height()
        self.host.resize(330, 760)
        self.settle()
        self.assertGreater(card.height(), wide_height)
        narrow_height = card.height()
        extra = QtWidgets.QWidget()
        extra.setFixedHeight(70)
        card.body_layout.addWidget(extra)
        self.settle()
        self.assertGreaterEqual(card.height(), narrow_height + 70)
        extra.hide()
        self.settle()
        self.assertAlmostEqual(card.height(), narrow_height, delta=2)

    def test_accordion_default_is_independent_and_exclusive_mode_resolves_open_cards(self):
        group = AccordionWidget()
        cards = [ExpandableCardWidget(title) for title in ("混合", "色度", "锐化")]
        for card in cards:
            card.body_layout.addWidget(QtWidgets.QLabel("设置内容"))
            group.addCard(card)
        self.show_widget(group)
        self.assertEqual(group.cards(), tuple(cards))
        self.assertFalse(group.is_exclusive())
        cards[0].set_expanded(True, animated=False)
        cards[1].set_expanded(True, animated=False)
        self.assertTrue(cards[0].is_expanded())
        self.assertTrue(cards[1].is_expanded())
        group.set_exclusive(True)
        self.settle()
        self.assertEqual(sum(card.is_expanded() for card in cards), 1)
        cards[2].setExpanded(True, animated=False)
        self.settle()
        self.assertEqual([card.isExpanded() for card in cards], [False, False, True])
        group.setExclusive(False)
        cards[0].set_expanded(True, animated=False)
        self.assertTrue(cards[0].is_expanded())
        self.assertTrue(cards[2].is_expanded())

    def test_removing_card_disconnects_group_and_never_shows_a_detached_window(self):
        group = AccordionWidget(exclusive=True)
        first = ExpandableCardWidget("混合", expanded=True)
        removed = ExpandableCardWidget("色度")
        group.add_card(first)
        group.add_card(removed)
        self.show_widget(group)
        self.assertTrue(group.remove_card(removed))
        self.assertEqual(group.cards(), (first,))
        self.assertFalse(removed.isVisible())
        removed.set_expanded(True, animated=False)
        self.assertTrue(first.is_expanded())
        self.assertFalse(removed.isVisible())
        # A removed card remains reusable, and transferring ownership is safe.
        group.add_card(removed)
        self.settle()
        self.assertTrue(removed.isVisible())
        self.assertFalse(first.is_expanded())
        destroyed = []
        removed.destroyed.connect(lambda *_: destroyed.append(True))
        self.assertTrue(group.removeCard(removed, delete=True))
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(destroyed, [True])
        self.assertFalse(group.remove_card(removed))

    def test_theme_changes_and_deletion_during_animation_are_safe(self):
        group = AccordionWidget(exclusive=True)
        for title in ("混合", "色度", "锐化"):
            card = ExpandableCardWidget(title)
            content = QtWidgets.QWidget()
            content.setFixedHeight(120)
            card.body_layout.addWidget(content)
            group.add_card(card)
        self.show_widget(group)
        before = {id(widget) for widget in self.app.topLevelWidgets() if widget.isVisible()}
        for card, mode in zip(group.cards(), ("dark", "light", "dark")):
            card.toggle()
            theme.set_mode(mode)
            QTest.qWait(30)
        self.assertEqual({id(widget) for widget in self.app.topLevelWidgets() if widget.isVisible()}, before)
        group.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode("light")
        self.settle()
        self.assertEqual(self.errors, [])

    def test_transferring_card_and_direct_child_deletion_update_both_containers(self):
        source = AccordionWidget(exclusive=True)
        target = AccordionWidget(exclusive=True)
        stack = QtWidgets.QWidget()
        stack_layout = QtWidgets.QVBoxLayout(stack)
        stack_layout.addWidget(source)
        stack_layout.addWidget(target)
        moving = ExpandableCardWidget("混合", expanded=True)
        resident = ExpandableCardWidget("色度", expanded=True)
        source.add_card(moving)
        target.add_card(resident)
        self.show_widget(stack)

        target.add_card(moving)
        self.settle()
        self.assertEqual(source.cards(), ())
        self.assertEqual(target.cards(), (resident, moving))
        self.assertIs(moving.parentWidget(), target)
        self.assertTrue(moving.isVisible())
        self.assertTrue(moving.is_expanded())
        self.assertFalse(resident.is_expanded())

        # Qt applications can delete owned children directly rather than using
        # the convenience removal method; future exclusivity must still work.
        moving.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(target.cards(), (resident,))
        resident.set_expanded(True, animated=False)
        newcomer = ExpandableCardWidget("锐化", expanded=True)
        target.add_card(newcomer)
        self.settle()
        self.assertFalse(resident.is_expanded())
        self.assertTrue(newcomer.is_expanded())


if __name__ == "__main__":
    unittest.main()
