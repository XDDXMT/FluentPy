/* Drop selection policy; Qt supplies native filesystem metadata. SPDX-License-Identifier: MIT */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "drop_accel.h"

static PyObject *normalize_extensions(PyObject *module, PyObject *argument) {
    PyObject *items = NULL, *result = NULL, *seen = NULL, *tuple = NULL;
    Py_ssize_t index;
    int unrestricted = 0;
    (void)module;
    if (PyUnicode_Check(argument) || PyBytes_Check(argument)) {
        PyErr_SetString(PyExc_TypeError, "extensions must be a sequence of strings, not a string");
        return NULL;
    }
    items = PySequence_Fast(argument, "extensions must be an iterable of strings");
    result = PyList_New(0);
    seen = PySet_New(NULL);
    if (items == NULL || result == NULL || seen == NULL)
        goto done;
    for (index = 0; index < PySequence_Fast_GET_SIZE(items); ++index) {
        PyObject *value = PySequence_Fast_GET_ITEM(items, index);
        PyObject *trimmed, *folded, *extension;
        Py_ssize_t length, offset = 0, cursor;
        int contains;
        if (!PyUnicode_Check(value)) {
            PyErr_SetString(PyExc_TypeError, "every extension must be str");
            goto done;
        }
        trimmed = PyObject_CallMethod(value, "strip", NULL);
        if (trimmed == NULL)
            goto done;
        folded = PyObject_CallMethod(trimmed, "casefold", NULL);
        Py_DECREF(trimmed);
        if (folded == NULL)
            goto done;
        length = PyUnicode_GET_LENGTH(folded);
        if (PyUnicode_CompareWithASCIIString(folded, "*") == 0 ||
            PyUnicode_CompareWithASCIIString(folded, "*.*") == 0) {
            unrestricted = 1;
            Py_DECREF(folded);
            continue;
        }
        if (length > 1 && PyUnicode_ReadChar(folded, 0) == '*' &&
            PyUnicode_ReadChar(folded, 1) == '.')
            offset = 1;
        extension = PyUnicode_Substring(folded, offset, length);
        Py_DECREF(folded);
        if (extension == NULL)
            goto done;
        length = PyUnicode_GET_LENGTH(extension);
        if (length == 0) {
            Py_DECREF(extension);
            PyErr_SetString(PyExc_ValueError, "extensions cannot contain empty strings");
            goto done;
        }
        if (PyUnicode_ReadChar(extension, 0) != '.') {
            PyObject *with_dot = PyUnicode_FromFormat(".%U", extension);
            Py_DECREF(extension);
            extension = with_dot;
            if (extension == NULL)
                goto done;
        }
        length = PyUnicode_GET_LENGTH(extension);
        for (cursor = 1; cursor < length; ++cursor) {
            Py_UCS4 ch = PyUnicode_ReadChar(extension, cursor);
            if (ch == '/' || ch == '\\' || ch == '*' || ch == '?' || ch == 0 ||
                Py_UNICODE_ISSPACE(ch))
                break;
        }
        if (length < 2 || cursor != length) {
            Py_DECREF(extension);
            PyErr_SetString(PyExc_ValueError,
                            "extensions must be suffixes such as .png or .tar.gz");
            goto done;
        }
        contains = PySet_Contains(seen, extension);
        if (contains < 0 || (!contains && (PySet_Add(seen, extension) < 0 ||
                                           PyList_Append(result, extension) < 0))) {
            Py_DECREF(extension);
            goto done;
        }
        Py_DECREF(extension);
    }
    tuple = unrestricted ? PyTuple_New(0) : PyList_AsTuple(result);
done:
    Py_XDECREF(items);
    Py_XDECREF(result);
    Py_XDECREF(seen);
    return tuple;
}

static int reject_path(PyObject *rejected, PyObject *path, const char *reason) {
    PyObject *item = Py_BuildValue("(Os)", path, reason);
    int result;
    if (item == NULL)
        return -1;
    result = PyList_Append(rejected, item);
    Py_DECREF(item);
    return result;
}

