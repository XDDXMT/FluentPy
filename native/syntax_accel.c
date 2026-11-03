/* Stateful lexical coloring for Qt text blocks. SPDX-License-Identifier: MIT */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <string.h>
#include "syntax_accel.h"

enum {
    HASH = 1,
    SLASH = 2,
    BLOCK = 4,
    SQL = 8,
    BACKTICK = 16,
    TRIPLE = 32,
    MARKUP = 64,
    CSS = 128,
    YAML = 256,
    CASELESS = 512,
    PYTHON = 1024,
    SHELL = 2048,
    PREPROCESSOR = 4096
};
enum {
    KEY = 0,
    STRING = 1,
    NUMBER = 2,
    LITERAL = 3,
    KEYWORD = 4,
    COMMENT = 5,
    OPERATOR = 6,
    FUNCTION = 7,
    TYPE = 8,
    TAG = 9,
    ATTRIBUTE = 10,
    DECORATOR = 11,
    VARIABLE = 12
};

typedef struct {
    PyObject *object;
    int kind;
    const void *data;
    Py_ssize_t length;
} SyntaxText;

static Py_UCS4 character(const SyntaxText *text, Py_ssize_t index) {
    return index < text->length ? PyUnicode_READ(text->kind, text->data, index) : 0;
}

static int matches(const SyntaxText *text, Py_ssize_t index, const char *literal) {
    size_t size = strlen(literal);
    if ((size_t)(text->length - index) < size)
        return 0;
    for (size_t offset = 0; offset < size; ++offset)
        if (character(text, index + (Py_ssize_t)offset) != (unsigned char)literal[offset])
            return 0;
    return 1;
}

static Py_ssize_t find_after(const SyntaxText *text, Py_ssize_t index, const char *delimiter) {
    while (index < text->length) {
        if (matches(text, index, delimiter))
            return index + (Py_ssize_t)strlen(delimiter);
        ++index;
    }
    return -1;
}

static Py_ssize_t quoted_end(const SyntaxText *text, Py_ssize_t index, const char *delimiter,
                             int skip, int *closed) {
    index += skip;
    while (index < text->length) {
        if (matches(text, index, delimiter)) {
            *closed = 1;
            return index + (Py_ssize_t)strlen(delimiter);
        }
        index += character(text, index) == '\\' ? 2 : 1;
    }
    *closed = 0;
    return text->length;
}

static int in_ascii(Py_UCS4 value, const char *characters) {
    return value != 0 && value < 128 && strchr(characters, (int)value) != NULL;
}

static int word_kind(const SyntaxText *text, Py_ssize_t start, Py_ssize_t end, PyObject *words,
                     int flags, int *expected) {
    PyObject *word = PyUnicode_Substring(text->object, start, end), *value;
    int result = *expected;
    if (word == NULL)
        return -2;
    if (flags & CASELESS) {
        PyObject *lower = PyUnicode_New(end - start, PyUnicode_MAX_CHAR_VALUE(word));
        if (lower == NULL) {
            Py_DECREF(word);
            return -2;
        }
        for (Py_ssize_t index = 0; index < end - start; ++index) {
            Py_UCS4 code = PyUnicode_READ_CHAR(word, index);
            if (code >= 'A' && code <= 'Z')
                code += 'a' - 'A';
            PyUnicode_WRITE(PyUnicode_KIND(lower), PyUnicode_DATA(lower), index, code);
        }
        Py_DECREF(word);
        word = lower;
    }
    value = PyDict_GetItemWithError(words, word);
    if (value != NULL) {
        long kind = PyLong_AsLong(value);
        if (PyErr_Occurred()) {
            Py_DECREF(word);
            return -2;
        }
        if (kind < 0 || kind > VARIABLE) {
            PyErr_SetString(PyExc_ValueError, "token kind must be between 0 and 12");
            Py_DECREF(word);
            return -2;
        }
        result = (int)kind;
    } else if (PyErr_Occurred()) {
        Py_DECREF(word);
        return -2;
    }
    *expected = -1;
    if (PyUnicode_CompareWithASCIIString(word, "class") == 0 ||
        PyUnicode_CompareWithASCIIString(word, "struct") == 0 ||
        PyUnicode_CompareWithASCIIString(word, "enum") == 0 ||
        PyUnicode_CompareWithASCIIString(word, "interface") == 0 ||
        PyUnicode_CompareWithASCIIString(word, "record") == 0)
        *expected = TYPE;
    else if (PyUnicode_CompareWithASCIIString(word, "def") == 0 ||
             PyUnicode_CompareWithASCIIString(word, "fn") == 0 ||
             PyUnicode_CompareWithASCIIString(word, "func") == 0 ||
             PyUnicode_CompareWithASCIIString(word, "function") == 0)
        *expected = FUNCTION;
    Py_DECREF(word);
    return result;
}

