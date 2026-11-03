"""Lexical state, UTF-16 ranges, C parity and public editor language changes."""

import os
import random
import sys
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from fluentpy import CodeEdit, SyntaxHighlighter, SyntaxToken
from fluentpy.backends import syntax
from fluentpy.qt import QtCore, QtWidgets

SAMPLES = {
    "python": [
        "@property",
        "class Example:",
        '    def hello(self, value: str = "😀"):',
        '        """first',
        '        second"""',
        "        return True # 中文注释",
    ],
    "java": [
        "public class Example {",
        "/* comment",
        'continued */ String name = "你好";',
        "public int value() { return 42; }",
        "}",
    ],
    "javascript": ["const name = `hello", "${world} 😀`;", "function sum(a, b) { return a + b; }"],
    "typescript": ["interface User { id: number; }", 'const value: string = "你好";'],
    "c": ["#include <stdio.h>", "int main(void) { /* hi */ return 0xFF; }"],
    "cpp": ["template <typename T> class Box {};", "std::vector<int> values = {1, 2};"],
    "csharp": ['public class Example { string Name = "value"; }'],
    "go": ["package main", "func main() { value := `hello", "world`; return }"],
    "rust": ["pub fn main() { let value: u32 = 42; }"],
    "sql": ["SELECT id, name FROM users WHERE active = true;", "-- comment", "/* unfinished"],
    "html": [
        "<!-- comment",
        'continued --> <div class="card">Hello</div>',
        '<img title="first',
        'second" src="x.png">',
    ],
    "xml": ['<?xml version="1.0"?>', '<node key="value">你好</node>'],
    "css": [".card { color: #ffffff; width: 12.5px; }"],
    "yaml": ['name: "FluentPy"', "enabled: true # comment"],
    "shell": ["#!/bin/sh", 'for value in "$HOME"; do echo $value; done'],
}


