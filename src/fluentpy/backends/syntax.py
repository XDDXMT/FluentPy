"""Stateful UTF-16 token spans for common programming languages.

Built-in languages share a tolerant lexical scanner implemented in C, with a
behavior-compatible Python reference. Spans describe colors, not diagnostics.
"""

from __future__ import annotations

from enum import IntEnum
from importlib import import_module

from ._compat import select_backend, strict_int


class SyntaxToken(IntEnum):
    Key = 0
    String = 1
    Number = 2
    Literal = 3
    Keyword = 4
    Comment = 5
    Operator = 6
    Function = 7
    Type = 8
    Tag = 9
    Attribute = 10
    Decorator = 11
    Variable = 12


(
    HASH,
    SLASH,
    BLOCK,
    SQL,
    BACKTICK,
    TRIPLE,
    MARKUP,
    CSS,
    YAML,
    CASELESS,
    PYTHON,
    SHELL,
    PREPROCESSOR,
) = (1 << bit for bit in range(13))


def _words(keywords="", types="", literals=""):
    result = {word: int(SyntaxToken.Keyword) for word in keywords.split()}
    result.update((word, int(SyntaxToken.Type)) for word in types.split())
    result.update((word, int(SyntaxToken.Literal)) for word in literals.split())
    return result


_C_WORDS = "auto break case const continue default do else enum extern for goto if inline register restrict return sizeof static struct switch typedef union unsigned volatile while"
_C_TYPES = "bool char double float int long short signed size_t void wchar_t"
_LANGUAGES = {
    "python": (
        HASH | TRIPLE | PYTHON,
        _words(
            "and as assert async await break case class continue def del elif else except finally for from global if import in is lambda match nonlocal not or pass raise return try while with yield",
            "bool bytes bytearray classmethod complex dict enumerate float frozenset int isinstance len list object print property range set slice staticmethod str super tuple type zip",
            "False None True",
        ),
    ),
    "java": (
        SLASH | BLOCK | TRIPLE,
        _words(
            "abstract assert break case catch class const continue default do else enum extends final finally for if implements import instanceof interface native new package private protected public record return sealed static strictfp super switch synchronized this throw throws transient try var volatile while yield",
            "boolean byte char double float int long short void String Object Integer Boolean List Map Set",
            "false null true",
        ),
    ),
    "javascript": (
        SLASH | BLOCK | BACKTICK,
        _words(
            "async await break case catch class const continue debugger default delete do else export extends finally for from function get if import in instanceof let new of return set static super switch this throw try typeof var void while with yield",
            "Array BigInt Boolean Date Error JSON Map Math Number Object Promise RegExp Set String Symbol console",
            "false null true undefined NaN Infinity",
        ),
    ),
    "typescript": (
        SLASH | BLOCK | BACKTICK,
        _words(
            "abstract as assert async await break case catch class const constructor continue declare default delete do else enum export extends finally for from function get if implements import in infer instanceof interface is keyof let module namespace new of private protected public readonly require return satisfies set static super switch this throw try type typeof var void while with yield",
            "any bigint boolean never number object string symbol unknown Array Date Error Map Promise Set String",
            "false null true undefined",
        ),
    ),
    "c": (SLASH | BLOCK | PREPROCESSOR, _words(_C_WORDS, _C_TYPES, "NULL false true")),
    "cpp": (
        SLASH | BLOCK | PREPROCESSOR,
        _words(
            _C_WORDS
            + " alignas alignof asm catch class concept constexpr consteval constinit co_await co_return co_yield decltype delete explicit export friend mutable namespace new noexcept nullptr operator private protected public requires template this thread_local throw try typename using virtual",
            _C_TYPES + " string vector array map set unique_ptr shared_ptr",
            "NULL false true nullptr",
        ),
    ),
    "csharp": (
        SLASH | BLOCK | PREPROCESSOR,
        _words(
            "abstract as async await base break case catch checked class const continue default delegate do else enum event explicit extern finally fixed for foreach goto if implicit in interface internal is lock namespace new operator out override params partial private protected public readonly record ref return sealed sizeof stackalloc static struct switch this throw try typeof unchecked unsafe using virtual volatile when where while yield",
            "bool byte char decimal double dynamic float int long object sbyte short string uint ulong ushort var void",
            "false null true",
        ),
    ),
    "go": (
        SLASH | BLOCK | BACKTICK,
        _words(
            "break case chan const continue default defer else fallthrough for func go goto if import interface map package range return select struct switch type var",
            "any bool byte complex64 complex128 error float32 float64 int int8 int16 int32 int64 rune string uint uint8 uint16 uint32 uint64 uintptr",
            "false nil true iota",
        ),
    ),
    "rust": (
        SLASH | BLOCK,
        _words(
            "as async await break const continue crate dyn else enum extern fn for if impl in let loop match mod move mut pub ref return self Self static struct super trait type unsafe use where while",
            "bool char f32 f64 i8 i16 i32 i64 i128 isize str String u8 u16 u32 u64 u128 usize Vec Option Result",
            "false true None Some Ok Err",
        ),
    ),
    "sql": (
        SQL | BLOCK | CASELESS,
        _words(
            "add all alter and as asc begin between by case check column commit constraint create database default delete desc distinct drop else end exists foreign from full group having in index inner insert into is join key left like limit not null offset on or order outer primary references right rollback select set table then transaction union unique update values view when where with",
            "bigint boolean char date decimal double float int integer numeric real smallint text timestamp varchar",
            "false null true",
        ),
    ),
    "html": (MARKUP, {}),
    "xml": (MARKUP, {}),
    "css": (
        BLOCK | CSS,
        _words(
            "important media supports import keyframes from to",
            "",
            "inherit initial none transparent unset",
        ),
    ),
    "yaml": (HASH | YAML, _words("", "", "false true null yes no on off")),
    "shell": (
        HASH | BACKTICK | SHELL,
        _words(
            "case do done elif else esac export fi for function if in local readonly return select then time trap until while",
            "alias cd echo exec exit printf pwd read set shift source test unset",
            "false true",
        ),
    ),
}
_ALIASES = {
    "py": "python",
    "js": "javascript",
    "ts": "typescript",
    "c++": "cpp",
    "cc": "cpp",
    "c#": "csharp",
    "cs": "csharp",
    "golang": "go",
    "rs": "rust",
    "htm": "html",
    "yml": "yaml",
    "sh": "shell",
    "bash": "shell",
    "text": "plain",
    "plaintext": "plain",
    "txt": "plain",
}
_ASCII_LOWER = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def supported_languages() -> tuple[str, ...]:
    return ("plain", "json", *_LANGUAGES)


