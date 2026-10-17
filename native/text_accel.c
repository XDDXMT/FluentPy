/* FluentPy's tolerant JSON syntax scanner. SPDX-License-Identifier: MIT
 *
 * No Qt or external C library is required. Python's immutable Unicode storage
 * is read directly; positions are accumulated in UTF-16 code units for Qt.
 * This deliberately tokenizes incomplete input instead of validating JSON.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "date_accel.h"
#include "drop_accel.h"
#include "shortcut_accel.h"
#include "time_accel.h"
#include "calendar_accel.h"

typedef struct {
    int kind;
    const void *data;
    Py_ssize_t length;
} TextView;

static Py_UCS4
read_character(const TextView *text, Py_ssize_t index)
{
    return PyUnicode_READ(text->kind, text->data, index);
}

static int
is_word(Py_UCS4 character)
{
    return character == '_' || Py_UNICODE_ISALNUM(character);
}

static Py_ssize_t
utf16_width(Py_UCS4 character)
{
    return character > 0xFFFFU ? 2 : 1;
}

static int
append_span(PyObject *spans, Py_ssize_t start, Py_ssize_t length, int kind)
{
    PyObject *span = PyTuple_New(3);
    PyObject *start_object, *length_object, *kind_object;
    int result;
    if (span == NULL) {
        return -1;
    }
    start_object = PyLong_FromSsize_t(start);
    length_object = PyLong_FromSsize_t(length);
    kind_object = PyLong_FromLong(kind);
    if (start_object == NULL || length_object == NULL || kind_object == NULL) {
        Py_XDECREF(start_object);
        Py_XDECREF(length_object);
        Py_XDECREF(kind_object);
        Py_DECREF(span);
        return -1;
    }
    PyTuple_SET_ITEM(span, 0, start_object);
    PyTuple_SET_ITEM(span, 1, length_object);
    PyTuple_SET_ITEM(span, 2, kind_object);
    result = PyList_Append(spans, span);
    Py_DECREF(span);
    return result;
}

/* Return the first complete quoted token end, or -1. As in Python re's
 * \\. rule, a backslash can escape anything except a newline. Unescaped
 * newlines are accepted because the original negated character class did so.
 */
static Py_ssize_t
scan_string(const TextView *text, Py_ssize_t start)
{
    Py_ssize_t index = start + 1;
    while (index < text->length) {
        Py_UCS4 character = read_character(text, index);
        if (character == '"') {
            return index + 1;
        }
        if (character == '\\') {
            if (index + 1 >= text->length || read_character(text, index + 1) == '\n') {
                return -1;
            }
            index += 2;
        } else {
            ++index;
        }
    }
    return -1;
}

/* Failed opening quotes can otherwise rescan the same escaped suffix many
 * times. Build this lookup lazily on the first failure, using the recurrence
 * for a string body scanned from i: quote ends it, backslash skips two code
 * points, and other characters skip one. Entries are read only at quotes.
 * Normal well-formed input does not allocate this scratch space.
 */