class SyntaxBackendTests(unittest.TestCase):
    def test_public_language_names_and_aliases(self):
        self.assertIn("python", CodeEdit.supported_languages())
        self.assertIn("java", CodeEdit.supported_languages())
        for alias, expected in (
            (" PY ", "python"),
            ("c++", "cpp"),
            ("C#", "csharp"),
            ("js", "javascript"),
            ("yml", "yaml"),
            ("text", "plain"),
        ):
            self.assertEqual(syntax.normalize_language(alias), expected)
        with self.assertRaises(ValueError):
            syntax.normalize_language("unsupported")

    def test_multiline_comment_and_string_state(self):
        scan = syntax.syntax_spans_python
        self.assertEqual(scan("/* first", "java")[1], 1)
        spans, state = scan("second */ return 1;", "java", 1)
        self.assertEqual(state, 0)
        self.assertEqual(spans[0], (0, 9, SyntaxToken.Comment))
        self.assertEqual(scan('"""first', "python")[1], 3)
        self.assertEqual(scan('second"""', "python", 3)[1], 0)
        self.assertEqual(scan("`first", "javascript")[1], 4)
        self.assertEqual(scan("second`", "javascript", 4)[1], 0)

    def test_comments_inside_strings_and_unicode_offsets_are_not_reinterpreted(self):
        source = '😀 name = "# not a comment" # comment'
        spans, _ = syntax.syntax_spans_python(source, "python")
        strings = [span for span in spans if span[2] == SyntaxToken.String]
        comments = [span for span in spans if span[2] == SyntaxToken.Comment]
        self.assertEqual(len(strings), 1)
        self.assertEqual(len(comments), 1)
        self.assertEqual(strings[0][0], len(source[: source.index('"')].encode("utf-16-le")) // 2)
        self.assertEqual(comments[0][0], len(source[: source.rindex("#")].encode("utf-16-le")) // 2)

    def test_plain_and_legacy_json_have_their_existing_contracts(self):
        from fluentpy.backends.text import json_spans_python

        self.assertEqual(syntax.syntax_spans_python('"hi" 123', "plain"), ([], 0))
        source = '{"title": "😀", "ok": true}'
        self.assertEqual(syntax.syntax_spans_python(source, "json"), (json_spans_python(source), 0))
        for invalid in (True, -1, 9, 1.0):
            with self.assertRaises((TypeError, ValueError)):
                syntax.syntax_spans_python("text", "python", invalid)

    @unittest.skipUnless(syntax.native_available(), "requires the current C scanner")
    def test_c_matches_python_for_real_multiline_samples(self):
        for language, lines in SAMPLES.items():
            state = 0
            for line in lines:
                with self.subTest(language=language, line=line, state=state):
                    reference = syntax.syntax_spans_python(line, language, state)
                    self.assertEqual(syntax.syntax_spans_native(line, language, state), reference)
                    state = reference[1]

    @unittest.skipUnless(syntax.native_available(), "requires the current C scanner")
    def test_c_matches_python_on_incomplete_and_non_bmp_random_input(self):
        randomizer = random.Random(20261031)
        alphabet = "aA_19 中文😀\ud800\udfff \"'`/#*<>!-+=():;{}\\\t\x00"
        for language in SAMPLES:
            for iteration in range(80):
                source = "".join(
                    randomizer.choice(alphabet) for _ in range(randomizer.randrange(90))
                )
                state = randomizer.randrange(9)
                with self.subTest(language=language, iteration=iteration, state=state):
                    self.assertEqual(
                        syntax.syntax_spans_native(source, language, state),
                        syntax.syntax_spans_python(source, language, state),
                    )

    def test_missing_new_native_api_falls_back_independently_of_older_backends(self):
        with (
            patch.object(syntax, "_extension", None),
            patch.dict(os.environ, {"FLUENTPY_BACKEND": "auto"}),
        ):
            self.assertEqual(syntax.backend_name(), "python")
            self.assertTrue(syntax.syntax_spans("return True", "python")[0])
        with (
            patch.object(syntax, "_extension", None),
            patch.dict(os.environ, {"FLUENTPY_BACKEND": "native"}),
        ):
            with self.assertRaises(RuntimeError):
                syntax.syntax_spans("return True", "python")


class SyntaxEditorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])

    def setUp(self):
        self.errors = []
        self.old_hook = sys.excepthook
        sys.excepthook = lambda kind, error, tb: self.errors.append(str(error))
        self.editor = CodeEdit(language="python")
        self.editor.show()

    def tearDown(self):
        self.editor.close()
        self.editor.deleteLater()
        self.app.sendPostedEvents(None, QtCore.QEvent.Type.DeferredDelete)
        self.app.processEvents()
        sys.excepthook = self.old_hook
        self.assertEqual(self.errors, [])

    def test_all_languages_can_be_selected_without_replacing_the_document(self):
        text = 'class Example { return "😀"; }'
        self.editor.set_code(text)
        document = self.editor.text_edit.document()
        for language in CodeEdit.supported_languages():
            self.editor.set_language(language)
            self.assertIs(self.editor.text_edit.document(), document)
            self.assertEqual(self.editor.code(), text)
            self.assertEqual(self.editor.language(), language)
            self.assertFalse(self.editor.syntax_highlighter().last_error())

    def test_provider_errors_are_signaled_without_escaping_a_qt_virtual_callback(self):
        events = []
        self.editor.highlightingError.connect(events.append)
        self.editor.set_code("hello")
        self.editor.set_token_provider(
            lambda text, state: ([(0, len(text), SyntaxToken.Keyword)], 0)
        )
        self.assertEqual(self.editor.acceleration_backend(), "custom")
        self.editor.set_token_provider(lambda text, state: ([(0, 999, 4)], 0))
        self.assertTrue(events)
        self.assertIn("outside", self.editor.syntax_highlighter().last_error())
        self.assertEqual(self.editor.code(), "hello")
        self.editor.set_token_provider(None)
        self.assertIn(self.editor.acceleration_backend(), ("native", "python"))

    def test_standalone_highlighter_attaches_to_an_existing_qt_document(self):
        highlighter = SyntaxHighlighter(self.editor.text_edit.document(), language="java")
        highlighter.set_colors({"keyword": "#123456", "string": "#345678"})
        self.assertIs(highlighter.document(), self.editor.text_edit.document())
        highlighter.setDocument(None)


if __name__ == "__main__":
    unittest.main()
