"""Theme receivers survive Python GC and live Qt child construction.

Run each probe in a fresh process: the original failure depended on cyclic GC
and could poison a later QWidget constructor or surface only during shutdown.
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_PROBE = r"""
import gc
import json
from pathlib import Path
import sys
import traceback
import weakref

sys.path.insert(0, str(Path(sys.argv[1]) / 'src'))
from fluentpy import CodeEdit, FluentWindow, LineEdit, theme
from fluentpy.qt import QtCore, QtWidgets, QT_API
if QT_API == 'PySide6':
    from PySide6.QtTest import QTest
else:
    from PyQt6.QtTest import QTest

app = QtWidgets.QApplication([])
app.setQuitOnLastWindowClosed(False)
errors = []
def report_error(kind, error, tb):
    errors.append(''.join(traceback.format_exception(kind, error, tb)))
    traceback.print_exception(kind, error, tb)
sys.excepthook = report_error
print('stage: app initialized', flush=True)

def flush():
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    app.processEvents()

original = theme.tokens
for index in range(8):
    print('stage: gc iteration', index, flush=True)
    abandoned = FluentWindow('Unretained documentation window')
    abandoned.set_theme_transition_enabled(bool(index % 2))
    # Force cyclic collection even if future ownership fixes make the ordinary
    # unretained window eligible for immediate reference-count destruction.
    abandoned._test_cycle = abandoned
    reference = weakref.ref(abandoned)
    abandoned = None
    gc.collect()
    assert reference() is None, 'An abandoned theme owner must not leak.'
    editor = CodeEdit()
    editor.set_code('{"retained": true}')
    assert editor.code() == '{"retained": true}'
    editor.deleteLater()
    flush()
    editor = None
    assert not errors, errors

window = FluentWindow('Dynamic transition children')
print('stage: dynamic window', flush=True)
window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
window.set_title_bar_enabled(True)
window.set_theme_transition_enabled(True)
window.resize(720, 620)
field = LineEdit()
field.setText('retained ')
button = QtWidgets.QPushButton('Apply')
clicks = []
button.clicked.connect(lambda: clicks.append(True))
window.content_layout.addWidget(field)
window.content_layout.addWidget(button)
window.content_layout.addStretch()
window.show()
QTest.qWait(100)
transition = window._theme_transition
assert transition.duration == 280
# Keep the real asynchronous transition open during construction even on a
# heavily loaded runner. Input should end it, without advancing its timeline.
transition.duration = 1500
theme.toggle()
assert transition.is_running()
assert transition._input_filter_installed
print('stage: animation started', flush=True)

dynamic = []
for widget_type in (LineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit, CodeEdit):
    print('stage: dynamic', widget_type.__name__, flush=True)
    widget = widget_type(parent=window)
    window.content_layout.insertWidget(2, widget)
    widget.show()
    dynamic.append(widget)
assert transition.is_running(), 'Child construction must not dismiss the transition.'
assert not errors, errors

# Exercise deferred C++ destruction while the application-wide input filter is
# installed, then immediately construct another editor against the same owner.
deleted = dynamic.pop()
deleted.deleteLater()
print('stage: deleting dynamic editor', flush=True)
flush()
deleted = None
replacement = CodeEdit(window)
replacement.set_code('{"created_during_transition": true}')
window.content_layout.insertWidget(2, replacement)
assert transition.is_running()
assert not errors, errors

field.setFocus()
field.setCursorPosition(len(field.text()))
QTest.keyClicks(field, 'typed')
print('stage: keyboard sent', flush=True)
assert field.text() == 'retained typed'
assert window.focusWidget() is field
flush()
assert not transition.is_running(), 'Keyboard input must reveal live content.'
assert not transition._input_filter_installed
assert window.updatesEnabled()

theme.toggle()
assert transition.is_running()
assert transition.layer.testAttribute(QtCore.Qt.WidgetAttribute.WA_TransparentForMouseEvents)
QTest.mouseClick(button, QtCore.Qt.MouseButton.LeftButton)
flush()
assert clicks == [True], 'The transition must not swallow the native button click.'
assert not transition.is_running()
assert not transition._input_filter_installed

# Delete an owner with its transition still running; Qt must detach all its
# filters before the next unrelated native editor is constructed.
theme.toggle()
assert transition.is_running()
window.deleteLater()
print('stage: deleting active window', flush=True)
flush()
window = field = button = replacement = transition = widget = None
dynamic.clear()
gc.collect()
editor = CodeEdit()
editor.set_code('still usable')
assert editor.code() == 'still usable'
editor.deleteLater()
flush()
editor = None
theme.set_theme(original.mode, accent=original.custom_accent)
gc.collect()
flush()
assert not errors, errors
print(json.dumps({'platform': app.platformName(), 'gc_iterations': 8,
                  'dynamic_widget_types': 4, 'keyboard': True, 'mouse': True,
                  'errors': errors}))
"""


class ThemeLifecycleTests(unittest.TestCase):
    def run_probe(self, platform):
        env = dict(os.environ, QT_QPA_PLATFORM=platform, QT_SCALE_FACTOR="1")
        result = subprocess.run(
            [
                sys.executable,
                "-I",
                "-B",
                "-X",
                "utf8",
                "-X",
                "faulthandler",
                "-c",
                _PROBE,
                str(ROOT),
            ],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=30,
        )
        details = f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        self.assertEqual(result.returncode, 0, details)
        self.assertIn('"gc_iterations": 8', result.stdout, details)
        self.assertIn('"keyboard": true, "mouse": true', result.stdout, details)
        self.assertIn('"errors": []', result.stdout, details)
        self.assertNotIn("Error calling Python override", result.stderr, details)
        self.assertNotIn("Traceback", result.stderr, details)
        self.assertNotIn("SystemError", result.stderr, details)

    def test_abandoned_windows_and_dynamic_children_offscreen(self):
        self.run_probe("offscreen")

    @unittest.skipUnless(sys.platform == "win32", "Native Windows Qt platform required")
    def test_abandoned_windows_and_dynamic_children_native_windows(self):
        self.run_probe("windows")


if __name__ == "__main__":
    unittest.main()
