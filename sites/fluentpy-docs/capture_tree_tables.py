"""Capture our Qt tree-list examples and native expansion/selection animation."""

from __future__ import annotations

import sys
import traceback

from capture_animations import (
    ROOT,
    SITE,
    QtCore,
    QTest,
    QtWidgets,
    _capture_font,
    _font_families,
    _image,
    _write_gif,
)

sys.path.insert(0, str(ROOT / "examples"))
from tree_tables import TreeTableExamples

from fluentpy import theme


def main():
    app = QtWidgets.QApplication([])
    app.setFont(_capture_font())
    errors = []
    previous = sys.excepthook

    def record_error(kind, error, tb):
        errors.append(str(error))
        traceback.print_exception(kind, error, tb)

    sys.excepthook = record_error
    output = SITE / "dist/assets/previews"
    output.mkdir(parents=True, exist_ok=True)
    for mode in ("light", "dark"):
        theme.set_mode(mode)
        root = QtWidgets.QWidget()
        root.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen)
        root.setObjectName("treeCanvas")
        root.setFont(_capture_font())
        root.setStyleSheet(
            f"QWidget#treeCanvas {{background:{theme.tokens.background};}}"
            f"QLabel {{color:{theme.tokens.text};background:transparent;}}"
        )
        layout = QtWidgets.QVBoxLayout(root)
        layout.setContentsMargins(22, 18, 22, 18)
        heading = QtWidgets.QLabel("树形数据列表 · 同一组件，多种用途")
        layout.addWidget(heading)
        examples = TreeTableExamples(root)
        layout.addWidget(examples)
        root.setFixedSize(1020, 640)
        root.show()
        QTest.qWait(180)
        _font_families(examples.metrics, "名称 CPU 内存 FluentPy")
        for scene, name in enumerate(("tree-list-demo", "tree-list-tasks", "tree-list-resources")):
            examples.scene.setCurrentIndex(scene)
            QTest.qWait(160)
            _image(root).save(output / f"{name}-{mode}.png")
        if mode == "light":
            examples.scene.setCurrentIndex(0)
            QTest.qWait(180)
            tree = examples.metrics
            frames, elapsed = [], []
            initial_note = examples.result.text()

            def restore():
                tree.clearSelection()
                tree.setCurrentIndex(QtCore.QModelIndex())
                tree.set_sort_mode("hierarchical")
                tree.sortByColumn(-1, QtCore.Qt.SortOrder.AscendingOrder)
                with tree.batch_update():
                    for number, value in enumerate((3.2, 14.5, 6.8, 0.8)):
                        tree.update_item(f"app-{number}", {"cpu": value})
                tree.set_header_summary("cpu", "15%")
                examples.result.setText(initial_note)

            operations = {
                600: lambda: tree.collapse(tree.view_index("apps")),
                1050: lambda: tree.expand(tree.view_index("apps")),
                1600: lambda: tree.sortByColumn(2, QtCore.Qt.SortOrder.DescendingOrder),
                2050: examples.update_batch,
                2500: lambda: examples.search.setText("浏览器"),
                3100: examples.search.clear,
                3500: lambda: tree.setCurrentIndex(tree.view_index("app-2")),
                3700: restore,
            }
            for time in range(0, 4000, 50):
                if time in operations:
                    operations[time]()
                app.processEvents()
                frames.append(_image(root))
                elapsed.append(time)
                QTest.qWait(50)
            frames[0].save(output / "tree-list-motion-light.png")
            print(_write_gif(frames, elapsed, output / "tree-list-motion-light.gif"))
        root.close()
        root.deleteLater()
        app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        app.processEvents()
    sys.excepthook = previous
    if errors:
        raise RuntimeError(errors)
    print("Captured three tree-list scenes in light/dark and the real Qt animations.")


if __name__ == "__main__":
    main()
