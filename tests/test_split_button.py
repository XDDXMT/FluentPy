"""Two-line split actions retain separate mouse, keyboard and menu semantics."""

import os
import sys
import unittest
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from fluentpy import AccentSplitButton, ActionMenu, FluentIcon, SplitButton, fluent_icon, theme
from fluentpy.qt import QT_API, QtCore, QtGui, QtWidgets

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class SplitButtonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.previous_hook = sys.excepthook
        sys.excepthook = lambda kind, error, tb: self.errors.append(str(error))
        self.previous_mode = theme.mode
        self.host = QtWidgets.QWidget()
        self.host.resize(780, 520)
        self.host.show()
        self.app.processEvents()

    def tearDown(self):
        self.host.close()
        self.host.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode(self.previous_mode)
        self.app.processEvents()
        sys.excepthook = self.previous_hook
        self.assertEqual(self.errors, [])

    def create(self, cls, description="1.0"):
        menu = ActionMenu(self.host)
        button = cls("启动游戏", self.host, menu=menu, description=description)
        button.setGeometry(32, 48, 240, button.sizeHint().height())
        button.show()
        self.app.processEvents()
        return button, menu

    def test_optional_description_keeps_single_line_api_and_restores_its_size(self):
        for cls in (SplitButton, AccentSplitButton):
            with self.subTest(cls=cls.__name__):
                button, menu = self.create(cls, "")
                self.assertEqual(button.sizeHint().height(), 32)
                self.assertEqual(button.menu_button.width(), 32)
                self.assertEqual(button.text(), "启动游戏")
                button.setDescription("1.1 · 预览版")
                self.assertGreaterEqual(button.sizeHint().height(), 52)
                self.assertEqual(button.description(), "1.1 · 预览版")
                self.assertEqual(button.accessibleDescription(), button.description())
                self.assertEqual(button.main_button.accessibleDescription(), button.description())
                button.set_description("")
                self.assertEqual(button.sizeHint().height(), 32)
                self.assertEqual(button.menu_button.width(), 32)
                button.setText("导出文档")
                self.assertEqual(button.text(), "导出文档")
                button.hide()

    def test_both_hit_regions_fill_a_taller_button_in_both_themes(self):
        for mode in ("light", "dark"):
            theme.set_mode(mode)
            for cls in (SplitButton, AccentSplitButton):
                with self.subTest(mode=mode, cls=cls.__name__):
                    button, menu = self.create(cls)
                    menu.add_action("切换版本")
                    button.resize(260, 76)
                    self.app.processEvents()
                    self.assertEqual(button.main_button.height(), 76)
                    self.assertEqual(button.menu_button.height(), 76)
                    self.assertEqual(button.menu_button.width(), 40)
                    calls = []
                    button.clicked.connect(lambda: calls.append(True))
                    QTest.mouseClick(
                        button.main_button,
                        QtCore.Qt.MouseButton.LeftButton,
                        pos=QtCore.QPoint(24, 68),
                    )
                    self.assertEqual(calls, [True])
                    QTest.mouseClick(
                        button.menu_button,
                        QtCore.Qt.MouseButton.LeftButton,
                        pos=QtCore.QPoint(20, 68),
                    )
                    self.assertIs(menu.anchor_widget(), button)
                    self.assertTrue(menu.isVisible())
                    self.assertEqual(calls, [True])
                    self.assertFalse(button.grab().isNull())
                    menu.dismiss(immediate=True)
                    button.hide()

    def test_selecting_an_option_does_not_run_the_primary_action(self):
        for cls in (SplitButton, AccentSplitButton):
            with self.subTest(cls=cls.__name__):
                button, menu = self.create(cls)
                menu.add_action("1.1", callback=lambda: button.set_description("1.1"))
                calls = []
                button.clicked.connect(lambda: calls.append(button.description()))
                QTest.mouseClick(button.menu_button, QtCore.Qt.MouseButton.LeftButton)
                menu._reveal.setCurrentTime(menu.SHOW_DURATION)
                QTest.keyClick(menu, QtCore.Qt.Key.Key_Return)
                self.assertEqual(button.description(), "1.1")
                self.assertEqual(calls, [])
                menu.dismiss(immediate=True)
                QTest.mouseClick(button.main_button, QtCore.Qt.MouseButton.LeftButton)
                self.assertEqual(calls, ["1.1"])
                button.hide()

    def test_keyboard_opens_menu_and_enter_space_activate_main_once(self):
        button, menu = self.create(AccentSplitButton)
        menu.add_action("更多版本")
        calls = []
        button.clicked.connect(lambda: calls.append(True))
        for key in (QtCore.Qt.Key.Key_Return, QtCore.Qt.Key.Key_Space):
            QTest.keyClick(button.main_button, key)
        self.assertEqual(len(calls), 2)
        QTest.keyClick(button.main_button, QtCore.Qt.Key.Key_Down)
        self.assertTrue(menu.isVisible())
        self.assertEqual(len(calls), 2)
        QTest.keyClick(menu, QtCore.Qt.Key.Key_Escape)
        menu._reveal.setCurrentTime(menu.HIDE_DURATION)
        self.app.processEvents()
        self.assertFalse(menu.isVisible())
        self.assertTrue(button.main_button.hasFocus())

    def test_disable_blocks_both_actions_and_dismisses_an_open_menu(self):
        button, menu = self.create(SplitButton)
        menu.add_action("版本")
        calls = []
        button.clicked.connect(lambda: calls.append(True))
        button.show_menu()
        button.setEnabled(False)
        self.assertFalse(menu.isVisible())
        button.main_button.click()
        button.menu_button.click()
        button.show_menu()
        self.assertEqual(calls, [])
        self.assertFalse(menu.isVisible())

    def test_arrow_press_and_rotation_stay_independent_from_main(self):
        button, menu = self.create(AccentSplitButton)
        menu.add_action("版本")
        QTest.mousePress(button.menu_button, QtCore.Qt.MouseButton.LeftButton)
        button.menu_button._press_animation.setCurrentTime(35)
        self.assertGreater(button.menu_button._press_progress, 0)
        self.assertEqual(button.main_button._press_progress, 0)
        QTest.mouseRelease(button.menu_button, QtCore.Qt.MouseButton.LeftButton)
        button.menu_button._arrow_animation.setCurrentTime(80)
        self.assertGreater(button.menu_button._arrow_progress, 0)
        self.assertLess(button.menu_button._arrow_progress, 1)
        menu.dismiss(immediate=True)

    def test_long_description_icon_and_larger_font_fit_without_paint_errors(self):
        for cls in (SplitButton, AccentSplitButton):
            with self.subTest(cls=cls.__name__):
                button, menu = self.create(
                    cls, "一个很长的自定义版本说明，用于检查窄窗口与字体变化"
                )
                button.setIcon(fluent_icon(FluentIcon.ARROW_EXPORT))
                button.setIconSize(QtCore.QSize(20, 20))
                self.assertEqual(button.iconSize(), QtCore.QSize(20, 20))
                font = QtGui.QFont(button.main_button.font())
                font.setPixelSize(28)
                button.main_button.setFont(font)
                hint = button.minimumSizeHint()
                self.assertGreater(hint.height(), 52)
                button.resize(hint)
                self.app.processEvents()
                self.assertEqual(button.menu_button.height(), button.height())
                self.assertFalse(button.grab().isNull())
                self.assertEqual(button.description(), button.accessibleDescription())
                button.hide()

    def test_workbench_example_changes_version_without_launching(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
        from buttons import ButtonExamples

        example = ButtonExamples(self.host)
        example.resize(740, 480)
        example.show()
        calls = []
        example.launch_split.clicked.connect(lambda: calls.append(True))
        versions = example.launch_split.menu().actions()
        versions[1].trigger()
        self.assertEqual(example.launch_split.description(), "1.1 · 预览版")
        self.assertFalse(versions[0].isChecked())
        self.assertTrue(versions[1].isChecked())
        self.assertEqual(calls, [])
        example.launch_split.main_button.click()
        self.assertEqual(calls, [True])
        self.assertIn("1.1 · 预览版", example.result.text())
