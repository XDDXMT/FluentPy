import os
os.environ['QT_QPA_PLATFORM']='offscreen'
import sys
import unittest
from unittest.mock import patch
from fluentpy import (ActionMenu, Button, ColorDialog, ColorPickerButton, ColorPaletteButton,
    ColorPickerPanel, ColorSwatchGroup, EyeDropperButton, ScreenColorPicker, Slider, theme)
from fluentpy.qt import QtCore, QtGui, QtWidgets, QT_API
if QT_API=='PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class ColorControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app=QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors=[]; self.old_hook=sys.excepthook
        sys.excepthook=lambda kind,error,tb:self.errors.append(error)
        self.owner=QtWidgets.QWidget();self.owner.resize(900,720)
        self.owner.show();self.owner.activateWindow();self.app.processEvents()

    def tearDown(self):
        self.owner.close();self.owner.deleteLater()
        self.app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents();sys.excepthook=self.old_hook
        self.assertEqual(self.errors,[])
        self.assertIsNone(QtWidgets.QApplication.overrideCursor())

    def button(self, cls=ColorPickerButton):
        button=cls(parent=self.owner);button.move(790,50);button.show();self.app.processEvents()
        return button

    def open_popup(self,button):
        button.show_popup();button._popup._reveal.setCurrentTime(button._popup.SHOW_DURATION)
        self.app.processEvents();return button._popup

    def test_panel_sync_hex_rgb_hsv_alpha_and_defensive_copy(self):
        panel=ColorPickerPanel('#80e4579b',self.owner)
        self.assertEqual(panel.color().getRgb(),(228,87,155,128))
        self.assertIsInstance(panel.channel_sliders[0],Slider)
        panel.channel_inputs[0].setValue(12)
        self.assertEqual(panel.color().red(),12)
        self.assertEqual(panel.hex_input.text(),'#800c579b')
        panel.set_format('hsv');panel.channel_inputs[0].setValue(120)
        self.assertEqual(panel.color().green(),max(panel.color().getRgb()[:3]))
        panel.channel_inputs[3].setValue(0);self.assertEqual(panel.color().alpha(),0)
        copy=panel.color();copy.setRed(0);self.assertNotEqual(copy,panel.color())

    def test_invalid_hex_preserves_last_valid_color_and_can_recover(self):
        panel=ColorPickerPanel('#ff0000',self.owner)
        panel.hex_input.setText('#oops');self.assertFalse(panel.validate())
        self.assertFalse(panel.is_valid());self.assertEqual(panel.color().name(),'#ff0000')
        panel.hex_input.setText('#0f0');self.assertTrue(panel.validate())
        self.assertTrue(panel.is_valid());self.assertEqual(panel.color().name(),'#00ff00')
        opaque=ColorPickerPanel('#1100ff00',self.owner,enable_alpha=False)
        self.assertEqual(opaque.color().alpha(),255)
        self.assertTrue(opaque.channel_inputs[3].isHidden())

    def test_hsv_hue_survives_black_and_returns_when_value_restored(self):
        panel=ColorPickerPanel('#00ff00',self.owner);panel.set_format('hsv')
        panel.channel_inputs[2].setValue(0);self.assertEqual(panel.color().name(),'#000000')
        self.assertEqual(panel.channel_inputs[0].value(),120)
        panel.channel_inputs[2].setValue(100);self.assertEqual(panel.color().name(),'#00ff00')

    def test_picker_commit_cancel_and_no_additional_native_window(self):
        button=self.button();commits=[];button.colorChanged.connect(commits.append)
        before=set(self.app.topLevelWidgets());popup=self.open_popup(button)
        self.assertIsInstance(popup,ActionMenu);self.assertFalse(popup.isWindow())
        self.assertEqual(set(self.app.topLevelWidgets()),before)
        button.editor.set_color('#e4579b');self.assertEqual(button.color().name(),'#0078d4')
        button.cancel_button.click();popup._reveal.setCurrentTime(popup.HIDE_DURATION)
        self.assertEqual(commits,[])
        self.open_popup(button);self.assertEqual(button.editor.color(),button.color())
        button.editor.set_color('#e4579b');button.confirm_button.click()
        popup._reveal.setCurrentTime(popup.HIDE_DURATION)
        self.assertEqual(button.color().name(),'#e4579b');self.assertEqual(len(commits),1)

    def test_typing_and_escape_are_handled_inside_custom_menu(self):
        button=self.button();popup=self.open_popup(button);entry=button.editor.hex_input
        entry.setFocus();entry.selectAll();QTest.keyClicks(entry,'#ff4500')
        self.assertTrue(popup.isVisible());self.assertEqual(button.editor.color().name(),'#ff4500')
        QTest.keyClick(entry,QtCore.Qt.Key.Key_Escape);popup._reveal.setCurrentTime(popup.HIDE_DURATION)
        self.assertFalse(popup.isVisible());self.assertEqual(button.color().name(),'#0078d4')

    def test_small_owner_bounds_and_hide_cleanup(self):
        self.owner.resize(390,400);button=self.button();button.move(300,350)
        popup=self.open_popup(button)
        self.assertTrue(self.owner.rect().contains(popup._surface.geometry()))
        self.assertGreater(popup._scroll.verticalScrollBar().maximum(),0)
        self.owner.hide();self.assertFalse(popup.isVisible())

    def test_palette_automatic_color_and_more_dialog_cancel(self):
        button=self.button(ColorPaletteButton);self.open_popup(button)
        button.palette.automatic_button.click();button._popup.dismiss(immediate=True)
        self.assertTrue(button.is_automatic());self.assertFalse(button.color().isValid())
        self.open_popup(button);button.palette.more_button.click()
        self.assertTrue(button.dialog.isVisible());self.assertFalse(button.dialog.isWindow())
        button.dialog.editor.set_color('#00ff00');button.dialog.reject();button.dialog._fade.setCurrentTime(100)
        self.assertTrue(button.is_automatic())
        self.open_popup(button);button.palette._buttons[-1].click()
        self.assertEqual(button.color().name(),'#7030a0')

    def test_dialog_validates_commits_and_cancel_keeps_original(self):
        dialog=ColorDialog('#0078d4',parent=self.owner,enable_alpha=True);selected=[]
        dialog.colorSelected.connect(selected.append);dialog.open()
        dialog.editor.set_color('#e4579b');dialog.reject();dialog._fade.setCurrentTime(100)
        self.assertEqual(dialog.color().name(),'#0078d4');self.assertEqual(selected,[])
        dialog.open();dialog.editor.hex_input.setText('invalid');dialog.accept()
        self.assertTrue(dialog.isVisible());self.assertFalse(dialog.yes_button.isEnabled())
        dialog.editor.set_color('#e4579b');dialog.accept();dialog._fade.setCurrentTime(100)
        self.assertEqual(dialog.color().name(),'#e4579b');self.assertEqual(len(selected),1)

    def test_swatch_exclusivity_wrapping_and_input_ownership(self):
        group=ColorSwatchGroup(parent=self.owner);group.resize(96,100);group.show();self.app.processEvents()
        group._buttons[3].click();self.assertEqual(group.color(),group._buttons[3].color())
        self.assertEqual(sum(button.isChecked() for button in group._buttons),1)
        self.assertIsInstance(group._buttons[0],Button)
        self.assertGreater(group._buttons[-1].y(),group._buttons[0].y())
        original=group.colors();self.assertRaises(ValueError,group.set_colors,[])
        self.assertEqual(group.colors(),original)

    def frames(self):
        image=QtGui.QImage(200,100,QtGui.QImage.Format.Format_RGB32);image.fill(QtGui.QColor('#e4579b'))
        image.setPixelColor(100,50,QtGui.QColor('#10aa22'))
        return [(QtCore.QRect(-100,0,100,50),image)]

    def test_eyedropper_synthetic_snapshot_maps_negative_origin_and_dpi(self):
        picker=ScreenColorPicker(self.owner);selected=[];picker.colorSelected.connect(selected.append)
        with patch.object(picker,'_capture_screens',self.frames):
            self.assertTrue(picker.start());self.assertFalse(picker.start())
            self.assertEqual(picker.sample_color(QtCore.QPoint(-50,25)).name(),'#10aa22')
            self.assertFalse(picker.sample_color(QtCore.QPoint(0,0)).isValid())
            picker._choose(QtCore.QPoint(-50,25))
        self.assertEqual(selected[0].name(),'#10aa22');self.assertFalse(picker.is_active())
        self.assertEqual(picker._overlays,[]);self.assertEqual(picker._frames,[])

    def test_eyedropper_failure_and_cancel_release_cursor(self):
        button=self.button(EyeDropperButton);failed=[];button.failed.connect(failed.append)
        with patch.object(button.picker,'_capture_screens',return_value=[]):
            self.assertFalse(button.picker.start());self.assertEqual(len(failed),1)
        with patch.object(button.picker,'_capture_screens',self.frames):
            self.assertTrue(button.picker.start());button.setEnabled(False)
        self.assertFalse(button.picker.is_active());self.assertIsNone(self.app.overrideCursor())

    def test_delete_active_eyedropper_and_popup_has_no_orphans(self):
        button=self.button(EyeDropperButton)
        with patch.object(button.picker,'_capture_screens',self.frames):
            button.picker.start()
        button.deleteLater();self.app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
        self.assertIsNone(self.app.overrideCursor())
        normal=self.button();self.open_popup(normal)
        normal.deleteLater();self.app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
        self.app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
        self.assertFalse(any(menu.isVisible() for menu in self.owner.findChildren(ActionMenu)))

    def test_direct_picker_deletion_also_releases_screen_overlays(self):
        picker=ScreenColorPicker()
        with patch.object(picker,'_capture_screens',self.frames):
            picker.start()
        picker.deleteLater();self.app.sendPostedEvents(None,QtCore.QEvent.Type.DeferredDelete)
        self.assertIsNone(self.app.overrideCursor())

    def test_gradient_slider_retains_keyboard_and_clears_back_to_normal(self):
        slider=Slider(parent=self.owner);slider.setRange(0,255);slider.resize(220,32);slider.show()
        slider.set_track_gradient([(0,'#00000000'),(1,'#ff0000')],checkerboard=True)
        slider.setFocus();QTest.keyClick(slider,QtCore.Qt.Key.Key_Right)
        self.assertEqual(slider.value(),1)
        self.assertFalse(slider.grab().isNull())
        self.assertRaises(ValueError,slider.set_track_gradient,[(float('nan'),'#000000'),(1,'#ffffff')])
        self.assertRaises(ValueError,slider.set_track_gradient,[(0,'#000000')])
        slider.clear_track_gradient();self.assertIsNone(slider._track_gradient)