def normalize_language(language: str) -> str:
    if not isinstance(language, str):
        raise TypeError("language must be str")
    language = _ALIASES.get(language.strip().lower(), language.strip().lower())
    if language not in supported_languages():
        raise ValueError(f"unsupported language: {language!r}")
    return language


try:
    _extension = import_module(f"{__package__.rpartition('.')[0]}._native")
    if not callable(getattr(_extension, "syntax_spans", None)):
        raise ImportError("The installed extension does not provide syntax_spans")
except (ImportError, OSError) as error:
    _extension, _native_error = None, str(error)
else:
    _native_error = None


def backend_name() -> str:
    return select_backend(_extension, _native_error, "syntax")


def native_available() -> bool:
    return _extension is not None


def _arguments(text, language, state):
    if not isinstance(text, str):
        raise TypeError("text must be str")
    language = normalize_language(language)
    state = strict_int(state, "previous_state")
    if not 0 <= state <= 8:
        raise ValueError("previous_state must be between 0 and 8")
    return language, state


def syntax_spans(text: str, language: str, previous_state: int = 0):
    """Return (UTF-16 spans, next state), preserving multiline comment/string state."""
    language, state = _arguments(text, language, previous_state)
    if language == "plain":
        return [], 0
    if language == "json":
        from .text import json_spans

        return json_spans(text), 0
    if backend_name() == "native":
        flags, words = _LANGUAGES[language]
        return _extension.syntax_spans(text, flags, words, state)
    return syntax_spans_python(text, language, state)


def syntax_spans_native(text: str, language: str, previous_state: int = 0):
    """Select the C scanner explicitly for differential checks and integrations."""
    language, state = _arguments(text, language, previous_state)
    if language == "plain":
        return [], 0
    if language == "json":
        from .text import json_spans_native

        return json_spans_native(text), 0
    if _extension is None:
        raise RuntimeError(
            f"Rebuild the native syntax scanner or use the Python fallback: {_native_error}"
        )
    flags, words = _LANGUAGES[language]
    return _extension.syntax_spans(text, flags, words, state)


