"""Compare the frozen editor, Python backend and C backend on identical JSON.

Each sample runs in its own process. GUI timings include full-document syntax
highlighting, deferred events and the first rendered frame; validation is outside
the timed region. Run with --json for newline-delimited progress events.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time
import types

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from benchmark_baseline import dataset_metadata, generate_json


def load_legacy():
    source = json.loads((ROOT / "benchmarks" / "baseline-original-source.json").read_text(encoding="utf-8-sig"))["code_edit"]
    name = "fluentpy.widgets._performance_legacy_code_edit"
    module = types.ModuleType(name)
    module.__package__ = "fluentpy.widgets"
    sys.modules[name] = module
    exec(compile(source, "frozen-original-code-edit.py", "exec"), module.__dict__)
    return module


def legacy_line_spans(text, pattern):
    offsets = [0]
    for character in text:
        offsets.append(offsets[-1] + (2 if ord(character) > 0xFFFF else 1))
    result = []
    for match in pattern.finditer(text):
        token = match.group()
        if token.startswith('"'):
            kind = 0 if text[match.end():].lstrip().startswith(":") else 1
        elif token in ("true", "false", "null"):
            kind = 3
        else:
            kind = 2
        start, end = match.span()
        result.append((offsets[start], offsets[end] - offsets[start], kind))
    return result


def worker(backend, lines):
    os.environ["FLUENTPY_BACKEND"] = "python" if backend == "legacy" else backend
    from fluentpy import CodeEdit, LineEdit, theme
    from fluentpy.backends.text import json_spans_native, json_spans_python, native_available
    from fluentpy.qt import QT_API, QtCore, QtGui, QtWidgets
    from fluentpy.theme.fonts import ui_font

    source = generate_json(lines)
    blocks = source.split("\n")
    app = QtWidgets.QApplication([])
    app.setFont(ui_font(14))
    app.setQuitOnLastWindowClosed(False)
    theme.set_mode("light")
    errors = []
    sys.excepthook = lambda kind, error, traceback: errors.append(str(error))
    legacy = load_legacy() if backend == "legacy" else None
    editor_class = legacy.CodeEdit if legacy else CodeEdit
    if backend == "legacy":
        scan = lambda line: legacy_line_spans(line, legacy._JsonHighlighter._tokens)
    else:
        scan = json_spans_native if backend == "native" else json_spans_python
    if backend == "native" and not native_available():
        raise RuntimeError("C extension is unavailable for this interpreter; build it first.")

    lexer_samples = []
    for _ in range(3):
        start = time.perf_counter()
        tokens = [scan(line) for line in blocks]
        lexer_samples.append((time.perf_counter() - start) * 1000)
    expected_tokens = sum(map(len, tokens))
    view = editor_class()
    actual_backend = "legacy" if legacy else view.acceleration_backend()
    if actual_backend != backend:
        raise AssertionError(f"Requested {backend}, editor actually selected {actual_backend}")
    view.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    view.resize(820, 520)
    view.show()
    view.clearFocus()
    app.processEvents()
    load_start = time.perf_counter()
    view.set_code(source)
    set_done = time.perf_counter()
    for _ in range(3):
        app.processEvents()
    events_done = time.perf_counter()
    frame = view.grab()
    ready = time.perf_counter()
    load_clocks = {
        "set_text_ms": (set_done - load_start) * 1000,
        "events_ms": (events_done - set_done) * 1000,
        "first_frame_ms": (ready - events_done) * 1000,
        "load_ready_ms": (ready - load_start) * 1000,
    }
    if frame.isNull() or view.code() != source:
        raise AssertionError("Editor did not render or preserve the complete JSON.")
    area = view.text_edit
    formatted = 0
    block = area.document().firstBlock()
    while block.isValid():
        formatted += len(block.layout().formats())
        block = block.next()
    if area.blockCount() != lines or formatted != expected_tokens:
        raise AssertionError(f"Incomplete highlighting: {area.blockCount()} blocks, {formatted}/{expected_tokens} tokens")

    start = time.perf_counter()
    view._highlighter.rehighlight()
    app.processEvents()
    view.grab()
    rehighlight_ms = (time.perf_counter() - start) * 1000
    edit_samples = []
    for _ in range(3):
        block = area.document().findBlockByNumber(lines // 2)
        cursor = QtGui.QTextCursor(block)
        cursor.movePosition(QtGui.QTextCursor.MoveOperation.EndOfBlock)
        area.setTextCursor(cursor)
        area.centerCursor()
        app.processEvents()
        view.grab()
        start = time.perf_counter()
        area.insertPlainText(" ")
        app.processEvents()
        view.grab()
        edit_samples.append((time.perf_counter() - start) * 1000)
        area.undo()
        app.processEvents()
    if view.code() != source:
        raise AssertionError("Undo did not preserve the source.")
    bar = area.verticalScrollBar()
    start = time.perf_counter()
    for index in range(30):
        bar.setValue(round(bar.maximum() * index / 29))
        app.processEvents()
        area.viewport().grab()
    scroll_ms = (time.perf_counter() - start) * 1000
    result = {
        "backend": backend,
        "actual_backend": actual_backend,
        "dataset": dataset_metadata(source),
        "lexer_ms": statistics.median(lexer_samples),
        **load_clocks,
        "rehighlight_ms": rehighlight_ms,
        "edit_ms": statistics.median(edit_samples),
        "scroll_ms": scroll_ms,
        "preserved_exact_text": True,
        "complete_highlighting": True,
        "formatted_tokens": formatted,
        "block_count": area.blockCount(),
        "environment": {"python": platform.python_version(), "qt": QtCore.qVersion(), "qt_api": QT_API, "platform_plugin": app.platformName(), "os": platform.platform(), "processor": platform.processor()},
    }
    if backend == "legacy":
        line = LineEdit()
        line.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        line.resize(820, 36)
        line.show()
        app.processEvents()
        default_max = line.maxLength()
        line.setText(source)
        default_preserved = line.text() == source
        default_units = len(line.text().encode("utf-16-le")) // 2
        line.setMaxLength(dataset_metadata(source)["utf16_units"] + 1)
        start = time.perf_counter()
        line.setText(source)
        app.processEvents()
        line.grab()
        full_ms = (time.perf_counter() - start) * 1000
        result["line_edit"] = {"default_max_length": default_max, "default_preserved_exact_text": default_preserved, "default_utf16_units": default_units, "preserved_exact_text": line.text() == source, "full_load_ready_ms": full_ms, "engine": "Qt QLineEdit; no JSON lexer"}
        line.hide()
    view.hide()
    if errors:
        raise AssertionError(errors)
    return result


def emit(event, structured):
    if structured:
        print(json.dumps(event, ensure_ascii=False), flush=True)
    elif event["event"] == "progress":
        print(event["message"], flush=True)


def source_fingerprints():
    files = ("scripts/benchmark_text.py", "src/fluentpy/widgets/code_edit.py", "src/fluentpy/backends/text.py", "native/text_accel.c")
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in files}


def run(args):
    from fluentpy.backends.text import native_available
    fingerprints = source_fingerprints()
    backends = ["legacy", "python"] + (["native"] if native_available() else [])
    samples = {backend: [] for backend in backends}
    for repetition in range(args.repeat):
        # Rotate execution order so warm machine state is shared across modes.
        order = backends[repetition % len(backends):] + backends[:repetition % len(backends)]
        for backend in order:
            emit({"event": "progress", "message": f"{args.lines:,} 行 · {backend} · 第 {repetition + 1}/{args.repeat} 轮"}, args.json)
            environment = dict(os.environ)
            environment["FLUENTPY_BACKEND"] = "python" if backend == "legacy" else backend
            environment["PYTHONIOENCODING"] = "utf-8"
            completed = subprocess.run([sys.executable, "-B", str(Path(__file__).resolve()), "--worker", backend, "--lines", str(args.lines)], cwd=ROOT, env=environment, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=args.timeout)
            if completed.returncode:
                raise RuntimeError(f"{backend} failed: {completed.stderr[-4000:]}")
            sample = json.loads(completed.stdout.strip().splitlines()[-1])
            samples[backend].append(sample)
    metrics = ("lexer_ms", "load_ready_ms", "set_text_ms", "events_ms", "first_frame_ms", "rehighlight_ms", "edit_ms", "scroll_ms")
    summary = {backend: {name: statistics.median(sample[name] for sample in rows) for name in metrics} for backend, rows in samples.items()}
    first = samples["legacy"][0]
    if fingerprints != source_fingerprints():
        raise RuntimeError("Benchmark or implementation changed during measurement; rerun for a consistent report.")
    report = {
        "schema": 1,
        "dataset": first["dataset"],
        "environment": first["environment"],
        "backend_available": "native" in samples,
        "repeat": args.repeat,
        "summary": summary,
        "samples": samples,
        "source_sha256": fingerprints,
        "line_edit": {**first["line_edit"], "full_load_ready_ms": statistics.median(row["line_edit"]["full_load_ready_ms"] for row in samples["legacy"])},
        "method": "Fresh process per sample; rotated mode order; full JSON preserved; all blocks/tokens checked outside timing; lexer uses the same per-line input as Qt; full highlighting and first frame included, not just setPlainText return; edited middle line is scrolled into view before edit timing; scroll_ms is 30 rendered steps.",
    }
    report["speedups"] = {name: summary["python"][name] / summary["native"][name] for name in metrics} if "native" in summary else {}
    destination = Path(args.output).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    emit({"event": "result", "report": report, "path": str(destination)}, args.json)
    if not args.json:
        print(json.dumps({"dataset": report["dataset"], "summary": summary, "speedups_python_to_native": report["speedups"], "line_edit": report["line_edit"], "output": str(destination)}, ensure_ascii=False, indent=2))
    return report


def main():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", choices=("legacy", "python", "native"))
    parser.add_argument("--lines", type=int, default=10000)
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=45)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--output", default=str(ROOT / "benchmarks" / "text-performance.json"))
    args = parser.parse_args()
    if not 8 <= args.lines <= 1000000 or not 1 <= args.repeat <= 20 or args.timeout <= 0:
        parser.error("lines must be 8..1000000; repeat 1..20; timeout must be positive")
    try:
        if args.worker:
            print(json.dumps(worker(args.worker, args.lines), ensure_ascii=False))
        else:
            run(args)
    except Exception as error:
        if args.json:
            emit({"event": "error", "message": str(error)}, True)
        else:
            print(f"Benchmark failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
