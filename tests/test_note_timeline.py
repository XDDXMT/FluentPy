import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from dataclasses import FrozenInstanceError
import sys
import unittest
from unittest import mock

import fluentpy
from fluentpy import NoteEvent, NoteTimeline, ThemeMode, theme
from fluentpy import widgets
from fluentpy.qt import QtCore, QtGui, QtWidgets


class NoteEventTests(unittest.TestCase):
    def test_public_exports_and_immutable_value(self):
        self.assertIs(fluentpy.NoteEvent, widgets.NoteEvent)
        self.assertIs(fluentpy.NoteTimeline, widgets.NoteTimeline)
        self.assertIn("NoteEvent", fluentpy.__all__)
        self.assertIn("NoteTimeline", fluentpy.__all__)
        note = NoteEvent(1, 0.5, 127)
        self.assertEqual((note.start, note.duration, note.pitch, note.track), (1.0, 0.5, 127, 0))
        with self.assertRaises(FrozenInstanceError):
            note.pitch = 60

    def test_rejects_invalid_note_values(self):
        valid = {"start": 0.0, "duration": 1.0, "pitch": 60, "track": 0}
        invalid = {
            "start": [-1, float("nan"), float("inf"), True, "1", None],
            "duration": [-1, float("nan"), float("inf"), False, "1", None],
            "pitch": [-1, 128, 60.5, float("nan"), True, "60", None],
            "track": [-1, 0.5, float("inf"), True, "0", None],
        }
        for field, values in invalid.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    with self.assertRaises((TypeError, ValueError)):
                        NoteEvent(**{**valid, field: value})
        with self.assertRaises(ValueError):
            NoteEvent(1e308, 1e308, 60)
        self.assertEqual(NoteEvent(0, 0, 0, 1000).track, 1000)


class NoteTimelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.previous_mode = theme.mode
        theme.set_mode(ThemeMode.LIGHT)
        self.view = NoteTimeline()
        self.view.resize(300, 90)
        self.view.show()
        self.app.processEvents()

    def tearDown(self):
        self.view.close()
        self.view.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        theme.set_mode(self.previous_mode)
        self.app.processEvents()

    def render(self):
        self.app.processEvents()
        pixmap = QtGui.QPixmap(self.view.size())
        pixmap.fill(QtCore.Qt.GlobalColor.transparent)
        self.view.render(pixmap)
        return pixmap.toImage()

    @staticmethod
    def red_pixels(image, *, x_from=0, x_to=None, y_from=0, y_to=None):
        x_to = image.width() if x_to is None else x_to
        y_to = image.height() if y_to is None else y_to
        return sum(
            color.red() > color.green() + 40 and color.red() > color.blue() + 40
            for x in range(x_from, x_to)
            for y in range(y_from, y_to)
            for color in [image.pixelColor(x, y)]
        )

    def test_notes_copy_iterable_and_preserve_trailing_silence(self):
        notes = [NoteEvent(3, 2, 64), NoteEvent(0, 1, 60)]
        original = notes.copy()
        self.view.set_notes(notes, duration=8)
        self.assertIsInstance(self.view.notes(), tuple)
        self.assertEqual(self.view.notes(), tuple(original))
        self.assertEqual(notes, original)
        self.assertEqual(self.view.duration(), 8)
        self.assertEqual(self.view.pitch_range(), (60, 64))
        notes.clear()
        self.assertEqual(self.view.notes(), tuple(original))
        self.view.set_notes((note for note in original), duration=1)
        self.assertEqual(self.view.duration(), 5)

    def test_invalid_update_preserves_notes_duration_position_and_drawing(self):
        self.view.set_notes([NoteEvent(0, 2, 60)], duration=4)
        self.view.set_position(1)
        before = (self.view.notes(), self.view.duration(), self.view.position(), self.view.pitch_range())
        before_image = self.render()
        for duration in [-1, float("nan"), float("inf"), True, "4"]:
            with self.subTest(duration=duration):
                with self.assertRaises((TypeError, ValueError)):
                    self.view.set_notes([NoteEvent(0, 1, 80)], duration=duration)
                self.assertEqual((self.view.notes(), self.view.duration(), self.view.position(), self.view.pitch_range()), before)
        with self.assertRaises(TypeError):
            self.view.set_notes([NoteEvent(0, 1, 80), (0, 1, 60)])

        def interrupted_notes():
            yield NoteEvent(0, 1, 80)
            raise RuntimeError("source interrupted")

        with self.assertRaises(RuntimeError):
            self.view.set_notes(interrupted_notes())
        self.assertEqual((self.view.notes(), self.view.duration(), self.view.position(), self.view.pitch_range()), before)
        self.assertEqual(self.render(), before_image)

    def test_position_clamps_and_only_changed_values_emit(self):
        changed = []
        self.view.positionChanged.connect(changed.append)
        self.view.set_notes([NoteEvent(0, 2, 60)])
        for position in [-5, 0, 0.5, 0.5, 100, 2, -1]:
            self.view.set_position(position)
        self.assertEqual(changed, [0.5, 2.0, 0.0])
        self.view.set_position(1)
        for value in [float("nan"), float("inf"), float("-inf"), True, "1", None]:
            with self.subTest(value=value):
                with self.assertRaises((TypeError, ValueError)):
                    self.view.set_position(value)
                self.assertEqual(self.view.position(), 1)
        self.view.set_notes([NoteEvent(1, 1, 65)])
        self.assertEqual(changed[-2:], [1.0, 0.0])
        self.assertEqual(self.view.position(), 0)

    def test_fixed_pitch_range_and_automatic_reset(self):
        self.assertEqual(self.view.pitch_range(), (48, 85))
        self.view.set_pitch_range(0, 127)
        self.view.set_notes([NoteEvent(0, 1, 60)])
        self.assertEqual(self.view.pitch_range(), (0, 127))
        for bounds in [(61, 60), (-1, 127), (0, 128), (True, 80), (60.5, 80), (None, 80), (60, None)]:
            with self.subTest(bounds=bounds):
                with self.assertRaises((TypeError, ValueError)):
                    self.view.set_pitch_range(*bounds)
                self.assertEqual(self.view.pitch_range(), (0, 127))
        self.view.set_pitch_range()
        self.assertEqual(self.view.pitch_range(), (60, 60))
        self.view.clear()
        self.assertEqual(self.view.pitch_range(), (48, 85))

    def test_clear_resets_data_but_keeps_display_preferences(self):
        self.view.set_pitch_range(36, 96)
        self.view.set_track_colors(["#ff0000"])
        self.view.set_empty_text("Choose a score")
        self.view.set_notes([NoteEvent(1, 1, 60)])
        self.view.set_position(1)
        self.view.clear()
        self.assertEqual(self.view.notes(), ())
        self.assertEqual((self.view.duration(), self.view.position()), (0, 0))
        self.assertEqual(self.view.pitch_range(), (36, 96))
        self.assertEqual(self.view.empty_text(), "Choose a score")
        self.view.set_notes([NoteEvent(0, 1, 60)])
        self.assertGreater(self.red_pixels(self.render()), 0)

    def test_track_palette_copies_qcolors_and_rejects_invalid_replacements(self):
        color = QtGui.QColor("#ff0000")
        colors = [color]
        self.view.set_track_colors(colors)
        self.view.set_notes([NoteEvent(0, 1, 60, track=5)])
        before_image = self.render()
        color.setRgb(0, 255, 0)
        colors.clear()
        # Force a fresh layer so the check detects QColor sharing, not just caching.
        self.view.set_notes(self.view.notes())
        self.assertEqual(self.render(), before_image)
        self.assertGreater(self.red_pixels(before_image), 0)
        for invalid in [[], ["not a color"], [QtGui.QColor()], ["#00ff00", "invalid"]]:
            with self.subTest(invalid=invalid):
                with self.assertRaises((TypeError, ValueError)):
                    self.view.set_track_colors(invalid)
                self.assertEqual(self.render(), before_image)

    def test_pitch_and_time_endpoints_are_visible(self):
        self.view.set_pitch_range(0, 127)
        self.view.set_track_colors(["#ff0000"])
        self.view.set_notes([NoteEvent(0, 0, 127), NoteEvent(1, 0, 0)])
        image = self.render()
        self.assertGreater(self.red_pixels(image, x_to=4, y_to=8), 0)
        self.assertGreater(self.red_pixels(image, x_from=296, y_from=78), 0)

    def test_zero_duration_single_pitch_and_very_small_widget_render(self):
        self.view.set_track_colors(["#ff0000"])
        self.view.set_notes([NoteEvent(0, 0, 60)])
        self.assertEqual(self.view.duration(), 0)
        self.assertEqual(self.view.pitch_range(), (60, 60))
        self.assertGreater(self.red_pixels(self.render()), 0)
        self.view.setMinimumSize(0, 0)
        for size in [(1, 1), (2, 3), (5, 5)]:
            with self.subTest(size=size):
                self.view.resize(*size)
                image = self.render()
                self.assertEqual((image.width(), image.height()), size)
                self.assertFalse(image.isNull())
                self.view.clear()
                self.assertFalse(self.render().isNull())
                self.view.set_notes([NoteEvent(0, 0, 60)])

    def test_empty_text_redraws_without_changing_song_state(self):
        default_image = self.render()
        self.view.set_empty_text("Drop a MIDI file here")
        self.assertNotEqual(self.render(), default_image)
        self.assertEqual(self.view.empty_text(), "Drop a MIDI file here")
        with self.assertRaises(TypeError):
            self.view.set_empty_text(None)
        self.assertEqual((self.view.notes(), self.view.duration(), self.view.position()), ((), 0, 0))

    def test_position_updates_reuse_static_note_layer(self):
        self.view.set_notes([NoteEvent(0, 1, 60), NoteEvent(2, 1, 72)])
        with mock.patch.object(self.view, "_make_background", wraps=self.view._make_background) as rebuild:
            self.render()
            initial_count = rebuild.call_count
            self.assertGreater(initial_count, 0)
            for position in [0.25, 0.5, 1, 2.5, 3]:
                self.view.set_position(position)
                self.render()
            self.assertEqual(rebuild.call_count, initial_count)
            self.view.set_notes([NoteEvent(0, 1, 80)])
            self.render()
            self.assertGreater(rebuild.call_count, initial_count)

    def test_resize_and_device_pixel_ratio_refresh_cached_layer(self):
        self.view.set_notes([NoteEvent(0, 1, 60)])
        with mock.patch.object(self.view, "_make_background", wraps=self.view._make_background) as rebuild:
            self.render()
            initial_count = rebuild.call_count
            self.view.resize(420, 110)
            self.render()
            self.assertGreater(rebuild.call_count, initial_count)
            resized_count = rebuild.call_count
            with mock.patch.object(self.view, "devicePixelRatioF", return_value=2.0):
                self.render()
                self.assertGreater(rebuild.call_count, resized_count)
                self.assertEqual(self.view._background.devicePixelRatio(), 2.0)
                self.assertEqual(self.view._background.size(), QtCore.QSize(840, 220))
                ratio_count = rebuild.call_count
                self.view.set_position(0.5)
                self.render()
                self.assertEqual(rebuild.call_count, ratio_count)
            self.render()
            self.assertGreater(rebuild.call_count, ratio_count)

    def test_theme_changes_redraw_and_destroyed_widgets_disconnect(self):
        self.view.set_notes([NoteEvent(0, 1, 60)])
        light_image = self.render()
        theme.set_mode(ThemeMode.DARK)
        self.assertNotEqual(self.render(), light_image)
        errors = []
        previous_hook = sys.excepthook
        sys.excepthook = lambda kind, error, traceback: errors.append(error)
        try:
            for _ in range(3):
                retired = NoteTimeline()
                retired.set_notes([NoteEvent(0, 1, 60)])
                retired.deleteLater()
                self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
                theme.toggle()
                self.app.processEvents()
            self.assertEqual(errors, [])
        finally:
            sys.excepthook = previous_hook


if __name__ == "__main__":
    unittest.main()
