"""Compare original/Python/C text performance without blocking this UI.

Run ``python examples/text_performance.py`` after building the optional native
extension. Measurements execute in a QProcess; the preview remains editable.
"""

from __future__ import annotations

import argparse
import codecs
import json
import os
from pathlib import Path
import sys

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from fluentpy import AccentButton, Button, CodeEdit, ComboBox, FluentWindow, ProgressBar, theme  # noqa: E402
from fluentpy.backends.text import native_available  # noqa: E402
from fluentpy.qt import QtCore, QtGui, QtWidgets  # noqa: E402
from fluentpy.theme.fonts import ui_font  # noqa: E402
from scripts.benchmark_baseline import generate_json  # noqa: E402


METRICS = (
    ("载入与首帧", "load_ready_ms"),
    ("JSON 分词", "lexer_ms"),
    ("完整重新高亮", "rehighlight_ms"),
    ("单次编辑", "edit_ms"),
    ("连续滚动", "scroll_ms"),
)


class TextPerformanceDemo(FluentWindow):
    def __init__(self, *, dark: bool = False) -> None:
        super().__init__("FluentPy · C 扩展性能对照")
        self.resize(1000, 790)
        self.setMinimumSize(820, 660)
        self.set_dark(dark)
        self._stdout = ""
        self._stderr = ""
        self._stdout_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._stderr_decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
        self._cancelled = False
        self._received_result = False
        self._completed_stages = 0
        self._report: dict | None = None
        self.process = QtCore.QProcess(self)
        self.process.readyReadStandardOutput.connect(self._read_stdout)
        self.process.readyReadStandardError.connect(self._read_stderr)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._process_error)
        self._tree_killer = QtCore.QProcess(self)
        self._tree_killer.errorOccurred.connect(self._tree_kill_error)
        self.elapsed = QtCore.QElapsedTimer()
        self.clock = QtCore.QTimer(self)
        self.clock.setInterval(200)
        self.clock.timeout.connect(self._tick)

        layout = self.content_layout
        layout.setContentsMargins(24, 22, 24, 22)
        layout.setSpacing(12)
        heading = QtWidgets.QLabel("把提速交给实测")
        heading.setObjectName("benchmarkHeading")
        layout.addWidget(heading)
        introduction = QtWidgets.QLabel("同一份 JSON，对照原始版本、Python 后端与 C 后端。测量完整高亮、编辑和滚动，保留全部文本。")
        introduction.setObjectName("muted")
        introduction.setWordWrap(True)
        layout.addWidget(introduction)

        controls = QtWidgets.QHBoxLayout()
        controls.setSpacing(10)
        controls.addWidget(QtWidgets.QLabel("数据规模"))
        self.scale = ComboBox()
        self.scale.addItems(["1,000 行 JSON", "10,000 行 JSON", "50,000 行 JSON"])
        self.scale.setCurrentIndex(1)
        controls.addWidget(self.scale)
        self.run_button = AccentButton("开始对照")
        self.run_button.clicked.connect(self.start_benchmark)
        controls.addWidget(self.run_button)
        self.cancel_button = Button("停止")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_benchmark)
        controls.addWidget(self.cancel_button)
        controls.addStretch()
        self.time_label = QtWidgets.QLabel("每项取 3 次测量中位数")
        self.time_label.setObjectName("muted")
        controls.addWidget(self.time_label)
        layout.addLayout(controls)

        self.backend_label = QtWidgets.QLabel("C 扩展已加载 · 测试将在独立进程运行" if native_available() else "C 扩展尚未编译 · 可先查看 Python 基准")
        self.backend_label.setObjectName("muted")
        layout.addWidget(self.backend_label)
        self.progress = ProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)
        self.status = QtWidgets.QLabel("选择数据规模，然后开始。测试时仍可在下方编辑示例。")
        self.status.setWordWrap(True)
        layout.addWidget(self.status)

        self.table = QtWidgets.QTableWidget(len(METRICS), 5)
        self.table.setHorizontalHeaderLabels(["指标", "原始版本", "Python 后端", "C 后端", "C 相对原始"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.table.setShowGrid(False)
        self.table.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.table.horizontalHeader().setSectionResizeMode(QtWidgets.QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.table.setMinimumHeight(204)
        self.table.setMaximumHeight(230)
        self.table.verticalHeader().setDefaultSectionSize(33)
        layout.addWidget(self.table)
        self._clear_table()

        self.data_label = QtWidgets.QLabel("载入统计会包含 UTF-16 长度、完整性校验与真实 Qt 高亮。耗时越低越好；倍率仅代表本机这次测量。")
        self.data_label.setObjectName("muted")
        self.data_label.setWordWrap(True)
        layout.addWidget(self.data_label)
        self.line_warning = QtWidgets.QLabel("LineEdit 是单行控件，默认最多 32,767 个 UTF-16 单元。万行 JSON 应使用 CodeEdit 或 TextEdit。")
        self.line_warning.setObjectName("muted")
        self.line_warning.setWordWrap(True)
        layout.addWidget(self.line_warning)

        preview_header = QtWidgets.QHBoxLayout()
        preview_header.addWidget(QtWidgets.QLabel("可编辑示例 · 不参与上方耗时"))
        preview_header.addStretch()
        self.report_button = Button("打开完整报告")
        self.report_button.setEnabled(False)
        self.report_button.clicked.connect(self.open_report)
        preview_header.addWidget(self.report_button)
        layout.addLayout(preview_header)
        self.preview = CodeEdit()
        self.preview.set_indent_size(2)
        self.preview.set_code(generate_json(48))
        layout.addWidget(self.preview, 1)
        self._apply_demo_theme()
        theme.subscribe(self, self._apply_demo_theme)
        self._load_previous_report()

    def _load_previous_report(self) -> None:
        path = Path(os.environ.get("FLUENTPY_BENCHMARK_REPORT", str(ROOT / "benchmarks" / "text-performance.json")))
        if not path.is_file():
            return
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
            lines = report.get("dataset", {}).get("lines")
            if lines in (1000, 10000, 50000) and isinstance(report.get("summary"), dict):
                self._show_report(report)
                self.scale.setCurrentIndex((1000, 10000, 50000).index(lines))
                self.status.setText("已载入上一次本机对照报告，点击“开始对照”可重新测量。")
        except (OSError, ValueError, TypeError):
            pass

    def _apply_demo_theme(self) -> None:
        if not hasattr(self, "table"):
            return
        tokens = theme.tokens
        self.table.setStyleSheet(
            f"QTableWidget {{ background: {tokens.surface}; color: {tokens.text}; border: 1px solid {tokens.border}; border-radius: 5px; }}"
            f"QTableWidget::item {{ border: none; padding: 4px 10px; }}"
            f"QHeaderView::section {{ background: {tokens.surface}; color: {tokens.text_muted}; border: none; padding: 8px 10px; }}"
            "QTableCornerButton::section { border: none; }"
        )
        heading = self.findChild(QtWidgets.QLabel, "benchmarkHeading")
        if heading:
            heading.setStyleSheet(f"font-size: 24px; font-weight: 600; color: {tokens.text};")

    def _clear_table(self) -> None:
        for row, (label, _key) in enumerate(METRICS):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(label))
            for column in range(1, 5):
                self.table.setItem(row, column, QtWidgets.QTableWidgetItem("—"))

    def start_benchmark(self) -> None:
        if self.process.state() != QtCore.QProcess.ProcessState.NotRunning:
            return
        script = ROOT / "scripts" / "benchmark_text.py"
        if not script.is_file():
            self.status.setText("未找到性能测量脚本，请从完整的 FluentPy 项目运行此示例。")
            return
        self._stdout = self._stderr = ""
        self._stdout_decoder.reset()
        self._stderr_decoder.reset()
        self._cancelled = self._received_result = False
        self._completed_stages = 0
        self._clear_table()
        self.scale.setEnabled(False)
        self.run_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.report_button.setEnabled(False)
        self.progress.setRange(0, 0)
        self.status.setText("正在准备相同的 JSON 数据与独立测试进程……")
        lines = (1000, 10000, 50000)[self.scale.currentIndex()]
        executable = Path(sys.executable)
        if executable.name.lower() == "pythonw.exe":
            executable = executable.with_name("python.exe")
        env = QtCore.QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("PYTHONUNBUFFERED", "1")
        self.process.setProcessEnvironment(env)
        self.process.setWorkingDirectory(str(ROOT))
        self.process.setProgram(str(executable))
        command = ["--benchmark"] if getattr(sys, "frozen", False) else ["-B", str(script)]
        self.process.setArguments(command + ["--lines", str(lines), "--repeat", "3", "--json"])
        self.elapsed.start()
        self.clock.start()
        self.process.start()

    def cancel_benchmark(self) -> None:
        if self.process.state() != QtCore.QProcess.ProcessState.NotRunning:
            self._cancelled = True
            self.status.setText("正在停止测试……")
            self._stop_owned_process_tree()

    def _stop_owned_process_tree(self) -> None:
        """Stop only this QProcess and its benchmark workers, asynchronously."""
        if self.process.state() == QtCore.QProcess.ProcessState.NotRunning:
            return
        process_id = int(self.process.processId())
        if sys.platform == "win32" and process_id > 0:
            if self._tree_killer.state() != QtCore.QProcess.ProcessState.NotRunning:
                return
            taskkill = Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "taskkill.exe"
            self._tree_killer.setProgram(str(taskkill))
            self._tree_killer.setArguments(["/PID", str(process_id), "/T", "/F"])
            self._tree_killer.start()
        else:
            self.process.kill()

    def _tree_kill_error(self, _error) -> None:
        if self.process.state() != QtCore.QProcess.ProcessState.NotRunning:
            self.process.kill()

    def _read_stdout(self) -> None:
        self._stdout += self._stdout_decoder.decode(bytes(self.process.readAllStandardOutput()))
        while "\n" in self._stdout:
            line, self._stdout = self._stdout.split("\n", 1)
            self._consume_line(line)

    def _read_stderr(self) -> None:
        self._stderr = (self._stderr + self._stderr_decoder.decode(bytes(self.process.readAllStandardError())))[-30000:]

    def _consume_line(self, line: str) -> None:
        if not line.strip():
            return
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            self._stderr = (self._stderr + "\n" + line)[-30000:]
            return
        kind = event.get("event")
        if kind == "progress":
            self.status.setText(str(event.get("message", "测量中……")))
        elif kind == "result":
            self._received_result = True
            self._show_report(event.get("report", {}))
        elif kind == "error":
            self.status.setText("测试未完成：" + str(event.get("message", "未知错误")))

    @staticmethod
    def _number(value) -> float | None:
        return float(value) if isinstance(value, (int, float)) else None

    def _show_report(self, report: dict) -> None:
        self._report = report
        summary = report.get("summary", {})
        for row, (_label, key) in enumerate(METRICS):
            for column, backend in enumerate(("legacy", "python", "native"), start=1):
                value = self._number(summary.get(backend, {}).get(key))
                self.table.item(row, column).setText(f"{value:.2f} ms" if value is not None else "—")
            old = self._number(summary.get("legacy", {}).get(key))
            native = self._number(summary.get("native", {}).get(key))
            self.table.item(row, 4).setText(f"{old / native:.2f}×" if old is not None and native and native > 0 else "—")
        dataset = report.get("dataset", {})
        lines = dataset.get("lines", 0)
        size = dataset.get("utf8_bytes", 0) / 1024
        utf16 = dataset.get("utf16_units", dataset.get("utf16_length", 0))
        repetitions = report.get("repeat", 3)
        self.data_label.setText(f"{lines:,} 行 · {size:,.1f} KiB UTF-8 · {utf16:,} 个 UTF-16 单元。每项取 {repetitions} 次测量中位数；本机实测，耗时越低越好。")
        if self.process.state() == QtCore.QProcess.ProcessState.NotRunning:
            self.time_label.setText(f"每项取 {repetitions} 次测量中位数")
        available = bool(report.get("backend_available"))
        self.backend_label.setText("C 扩展已加载 · Python 与 C 使用相同文本、颜色和完整高亮路径" if available else "C 扩展未加载 · 当前报告仅包含可用的 Python 测量")
        line_info = report.get("line_edit", {})
        exact = line_info.get("default_preserved_exact_text", line_info.get("preserved_exact_text"))
        maximum = line_info.get("default_max_length", 32767)
        if exact is False:
            self.line_warning.setText(f"LineEdit 完整性检查：默认上限 {maximum:,} 个 UTF-16 单元，输入被截断。该耗时不计作万行 JSON 提速。")
        elif exact is True:
            self.line_warning.setText(f"LineEdit 完整性检查：本次文本在默认 {maximum:,} 个 UTF-16 单元上限内，完整保留。多行编辑仍请使用 CodeEdit 或 TextEdit。")
        else:
            self.line_warning.setText("LineEdit 是单行控件；本次报告未提供其完整性检查结果。")
        self.progress.setRange(0, 100)
        self.progress.setValue(100)
        self.status.setText("对照完成。下方为独立可编辑示例，完整数据与测量明细已写入报告。")
        self.report_button.setEnabled(Path(os.environ.get("FLUENTPY_BENCHMARK_REPORT", str(ROOT / "benchmarks" / "text-performance.json"))).is_file())

    def _tick(self) -> None:
        self.time_label.setText(f"已用 {self.elapsed.elapsed() / 1000:.1f} 秒 · 窗口可继续操作")

    def _finished(self, exit_code: int, _exit_status) -> None:
        self._read_stdout()
        self._read_stderr()
        if self._stdout.strip():
            self._consume_line(self._stdout)
            self._stdout = ""
        self.clock.stop()
        self.time_label.setText(f"用时 {self.elapsed.elapsed() / 1000:.1f} 秒")
        self.scale.setEnabled(True)
        self.run_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress.setRange(0, 100)
        if self._cancelled:
            self.status.setText("测试已停止，可以重新选择数据规模。")
            self.progress.setValue(0)
        elif not self._received_result:
            detail = self._stderr.strip().splitlines()[-1] if self._stderr.strip() else f"退出状态 {exit_code}"
            self.status.setText("测试未完成：" + detail)
            self.progress.setValue(0)
        self.report_button.setEnabled(Path(os.environ.get("FLUENTPY_BENCHMARK_REPORT", str(ROOT / "benchmarks" / "text-performance.json"))).is_file())

    def _process_error(self, error) -> None:
        if error == QtCore.QProcess.ProcessError.FailedToStart:
            self.clock.stop()
            self.scale.setEnabled(True)
            self.run_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.status.setText("无法启动测试进程：" + self.process.errorString())

    def open_report(self) -> None:
        path = Path(os.environ.get("FLUENTPY_BENCHMARK_REPORT", str(ROOT / "benchmarks" / "text-performance.json")))
        if path.is_file():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(path)))

    def closeEvent(self, event) -> None:
        if self.process.state() != QtCore.QProcess.ProcessState.NotRunning:
            self._cancelled = True
            self._stop_owned_process_tree()
            if self._tree_killer.state() != QtCore.QProcess.ProcessState.NotRunning:
                self._tree_killer.waitForFinished(1500)
            self.process.waitForFinished(1500)
        super().closeEvent(event)


