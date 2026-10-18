"""Run with -I in a clean venv to exercise the installed wheel, never src/."""
import argparse
from importlib import metadata, resources
import json
import os
from pathlib import Path
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expect-backend', choices=('python', 'native'), required=True)
    parser.add_argument('--expect-version', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    os.environ['FLUENTPY_BACKEND'] = 'auto'
    import fluentpy
    from fluentpy import (FluentWindow, AccentButton, AffixLineEdit, PinCodeEdit,
                          TableView, DatePicker, CodeEdit, InfoBar, FluentIcon, fluent_icon, theme)
    from fluentpy.backends import text, date, time, calendar, drop, shortcut, color
    from fluentpy.backends import input as segmented
    from fluentpy.qt import QtCore, QtGui, QtWidgets
    package_path = Path(fluentpy.__file__).resolve()
    assert package_path.is_relative_to(Path(sys.prefix).resolve()), package_path
    version = metadata.version('fluentpy-qt')
    assert version == fluentpy.__version__ == args.expect_version
    backends = {name: module.backend_name() for name, module in (
        ('text', text), ('date', date), ('time', time), ('calendar', calendar),
        ('drop', drop), ('shortcut', shortcut), ('color', color), ('input', segmented))}
    assert set(backends.values()) == {args.expect_backend}, backends
    assert text.json_spans('{"ok":true,"n":12}')
    assert date.days_in_month(2024, 2) == 29
    assert time.step_time(23, 59, 1, 1) == (23, 0)
    assert calendar.shift_date((2024, 2, 28), days=2) == (2024, 3, 1)
    assert drop.normalize_extensions(['.txt']) == ('.txt',)
    assert shortcut.normalize(ord('s'), 0x04000000) == (ord('S'), 0x04000000)
    assert color.parse_hex('#123456') == (18, 52, 86, 255)
    assert segmented.split_code('1234', 4) == ('1', '2', '3', '4')
    errors = []
    sys.excepthook = lambda kind, value, tb: errors.append(str(value))
    app = QtWidgets.QApplication([])
    app.setQuitOnLastWindowClosed(False)
    icons = list(FluentIcon)
    for icon in icons:
        assert not fluent_icon(icon).pixmap(24, 24).isNull(), icon
    assert resources.files('fluentpy.assets.icons').joinpath('SOURCE.md').is_file()
    window = FluentWindow('Installed wheel')
    window.resize(800, 600)
    window.set_title_bar_enabled(True)
    window.content_layout.addWidget(AccentButton('Installed package'))
    affix = AffixLineEdit(prefix='https://', suffix='.com')
    affix.setText('example')
    assert affix.text() == 'example'
    window.content_layout.addWidget(affix)
    pin = PinCodeEdit()
    pin.set_text('1234')
    assert pin.text() == '1234'
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
    assert table.selection_text() == '2'
    window.content_layout.addWidget(table)
    editor = CodeEdit()
    editor.setPlainText('{"installed":true}')
    window.content_layout.addWidget(editor)
    window.content_layout.addWidget(InfoBar('Installed package', 'Inline message', window))
    window.show()
    for mode in ('light', 'dark'):
        theme.set_mode(mode)
        app.processEvents()
        assert not window.grab().isNull()
        assert pin.text() == '1234'
    window.close()
    window.deleteLater()
    app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
    app.processEvents()
    assert not errors, errors
    report = {'distribution': 'fluentpy-qt', 'version': version, 'package_path': str(package_path),
              'qt': QtCore.qVersion(), 'backends': backends, 'icons': len(icons), 'qt_errors': errors}
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
