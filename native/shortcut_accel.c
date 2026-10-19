/* Single-chord shortcut policy. Qt supplies native key events and strings.
 * SPDX-License-Identifier: MIT */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "shortcut_accel.h"

#define SHIFT 0x02000000L
#define CTRL 0x04000000L
#define ALT 0x08000000L
#define META 0x10000000L
#define NUM 0x20000000L
#define MODIFIERS (SHIFT | CTRL | ALT | META | NUM)

static int integer(PyObject *value, long *result) {
    if (!PyLong_Check(value) || PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "shortcut keys and modifiers must be integers");
        return -1;
    }
    *result = PyLong_AsLong(value);
    return PyErr_Occurred() ? -1 : 0;
}

static int valid_modifiers(long modifiers) {
    if (modifiers < 0 || (modifiers & ~MODIFIERS)) {
        PyErr_SetString(PyExc_ValueError, "unsupported shortcut modifier bits");
        return -1;
    }
    return 0;
}

static int normalize(long *key, long modifiers) {
    if (valid_modifiers(modifiers) < 0)
        return -1;
    if (*key == 0 && modifiers == 0)
        return 0;
    if ((*key < 0x20 || *key > 0x10ffff || (*key >= 0xd800 && *key <= 0xdfff)) &&
        !(*key >= 0x01000000L && *key < 0x01020000L)) {
        PyErr_SetString(PyExc_ValueError, "shortcut requires one valid non-modifier Qt key");
        return -1;
    }
    if (*key >= 0x01000020L && *key <= 0x01000026L) {
        PyErr_SetString(PyExc_ValueError, "a modifier or lock key alone is not a shortcut");
        return -1;
    }
    if (*key >= 'a' && *key <= 'z')
        *key -= 'a' - 'A';
    return 0;
}

static PyObject *normalize_shortcut(PyObject *module, PyObject *args) {
    PyObject *key_object, *modifiers_object;
    long key, modifiers;
    (void)module;
    if (!PyArg_ParseTuple(args, "OO:shortcut_normalize", &key_object, &modifiers_object) ||
        integer(key_object, &key) < 0 || integer(modifiers_object, &modifiers) < 0 ||
        normalize(&key, modifiers) < 0)
        return NULL;
    return Py_BuildValue("(ll)", key, modifiers);
}

static PyObject *modifier_labels(PyObject *module, PyObject *argument) {
    const long flags[] = {CTRL, ALT, SHIFT, META, NUM};
    const char *names[] = {"Ctrl", "Alt", "Shift", "Meta", "Num"};
    long modifiers;
    PyObject *labels, *result;
    int i;
    (void)module;
    if (integer(argument, &modifiers) < 0 || valid_modifiers(modifiers) < 0)
        return NULL;
    labels = PyList_New(0);
    if (labels == NULL)
        return NULL;
    for (i = 0; i < 5; ++i) {
        if (modifiers & flags[i]) {
            PyObject *name = PyUnicode_FromString(names[i]);
            if (name == NULL || PyList_Append(labels, name) < 0) {
                Py_XDECREF(name);
                Py_DECREF(labels);
                return NULL;
            }
            Py_DECREF(name);
        }
    }
    result = PyList_AsTuple(labels);
    Py_DECREF(labels);
    return result;
}

static PyObject *conflicts(PyObject *module, PyObject *args) {
    PyObject *key_object, *modifiers_object, *reserved, *items;
    long key, modifiers;
    Py_ssize_t i;
    int conflict = 0;
    (void)module;
    if (!PyArg_ParseTuple(args, "OOO:shortcut_conflicts", &key_object, &modifiers_object,
                          &reserved) ||
        integer(key_object, &key) < 0 || integer(modifiers_object, &modifiers) < 0 ||
        normalize(&key, modifiers) < 0)
        return NULL;
    if (PyUnicode_Check(reserved) || PyBytes_Check(reserved)) {
        PyErr_SetString(PyExc_TypeError, "reserved shortcuts must be pairs, not text");
        return NULL;
    }
    items = PySequence_Fast(reserved, "reserved shortcuts must be iterable");
    if (items == NULL)
        return NULL;
    for (i = 0; i < PySequence_Fast_GET_SIZE(items); ++i) {
        PyObject *pair =
            PySequence_Fast(PySequence_Fast_GET_ITEM(items, i), "reserved shortcut must be a pair");
        long other_key, other_modifiers;
        if (pair == NULL) {
            Py_DECREF(items);
            return NULL;
        }
        if (PySequence_Fast_GET_SIZE(pair) != 2) {
            Py_DECREF(pair);
            Py_DECREF(items);
            PyErr_SetString(PyExc_ValueError, "reserved shortcut must contain key and modifiers");
            return NULL;
        }
        if (integer(PySequence_Fast_GET_ITEM(pair, 0), &other_key) < 0 ||
            integer(PySequence_Fast_GET_ITEM(pair, 1), &other_modifiers) < 0 ||
            normalize(&other_key, other_modifiers) < 0) {
            Py_DECREF(pair);
            Py_DECREF(items);
            return NULL;
        }
        conflict |= key != 0 && key == other_key && modifiers == other_modifiers;
        Py_DECREF(pair);
    }
    Py_DECREF(items);
    return PyBool_FromLong(conflict);
}

static PyMethodDef methods[] = {
    {"shortcut_normalize", normalize_shortcut, METH_VARARGS,
     "Validate one Qt key chord; normalize ASCII letters."},
    {"shortcut_modifier_labels", modifier_labels, METH_O,
     "Ordered modifier labels for a Qt modifier mask."},
    {"shortcut_conflicts", conflicts, METH_VARARGS,
     "Check a chord against all reserved chords; validate the entire input."},
    {NULL, NULL, 0, NULL}};

int fluentpy_add_shortcut_methods(PyObject *module) {
    return PyModule_AddFunctions(module, methods);
}