static PyObject *filter_paths(PyObject *module, PyObject *args) {
    PyObject *candidates, *raw_extensions, *items = NULL, *extensions = NULL;
    PyObject *accepted = NULL, *rejected = NULL, *seen = NULL, *result = NULL;
    Py_ssize_t index;
    int allow_files, allow_folders, multiple, case_sensitive;
    (void)module;
    if (!PyArg_ParseTuple(args, "OOpppp:drop_filter_paths", &candidates, &raw_extensions,
                          &allow_files, &allow_folders, &multiple, &case_sensitive))
        return NULL;
    if (PyUnicode_Check(candidates) || PyBytes_Check(candidates)) {
        PyErr_SetString(PyExc_TypeError, "candidates must be a sequence of (path, kind) pairs");
        return NULL;
    }
    items = PySequence_Fast(candidates, "candidates must be iterable");
    extensions = normalize_extensions(NULL, raw_extensions);
    accepted = PyList_New(0);
    rejected = PyList_New(0);
    seen = PySet_New(NULL);
    if (items == NULL || extensions == NULL || accepted == NULL || rejected == NULL || seen == NULL)
        goto done;
    for (index = 0; index < PySequence_Fast_GET_SIZE(items); ++index) {
        PyObject *pair = PySequence_Fast(PySequence_Fast_GET_ITEM(items, index),
                                         "candidate must be (path, kind)");
        PyObject *path, *kind_object, *key = NULL;
        long kind;
        const char *reason = NULL;
        if (pair == NULL)
            goto done;
        if (PySequence_Fast_GET_SIZE(pair) != 2) {
            Py_DECREF(pair);
            PyErr_SetString(PyExc_ValueError, "candidate must have exactly two items");
            goto done;
        }
        path = PySequence_Fast_GET_ITEM(pair, 0);
        kind_object = PySequence_Fast_GET_ITEM(pair, 1);
        if (!PyUnicode_Check(path) || !PyLong_Check(kind_object) || PyBool_Check(kind_object)) {
            Py_DECREF(pair);
            PyErr_SetString(PyExc_TypeError, "candidate path must be str and kind must be int");
            goto done;
        }
        kind = PyLong_AsLong(kind_object);
        if (kind == -1 && PyErr_Occurred()) {
            Py_DECREF(pair);
            goto done;
        }
        if (kind < 0 || kind > 3) {
            Py_DECREF(pair);
            PyErr_SetString(PyExc_ValueError,
                            "kind must be missing=0, file=1, folder=2 or other=3");
            goto done;
        }
        if (PyUnicode_GET_LENGTH(path) == 0 ||
            PyUnicode_FindChar(path, 0, 0, PyUnicode_GET_LENGTH(path), 1) >= 0)
            reason = "invalid";
        else if (kind == 0)
            reason = "missing";
        else if ((kind == 1 && !allow_files) || (kind == 2 && !allow_folders) || kind == 3)
            reason = "type";
        else if (kind == 1 && PyTuple_GET_SIZE(extensions)) {
            PyObject *folded = PyObject_CallMethod(path, "casefold", NULL);
            Py_ssize_t suffix;
            int matches = 0;
            if (folded == NULL) {
                Py_DECREF(pair);
                goto done;
            }
            for (suffix = 0; suffix < PyTuple_GET_SIZE(extensions); ++suffix) {
                matches = PyUnicode_Tailmatch(folded, PyTuple_GET_ITEM(extensions, suffix), 0,
                                              PyUnicode_GET_LENGTH(folded), 1);
                if (matches != 0)
                    break;
            }
            Py_DECREF(folded);
            if (matches < 0) {
                Py_DECREF(pair);
                goto done;
            }
            if (!matches)
                reason = "extension";
        }
        if (reason == NULL) {
            int contains;
            key = case_sensitive ? Py_NewRef(path) : PyObject_CallMethod(path, "casefold", NULL);
            if (key == NULL) {
                Py_DECREF(pair);
                goto done;
            }
            contains = PySet_Contains(seen, key);
            if (contains < 0) {
                Py_DECREF(key);
                Py_DECREF(pair);
                goto done;
            }
            if (contains)
                reason = "duplicate";
            else if (!multiple && PyList_GET_SIZE(accepted))
                reason = "multiple";
            else if (PySet_Add(seen, key) < 0) {
                Py_DECREF(key);
                Py_DECREF(pair);
                goto done;
            }
            Py_DECREF(key);
        }
        if (reason != NULL) {
            if (reject_path(rejected, path, reason) < 0) {
                Py_DECREF(pair);
                goto done;
            }
        } else {
            PyObject *item = Py_BuildValue("(Ol)", path, kind);
            if (item == NULL || PyList_Append(accepted, item) < 0) {
                Py_XDECREF(item);
                Py_DECREF(pair);
                goto done;
            }
            Py_DECREF(item);
        }
        Py_DECREF(pair);
    }
    result = PyTuple_Pack(2, accepted, rejected);
done:
    Py_XDECREF(items);
    Py_XDECREF(extensions);
    Py_XDECREF(accepted);
    Py_XDECREF(rejected);
    Py_XDECREF(seen);
    return result;
}

static PyMethodDef methods[] = {
    {"drop_normalize_extensions", normalize_extensions, METH_O,
     "Normalize accepted file suffixes; an empty tuple accepts all file types."},
    {"drop_filter_paths", filter_paths, METH_VARARGS,
     "Filter (canonical path, Qt file kind) candidates with stable order and rejection reasons."},
    {NULL, NULL, 0, NULL}};

int fluentpy_add_drop_methods(PyObject *module) {
    return PyModule_AddFunctions(module, methods);
}
