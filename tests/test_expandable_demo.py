"""The demo must compose the library controls and retain native scrolling."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "examples"))
from expandable_cards import ExpandableCardsDemo
from fluentpy import FluentScrollBar, ToggleSwitch, theme
from fluentpy.qt import QtCore, QtWidgets, QT_API
if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class ExpandableDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.mode = theme.mode
        self.demo = ExpandableCardsDemo()
        self.demo.show()
        self.app.processEvents()

    def tearDown(self):
        self.demo.close()
        self.demo.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode(self.mode)

    def test_demo_uses_existing_switches_and_scrollbars_in_both_themes(self):
        for widget in (self.demo.dark_toggle, self.demo.content.sharp_enabled, self.demo.exclusive_toggle):
            self.assertIs(type(widget), ToggleSwitch)
        self.assertIs(type(self.demo.scroll.verticalScrollBar()), FluentScrollBar)
        self.assertIs(type(self.demo.scroll.horizontalScrollBar()), FluentScrollBar)
        self.demo.resize(350, 570)
        for card in self.demo.content.accordion.cards():
            card.set_expanded(True, animated=False)
        for mode in ("light", "dark"):
            theme.set_mode(mode)
            QTest.qWait(50)
            bar = self.demo.scroll.verticalScrollBar()
            self.assertGreater(bar.maximum(), 0)
            bar.setValue(bar.maximum())
            self.app.processEvents()
            slider = self.demo.content.sharpness
            point = slider.mapTo(self.demo.scroll.viewport(), slider.rect().center())
            self.assertTrue(self.demo.scroll.viewport().rect().contains(point))
            self.assertLessEqual(self.demo.scroll.widget().width(), self.demo.scroll.viewport().width())

    def test_default_switch_matches_explicit_unchecked_rendering(self):
        for mode in ("light", "dark"):
            theme.set_mode(mode)
            switch = ToggleSwitch(self.demo)
            switch.move(20, 20)
            switch.show()
            self.app.processEvents()
            initial = switch.grab().toImage()
            switch.setChecked(False)
            self.assertEqual(initial, switch.grab().toImage())
            switch.deleteLater()

    def test_programmatic_state_cancels_in_flight_knob_motion(self):
        switch = self.demo.exclusive_toggle
        switch.click()
        QTest.qWait(40)
        switch.setChecked(False)
        expected = switch.property("knobOffset")
        QTest.qWait(180)
        self.assertFalse(switch.isChecked())
        self.assertEqual(switch.property("knobOffset"), expected)
        self.assertFalse(self.demo.content.accordion.is_exclusive())


if __name__ == "__main__":
    unittest.main()
