"""Actual Qt playback/seek and independently embeddable media controls."""

import os
import subprocess
import sys
import tempfile
import time
import unittest
import wave
from pathlib import Path

from media_fixtures import video_fixture

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from fluentpy import (
    AudioPlayer,
    Button,
    CompactAudioPlayer,
    MediaController,
    VideoPlayer,
    VolumeControl,
    VolumeFlyout,
    theme,
)
from fluentpy.qt import QT_API, QtCore, QtWidgets

if QT_API == "PySide6":
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest


class MediaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "silence.wav"
        with wave.open(str(self.path), "wb") as output:
            output.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
            output.writeframes(b"\x00\x00" * 16000 * 4)
        self.controller = MediaController()
        self.controller.set_muted(True)
        self.widgets = []

    def tearDown(self):
        self.controller.clear()
        for widget in self.widgets:
            widget.close()
            widget.deleteLater()
        self.controller.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.temp.cleanup()

    def wait_for(self, predicate, timeout=5000):
        deadline = time.monotonic() + timeout / 1000
        while not predicate() and time.monotonic() < deadline:
            QTest.qWait(25)
        self.assertTrue(predicate(), "Qt multimedia did not reach the expected state")

    def test_plain_import_does_not_initialize_multimedia(self):
        code = "import sys, fluentpy; assert not any(k.endswith('QtMultimedia') for k in sys.modules); c=fluentpy.MediaController(); c.set_volume(.4); assert c._player is None"
        result = subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, timeout=15
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_real_wav_load_play_pause_and_seek(self):
        errors = []
        self.controller.errorOccurred.connect(errors.append)
        self.controller.set_source(self.path)
        self.wait_for(lambda: self.controller.duration() == 4000)
        self.assertFalse(self.controller.is_playing())
        self.assertTrue(self.controller.is_seekable())
        self.controller.play()
        self.wait_for(lambda: self.controller.position() > 100)
        self.controller.pause()
        self.wait_for(lambda: not self.controller.is_playing())
        self.controller.seek(2500)
        self.wait_for(lambda: abs(self.controller.position() - 2500) < 50)
        self.controller.seek_by(-1000)
        self.wait_for(lambda: abs(self.controller.position() - 1500) < 50)
        self.controller.seek(-100)
        self.assertEqual(self.controller.position(), 0)
        self.assertEqual(errors, [])

    def test_shared_controls_synchronize_without_signal_seek_feedback(self):
        full = AudioPlayer(controller=self.controller)
        compact = CompactAudioPlayer(controller=self.controller)
        self.widgets.extend([full, compact])
        for widget in self.widgets:
            widget.show()
        self.controller.set_source(self.path)
        self.wait_for(lambda: full._duration == 4000)
        seeks = []
        self.controller.positionChanged.connect(seeks.append)
        self.controller.seek(2000)
        self.wait_for(lambda: full.timeline.value() == 5000 and compact.timeline.value() == 5000)
        QTest.qWait(220)
        self.assertAlmostEqual(full.timeline._display_position, 5000, delta=2)
        self.assertAlmostEqual(compact.timeline._display_position, 5000, delta=2)
        self.assertTrue(compact.play_button.isVisible())
        self.assertLess(len(seeks), 4)
        full.timeline.setValue(7500)
        self.wait_for(lambda: self.controller.position() == 3000)
        full.volume_slider.setValue(25)
        self.assertEqual(compact.volume_slider.value(), 25)
        self.assertAlmostEqual(self.controller.volume(), 0.25)
        full.volume_button.click()
        self.assertTrue(full.volume_flyout.isVisible())
        self.assertFalse(self.controller.is_muted())
        full.set_seek_steps(5, 15)
        self.assertEqual(full.back_button.toolTip(), "后退 5 秒")
        extra = QtWidgets.QLabel("扩展操作")
        full.trailing_layout.addWidget(extra)
        self.assertEqual(full.trailing_layout.itemAt(0).widget(), extra)

    def test_video_surface_exposes_native_output_and_controls(self):
        video = VideoPlayer(controller=self.controller)
        self.widgets.append(video)
        self.assertIs(video.controls.controller, self.controller)
        self.assertIs(self.controller.player().videoOutput(), video.video_widget)
        self.assertIsNotNone(video.video_widget.videoSink())
        self.assertIs(video.controls.trailing_layout.itemAt(0).widget(), video.full_screen_button)

    def test_speaker_click_opens_volume_without_muting_and_escape_restores_layout(self):
        host = QtWidgets.QWidget()
        host.resize(500, 260)
        layout = QtWidgets.QVBoxLayout(host)
        full = AudioPlayer(controller=self.controller)
        layout.addWidget(full)
        self.widgets.append(host)
        host.show()
        self.app.processEvents()
        before = full.size()
        full.volume_button.click()
        QTest.qWait(150)
        popup = full.volume_flyout
        self.assertTrue(popup.isVisible())
        self.assertTrue(
            self.controller.is_muted(), "opening the selector must not change mute state"
        )
        self.assertEqual(full.size(), before)
        self.assertEqual(full.volume_button.property("fluentIcon"), "SPEAKER_MUTE")
        popup.control.slider.setValue(37)
        self.assertAlmostEqual(self.controller.volume(), 0.37)
        self.assertFalse(self.controller.is_muted())
        self.assertEqual(popup.control.value_label.text(), "37")
        self.assertEqual(full.volume_button.property("fluentIcon"), "SPEAKER_1")
        QTest.keyClick(popup.control.slider, QtCore.Qt.Key.Key_Right)
        self.assertEqual(popup.control.slider.value(), 38)
        QTest.keyClick(popup.control.slider, QtCore.Qt.Key.Key_Escape)
        self.assertFalse(popup.isVisible())
        full.volume_button.click()
        self.assertTrue(popup.isVisible())
        host.hide()
        self.app.processEvents()
        self.assertFalse(popup.isVisible())

    def test_volume_popup_closes_on_outside_click_and_independent_control_stays_in_sync(self):
        host = QtWidgets.QWidget()
        host.resize(500, 260)
        layout = QtWidgets.QVBoxLayout(host)
        full = CompactAudioPlayer(controller=self.controller)
        outside = Button("其他操作")
        layout.addWidget(full)
        layout.addWidget(outside)
        self.widgets.append(host)
        independent = VolumeControl(controller=self.controller)
        self.widgets.append(independent)
        host.show()
        self.app.processEvents()
        full.volume_button.click()
        self.assertTrue(full.volume_flyout.isVisible())
        full.volume_slider.setValue(100)
        self.assertEqual(independent.value_label.text(), "100")
        self.assertEqual(full.volume_button.property("fluentIcon"), "SPEAKER_2")
        QTest.mouseClick(outside, QtCore.Qt.MouseButton.LeftButton)
        self.assertFalse(full.volume_flyout.isVisible())
        independent.mute_button.click()
        self.assertTrue(self.controller.is_muted())
        for mode in ("dark", "light"):
            theme.set_mode(mode)
            self.assertFalse(independent.grab().isNull())
        self.assertIsInstance(full.volume_flyout, VolumeFlyout)

    def test_native_video_sink_receives_decoded_frames(self):
        video = VideoPlayer(controller=self.controller)
        self.widgets.append(video)
        frames = []
        errors = []
        video.video_widget.videoSink().videoFrameChanged.connect(
            lambda frame: frames.append(frame.toImage()) if frame.isValid() else None
        )
        self.controller.errorOccurred.connect(errors.append)
        video.set_source(video_fixture(Path(self.temp.name) / "original.avi"))
        self.wait_for(lambda: self.controller.duration() > 0)
        self.controller.play()
        self.wait_for(lambda: len(frames) >= 3)
        self.controller.pause()
        self.assertTrue(all(image.size() == QtCore.QSize(160, 90) for image in frames))
        self.assertNotEqual(frames[0].pixelColor(0, 0), frames[-1].pixelColor(0, 0))
        self.assertEqual(errors, [])

    def test_parameter_validation_and_optional_pause_on_hide(self):
        with self.assertRaises(ValueError):
            self.controller.set_source(Path(self.temp.name) / "missing.wav")
        with self.assertRaises(ValueError):
            self.controller.set_volume(float("nan"))
        with self.assertRaises(ValueError):
            self.controller.set_playback_rate(0)
        with self.assertRaises(TypeError):
            self.controller.seek(1.5)
        player = AudioPlayer(controller=self.controller)
        self.widgets.append(player)
        player.set_pause_on_hide(True)
        player.show()
        self.controller.set_source(self.path)
        self.wait_for(lambda: self.controller.duration() > 0)
        self.controller.play()
        self.wait_for(self.controller.is_playing)
        player.hide()
        self.wait_for(lambda: not self.controller.is_playing())


if __name__ == "__main__":
    unittest.main()
