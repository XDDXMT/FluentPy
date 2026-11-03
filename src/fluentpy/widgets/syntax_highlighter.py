"""Qt syntax formatting with selectable built-in or application token providers."""

from __future__ import annotations

from collections.abc import Callable

from ..backends import syntax
from ..backends import text as text_backend
from ..qt import QtGui, Signal

TOKEN_NAMES = (
    "key",
    "string",
    "number",
    "literal",
    "keyword",
    "comment",
    "operator",
    "function",
    "type",
    "tag",
    "attribute",
    "decorator",
    "variable",
)


class SyntaxHighlighter(QtGui.QSyntaxHighlighter):
    """Color QTextDocument blocks without modifying text or cursor positions.

    A custom provider receives (block_text, previous_state) and returns
    (spans, next_state). Spans contain UTF-16 start, length and SyntaxToken
    values. Providers run on the document's GUI thread and should return fast.
    """

    errorOccurred = Signal(str)

    def __init__(self, document, *, language: str = "json"):
        self.language = syntax.normalize_language(language)
        self.formats = {}
        self._provider = None
        self._last_error = ""
        self._select_backend()
        super().__init__(document)

    def _select_backend(self):
        if self._provider is not None:
            self.backend = "custom"
            self._scan = self._provider
        elif self.language in {"plain", "json"}:
            self.backend = text_backend.backend_name()
            scanner = (
                text_backend.json_spans_native
                if self.backend == "native"
                else text_backend.json_spans_python
            )
            self._scan = lambda text, state: (scanner(text), 0)
        else:
            self.backend = syntax.backend_name()
            scanner = (
                syntax.syntax_spans_native
                if self.backend == "native"
                else syntax.syntax_spans_python
            )
            self._scan = lambda text, state: scanner(text, self.language, state)

    def rehighlight(self):
        self._select_backend()
        self._last_error = ""
        super().rehighlight()

    def set_language(self, language: str) -> None:
        language = syntax.normalize_language(language)
        # Resolve errors before a virtual Qt callback can observe new state.
        if language not in {"plain", "json"}:
            syntax.backend_name()
        else:
            text_backend.backend_name()
        self.language = language
        self.rehighlight()

    def set_token_provider(self, provider: Callable | None) -> None:
        """Use an application lexer; None resumes the selected built-in language."""
        if provider is not None and not callable(provider):
            raise TypeError("provider must be callable or None")
        self._provider = provider
        self.rehighlight()

    def set_colors(self, colors: dict[str, str]) -> None:
        formats = {}
        for name, color in colors.items():
            if name not in TOKEN_NAMES:
                raise ValueError(f"unknown token color: {name}")
            foreground = QtGui.QColor(color)
            if not foreground.isValid():
                raise ValueError(f"invalid token color: {color}")
            fmt = QtGui.QTextCharFormat()
            fmt.setForeground(foreground)
            formats[name] = fmt
        self.formats = formats
        self.rehighlight()

    def highlightBlock(self, text):
        if self.language == "plain" and self._provider is None or not self.formats:
            self.setCurrentBlockState(0)
            return
        try:
            state = max(0, self.previousBlockState())
            spans, state = self._scan(text, state)
            if not isinstance(state, int) or isinstance(state, bool) or not 0 <= state < 2**31:
                raise ValueError("provider state must be a non-negative 32-bit integer")
            self.setCurrentBlockState(state)
            bound = sum(2 if ord(char) > 0xFFFF else 1 for char in text) if self._provider else 0
            for start, length, kind in spans:
                if self._provider and (
                    not isinstance(start, int)
                    or not isinstance(length, int)
                    or start < 0
                    or length < 0
                    or start + length > bound
                ):
                    raise ValueError("provider span is outside the current UTF-16 block")
                if not isinstance(kind, int) or not 0 <= kind < len(TOKEN_NAMES):
                    raise ValueError("invalid syntax token kind")
                name = TOKEN_NAMES[kind]
                if name in self.formats:
                    self.setFormat(start, length, self.formats[name])
        except Exception as error:
            self.setCurrentBlockState(0)
            self._last_error = str(error)
            self.errorOccurred.emit(self._last_error)

    def last_error(self) -> str:
        return self._last_error
