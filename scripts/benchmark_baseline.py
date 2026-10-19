"""Reproducible pre-acceleration snapshot benchmark (Windows Qt, hidden window).

The source archive beside the result freezes CodeEdit and LineEdit as they were
before native backend work. Each sample runs in a child process with a 5-second
budget so unusually long single-line shaping cannot hang the parent benchmark.
"""

from __future__ import annotations

import argparse
import cProfile
import hashlib
import io
import json
import os
import platform
import pstats
import statistics
import subprocess
import sys
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "benchmarks" / "baseline-original-source.json"


def generate_json(lines: int = 10000) -> str:
    """Valid deterministic JSON, exactly `lines` logical lines, UTF-8 and emoji.

    The 10k fixture contains 1,249 six-field records, four root metadata fields,
    and JSON brackets. Smaller arbitrary line counts use valid trailing root
    string fields to consume any remainder rather than changing the records.
    """
    if lines < 8:
        raise ValueError("lines must be at least 8")
    count, extra = divmod(lines - 8, 8)
    records = [
        {
            "id": index,
            "RecordName": f"node-{index:05d}.example.org",
            "enabled": index % 3 != 0,
            "ratio": round(index / 19, 4),
            "comment": "中文 😀 café" if index % 5 == 0 else "ASCII text",
            "value": f"https://example.org/items/{index}?active=true",
        }
        for index in range(count)
    ]
    root = {
        "TotalCount": count,
        "RequestId": "27A90792-2B98-5435-8589-A2AF90E6C374",
        "PageSize": count,
        "PageNumber": 1,
        "Records": records,
    }
    for index in range(extra):
        root[f"padding_{index}"] = "deterministic fixture"
    text = json.dumps(root, ensure_ascii=False, indent=2)
    assert len(text.splitlines()) == lines
    return text


def dataset_metadata(text: str) -> dict:
    return {
        "lines": len(text.splitlines()),
        "unicode_scalars": len(text),
        "utf8_bytes": len(text.encode("utf-8")),
        "utf16_units": len(text.encode("utf-16-le")) // 2,
        "sha256_utf8": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "records": len(json.loads(text)["Records"]),
    }


def original_modules():
    """Load frozen module code with the real FluentPy relative imports."""
    sys.path.insert(0, str(ROOT / "src"))
    # Bypass the evolving top-level exports; only frozen widget sources and
    # their unchanged Qt/theme/scrollbar dependencies participate in baseline.
    for name, path in (
        ("fluentpy", ROOT / "src" / "fluentpy"),
        ("fluentpy.widgets", ROOT / "src" / "fluentpy" / "widgets"),
    ):
        if name not in sys.modules:
            package = types.ModuleType(name)
            package.__path__ = [str(path)]
            package.__package__ = name
            sys.modules[name] = package
    snapshot = json.loads(ARCHIVE.read_text(encoding="utf-8-sig"))
    modules = {}
    for key in ("code_edit", "line_edit"):
        name = f"fluentpy.widgets._benchmark_original_{key}"
        module = types.ModuleType(name)
        module.__package__ = "fluentpy.widgets"
        module.__file__ = str(ARCHIVE) + "::" + key
        sys.modules[name] = module
        exec(compile(snapshot[key], module.__file__, "exec"), module.__dict__)
        modules[key] = module
    return modules


def original_spans(text: str, pattern):
    """Exact original per-block lexer without Qt setFormat crossing overhead."""
    result = []
    for line in text.split("\n"):
        offsets = [0]
        for character in line:
            offsets.append(offsets[-1] + (2 if ord(character) > 0xFFFF else 1))
        spans = []
        for match in pattern.finditer(line):
            token = match.group()
            if token.startswith('"'):
                kind = "key" if line[match.end() :].lstrip().startswith(":") else "string"
            elif token in ("true", "false", "null"):
                kind = "literal"
            else:
                kind = "number"
            spans.append(
                (offsets[match.start()], offsets[match.end()] - offsets[match.start()], kind)
            )
        result.append(spans)
    return result


def profile_summary(profile, limit=18):
    output = io.StringIO()
    pstats.Stats(profile, stream=output).strip_dirs().sort_stats("cumulative").print_stats(limit)
    return output.getvalue()


