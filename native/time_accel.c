/* Time-wheel policies for FluentPy. SPDX-License-Identifier: MIT
 * Canonical values are 24-hour (hour, minute). Each column changes independently.
 * 12-hour hour steps preserve AM/PM; the period column has two bounded rows.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "time_accel.h"

static int integer(PyObject *value, const char *name) {
    if (!PyLong_Check(value) || PyBool_Check(value)) {
        PyErr_Format(PyExc_TypeError, "%s must be an int, not bool or another type", name);
        return -1;
    }
    return 0;
}

static int bounded(PyObject *value, const char *name, int lower, int upper, int *result) {
    int overflow = 0;
    long number;
    if (integer(value, name) < 0)
        return -1;
    number = PyLong_AsLongAndOverflow(value, &overflow);
    if (overflow || number < lower || number > upper) {
        PyErr_Format(PyExc_ValueError, "%s must be between %d and %d", name, lower, upper);
        return -1;
    }
    if (PyErr_Occurred())
        return -1;
    *result = (int)number;
    return 0;
}

static int mode(PyObject *value, int *result) {
    if (value && !PyBool_Check(value)) {
        PyErr_SetString(PyExc_TypeError, "use_12_hour must be bool");
        return -1;
    }
    *result = value == Py_True;
    return 0;
}

static int parts(PyObject *hour, PyObject *minute, int *h, int *m) {
    return bounded(hour, "hour", 0, 23, h) < 0 || bounded(minute, "minute", 0, 59, m) < 0 ? -1 : 0;
}

static int wrap(int value, int count) {
    int result = value % count;
    return result < 0 ? result + count : result;
}

static PyObject *validate_time(PyObject *self, PyObject *args, PyObject *kwargs) {
    static char *names[] = {"hour", "minute", NULL};
    PyObject *hour, *minute;
    int h, m;
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OO:time_validate_time", names, &hour,
                                     &minute) ||
        parts(hour, minute, &h, &m) < 0)
        return NULL;
    return Py_BuildValue("(ii)", h, m);
}

static PyObject *display_time(PyObject *self, PyObject *args, PyObject *kwargs) {
    static char *names[] = {"hour", "minute", "use_12_hour", NULL};
    PyObject *hour, *minute, *use_12_hour = NULL;
    int h, m, twelve;
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OO|O:time_display_time", names, &hour, &minute,
                                     &use_12_hour) ||
        parts(hour, minute, &h, &m) < 0 || mode(use_12_hour, &twelve) < 0)
        return NULL;
    return Py_BuildValue("(iii)", twelve ? (h % 12 ? h % 12 : 12) : h, m, h >= 12);
}

static PyObject *from_display(PyObject *self, PyObject *args, PyObject *kwargs) {
    static char *names[] = {"hour", "minute", "period", NULL};
    PyObject *hour, *minute, *period;
    int h, m, p;
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OOO:time_from_display", names, &hour, &minute,
                                     &period) ||
        bounded(hour, "hour", 1, 12, &h) < 0 || bounded(minute, "minute", 0, 59, &m) < 0 ||
        bounded(period, "period", 0, 1, &p) < 0)
        return NULL;
    return Py_BuildValue("(ii)", h % 12 + p * 12, m);
}

static PyObject *step_time(PyObject *self, PyObject *args, PyObject *kwargs) {
    static char *names[] = {"hour", "minute", "column", "steps", "use_12_hour", NULL};
    PyObject *hour, *minute, *column, *steps, *use_12_hour = NULL, *exact, *modulus, *remainder;
    int h, m, c, twelve, amount, count, display;
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OOOO|O:time_step_time", names, &hour, &minute,
                                     &column, &steps, &use_12_hour) ||
        parts(hour, minute, &h, &m) < 0 || mode(use_12_hour, &twelve) < 0 ||
        bounded(column, "column", 0, twelve ? 2 : 1, &c) < 0 || integer(steps, "steps") < 0)
        return NULL;
    /* PyNumber_Index returns an exact int: subclasses cannot change arithmetic. */
    exact = PyNumber_Index(steps);
    if (!exact)
        return NULL;
    if (c == 2) {
        PyObject *zero = PyLong_FromLong(0);
        int positive, negative;
        if (!zero) {
            Py_DECREF(exact);
            return NULL;
        }
        positive = PyObject_RichCompareBool(exact, zero, Py_GT);
        negative = PyObject_RichCompareBool(exact, zero, Py_LT);
        Py_DECREF(zero);
        Py_DECREF(exact);
        if (positive < 0 || negative < 0)
            return NULL;
        h = h % 12 + (positive ? 1 : negative ? 0 : h >= 12) * 12;
    } else {
        count = c == 1 ? 60 : twelve ? 12 : 24;
        modulus = PyLong_FromLong(count);
        if (!modulus) {
            Py_DECREF(exact);
            return NULL;
        }
        remainder = PyNumber_Remainder(exact, modulus);
        Py_DECREF(exact);
        Py_DECREF(modulus);
        if (!remainder)
            return NULL;
        amount = (int)PyLong_AsLong(remainder);
        Py_DECREF(remainder);
        if (PyErr_Occurred())
            return NULL;
        if (c == 1)
            m = (m + amount) % 60;
        else if (twelve) {
            display = h % 12 ? h % 12 : 12;
            display = (display - 1 + amount) % 12 + 1;
            h = display % 12 + (h >= 12) * 12;
        } else
            h = (h + amount) % 24;
    }
    return Py_BuildValue("(ii)", h, m);
}

static PyObject *column_values(PyObject *self, PyObject *args, PyObject *kwargs) {
    static char *names[] = {"hour", "minute", "column", "radius", "use_12_hour", NULL};
    PyObject *hour, *minute, *column, *radius = NULL, *use_12_hour = NULL, *result;
    int h, m, c, r = 4, twelve, center, lower, count, i;
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OOO|OO:time_column_values", names, &hour,
                                     &minute, &column, &radius, &use_12_hour) ||
        parts(hour, minute, &h, &m) < 0 || mode(use_12_hour, &twelve) < 0 ||
        bounded(column, "column", 0, twelve ? 2 : 1, &c) < 0 ||
        (radius && bounded(radius, "radius", 0, 100, &r) < 0))
        return NULL;
    center = c == 2 ? h >= 12 : c == 1 ? m : twelve ? (h % 12 ? h % 12 : 12) : h;
    lower = c == 0 && twelve ? 1 : 0;
    count = c == 1 ? 60 : twelve ? 12 : 24;
    result = PyTuple_New(2 * r + 1);
    if (!result)
        return NULL;
    for (i = 0; i < 2 * r + 1; ++i) {
        int value = center + i - r;
        PyObject *item;
        if (c == 2 && (value < 0 || value > 1))
            item = Py_NewRef(Py_None);
        else
            item = PyLong_FromLong(c == 2 ? value : wrap(value - lower, count) + lower);
        if (!item) {
            Py_DECREF(result);
            return NULL;
        }
        PyTuple_SET_ITEM(result, i, item);
    }
    return result;
}

#define TIME_METHOD(name)                                                                          \
    {"time_" #name, (PyCFunction)(void (*)(void))name, METH_VARARGS | METH_KEYWORDS,               \
     "Validated time-wheel policy."}
static PyMethodDef methods[] = {TIME_METHOD(validate_time), TIME_METHOD(display_time),
                                TIME_METHOD(from_display),  TIME_METHOD(step_time),
                                TIME_METHOD(column_values), {NULL, NULL, 0, NULL}};

int fluentpy_add_time_methods(PyObject *module) {
    return PyModule_AddFunctions(module, methods);
}
