"""Validate an installed wheel in an isolated interpreter."""

import argparse
import json
import os
import sys
from importlib import metadata, resources
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expect-backend", choices=("python", "native"), required=True)
    parser.add_argument("--expect-version", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    os.environ["FLUENTPY_BACKEND"] = "auto"
    import fluentpy
    from fluentpy import (
        AccentButton,
        AccentSplitButton,
        ActionMenu,
        AffixLineEdit,
        AudioPlayer,
        AvatarPicker,
        CodeEdit,
        CompactAudioPlayer,
        DatePicker,
        FluentIcon,
        FluentWindow,
        ImageCropper,
        ImageMagnifier,
        ImageView,
        InfoBar,
        MediaController,
        PinCodeEdit,
        TableView,
        TreeColumn,
        TreeTableWidget,
        VideoPlayer,
        fluent_icon,
        theme,
    )
    from fluentpy.backends import calendar, color, date, drop, shortcut, syntax, text, time
    from fluentpy.backends import input as segmented
    from fluentpy.qt import QtCore, QtGui, QtWidgets

    package_path = Path(fluentpy.__file__).resolve()
    assert package_path.is_relative_to(Path(sys.prefix).resolve()), package_path
    version = metadata.version("fluentpy-qt")
    assert version == fluentpy.__version__ == args.expect_version
    backends = {
        name: module.backend_name()
        for name, module in (
            ("text", text),
            ("date", date),
            ("time", time),
            ("calendar", calendar),
            ("drop", drop),
            ("shortcut", shortcut),
            ("color", color),
            ("input", segmented),
            ("syntax", syntax),
        )
    }
    assert set(backends.values()) == {args.expect_backend}, backends
    assert text.json_spans('{"ok":true,"n":12}')
    assert syntax.syntax_spans("class Example { return true; }", "java")[0]
    assert date.days_in_month(2024, 2) == 29
    assert time.step_time(23, 59, 1, 1) == (23, 0)
    assert calendar.shift_date((2024, 2, 28), days=2) == (2024, 3, 1)
    assert drop.normalize_extensions([".txt"]) == (".txt",)
    assert shortcut.normalize(ord("s"), 0x04000000) == (ord("S"), 0x04000000)
    assert color.parse_hex("#123456") == (18, 52, 86, 255)
    assert segmented.split_code("1234", 4) == ("1", "2", "3", "4")
    errors = []
    sys.excepthook = lambda kind, value, tb: errors.append(str(value))
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    independent = QtWidgets.QWidget()
    independent.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
    independent_layout = QtWidgets.QVBoxLayout(independent)
    image = QtGui.QImage(400, 200, QtGui.QImage.Format.Format_RGB32)
    image.fill(QtGui.QColor("#009faa"))
    display = ImageView(image)
    independent_layout.addWidget(display)
    avatar = AvatarPicker(image)
    independent_layout.addWidget(avatar)
    crop = ImageCropper(image)
    crop.set_aspect_ratio(1)
    assert crop.cropped_image().width() == crop.cropped_image().height()
    magnifier = ImageMagnifier(image)
    magnifier.set_lens_size(QtCore.QSize(120, 90))
    magnifier.set_anchor(QtCore.QPointF(200, 100))
    assert magnifier.magnified_image().size() == QtCore.QSize(120, 90)
    independent_layout.addWidget(magnifier)
    hierarchy = TreeTableWidget([TreeColumn("name", "Name"), TreeColumn("value", "Value")])
    group = hierarchy.append_item({"name": "Group"}, key="group", group=True)
    hierarchy.append_item({"name": "Parent", "value": 5}, parent=group, key="parent")
    hierarchy.append_item({"name": "Child", "value": 12}, parent="parent", key="child")
    hierarchy.set_sort_mode("flat")
    hierarchy.sortByColumn(1, QtCore.Qt.SortOrder.DescendingOrder)
    assert hierarchy.model().index(0, 1).data() == 12
    hierarchy.set_sort_mode("hierarchical")
    independent_layout.addWidget(hierarchy)
    media = MediaController(independent)
    media.set_muted(True)
    compact = CompactAudioPlayer(controller=media)
    full = AudioPlayer(controller=media)
    independent_layout.addWidget(compact)
    independent_layout.addWidget(full)
    video = VideoPlayer(controller=media)
    assert video.controller.player().videoOutput() is video.video_widget
    video.deleteLater()
    independent.resize(700, 800)
    independent.show()
    app.processEvents()
    assert compact.play_button.isVisible()
    compact.volume_button.click()
    app.processEvents()
    assert compact.volume_flyout.isVisible()
    assert media.is_muted()
    compact.volume_slider.setValue(33)
    assert compact.volume_flyout.control.value_label.text() == "33"
    assert abs(media.volume() - 0.33) < 0.001 and not media.is_muted()
    compact.volume_flyout.dismiss()
    assert not independent.grab().isNull()
    assert "showcase" not in sys.modules and "tree_tables" not in sys.modules
    for widget in (crop, independent):
        widget.close()
        widget.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    icons = list(FluentIcon)
    for icon in icons:
        assert not fluent_icon(icon).pixmap(24, 24).isNull(), icon
    assert resources.files("fluentpy.assets.icons").joinpath("SOURCE.md").is_file()
    inventory = json.loads(
        resources.files("fluentpy.assets.icons").joinpath("UPSTREAM.json").read_text("utf-8")
    )
    assert len(inventory["icons"]) + 1 == len(icons)
    assert inventory["license"] == "MIT"
    window = FluentWindow("Installed wheel")
    window.resize(800, 600)
    window.set_title_bar_enabled(True)
    window.content_layout.addWidget(AccentButton("Installed package"))
    affix = AffixLineEdit(prefix="https://", suffix=".com")
    affix.setText("example")
    assert affix.text() == "example"
    window.content_layout.addWidget(affix)
    pin = PinCodeEdit()
    pin.set_text("1234")
    assert pin.text() == "1234"
    window.content_layout.addWidget(pin)
    picker = DatePicker()
    picker.set_date(QtCore.QDate(2024, 2, 29))
    window.content_layout.addWidget(picker)
    table = TableView()
    model = QtGui.QStandardItemModel(0, 1, window)
    for value in (30, 2, 10):
        item = QtGui.QStandardItem()
        item.setData(value, QtCore.Qt.ItemDataRole.DisplayRole)
        model.appendRow(item)
    proxy = QtCore.QSortFilterProxyModel(window)
    proxy.setSourceModel(model)
    table.setModel(proxy)
    table.setSortingEnabled(True)
    table.sortByColumn(0, QtCore.Qt.SortOrder.AscendingOrder)
    assert [proxy.index(row, 0).data() for row in range(3)] == [2, 10, 30]
    table.selectRow(0)
    assert table.selection_text() == "2"
    window.content_layout.addWidget(table)
    editor = CodeEdit()
    for language in CodeEdit.supported_languages():
        editor.set_language(language)
        editor.set_code('class Example { return "😀"; }')
        assert not editor.syntax_highlighter().last_error()
    editor.set_language("json")
    editor.setPlainText('{"installed":true}')
    window.content_layout.addWidget(editor)
    window.content_layout.addWidget(InfoBar("Installed package", "Inline message", window))
    split = AccentSplitButton("Launch", window, description="1.0")
    versions = ActionMenu(window)
    choice = versions.add_action("1.1", callback=lambda: split.set_description("1.1"))
    split.set_menu(versions)
    split_calls = []
    split.clicked.connect(lambda: split_calls.append(split.description()))
    window.content_layout.addWidget(split)
    window.show()
    split.show_menu()
    assert versions.isVisible()
    choice.trigger()
    versions.dismiss(immediate=True)
    assert split.description() == "1.1" and not split_calls
    split.main_button.click()
    assert split_calls == ["1.1"]
    assert split.menu_button.height() == split.main_button.height() >= 52
    for mode in ("light", "dark"):
        theme.set_mode(mode)
        app.processEvents()
        assert not window.grab().isNull()
        assert pin.text() == "1234"
    window.close()
    window.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    app.processEvents()
    assert not errors, errors
    report = {
        "distribution": "fluentpy-qt",
        "version": version,
        "package_path": str(package_path),
        "qt": QtCore.qVersion(),
        "backends": backends,
        "icons": len(icons),
        "split_button_description": split.description(),
        "qt_errors": errors,
    }
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