static PyObject *syntax_spans(PyObject *self, PyObject *args) {
    PyObject *input, *words, *spans;
    SyntaxText text;
    int flags, state, expected = -1;
    Py_ssize_t index = 0, position = 0;
    (void)self;
    if (!PyArg_ParseTuple(args, "OiOi:syntax_spans", &input, &flags, &words, &state))
        return NULL;
    if (!PyUnicode_Check(input)) {
        PyErr_SetString(PyExc_TypeError, "text must be str");
        return NULL;
    }
    if (!PyDict_Check(words)) {
        PyErr_SetString(PyExc_TypeError, "words must be dict");
        return NULL;
    }
    if (flags < 0 || flags > 8191 || state < 0 || state > 8) {
        PyErr_SetString(PyExc_ValueError, "invalid syntax flags or state");
        return NULL;
    }
    text.object = input;
    text.kind = PyUnicode_KIND(input);
    text.data = PyUnicode_DATA(input);
    text.length = PyUnicode_GET_LENGTH(input);
    spans = PyList_New(0);
    if (spans == NULL)
        return NULL;
    while (index < text.length) {
        Py_ssize_t start = index, end = index + 1, following, width = 0;
        Py_UCS4 code = character(&text, index);
        int kind = -1, closed = 0;
        if (state == 1 || state == 5) {
            end = find_after(&text, index, state == 1 ? "*/" : "-->");
            kind = COMMENT;
            if (end < 0)
                end = text.length;
            else
                state = 0;
        } else if (state == 2 || state == 3 || state == 4 || state == 7 || state == 8) {
            const char *delimiter = state == 2   ? "'''"
                                    : state == 3 ? "\"\"\""
                                    : state == 4 ? "`"
                                    : state == 7 ? "'"
                                                 : "\"";
            end = quoted_end(&text, index, delimiter, 0, &closed);
            kind = STRING;
            if (closed)
                state = state == 7 || state == 8 ? 6 : 0;
        } else if (Py_UNICODE_ISSPACE(code)) {
            /* Whitespace advances positions without allocating a token. */
        } else if ((flags & MARKUP) && matches(&text, index, "<!--")) {
            end = find_after(&text, index + 4, "-->");
            kind = COMMENT;
            state = end < 0 ? 5 : 0;
            if (end < 0)
                end = text.length;
        } else if ((flags & MARKUP) && code == '<') {
            if (in_ascii(character(&text, end), "/!?"))
                ++end;
            while (end < text.length && (Py_UNICODE_ISALNUM(character(&text, end)) ||
                                         in_ascii(character(&text, end), "_-:")))
                ++end;
            kind = TAG;
            state = 6;
        } else if (state == 6 && code == '>') {
            kind = TAG;
            state = 0;
        } else if (((flags & HASH) && code == '#') ||
                   ((flags & SLASH) && matches(&text, index, "//")) ||
                   ((flags & SQL) && matches(&text, index, "--"))) {
            end = text.length;
            kind = COMMENT;
        } else if ((flags & PREPROCESSOR) && code == '#') {
            end = text.length;
            kind = DECORATOR;
        } else if ((flags & BLOCK) && matches(&text, index, "/*")) {
            end = find_after(&text, index + 2, "*/");
            kind = COMMENT;
            if (end < 0) {
                end = text.length;
                state = 1;
            }
        } else if (code == '\'' || code == '"' || (code == '`' && (flags & BACKTICK))) {
            char delimiter[4] = {(char)code, 0, 0, 0};
            int triple = (flags & TRIPLE) && character(&text, index + 1) == code &&
                         character(&text, index + 2) == code;
            if (triple)
                delimiter[1] = delimiter[2] = (char)code;
            end = quoted_end(&text, index, delimiter, triple ? 3 : 1, &closed);
            kind = STRING;
            if (!closed) {
                if (triple)
                    state = code == '\'' ? 2 : 3;
                else if (code == '`')
                    state = 4;
                else if (state == 6)
                    state = code == '\'' ? 7 : 8;
                else
                    state = 0;
            }
        } else if ((flags & PYTHON) && code == '@') {
            while (end < text.length && (Py_UNICODE_ISALNUM(character(&text, end)) ||
                                         in_ascii(character(&text, end), "_.")))
                ++end;
            kind = DECORATOR;
        } else if ((flags & SHELL) && code == '$') {
            while (end < text.length && (Py_UNICODE_ISALNUM(character(&text, end)) ||
                                         in_ascii(character(&text, end), "_{}?")))
                ++end;
            kind = VARIABLE;
        } else if (Py_UNICODE_ISDECIMAL(code) ||
                   (code == '.' && index + 1 < text.length &&
                    Py_UNICODE_ISDECIMAL(character(&text, index + 1))) ||
                   ((flags & CSS) && code == '#')) {
            while (end < text.length) {
                Py_UCS4 current = character(&text, end);
                if (Py_UNICODE_ISALNUM(current) || in_ascii(current, "_.") ||
                    (in_ascii(current, "+-") && in_ascii(character(&text, end - 1), "eE")))
                    ++end;
                else
                    break;
            }
            kind = NUMBER;
        } else if (Py_UNICODE_ISALPHA(code) || in_ascii(code, "_$")) {
            while (end < text.length && (Py_UNICODE_ISALNUM(character(&text, end)) ||
                                         in_ascii(character(&text, end), "_$") ||
                                         (state == 6 && in_ascii(character(&text, end), "-:"))))
                ++end;
            following = end;
            while (following < text.length && Py_UNICODE_ISSPACE(character(&text, following)))
                ++following;
            if (state == 6)
                kind = ATTRIBUTE;
            else {
                kind = word_kind(&text, start, end, words, flags, &expected);
                if (kind == -2) {
                    Py_DECREF(spans);
                    return NULL;
                }
            }
            if (kind < 0 && following < text.length) {
                if (character(&text, following) == '(')
                    kind = FUNCTION;
                else if ((flags & (CSS | YAML)) && character(&text, following) == ':') {
                    kind = KEY;
                    expected = -1;
                }
            }
        } else if (in_ascii(code, "+-*/%=!<>^&|~?:.,;(){}[]")) {
            kind = OPERATOR;
        }
        for (Py_ssize_t offset = start; offset < end; ++offset)
            width += character(&text, offset) > 0xFFFFU ? 2 : 1;
        if (kind >= 0) {
            PyObject *span = Py_BuildValue("(nni)", position, width, kind);
            if (span == NULL || PyList_Append(spans, span) < 0) {
                Py_XDECREF(span);
                Py_DECREF(spans);
                return NULL;
            }
            Py_DECREF(span);
        }
        position += width;
        index = end;
    }
    return Py_BuildValue("Ni", spans, state);
}

static PyMethodDef methods[] = {
    {"syntax_spans", syntax_spans, METH_VARARGS, "Stateful syntax token spans in UTF-16 units."},
    {NULL, NULL, 0, NULL}};

int fluentpy_add_syntax_methods(PyObject *module) {
    return PyModule_AddFunctions(module, methods);
}