static Py_ssize_t *
build_quote_ends(const TextView *text)
{
    Py_ssize_t *ends;
    Py_ssize_t index, next = -1, after_next = -1;
    if ((size_t)text->length > (size_t)PY_SSIZE_T_MAX / sizeof(*ends)) {
        PyErr_NoMemory();
        return NULL;
    }
    ends = PyMem_Malloc((size_t)text->length * sizeof(*ends));
    if (ends == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    for (index = text->length; index > 0;) {
        Py_UCS4 character = read_character(text, --index);
        Py_ssize_t current;
        if (character == '"') {
            ends[index] = next;
            current = index + 1;
        } else if (character == '\\') {
            current = index + 1 < text->length && read_character(text, index + 1) != '\n'
                ? after_next : -1;
        } else {
            current = next;
        }
        after_next = next;
        next = current;
    }
    return ends;
}

static Py_ssize_t
scan_number(const TextView *text, Py_ssize_t start)
{
    Py_ssize_t index = start;
    Py_UCS4 character;
    if (start > 0) {
        character = read_character(text, start - 1);
        if (is_word(character) || character == '.') {
            return -1;
        }
    }
    if (read_character(text, index) == '-') {
        if (++index == text->length) {
            return -1;
        }
    }
    character = read_character(text, index);
    if (character == '0') {
        ++index;
    } else if (character >= '1' && character <= '9') {
        do {
            ++index;
        } while (index < text->length && Py_UNICODE_ISDECIMAL(read_character(text, index)));
    } else {
        return -1;
    }
    if (index + 1 < text->length && read_character(text, index) == '.' &&
            Py_UNICODE_ISDECIMAL(read_character(text, index + 1))) {
        index += 2;
        while (index < text->length && Py_UNICODE_ISDECIMAL(read_character(text, index))) {
            ++index;
        }
    }
    if (index < text->length &&
            (read_character(text, index) == 'e' || read_character(text, index) == 'E')) {
        Py_ssize_t exponent = index + 1;
        if (exponent < text->length &&
                (read_character(text, exponent) == '+' || read_character(text, exponent) == '-')) {
            ++exponent;
        }
        if (exponent < text->length && Py_UNICODE_ISDECIMAL(read_character(text, exponent))) {
            index = exponent + 1;
            while (index < text->length && Py_UNICODE_ISDECIMAL(read_character(text, index))) {
                ++index;
            }
        }
    }
    if (index < text->length) {
        character = read_character(text, index);
        if (is_word(character) || character == '.') {
            return -1;
        }
    }
    return index;
}

static Py_ssize_t
scan_literal(const TextView *text, Py_ssize_t start)
{
    const char *literal;
    Py_ssize_t length, offset, end;
    if (start > 0 && is_word(read_character(text, start - 1))) {
        return -1;
    }
    switch (read_character(text, start)) {
        case 't': literal = "true"; length = 4; break;
        case 'f': literal = "false"; length = 5; break;
        case 'n': literal = "null"; length = 4; break;
        default: return -1;
    }
    if (text->length - start < length) {
        return -1;
    }
    for (offset = 1; offset < length; ++offset) {
        if (read_character(text, start + offset) != (Py_UCS4)literal[offset]) {
            return -1;
        }
    }
    end = start + length;
    return end < text->length && is_word(read_character(text, end)) ? -1 : end;
}

static PyObject *
json_spans(PyObject *module, PyObject *argument)
{
    TextView text;
    Py_ssize_t index = 0, position = 0;
    Py_ssize_t *quote_ends = NULL;
    PyObject *spans;
    (void)module;
    if (!PyUnicode_Check(argument)) {
        PyErr_SetString(PyExc_TypeError, "text must be str");
        return NULL;
    }
    if (PyUnicode_READY(argument) < 0) {
        return NULL;
    }
    text.kind = PyUnicode_KIND(argument);
    text.data = PyUnicode_DATA(argument);
    text.length = PyUnicode_GET_LENGTH(argument);
    /* Even with one astral character per scalar, positions cannot overflow. */
    if (text.length > PY_SSIZE_T_MAX / 2) {
        PyErr_SetString(PyExc_OverflowError, "text is too large for UTF-16 positions");
        return NULL;
    }
    spans = PyList_New(0);
    if (spans == NULL) {
        return NULL;
    }
    while (index < text.length) {
        Py_UCS4 character = read_character(&text, index);
        Py_ssize_t end = -1;
        int kind = -1;
        if (character == '"') {
            if (quote_ends != NULL) {
                end = quote_ends[index];
            } else {
                end = scan_string(&text, index);
                if (end < 0) {
                    quote_ends = build_quote_ends(&text);
                    if (quote_ends == NULL) {
                        Py_DECREF(spans);
                        return NULL;
                    }
                }
            }
            if (end >= 0) {
                Py_ssize_t following = end;
                while (following < text.length && Py_UNICODE_ISSPACE(read_character(&text, following))) {
                    ++following;
                }
                kind = following < text.length && read_character(&text, following) == ':' ? 0 : 1;
            }
        } else if (character == '-' || (character >= '0' && character <= '9')) {
            end = scan_number(&text, index);
            kind = 2;
        } else if (character == 't' || character == 'f' || character == 'n') {
            end = scan_literal(&text, index);
            kind = 3;
        }
        if (end >= 0) {
            Py_ssize_t cursor, width = 0;
            if (text.kind == PyUnicode_4BYTE_KIND) {
                for (cursor = index; cursor < end; ++cursor) {
                    width += utf16_width(read_character(&text, cursor));
                }
            } else {
                width = end - index;
            }
            if (append_span(spans, position, width, kind) < 0) {
                PyMem_Free(quote_ends);
                Py_DECREF(spans);
                return NULL;
            }
            index = end;
            position += width;
        } else {
            ++index;
            position += utf16_width(character);
        }
    }
    PyMem_Free(quote_ends);
    return spans;
}

PyDoc_STRVAR(json_spans_doc,
    "json_spans(text, /) -> list[tuple[int, int, int]]\n\n"
    "Tolerant JSON token spans as UTF-16 start, length, kind.\n"
    "Kinds: key=0, string=1, number=2, literal=3. No source mutation.");

static PyMethodDef methods[] = {
    {"json_spans", json_spans, METH_O, json_spans_doc},
    {NULL, NULL, 0, NULL}
};

static struct PyModuleDef module = {
    PyModuleDef_HEAD_INIT,
    "_native",
    "Native text, calendar, time, file-selection and shortcut policies for FluentPy.",
    -1,
    methods,
    NULL, NULL, NULL, NULL
};

PyMODINIT_FUNC
PyInit__native(void)
{
    PyObject *result = PyModule_Create(&module);
    if (result == NULL) {
        return NULL;
    }
    if (fluentpy_add_date_methods(result) < 0) {
        Py_DECREF(result);
        return NULL;
    }
    if (fluentpy_add_drop_methods(result) < 0) {
        Py_DECREF(result);
        return NULL;
    }
    if (fluentpy_add_shortcut_methods(result) < 0) {
        Py_DECREF(result);
        return NULL;
    }
    if (fluentpy_add_time_methods(result) < 0) {
        Py_DECREF(result);
        return NULL;
    }
    if (fluentpy_add_calendar_methods(result) < 0) {
        Py_DECREF(result);
        return NULL;
    }
    return result;
}
