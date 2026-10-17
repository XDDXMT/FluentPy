"""Capture only FluentPy's file/folder areas; component media is always light."""

from pathlib import Path
import sys
import io

from PIL import Image

SITE = Path(__file__).resolve().parent
from source_project import source_root
ROOT = source_root()
sys.path.insert(0, str(ROOT / "src"))
from fluentpy import FileDropWidget, FolderDropWidget, theme
from fluentpy.qt import QtCore, QtGui, QtWidgets
from fluentpy.theme.fonts import ui_font

app = QtWidgets.QApplication([])
app.setFont(ui_font(14))
theme.set_mode("light")
output = SITE / "dist" / "assets" / "previews"
output.mkdir(parents=True, exist_ok=True)
retained = []

def capture(widget, width, name):
    host = QtWidgets.QWidget()
    host.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    host.setObjectName("dropPreview")
    host.setStyleSheet(f"QWidget#dropPreview {{background: {theme.tokens.surface_high};}}")
    layout = QtWidgets.QVBoxLayout(host)
    layout.setContentsMargins(20, 20, 20, 20)
    layout.addWidget(widget)
    host.resize(width, 184)
    host.show()
    app.processEvents()
    assert host.grab().save(str(output / f"{name}-light.png"))
    retained.append(host)
    return host

files = FileDropWidget()
host = capture(files, 340, "drop-file")
capture(FolderDropWidget(), 286, "drop-folder")
mime = QtCore.QMimeData()
mime.setUrls([QtCore.QUrl.fromLocalFile(str(ROOT / "docs" / "assets" / "drop-light.png"))])
frames = []
for elapsed in range(0, 1600, 40):
    if elapsed == 0:
        app.sendEvent(files, QtGui.QDragEnterEvent(QtCore.QPoint(12, 12), QtCore.Qt.DropAction.CopyAction, mime,
                      QtCore.Qt.MouseButton.LeftButton, QtCore.Qt.KeyboardModifier.NoModifier))
    if elapsed == 800:
        app.sendEvent(files, QtGui.QDragLeaveEvent())
    files._animation.setCurrentTime(min(150, elapsed if elapsed < 800 else elapsed-800))
    app.processEvents()
    data = QtCore.QByteArray()
    buffer = QtCore.QBuffer(data)
    buffer.open(QtCore.QIODevice.OpenModeFlag.WriteOnly)
    assert host.grab().save(buffer, "PNG")
    frames.append(Image.open(io.BytesIO(bytes(data))).convert("RGB"))
frames[0].save(output / "drop-file-active-light.gif", save_all=True, append_images=frames[1:],
               duration=40, loop=0, disposal=2)
print("Captured file/folder PNGs and drag feedback GIF at natural component sizes.")
