"""Passive cards retain independent child controls and safe Qt lifetimes."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import sys
import unittest

from fluentpy import theme
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.widgets.card import CardWidget, ElevatedCardWidget, SimpleCardWidget
from fluentpy.widgets.header_card import GroupHeaderCardWidget, HeaderCardWidget

if "PySide6" in QtCore.__name__:
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest

BASE_CARDS = (CardWidget, SimpleCardWidget, ElevatedCardWidget)
ALL_CARDS = BASE_CARDS + (HeaderCardWidget, GroupHeaderCardWidget)


class _ConstructorEvents(QtCore.QObject):
    def __init__(self):
        super().__init__()
        self.top_level_shows = []

    def eventFilter(self, watched, event):
        if (
            isinstance(watched, QtWidgets.QWidget)
            and event.type() == QtCore.QEvent.Type.Show
            and watched.isWindow()
        ):
            self.top_level_shows.append(type(watched).__name__)
        return False


class CardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.original_mode = theme.mode
        self.errors = []
        self.original_hook = sys.excepthook
        sys.excepthook = lambda _kind, error, _tb: self.errors.append(str(error))
        self.host = QtWidgets.QWidget()
        self.host.resize(500, 380)
        self.layout = QtWidgets.QVBoxLayout(self.host)

    def tearDown(self):
        try:
            if self.host is not None:
                self.host.close()
                self.host.deleteLater()
            self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
            theme.set_mode(self.original_mode)
            self.app.processEvents()
            self.assertEqual(self.errors, [])
        finally:
            sys.excepthook = self.original_hook

    def card(self, kind=CardWidget):
        card = kind(parent=self.host)
        card.setMinimumSize(320, 220)
        self.layout.addWidget(card)
        self.host.show()
        self.app.processEvents()
        return card

    def enter(self, card):
        point = QtCore.QPointF(10, 10)
        self.app.sendEvent(
            card,
            QtGui.QEnterEvent(
                point, point, QtCore.QPointF(card.mapToGlobal(QtCore.QPoint(10, 10)))
            ),
        )
        card._hover_animation.setCurrentTime(card._hover_animation.duration())

    def test_radius_aliases_fonts_and_ordinary_layout(self):
        for kind in BASE_CARDS:
            card = kind(self.host)
            self.assertIsNone(card.layout())
            self.assertEqual(card.border_radius(), 8)
            self.assertEqual(card.borderRadius(), 8)
            card.set_border_radius(14)
            self.assertEqual(card.borderRadius(), 14)
            card.setBorderRadius(0)
            self.assertEqual(card.border_radius(), 0)
            layout = QtWidgets.QVBoxLayout(card)
            layout.addWidget(QtWidgets.QLabel("任意 Qt 内容", card))
            self.assertIs(card.layout(), layout)
            self.assertIn("Microsoft YaHei UI", card.font().families())
            for invalid in (None, True, 1.5, "8"):
                with self.assertRaises(TypeError):
                    card.set_border_radius(invalid)
            with self.assertRaises(ValueError):
                card.set_border_radius(-1)

    def test_all_five_types_are_passive_and_nonfocusable(self):
        for kind in ALL_CARDS:
            card = self.card(kind)
            self.assertFalse(hasattr(card, "clicked"))
            self.assertFalse(hasattr(card, "_press_progress"))
            self.assertFalse(hasattr(card, "_press_animation"))
            self.assertEqual(card.focusPolicy(), QtCore.Qt.FocusPolicy.NoFocus)
            self.assertEqual(card.cursor().shape(), QtCore.Qt.CursorShape.ArrowCursor)
            card.hide()
        self.assertNotIn("mousePressEvent", CardWidget.__dict__)
        self.assertNotIn("mouseReleaseEvent", CardWidget.__dict__)
        self.assertNotIn("keyPressEvent", CardWidget.__dict__)
        self.assertNotIn("keyReleaseEvent", CardWidget.__dict__)

    def test_card_mouse_and_keyboard_do_not_press_or_focus_surface(self):
        for kind in ALL_CARDS:
            card = self.card(kind)
            self.enter(card)
            color, geometry = card._surface_color().rgba(), QtCore.QRect(card.geometry())
            for button in (QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.MouseButton.RightButton):
                QTest.mousePress(card, button)
                self.assertEqual(card._surface_color().rgba(), color)
                QTest.mouseRelease(card, button)
            for key in (QtCore.Qt.Key.Key_Space, QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Enter):
                QTest.keyClick(card, key)
            self.assertEqual(card._surface_color().rgba(), color)
            self.assertEqual(card.geometry(), geometry)
            self.assertFalse(card.hasFocus())
            card.hide()

    def test_plain_and_nested_labels_remain_passive(self):
        card = self.card()
        layout = QtWidgets.QVBoxLayout(card)
        direct = QtWidgets.QLabel("默认标签", card)
        container = QtWidgets.QWidget(card)
        nested = QtWidgets.QLabel("嵌套标签", container)
        nested_layout = QtWidgets.QVBoxLayout(container)
        nested_layout.addWidget(nested)
        layout.addWidget(direct)
        layout.addWidget(container)
        self.app.processEvents()
        self.enter(card)
        original = card._surface_color().rgba()
        QTest.mouseClick(direct, QtCore.Qt.MouseButton.LeftButton)
        QTest.mouseClick(nested, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(card._surface_color().rgba(), original)
        self.assertFalse(card.hasFocus())

    def test_internal_controls_keep_mouse_keyboard_and_links(self):
        card = self.card()
        layout = QtWidgets.QVBoxLayout(card)
        button, entry = QtWidgets.QPushButton("按钮", card), QtWidgets.QLineEdit(card)
        link = QtWidgets.QLabel('<a href="local:test">链接</a>', card)
        for child in (button, entry, link):
            layout.addWidget(child)
        self.app.processEvents()
        clicks, links = [], []
        button.clicked.connect(lambda: clicks.append(True))
        link.linkActivated.connect(links.append)
        QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
        button.setFocus()
        QTest.keyClick(button, QtCore.Qt.Key.Key_Space)
        QTest.mouseClick(entry, QtCore.Qt.MouseButton.LeftButton)
        QTest.keyClicks(entry, "abc")
        QTest.keyClick(entry, QtCore.Qt.Key.Key_Return)
        QTest.mouseClick(
            link, QtCore.Qt.MouseButton.LeftButton, pos=QtCore.QPoint(6, link.height() // 2)
        )
        self.assertEqual(clicks, [True, True])
        self.assertEqual(entry.text(), "abc")
        self.assertEqual(links, ["local:test"])
        self.assertFalse(card.hasFocus())

    def test_disabling_resets_hover_and_controls_remain_qt_children(self):
        card = self.card()
        button = QtWidgets.QPushButton("内部操作", card)
        button.setGeometry(20, 20, 160, 35)
        button.show()
        clicks = []
        button.clicked.connect(lambda: clicks.append(True))
        self.enter(card)
        card.setEnabled(False)
        QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(clicks, [])
        self.assertFalse(button.isEnabled())
        self.assertEqual(card._hover_progress, 0.0)
        card.setEnabled(True)
        QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(clicks, [True])

    def test_only_plain_card_background_changes_on_hover(self):
        for mode in ("light", "dark"):
            theme.set_mode(mode)
            for kind in ALL_CARDS:
                card = self.card(kind)
                initial = card._surface_color().rgba()
                self.enter(card)
                if kind is CardWidget:
                    self.assertNotEqual(card._surface_color().rgba(), initial)
                else:
                    self.assertEqual(card._surface_color().rgba(), initial)
                card.hide()
                self.assertEqual(card._hover_progress, 0.0)

    def test_elevated_shadow_changes_only_on_hover_not_press_or_geometry(self):
        card = self.card(ElevatedCardWidget)
        geometry = QtCore.QRect(card.geometry())
        initial = (card._shadow.blurRadius(), card._shadow.offset().y())
        self.enter(card)
        hovered = (
            card._shadow.blurRadius(),
            card._shadow.offset().y(),
            card._shadow.color().rgba(),
        )
        self.assertNotEqual(initial, hovered[:2])
        self.assertLessEqual(card._shadow.color().alpha(), 40)
        QTest.mousePress(card, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(
            (card._shadow.blurRadius(), card._shadow.offset().y(), card._shadow.color().rgba()),
            hovered,
        )
        QTest.mouseRelease(card, QtCore.Qt.MouseButton.LeftButton)
        self.assertEqual(
            (card._shadow.blurRadius(), card._shadow.offset().y(), card._shadow.color().rgba()),
            hovered,
        )
        self.assertEqual(card.geometry(), geometry)

    def test_construction_does_not_show_or_create_native_labels(self):
        observer = _ConstructorEvents()
        self.app.installEventFilter(observer)
        try:
            for kind in ALL_CARDS:
                card = kind(parent=self.host)
                self.assertFalse(card.isVisible())
                self.assertFalse(card.isWindow())
                self.assertIsNone(card.windowHandle())
                for label in card.findChildren(QtWidgets.QLabel):
                    self.assertIsNotNone(label.parentWidget())
                    self.assertIsNone(label.windowHandle())
            self.assertEqual(observer.top_level_shows, [])
        finally:
            self.app.removeEventFilter(observer)

    def test_theme_and_hover_callbacks_are_safe_after_parent_deletion(self):
        cards = [self.card(kind) for kind in ALL_CARDS]
        for card in cards:
            self.enter(card)
        destroyed = []
        for card in cards:
            card.destroyed.connect(lambda *_: destroyed.append(True))
        self.host.close()
        self.host.deleteLater()
        self.host = None
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(len(destroyed), 5)
        for mode in ("dark", "light"):
            theme.set_mode(mode)
            self.app.processEvents()
        QTest.qWait(180)
        self.assertEqual(self.errors, [])


if __name__ == "__main__":
    unittest.main()