def main() -> int:
    parser = argparse.ArgumentParser(description="FluentPy native text performance demo")
    parser.add_argument("--dark", action="store_true")
    parser.add_argument("--screenshot", type=Path, metavar="PATH", help="Save a rendered demo image after loading the saved report")
    parser.add_argument("--quit-after-screenshot", action="store_true", help="Render the screenshot in a hidden window and exit")
    args = parser.parse_args()
    if args.quit_after_screenshot and not args.screenshot:
        parser.error("--quit-after-screenshot requires --screenshot PATH")
    app = QtWidgets.QApplication(sys.argv)
    app.setFont(ui_font(14))
    window = TextPerformanceDemo(dark=args.dark)
    if args.quit_after_screenshot:
        window.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    window.show()
    if args.screenshot:
        def save_screenshot() -> None:
            try:
                destination = args.screenshot.expanduser().resolve()
                destination.parent.mkdir(parents=True, exist_ok=True)
                if not window.grab().save(str(destination)):
                    raise OSError(f"Could not save screenshot: {destination}")
                print(f"Screenshot saved: {destination}", flush=True)
            except (OSError, ValueError) as error:
                print(str(error), file=sys.stderr, flush=True)
                if args.quit_after_screenshot:
                    window.close()
                    app.exit(1)
                return
            if args.quit_after_screenshot:
                window.close()
                app.quit()
        QtCore.QTimer.singleShot(250, save_screenshot)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
