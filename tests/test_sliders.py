"""Input/value semantics for horizontal, vertical, tooltip and range sliders."""
import os
import sys
import unittest
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
from fluentpy import Slider, ToolTipSlider, RangeSlider, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets, QT_API
if QT_API == 'PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class SliderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, error, tb: self.errors.append(str(error))
        self.owner = QtWidgets.QWidget()
        self.owner.resize(600, 430)
        self.owner.show()

    def tearDown(self):
        self.owner.close()
        self.owner.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def slider(self, cls=Slider, orientation=QtCore.Qt.Orientation.Horizontal):
        widget = cls(orientation, self.owner)
        widget.setGeometry(45, 100, 400, 34) if orientation == QtCore.Qt.Orientation.Horizontal else widget.setGeometry(250, 45, 34, 300)
        widget.setRange(0, 100)
        widget.show()
        return widget

    def click(self, widget, value):
        QTest.mouseClick(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(value).toPoint())

    def finish_motion(self, widget):
        for name in ('_position_animation', '_range_animation', '_tip_fade', '_tip_motion'):
            animation = getattr(widget, name, None)
            if animation is not None and animation.state() == QtCore.QAbstractAnimation.State.Running:
                animation.setCurrentTime(animation.duration())

    def test_track_click_and_drag_match_painted_handle_in_both_orientations(self):
        for orientation in (QtCore.Qt.Orientation.Horizontal, QtCore.Qt.Orientation.Vertical):
            widget = self.slider(orientation=orientation)
            self.click(widget, 75)
            self.assertAlmostEqual(widget.value(), 75, delta=1)
            point = widget._point_for_value(widget.value()).toPoint()
            QTest.mousePress(widget, QtCore.Qt.MouseButton.LeftButton, pos=point)
            QTest.mouseMove(widget, widget._point_for_value(20).toPoint())
            QTest.mouseRelease(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(20).toPoint())
            self.assertAlmostEqual(widget.value(), 20, delta=1)
            self.assertFalse(widget.isSliderDown())
            self.assertFalse(widget.grab().isNull())
            widget.hide()

    def test_rtl_and_inverted_appearance_keep_input_and_drawing_consistent(self):
        widget = self.slider()
        for direction in (QtCore.Qt.LayoutDirection.LeftToRight, QtCore.Qt.LayoutDirection.RightToLeft):
            widget.setLayoutDirection(direction)
            for inverted in (False, True):
                widget.setInvertedAppearance(inverted)
                self.click(widget, 65)
                self.assertAlmostEqual(widget.value(), 65, delta=1)
                self.finish_motion(widget)
                self.assertTrue(widget._handle_rect().contains(widget._point_for_value(widget.value())))

    def test_tracking_off_moves_position_and_commits_once_on_release(self):
        widget = self.slider()
        widget.setValue(20)
        widget.setTracking(False)
        changes, released = [], []
        widget.valueChanged.connect(changes.append)
        widget.sliderReleased.connect(lambda: released.append(True))
        QTest.mousePress(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(20).toPoint())
        QTest.mouseMove(widget, widget._point_for_value(80).toPoint())
        self.assertEqual(widget.value(), 20)
        self.assertAlmostEqual(widget.sliderPosition(), 80, delta=1)
        QTest.mouseRelease(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(80).toPoint())
        self.assertEqual(len(changes), 1)
        self.assertEqual(released, [True])

    def test_native_keyboard_steps_and_degenerate_bounds(self):
        widget = self.slider()
        widget.setSingleStep(3)
        widget.setPageStep(20)
        QTest.keyClick(widget, QtCore.Qt.Key.Key_Right)
        self.assertEqual(widget.value(), 3)
        QTest.keyClick(widget, QtCore.Qt.Key.Key_PageUp)
        self.assertEqual(widget.value(), 23)
        QTest.keyClick(widget, QtCore.Qt.Key.Key_End)
        self.assertEqual(widget.value(), 100)
        widget.setRange(5, 5)
        self.click(widget, 5)
        self.assertEqual(widget.value(), 5)
        self.assertFalse(widget.grab().isNull())

    def test_tooltip_format_tracks_handle_stays_inside_and_hides(self):
        widget = self.slider(ToolTipSlider)
        widget.move(10, 2)
        widget.setValueFormat('{value}%')
        widget.setValue(62)
        widget.show_value_tip()
        self.assertEqual(widget._value_label.text(), '62%')
        self.assertTrue(self.owner.rect().contains(widget._value_label.geometry()))
        self.assertFalse(widget._value_label.isWindow())
        widget.setValue(20)
        self.assertEqual(widget._value_label.text(), '20%')
        with self.assertRaises(ValueError):
            widget.setValueFormat('{unknown}')
        widget.setEnabled(False)
        self.assertFalse(widget._value_label.isVisible())
        widget.setEnabled(True)
        widget.show_value_tip()
        widget.hide()
        self.assertFalse(widget._value_label.isVisible())

    def test_range_order_signals_and_atomic_invalid_values(self):
        widget = self.slider(RangeSlider)
        changes = []
        widget.valuesChanged.connect(lambda a, b: changes.append((a, b)))
        widget.setValues(15, 80)
        widget.setValues(15, 80)
        self.assertEqual(changes, [(15, 80)])
        for pair in ((90, 20), (-1, 50), (0, 101)):
            with self.assertRaises(ValueError):
                widget.setValues(*pair)
        self.assertEqual(widget.values(), (15, 80))
        widget.setActiveHandle('upper')
        widget.setRange(0, 10)
        self.assertEqual(widget.values(), (10, 10))
        self.assertTrue(all(a <= b for a, b in changes))

    def test_range_drag_cannot_cross_and_space_switches_keyboard_handle(self):
        widget = self.slider(RangeSlider)
        widget.setValues(25, 75)
        QTest.mousePress(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(25).toPoint())
        QTest.mouseMove(widget, widget._point_for_value(95).toPoint())
        QTest.mouseRelease(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(95).toPoint())
        self.assertEqual(widget.values(), (75, 75))
        widget.setValues(25, 75)
        widget.setActiveHandle('lower')
        QTest.keyClick(widget, QtCore.Qt.Key.Key_Space)
        QTest.keyClick(widget, QtCore.Qt.Key.Key_Left)
        self.assertEqual(widget.values(), (25, 74))
        self.assertEqual(widget.activeHandle(), 'upper')

    def test_range_tracking_off_commits_pair_on_release(self):
        widget = self.slider(RangeSlider)
        widget.setValues(20, 80)
        widget.setTracking(False)
        QTest.mousePress(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(80).toPoint())
        QTest.mouseMove(widget, widget._point_for_value(40).toPoint())
        self.assertEqual(widget.values(), (20, 80))
        QTest.mouseRelease(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(40).toPoint())
        self.assertAlmostEqual(widget.upperValue(), 40, delta=1)
        self.assertEqual(widget.lowerValue(), 20)

    def test_vertical_range_and_gradient_theme_switch_preserve_values(self):
        widget = self.slider(RangeSlider, QtCore.Qt.Orientation.Vertical)
        widget.setValues(10, 85)
        widget.setActiveHandle('upper')
        self.click(widget, 65)
        self.assertAlmostEqual(widget.upperValue(), 65, delta=1)
        for mode in ('dark', 'light'):
            theme.set_mode(mode)
            widget.set_track_gradient([(0, '#004488'), (1, '#44ddff')], checkerboard=True)
            self.assertFalse(widget.grab().isNull())
        widget.hide()
        self.assertFalse(widget.isSliderDown())

    def test_keyboard_and_programmatic_motion_preserve_native_values_and_retarget_from_current_frame(self):
        for orientation in (QtCore.Qt.Orientation.Horizontal, QtCore.Qt.Orientation.Vertical):
            widget = self.slider(orientation=orientation)
            changes = []
            widget.valueChanged.connect(changes.append)
            widget.setValue(80)
            self.assertEqual(widget.value(), 80)
            self.assertEqual(changes, [80])
            animation = widget._position_animation
            self.assertEqual(animation.state(), QtCore.QAbstractAnimation.State.Running)
            animation.setCurrentTime(55)
            intermediate = widget._display_position
            self.assertGreater(intermediate, 0)
            self.assertLess(intermediate, 80)
            widget.setValue(30)
            self.assertEqual(widget.value(), 30)
            self.assertAlmostEqual(widget._display_position, intermediate)
            self.assertAlmostEqual(animation.startValue(), intermediate)
            self.finish_motion(widget)
            self.assertEqual(widget._display_position, 30)
            QTest.keyClick(widget, QtCore.Qt.Key.Key_Right if orientation == QtCore.Qt.Orientation.Horizontal else QtCore.Qt.Key.Key_Up)
            self.assertEqual(widget.value(), 31)
            self.assertEqual(widget._display_position, 30)
            self.finish_motion(widget)
            self.assertEqual(widget._display_position, 31)
            self.assertEqual(changes, [80, 30, 31])

    def test_track_jump_animates_and_grabbing_mid_animation_follows_pointer_immediately(self):
        widget = self.slider()
        self.click(widget, 85)
        self.assertAlmostEqual(widget.value(), 85, delta=1)
        widget._position_animation.setCurrentTime(50)
        point = widget._point_for_value(widget._display_position).toPoint()
        QTest.mousePress(widget, QtCore.Qt.MouseButton.LeftButton, pos=point)
        self.assertEqual(widget._position_animation.state(), QtCore.QAbstractAnimation.State.Stopped)
        QTest.mouseMove(widget, widget._point_for_value(40).toPoint())
        self.assertAlmostEqual(widget.sliderPosition(), 40, delta=1)
        self.assertEqual(widget._display_position, widget.sliderPosition())
        QTest.mouseRelease(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(40).toPoint())
        self.assertEqual(widget._display_position, widget.value())

    def test_hover_press_reverse_smoothly_and_hidden_or_disabled_sliders_stop_motion(self):
        widget = self.slider()
        QTest.mouseMove(widget, widget._point_for_value(0).toPoint())
        widget._center_animation.setCurrentTime(70)
        self.assertGreater(widget._center_progress, 0)
        QTest.mousePress(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(0).toPoint())
        widget._press_animation.setCurrentTime(35)
        pressed = widget._press_progress
        self.assertGreater(pressed, 0)
        QTest.mouseRelease(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(0).toPoint())
        self.assertAlmostEqual(widget._press_animation.startValue(), pressed)
        widget.setValue(80)
        widget.setEnabled(False)
        for name in ('_position_animation', '_center_animation', '_press_animation'):
            self.assertEqual(getattr(widget, name).state(), QtCore.QAbstractAnimation.State.Stopped)
        self.assertEqual(widget._display_position, widget.value())
        widget.setEnabled(True)
        widget.setValue(20)
        widget.hide()
        self.assertEqual(widget._position_animation.state(), QtCore.QAbstractAnimation.State.Stopped)

    def test_default_tooltip_is_numeric_and_fade_reversals_preserve_current_opacity(self):
        widget = self.slider(ToolTipSlider)
        widget.setRange(-200, 500)
        widget.setValue(137)
        widget.show_value_tip()
        self.assertEqual(widget._value_label.text(), '137')
        widget._tip_fade.setCurrentTime(40)
        opacity = widget._tip_opacity
        self.assertGreater(opacity, 0)
        self.assertLess(opacity, 1)
        widget.hide_value_tip()
        self.assertEqual(widget._tip_fade.startValue(), opacity)
        widget._tip_fade.setCurrentTime(30)
        hidden_opacity = widget._tip_opacity
        widget.show_value_tip()
        self.assertAlmostEqual(widget._tip_fade.startValue(), hidden_opacity)
        self.finish_motion(widget)
        self.assertEqual(widget._tip_opacity, 1)
        widget.hide_value_tip()
        self.finish_motion(widget)
        self.assertFalse(widget._value_label.isVisible())

    def test_tooltip_follows_rendered_handle_during_motion_and_direct_drag(self):
        for orientation in (QtCore.Qt.Orientation.Horizontal, QtCore.Qt.Orientation.Vertical):
            widget = self.slider(ToolTipSlider, orientation)
            widget.show_value_tip()
            self.finish_motion(widget)
            widget.setValue(80)
            widget._position_animation.setCurrentTime(55)
            self.assertEqual(widget._value_label.text(), '80')
            self.assertEqual(widget._value_label.pos(), widget._tip_target())
            self.assertTrue(self.owner.rect().contains(widget._value_label.geometry()))
            point = widget._point_for_value(widget._display_position).toPoint()
            QTest.mousePress(widget, QtCore.Qt.MouseButton.LeftButton, pos=point)
            QTest.mouseMove(widget, widget._point_for_value(35).toPoint())
            self.assertEqual(widget._value_label.text(), str(widget.sliderPosition()))
            self.assertEqual(widget._value_label.pos(), widget._tip_target())
            widget.hide()
            self.assertFalse(widget._value_label.isVisible())
            self.assertEqual(widget._tip_fade.state(), QtCore.QAbstractAnimation.State.Stopped)
            self.assertEqual(widget._tip_motion.state(), QtCore.QAbstractAnimation.State.Stopped)

    def test_range_endpoint_motion_is_ordered_and_restarts_without_visual_jump(self):
        widget = self.slider(RangeSlider)
        widget.setValues(10, 90)
        self.assertEqual(widget.values(), (10, 90))
        animation = widget._range_animation
        animation.setCurrentTime(65)
        displayed = widget._display_lower, widget._display_upper
        self.assertLess(displayed[0], displayed[1])
        self.assertNotEqual(displayed, (10, 90))
        widget.setValues(40, 60)
        self.assertEqual((widget._display_lower, widget._display_upper), displayed)
        self.finish_motion(widget)
        self.assertEqual((widget._display_lower, widget._display_upper), (40, 60))
        widget.setValue(45)
        self.assertEqual(widget.values(), (45, 60))
        self.assertEqual(animation.state(), QtCore.QAbstractAnimation.State.Running)
        widget.hide()
        self.assertEqual(animation.state(), QtCore.QAbstractAnimation.State.Stopped)

    def test_range_tracking_both_orientations_has_no_visual_drag_lag_and_commits_once(self):
        for orientation in (QtCore.Qt.Orientation.Horizontal, QtCore.Qt.Orientation.Vertical):
            for tracking in (True, False):
                widget = self.slider(RangeSlider, orientation)
                widget.setValues(20, 80)
                self.finish_motion(widget)
                widget.setTracking(tracking)
                changes = []
                widget.valuesChanged.connect(lambda a, b: changes.append((a, b)))
                QTest.mousePress(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(80).toPoint())
                QTest.mouseMove(widget, widget._point_for_value(45).toPoint())
                self.assertAlmostEqual(widget._display_upper, 45, delta=1)
                self.assertEqual(widget._range_animation.state(), QtCore.QAbstractAnimation.State.Stopped)
                if not tracking:
                    self.assertEqual(widget.values(), (20, 80))
                    self.assertEqual(changes, [])
                QTest.mouseRelease(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(45).toPoint())
                self.assertAlmostEqual(widget.upperValue(), 45, delta=1)
                self.assertEqual(len(changes), 1)
                widget.hide()

    def test_native_slider_tracking_in_both_orientations_does_not_animate_direct_drag(self):
        for orientation in (QtCore.Qt.Orientation.Horizontal, QtCore.Qt.Orientation.Vertical):
            for tracking in (True, False):
                widget = self.slider(orientation=orientation)
                widget.setValue(20)
                self.finish_motion(widget)
                widget.setTracking(tracking)
                changes = []
                widget.valueChanged.connect(changes.append)
                QTest.mousePress(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(20).toPoint())
                QTest.mouseMove(widget, widget._point_for_value(80).toPoint())
                self.assertEqual(widget._display_position, widget.sliderPosition())
                self.assertEqual(widget._position_animation.state(), QtCore.QAbstractAnimation.State.Stopped)
                if not tracking:
                    self.assertEqual(widget.value(), 20)
                    self.assertEqual(changes, [])
                QTest.mouseRelease(widget, QtCore.Qt.MouseButton.LeftButton, pos=widget._point_for_value(80).toPoint())
                self.assertAlmostEqual(widget.value(), 80, delta=1)
                self.assertEqual(len(changes), 1)
                widget.hide()


if __name__ == '__main__':
    unittest.main()
