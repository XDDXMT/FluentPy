"""The general slider playground presents values in their original units."""
import os
from pathlib import Path
import sys
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'examples'))

from fluentpy import ToolTipSlider, RangeSlider
from fluentpy.qt import QtCore, QtWidgets
from sliders import SliderExamples


class SliderDemoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def test_tooltip_example_keeps_raw_numeric_value_across_custom_bounds(self):
        demo = SliderExamples()
        demo.resize(860, 600)
        demo.show()
        demo.kind.setCurrentIndex(1)
        demo.maximum_input.setValue(500)
        demo.value_input.setValue(137)
        self.assertIsInstance(demo.preview, ToolTipSlider)
        self.assertEqual(demo.preview.valueFormat(), '{value}')
        demo.preview.show_value_tip()
        self.assertEqual(demo.preview._value_label.text(), '137')
        self.assertEqual(demo.readout.text(), '137')
        demo.orientation.setCurrentIndex(1)
        self.assertEqual(demo.preview.valueFormat(), '{value}')
        self.assertEqual(demo.preview.value(), 137)
        demo.close()
        demo.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)

    def test_changing_kind_disposes_running_tooltip_and_range_animations(self):
        demo = SliderExamples()
        demo.resize(860, 600)
        demo.show()
        demo.kind.setCurrentIndex(1)
        old = demo.preview
        old.show_value_tip()
        label = old._value_label
        removed = []
        label.destroyed.connect(lambda *_args: removed.append(True))
        demo.kind.setCurrentIndex(2)
        self.assertIsInstance(demo.preview, RangeSlider)
        self.assertFalse(label.isVisible())
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.assertEqual(removed, [True])
        demo.close()
        demo.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)


if __name__ == '__main__':
    unittest.main()
