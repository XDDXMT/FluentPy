from __future__ import annotations

import sys

from fluentpy import BreadcrumbBar, NavigationView, Pivot, SegmentedWidget, TabBar
from fluentpy.qt import QtGui, QtWidgets


def app() -> QtWidgets.QApplication:
    instance = QtWidgets.QApplication.instance()
    if instance is None:
        instance = QtWidgets.QApplication(sys.argv[:1])
    return instance


def test_navigation_view_switches_routes_without_animation() -> None:
    app()
    view = NavigationView()
    first = QtWidgets.QLabel("first")
    second = QtWidgets.QLabel("second")

    view.add_sub_interface(first, QtGui.QIcon(), "First", "first")
    view.add_sub_interface(second, QtGui.QIcon(), "Second", "second")

    view.set_current_route("second", animated=False)

    assert view.current_route() == "second"
    assert view.stack.currentWidget() is second


def test_pivot_and_segmented_track_current_item() -> None:
    app()
    for cls in (Pivot, SegmentedWidget):
        control = cls()
        seen: list[str] = []
        control.currentChanged.connect(seen.append)
        control.add_item("start", "Start")
        control.add_item("pause", "Pause")

        control.set_current_item("pause", animated=False)

        assert control.current_item() is not None
        assert control.current_item().text() == "Pause"
        assert seen[-1] == "pause"


def test_breadcrumb_and_tabbar_emit_current_route() -> None:
    app()
    breadcrumb = BreadcrumbBar()
    breadcrumb_seen: list[str] = []
    breadcrumb.currentChanged.connect(breadcrumb_seen.append)
    breadcrumb.add_item("home", "Home")
    breadcrumb.add_item("leaf", "Leaf")
    breadcrumb.set_current_item("home")

    tabs = TabBar()
    tab_seen: list[str] = []
    tabs.currentChanged.connect(tab_seen.append)
    tabs.add_tab("desk", "Desk")
    tabs.add_tab("notes", "Notes")
    tabs.set_current_tab("notes")

    assert breadcrumb_seen[-1] == "home"
    assert tab_seen[-1] == "notes"