def syntax_spans_python(text: str, language: str, previous_state: int = 0):
    """Reference for the C scanner. Incomplete text is retained and colored tolerantly."""
    language, state = _arguments(text, language, previous_state)
    if language == "plain":
        return [], 0
    if language == "json":
        from .text import json_spans_python

        return json_spans_python(text), 0
    flags, words = _LANGUAGES[language]
    offsets, spans = [0], []
    for char in text:
        offsets.append(offsets[-1] + (2 if ord(char) > 0xFFFF else 1))
    length, index, expected = len(text), 0, 0

    def add(start, end, kind):
        if end > start:
            spans.append((offsets[start], offsets[end] - offsets[start], int(kind)))

    def quoted(start, delimiter, skip=0):
        cursor = start + skip
        while cursor < length:
            if text.startswith(delimiter, cursor):
                return cursor + len(delimiter), True
            cursor += 2 if text[cursor] == "\\" else 1
        return length, False

    while index < length:
        start, char = index, text[index]
        if state in (1, 5):
            delimiter = "*/" if state == 1 else "-->"
            end = text.find(delimiter, index)
            index = length if end < 0 else end + len(delimiter)
            add(start, index, SyntaxToken.Comment)
            if end >= 0:
                state = 0
            continue
        if state in (2, 3, 4, 7, 8):
            delimiter = {2: "'''", 3: '"""', 4: "`", 7: "'", 8: '"'}[state]
            index, closed = quoted(index, delimiter)
            add(start, index, SyntaxToken.String)
            if closed:
                state = 6 if state in (7, 8) else 0
            continue
        if char.isspace():
            index += 1
            continue
        if flags & MARKUP and text.startswith("<!--", index):
            end = text.find("-->", index + 4)
            index = length if end < 0 else end + 3
            add(start, index, SyntaxToken.Comment)
            state = 5 if end < 0 else 0
            continue
        if flags & MARKUP and char == "<":
            index += 1
            if index < length and text[index] in "/!?":
                index += 1
            while index < length and (text[index].isalnum() or text[index] in "_-:"):
                index += 1
            add(start, index, SyntaxToken.Tag)
            state = 6
            continue
        if state == 6 and char == ">":
            add(index, index + 1, SyntaxToken.Tag)
            index += 1
            state = 0
            continue
        if (
            flags & HASH
            and char == "#"
            or flags & SLASH
            and text.startswith("//", index)
            or flags & SQL
            and text.startswith("--", index)
        ):
            add(index, length, SyntaxToken.Comment)
            index = length
            continue
        if flags & PREPROCESSOR and char == "#":
            add(index, length, SyntaxToken.Decorator)
            index = length
            continue
        if flags & BLOCK and text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = length if end < 0 else end + 2
            add(start, index, SyntaxToken.Comment)
            if end < 0:
                state = 1
            continue
        if char in "\"'" or char == "`" and flags & BACKTICK:
            triple = bool(flags & TRIPLE and text.startswith(char * 3, index))
            delimiter = char * (3 if triple else 1)
            index, closed = quoted(index, delimiter, len(delimiter))
            add(start, index, SyntaxToken.String)
            if not closed:
                state = (
                    (2 if char == "'" else 3)
                    if triple
                    else 4
                    if char == "`"
                    else (7 if char == "'" else 8)
                    if state == 6
                    else 0
                )
            continue
        if flags & PYTHON and char == "@":
            index += 1
            while index < length and (text[index].isalnum() or text[index] in "_."):
                index += 1
            add(start, index, SyntaxToken.Decorator)
            continue
        if flags & SHELL and char == "$":
            index += 1
            while index < length and (text[index].isalnum() or text[index] in "_{}?"):
                index += 1
            add(start, index, SyntaxToken.Variable)
            continue
        if (
            char.isdecimal()
            or char == "."
            and index + 1 < length
            and text[index + 1].isdecimal()
            or flags & CSS
            and char == "#"
        ):
            index += 1
            while index < length:
                current = text[index]
                if (
                    current.isalnum()
                    or current in "_."
                    or current in "+-"
                    and text[index - 1] in "eE"
                ):
                    index += 1
                else:
                    break
            add(start, index, SyntaxToken.Number)
            continue
        if char.isalpha() or char in "_$":
            index += 1
            while index < length and (
                text[index].isalnum() or text[index] in "_$" or state == 6 and text[index] in "-:"
            ):
                index += 1
            word = text[start:index]
            lookup = word.translate(_ASCII_LOWER) if flags & CASELESS else word
            following = index
            while following < length and text[following].isspace():
                following += 1
            kind = SyntaxToken.Attribute if state == 6 else words.get(lookup, expected)
            if not kind and following < length:
                if text[following] == "(":
                    kind = SyntaxToken.Function
                elif flags & (CSS | YAML) and text[following] == ":":
                    kind = SyntaxToken.Key
                    add(start, index, kind)
                    expected = 0
                    continue
            if kind:
                add(start, index, kind)
            expected = (
                0
                if state == 6
                else SyntaxToken.Type
                if lookup in ("class", "struct", "enum", "interface", "record")
                else SyntaxToken.Function
                if lookup in ("def", "fn", "func", "function")
                else 0
            )
            continue
        if char in "+-*/%=!<>^&|~?:.,;(){}[]":
            add(index, index + 1, SyntaxToken.Operator)
        index += 1
    return spans, state
