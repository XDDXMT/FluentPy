"""Fixed header/footer, scrolling middle list and non-destructive navigation search."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import unittest

from fluentpy import FluentScrollBar, NavigationView, SearchLineEdit, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets


class SidebarRegionsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.mode = theme.mode
        self.view = NavigationView()
        self.view.resize(640, 420)
        self.sidebar = self.view.sidebar
        self.sidebar.set_expanded_width(216)
        self.sidebar.set_expanded(True)
        self.sidebar._width_animation.setCurrentTime(150)
        self.search = SearchLineEdit("搜索导航")
        self.sidebar.set_header_widget(self.search)
        self.header = self.view.add_sub_interface(
            QtWidgets.QLabel("概览"), QtGui.QIcon(), "概览", "overview", "header"
        )
        self.entries = []
        for index in range(30):
            item = self.view.add_sub_interface(
                QtWidgets.QLabel(str(index)), QtGui.QIcon(), f"页面 {index}", str(index)
            )
            self.entries.append(item)
        self.footer = self.view.add_sub_interface(
            QtWidgets.QLabel("设置"), QtGui.QIcon(), "设置", "settings", "bottom"
        )
        self.view.show()
        self.settle()

    def tearDown(self):
        self.view.close()
        self.view.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode(self.mode)

    def settle(self):
        for _ in range(3):
            self.app.processEvents()

    def assert_region_backgrounds_match_sidebar(self):
        # Render the sidebar's own surface without its child regions. Compare
        # fixed and scroll-region gutters at exactly the same coordinates so
        # the intentional vertical gradient is preserved, not approximated.
        reference = QtGui.QPixmap(self.sidebar.size())
        reference.fill(QtCore.Qt.GlobalColor.transparent)
        self.sidebar.render(
            reference,
            QtCore.QPoint(),
            QtGui.QRegion(),
            QtWidgets.QWidget.RenderFlag.DrawWindowBackground,
        )
        expected = reference.toImage()
        actual = self.sidebar.grab().toImage()
        for name, region in (
            ("header", self.sidebar.header_widget),
            ("viewport", self.sidebar.scroll_area.viewport()),
            ("footer", self.sidebar.footer_widget),
        ):
            for x in (1, max(1, region.width() - 3)):
                point = region.mapTo(self.sidebar, QtCore.QPoint(x, region.height() // 2))
                with self.subTest(
                    region=name, mode=theme.mode.value, width=self.sidebar.width(), point=point
                ):
                    self.assertEqual(actual.pixelColor(point), expected.pixelColor(point))

    def test_scrolling_middle_keeps_header_search_and_settings_fixed(self):
        bar = self.sidebar.scroll_area.verticalScrollBar()
        self.assertIs(type(bar), FluentScrollBar)
        self.assertGreater(bar.maximum(), 0)
        origin = {
            id(widget): widget.mapTo(self.sidebar, QtCore.QPoint())
            for widget in (self.search, self.header, self.footer)
        }
        before = self.entries[-1].mapTo(self.sidebar, QtCore.QPoint()).y()
        bar.setValue(bar.maximum())
        self.settle()
        self.assertLess(self.entries[-1].mapTo(self.sidebar, QtCore.QPoint()).y(), before)
        for widget in (self.search, self.header, self.footer):
            self.assertEqual(widget.mapTo(self.sidebar, QtCore.QPoint()), origin[id(widget)])
        self.footer.clicked.emit(True)
        self.assertEqual(self.view.current_route(), "settings")
        self.assertTrue(self.sidebar._indicator.isVisible())

    def test_selected_middle_entry_scrolls_into_view_and_indicator_never_leaks_into_fixed_regions(
        self,
    ):
        self.view.set_current_route("29", animated=False)
        self.settle()
        self.assertTrue(self.sidebar._indicator.isVisible())
        self.sidebar.scroll_area.verticalScrollBar().setValue(0)
        self.settle()
        self.assertTrue(self.sidebar._indicator.isHidden())
        self.assertEqual(self.view.current_route(), "29")
        self.sidebar.scroll_area.verticalScrollBar().setValue(
            self.sidebar.scroll_area.verticalScrollBar().maximum()
        )
        self.settle()
        self.assertFalse(self.sidebar._indicator.isHidden())

    def test_search_keeps_current_page_and_route_availability(self):
        self.view.set_current_route("1", animated=False)
        self.sidebar.set_filter_text("页面 29")
        self.settle()
        self.assertEqual(self.view.current_route(), "1")
        self.assertTrue(self.view.is_route_visible("1"))
        self.assertTrue(self.entries[1].isHidden())
        self.assertFalse(self.entries[29].isHidden())
        self.assertFalse(self.header.isHidden())
        self.assertFalse(self.footer.isHidden())
        self.sidebar.setFilterText("不存在")
        self.settle()
        self.assertTrue(self.sidebar._empty_label.isVisible())
        self.view.set_route_visible("2", False)
        self.sidebar.set_filter_text("")
        self.settle()
        self.assertEqual(self.view.current_route(), "1")
        self.assertFalse(self.entries[1].isHidden())
        self.assertTrue(self.entries[2].isHidden())

    def test_custom_widget_ownership_and_compact_mode(self):
        footer = QtWidgets.QLabel("本地账号")
        self.sidebar.set_footer_widget(footer)
        self.settle()
        self.assertTrue(footer.isVisible())
        self.sidebar.set_expanded(False)
        self.sidebar._width_animation.setCurrentTime(150)
        self.settle()
        self.assertFalse(self.search.isVisible())
        self.assertFalse(footer.isVisible())
        self.assertTrue(self.footer.isVisible())
        bar = self.sidebar.scroll_area.verticalScrollBar()
        self.assertFalse(bar.isVisible())
        bar.setValue(0)
        viewport = self.sidebar.scroll_area.viewport()
        point = viewport.rect().center()
        wheel = QtGui.QWheelEvent(
            QtCore.QPointF(point),
            QtCore.QPointF(viewport.mapToGlobal(point)),
            QtCore.QPoint(),
            QtCore.QPoint(0, -120),
            QtCore.Qt.MouseButton.NoButton,
            QtCore.Qt.KeyboardModifier.NoModifier,
            QtCore.Qt.ScrollPhase.NoScrollPhase,
            False,
        )
        self.app.sendEvent(viewport, wheel)
        self.assertGreater(bar.value(), 0)
        self.sidebar.set_expanded(True)
        self.sidebar._width_animation.setCurrentTime(150)
        self.settle()
        self.assertTrue(self.search.isVisible())
        destroyed = []
        footer.destroyed.connect(lambda *_: destroyed.append(True))
        self.sidebar.set_footer_widget(None)
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(destroyed, [True])
        self.search.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        replacement = SearchLineEdit("新搜索")
        self.sidebar.set_header_widget(replacement)
        self.settle()
        self.assertTrue(replacement.isVisible())

    def test_middle_surface_uses_sidebar_theme_instead_of_os_palette(self):
        for mode in ("light", "dark"):
            theme.set_mode(mode)
            # A Windows viewport can fill the propagated Window palette even
            # with transparent CSS. Force that background in offscreen tests
            # too, so this regression cannot pass only on the test platform.
            for region in (
                self.sidebar.header_widget,
                self.sidebar.scroll_area.viewport(),
                self.sidebar.scroll_widget,
                self.sidebar.footer_widget,
            ):
                palette = region.palette()
                palette.setColor(
                    QtGui.QPalette.ColorRole.Window,
                    QtGui.QColor("#1f2633" if mode == "dark" else "#f7f9fc"),
                )
                region.setPalette(palette)
                region.setAutoFillBackground(True)
            self.settle()
            self.assert_region_backgrounds_match_sidebar()

    def test_surface_stays_aligned_across_scroll_positions_widths_and_compact_theme_changes(self):
        bar = self.sidebar.scroll_area.verticalScrollBar()
        for mode in ("dark", "light", "dark"):
            theme.set_mode(mode)
            for expanded, width in ((True, 216), (True, 280), (False, 280)):
                self.sidebar.set_expanded_width(width)
                self.sidebar.set_expanded(expanded)
                self.sidebar._width_animation.setCurrentTime(150)
                self.settle()
                for value in (0, bar.maximum() // 2, bar.maximum()):
                    bar.setValue(value)
                    self.settle()
                    self.assert_region_backgrounds_match_sidebar()

    def test_invalid_zone_requests_do_not_reparent_structural_widgets(self):
        with self.assertRaises(ValueError):
            self.sidebar.set_header_widget(self.sidebar.header_widget)
        with self.assertRaises(ValueError):
            self.sidebar.set_footer_widget(self.search)
        count = self.view.stack.count()
        page = QtWidgets.QLabel("invalid")
        with self.assertRaises(ValueError):
            self.view.add_sub_interface(page, QtGui.QIcon(), "invalid", "invalid", "unknown")
        self.assertEqual(self.view.stack.count(), count)
        self.assertIsNone(page.parentWidget())
        page.deleteLater()

    def test_hidden_sidebar_restores_width_before_first_show(self):
        self.view.hide()
        self.sidebar.set_expanded(False)
        self.assertEqual(self.sidebar.width(), 48)
        self.sidebar.set_expanded(True)
        self.assertEqual(self.sidebar.width(), 216)
        self.assertEqual(
            self.sidebar._width_animation.state(), QtCore.QAbstractAnimation.State.Stopped
        )


if __name__ == "__main__":
    unittest.main()