def worker(case: str, lines: int, do_profile: bool) -> dict:
    os.environ["FLUENTPY_BACKEND"] = "python"
    modules = original_modules()
    from fluentpy.qt import QT_API, QtCore, QtGui, QtWidgets
    from fluentpy.theme import ThemeMode, theme

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    theme.set_mode(ThemeMode.LIGHT)
    text = generate_json(lines)
    profile = cProfile.Profile() if do_profile else None
    result = {
        "case": case,
        "dataset": dataset_metadata(text),
        "platform_plugin": app.platformName(),
        "qt_api": QT_API,
        "qt_version": QtCore.qVersion(),
        "python": sys.version,
    }
    if case == "tokenizer":
        if profile:
            profile.enable()
        start = time.perf_counter()
        spans = original_spans(text, modules["code_edit"]._JsonHighlighter._tokens)
        result["tokenizer_ms"] = (time.perf_counter() - start) * 1000
        if profile:
            profile.disable()
            result["profile"] = profile_summary(profile)
        result["span_count"] = sum(map(len, spans))
        return result

    if case in ("code-json", "code-plain"):
        widget = modules["code_edit"].CodeEdit(language="json" if case == "code-json" else "plain")
        area = widget.text_edit
    elif case in ("line-default", "line-full"):
        widget = modules["line_edit"].LineEdit()
        area = widget
        result["default_max_length"] = widget.maxLength()
        if case == "line-full":
            widget.setMaxLength(2147483647)
    elif case == "text-edit":
        widget = modules["line_edit"].TextEdit()
        area = widget
    elif case == "plain-qt":
        widget = QtWidgets.QPlainTextEdit()
        widget.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        area = widget
    else:
        raise ValueError(case)
    widget.resize(960, 640)
    widget.setAttribute(QtCore.Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    widget.show()
    for _ in range(3):
        app.processEvents()
    setter = widget.setText if case.startswith("line-") else area.setPlainText
    if profile:
        profile.enable()
    start = time.perf_counter()
    setter(text)
    after_set = time.perf_counter()
    for _ in range(3):
        app.processEvents()
    after_events = time.perf_counter()
    pixmap = QtGui.QPixmap(widget.size())
    widget.render(pixmap)
    after_render = time.perf_counter()
    if profile:
        profile.disable()
        result["profile"] = profile_summary(profile)
    result.update(
        {
            "set_text_ms": (after_set - start) * 1000,
            "deferred_events_ms": (after_events - after_set) * 1000,
            "first_render_ms": (after_render - after_events) * 1000,
            "load_events_render_ms": (after_render - start) * 1000,
            "window": "960x640; WA_DontShowOnScreen; native Qt platform",
        }
    )
    actual = widget.text() if case.startswith("line-") else area.toPlainText()
    result["preserved_exact_text"] = actual == text
    result["actual_utf16_units"] = len(actual.encode("utf-16-le")) // 2
    result["actual_logical_lines"] = len(actual.splitlines())
    if hasattr(area, "document"):
        result["block_count"] = area.document().blockCount()
    if case == "code-json":
        blocks = formatted = 0
        block = area.document().firstBlock()
        while block.isValid():
            blocks += 1
            formatted += len(block.layout().formats())
            block = block.next()
        result["format_ranges"] = formatted
        result["formatted_blocks_checked"] = blocks
        result["complete_highlighting"] = formatted == sum(
            map(len, original_spans(text, modules["code_edit"]._JsonHighlighter._tokens))
        )
    if not case.startswith("line-"):
        scroll = area.verticalScrollBar()
        maximum = scroll.maximum()
        scroll_start = time.perf_counter()
        for step in range(1, 31):
            scroll.setValue(maximum * step // 30)
            app.processEvents()
            widget.render(pixmap)
        result["scroll_30_steps_ms"] = (time.perf_counter() - scroll_start) * 1000
        result["scroll_30_step_mean_ms"] = result["scroll_30_steps_ms"] / 30
    widget.close()
    return result


def run(args):
    results = []
    cases = args.cases.split(",")
    for lines in args.lines:
        for case in cases:
            for repetition in range(args.repeat):
                command = [
                    sys.executable,
                    "-B",
                    __file__,
                    "--worker",
                    case,
                    "--worker-lines",
                    str(lines),
                ]
                env = dict(os.environ, FLUENTPY_BACKEND="python")
                env.pop("QT_QPA_PLATFORM", None)
                try:
                    proc = subprocess.run(
                        command,
                        capture_output=True,
                        text=True,
                        encoding="utf-8",
                        env=env,
                        timeout=args.timeout,
                    )
                    if proc.returncode:
                        result = {
                            "case": case,
                            "lines": lines,
                            "error": proc.stderr,
                            "returncode": proc.returncode,
                        }
                    else:
                        result = json.loads(proc.stdout)
                        result["repetition"] = repetition
                    if proc.stderr:
                        result["stderr"] = proc.stderr
                except subprocess.TimeoutExpired:
                    result = {"case": case, "lines": lines, "timeout_seconds": args.timeout}
                results.append(result)
                print(
                    f"{lines} {case} {repetition + 1}/{args.repeat}: "
                    + (
                        f"{result.get('load_events_render_ms', result.get('tokenizer_ms', 0)):.2f} ms"
                        if "dataset" in result
                        else "FAILED/TIMEOUT"
                    ),
                    flush=True,
                )
    summaries = []
    for lines in args.lines:
        for case in cases:
            group = [
                r
                for r in results
                if r.get("case") == case and r.get("dataset", {}).get("lines") == lines
            ]
            summary = {"lines": lines, "case": case, "successful_samples": len(group)}
            for key in (
                "tokenizer_ms",
                "set_text_ms",
                "deferred_events_ms",
                "first_render_ms",
                "load_events_render_ms",
                "scroll_30_steps_ms",
                "scroll_30_step_mean_ms",
            ):
                values = [r[key] for r in group if key in r]
                if values:
                    summary[key] = statistics.median(values)
            summaries.append(summary)
    profiles = []
    for case in ("tokenizer", "code-json"):
        command = [
            sys.executable,
            "-B",
            __file__,
            "--worker",
            case,
            "--worker-lines",
            "10000",
            "--profile",
        ]
        env = dict(os.environ, FLUENTPY_BACKEND="python")
        env.pop("QT_QPA_PLATFORM", None)
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env,
                timeout=args.timeout,
            )
            profiles.append(
                json.loads(proc.stdout)
                if proc.returncode == 0
                else {"case": case, "error": proc.stderr}
            )
        except subprocess.TimeoutExpired:
            profiles.append({"case": case, "timeout_seconds": args.timeout})
    report = {
        "methodology": {
            "captured_source": str(ARCHIVE.relative_to(ROOT)),
            "backend": "Original source frozen before native-backend integration; FLUENTPY_BACKEND=python",
            "platform": platform.platform(),
            "processor": platform.processor(),
            "python_executable": sys.executable,
            "sample_process": "Fresh Python process per sample; Qt QApplication on native Windows QPA; hidden 960x640 window",
            "timing": "time.perf_counter; no instrumentation in timing samples; cProfile only separate final samples",
            "render": "setPlainText/setText + processEvents 3 times + QWidget.render; does not include process/import/widget startup",
            "safety": f"Each child has {args.timeout} second hard timeout, including startup",
            "iterations": args.repeat,
            "dataset_recipe": "scripts.benchmark_baseline.generate_json(lines), json.dumps ensure_ascii=False indent=2, exactly requested logical lines",
            "line_edit_warning": "QLineEdit is single-line, default maxLength=32767 UTF-16 units. line-full overrides maxLength; not a multiline JSON editor.",
        },
        "datasets": [dataset_metadata(generate_json(lines)) for lines in args.lines],
        "medians": summaries,
        "samples": results,
        "profiles": profiles,
    }
    target = ROOT / "benchmarks" / "baseline-original.json"
    target.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {target}")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker")
    parser.add_argument("--worker-lines", type=int, default=10000)
    parser.add_argument("--profile", action="store_true")
    parser.add_argument("--lines", type=int, nargs="+", default=[1000, 10000])
    parser.add_argument("--repeat", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=5)
    parser.add_argument(
        "--cases",
        default="tokenizer,plain-qt,text-edit,code-plain,code-json,line-default,line-full",
    )
    options = parser.parse_args()
    if options.worker:
        print(
            json.dumps(
                worker(options.worker, options.worker_lines, options.profile), ensure_ascii=False
            )
        )
    else:
        run(options)
