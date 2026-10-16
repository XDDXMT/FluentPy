"""Render the real CodeEdit in both themes, with a light-only website preview."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from code_editor import SAMPLE
from fluentpy import CodeEdit, theme
from fluentpy.qt import QtCore, QtWidgets
from fluentpy.theme.fonts import ui_font

app = QtWidgets.QApplication([])
app.setFont(ui_font(14))
output = ROOT / "docs" / "assets"
output.mkdir(parents=True, exist_ok=True)
errors = []
sys.excepthook = lambda kind, error, traceback: errors.append(str(error))
retained = []
for mode in ("light", "dark"):
    theme.set_mode(mode)
    editor = CodeEdit()
    editor.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    editor.set_indent_size(2)
    editor.set_code(SAMPLE)
    editor.resize(760, 540)
    editor.show()
    editor.clearFocus()
    app.processEvents()
    editor.clearFocus()
    image = editor.grab()
    assert image.save(str(output / f"code-editor-{mode}.png"))
    if mode == "light":
        web = ROOT / "sites" / "fluentpy-docs" / "dist" / "assets" / "previews"
        if web.is_dir():
            assert image.save(str(web / "code-editor-light.png"))
    retained.append(editor)
    editor.hide()
assert not errors, errors
print("Rendered light/dark CodeEdit screenshots and the light-only documentation preview.")
