/* Gregorian calendar and second-precision wheel policies. SPDX-License-Identifier: MIT */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "calendar_accel.h"

static int bounded(PyObject *obj, const char *name, int lo, int hi, int *out) {
    int overflow = 0;
    long v;
    if (!PyLong_Check(obj) || PyBool_Check(obj)) {
        PyErr_Format(PyExc_TypeError, "%s must be an int, not bool or another type", name);
        return -1;
    }
    v = PyLong_AsLongAndOverflow(obj, &overflow);
    if (overflow || v < lo || v > hi) {
        PyErr_Format(PyExc_ValueError, "%s must be between %d and %d", name, lo, hi);
        return -1;
    }
    if (PyErr_Occurred())
        return -1;
    *out = (int)v;
    return 0;
}
static int month_length(int y, int m) {
    static const int lengths[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    return lengths[m - 1] + (m == 2 && y % 4 == 0 && (y % 100 != 0 || y % 400 == 0));
}
static int ordinal(const int *p) {
    int y = p[0] - 1, n = 365 * y + y / 4 - y / 100 + y / 400 + p[2];
    for (int m = 1; m < p[1]; ++m)
        n += month_length(p[0], m);
    return n;
}
static void from_ordinal(int n, int *p) {
    int lo = 1, hi = 9999, first[3] = {1, 1, 1};
    while (lo < hi) {
        int mid = (lo + hi + 1) / 2;
        first[0] = mid;
        if (ordinal(first) <= n)
            lo = mid;
        else
            hi = mid - 1;
    }
    p[0] = lo;
    first[0] = lo;
    n -= ordinal(first) - 1;
    p[1] = 1;
    while (n > month_length(lo, p[1]))
        n -= month_length(lo, p[1]++);
    p[2] = n;
}
static PyObject *parts_tuple(const int *p, int size) {
    PyObject *result = PyTuple_New(size);
    if (!result)
        return NULL;
    for (int i = 0; i < size; ++i) {
        PyObject *v = PyLong_FromLong(p[i]);
        if (!v) {
            Py_DECREF(result);
            return NULL;
        }
        PyTuple_SET_ITEM(result, i, v);
    }
    return result;
}
static int parse_parts(PyObject *obj, const char *name, int size, int *p) {
    static const char *names[] = {"year", "month", "day", "hour", "minute", "second"};
    static const int lower[] = {1, 1, 1, 0, 0, 0}, upper[] = {9999, 12, 31, 23, 59, 59};
    PyObject *seq = PySequence_Fast(obj, "date must be a sequence");
    if (!seq)
        return -1;
    if (PySequence_Fast_GET_SIZE(seq) != size) {
        PyErr_Format(PyExc_ValueError, "%s must contain %d parts", name, size);
        Py_DECREF(seq);
        return -1;
    }
    for (int i = 0; i < size; ++i) {
        if (bounded(PySequence_Fast_GET_ITEM(seq, i), names[i], lower[i], upper[i], &p[i]) < 0) {
            Py_DECREF(seq);
            return -1;
        }
    }
    Py_DECREF(seq);
    if (p[2] > month_length(p[0], p[1])) {
        PyErr_SetString(PyExc_ValueError, "day is out of range for month");
        return -1;
    }
    return 0;
}
static int compare(const int *a, const int *b, int size) {
    for (int i = 0; i < size; ++i)
        if (a[i] != b[i])
            return a[i] < b[i] ? -1 : 1;
    return 0;
}
static PyObject *normalized_list(PyObject *obj, int dates) {
    PyObject *seq = obj ? PySequence_Fast(obj, "disabled values must be iterable") : PyTuple_New(0),
             *set, *list, *result;
    if (!seq)
        return NULL;
    set = PySet_New(NULL);
    if (!set) {
        Py_DECREF(seq);
        return NULL;
    }
    for (Py_ssize_t i = 0; i < PySequence_Fast_GET_SIZE(seq); ++i) {
        PyObject *item = PySequence_Fast_GET_ITEM(seq, i), *value;
        int p[3], weekday;
        if (dates) {
            if (parse_parts(item, "disabled date", 3, p) < 0)
                goto fail;
            value = parts_tuple(p, 3);
        } else {
            if (bounded(item, "weekday", 0, 6, &weekday) < 0)
                goto fail;
            value = PyLong_FromLong(weekday);
        }
        if (!value)
            goto fail;
        int status = PySet_Add(set, value);
        Py_DECREF(value);
        if (status < 0)
            goto fail;
    }
    list = PySequence_List(set);
    if (!list)
        goto fail;
    if (PyList_Sort(list) < 0) {
        Py_DECREF(list);
        goto fail;
    }
    result = PyList_AsTuple(list);
    Py_DECREF(list);
    Py_DECREF(set);
    Py_DECREF(seq);
    return result;
fail:
    Py_DECREF(set);
    Py_DECREF(seq);
    return NULL;
}
static PyObject *rules(PyObject *minimum, PyObject *maximum, PyObject *weekdays, PyObject *dates) {
    int lo[3] = {1, 1, 1}, hi[3] = {9999, 12, 31};
    if ((minimum && parse_parts(minimum, "minimum", 3, lo) < 0) ||
        (maximum && parse_parts(maximum, "maximum", 3, hi) < 0))
        return NULL;
    if (compare(lo, hi, 3) > 0) {
        PyErr_SetString(PyExc_ValueError, "minimum must not be after maximum");
        return NULL;
    }
    PyObject *a = parts_tuple(lo, 3), *b = parts_tuple(hi, 3), *w = normalized_list(weekdays, 0),
             *d = normalized_list(dates, 1), *result = NULL;
    if (a && b && w && d)
        result = PyTuple_Pack(4, a, b, w, d);
    Py_XDECREF(a);
    Py_XDECREF(b);
    Py_XDECREF(w);
    Py_XDECREF(d);
    return result;
}
static int enabled(const int *p, PyObject *r) {
    PyObject *value = parts_tuple(p, 3), *weekday = PyLong_FromLong((ordinal(p) - 1) % 7);
    if (!value || !weekday) {
        Py_XDECREF(value);
        Py_XDECREF(weekday);
        return -1;
    }
    int low = PyObject_RichCompareBool(value, PyTuple_GET_ITEM(r, 0), Py_GE);
    int high = PyObject_RichCompareBool(value, PyTuple_GET_ITEM(r, 1), Py_LE);
    int w = PySequence_Contains(PyTuple_GET_ITEM(r, 2), weekday),
        d = PySequence_Contains(PyTuple_GET_ITEM(r, 3), value);
    Py_DECREF(value);
    Py_DECREF(weekday);
    return low < 0 || high < 0 || w < 0 || d < 0 ? -1 : low && high && !w && !d;
}
static PyObject *validate_rules(PyObject *self, PyObject *args, PyObject *kw) {
    static char *names[] = {"minimum", "maximum", "disabled_weekdays", "disabled_dates", NULL};
    PyObject *lo = NULL, *hi = NULL, *w = NULL, *d = NULL;
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kw, "|OOOO:calendar_validate_rules", names, &lo, &hi, &w,
                                     &d))
        return NULL;
    return rules(lo, hi, w, d);
}
static PyObject *is_selectable(PyObject *self, PyObject *args, PyObject *kw) {
    static char *names[] = {"value",          "minimum", "maximum", "disabled_weekdays",
                            "disabled_dates", NULL};
    PyObject *value, *lo = NULL, *hi = NULL, *w = NULL, *d = NULL, *r;
    int p[3], ok;
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kw, "O|OOOO:calendar_is_selectable", names, &value, &lo,
                                     &hi, &w, &d) ||
        parse_parts(value, "date", 3, p) < 0)
        return NULL;
    r = rules(lo, hi, w, d);
    if (!r)
        return NULL;
    ok = enabled(p, r);
    Py_DECREF(r);
    return ok < 0 ? NULL : PyBool_FromLong(ok);
}
static PyObject *month_cells(PyObject *self, PyObject *args, PyObject *kw) {
    static char *names[] = {
        "year",           "month",         "minimum", "maximum", "disabled_weekdays",
        "disabled_dates", "first_weekday", NULL};
    PyObject *year, *month, *lo = NULL, *hi = NULL, *w = NULL, *d = NULL, *first = NULL, *r,
                            *result;
    int p[3], weekday = 0;
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kw, "OO|OOOOO:calendar_month_cells", names, &year,
                                     &month, &lo, &hi, &w, &d, &first) ||
        bounded(year, "year", 1, 9999, &p[0]) < 0 || bounded(month, "month", 1, 12, &p[1]) < 0 ||
        (first && bounded(first, "first_weekday", 0, 6, &weekday) < 0))
        return NULL;
    r = rules(lo, hi, w, d);
    if (!r)
        return NULL;
    p[2] = 1;
    int start = ordinal(p);
    start -= ((start - 1) % 7 - weekday + 7) % 7;
    result = PyTuple_New(42);
    if (!result) {
        Py_DECREF(r);
        return NULL;
    }
    for (int i = 0; i < 42; ++i) {
        int n = start + i;
        PyObject *item;
        if (n < 1 || n > 3652059)
            item = Py_NewRef(Py_None);
        else {
            from_ordinal(n, p);
            int ok = enabled(p, r);
            if (ok < 0) {
                Py_DECREF(result);
                Py_DECREF(r);
                return NULL;
            }
            item = Py_BuildValue("(iiiO)", p[0], p[1], p[2], ok ? Py_True : Py_False);
        }
        if (!item) {
            Py_DECREF(result);
            Py_DECREF(r);
            return NULL;
        }
        PyTuple_SET_ITEM(result, i, item);
    }
    Py_DECREF(r);
    return result;
}
static int long_integer(PyObject *obj, const char *name, long *result) {
    if (!PyLong_Check(obj) || PyBool_Check(obj)) {
        PyErr_Format(PyExc_TypeError, "%s must be an int", name);
        return -1;
    }
    *result = PyLong_AsLong(obj);
    return PyErr_Occurred() ? -1 : 0;
}
static PyObject *shift_date(PyObject *self, PyObject *args, PyObject *kw) {
    static char *names[] = {"value", "days", "months", NULL};
    PyObject *value, *days = NULL, *months = NULL;
    int p[3];
    long ds = 0, ms = 0;
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kw, "O|OO:calendar_shift_date", names, &value, &days,
                                     &months) ||
        parse_parts(value, "date", 3, p) < 0 || (days && long_integer(days, "days", &ds) < 0) ||
        (months && long_integer(months, "months", &ms) < 0))
        return NULL;
    int index = (p[0] - 1) * 12 + p[1] - 1;
    index = ms < -index ? 0 : ms > 119987 - index ? 119987 : index + (int)ms;
    p[0] = index / 12 + 1;
    p[1] = index % 12 + 1;
    if (p[2] > month_length(p[0], p[1]))
        p[2] = month_length(p[0], p[1]);
    int n = ordinal(p);
    n = ds < 1 - n ? 1 : ds > 3652059 - n ? 3652059 : n + (int)ds;
    from_ordinal(n, p);
    return parts_tuple(p, 3);
}
static PyObject *normalize_range(PyObject *self, PyObject *args, PyObject *kw) {
    static char *names[] = {"start",          "end", "minimum", "maximum", "disabled_weekdays",
                            "disabled_dates", NULL};
    PyObject *start, *end, *lo = NULL, *hi = NULL, *w = NULL, *d = NULL, *r, *a, *b, *result;
    int p[3], q[3];
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kw, "OO|OOOO:calendar_normalize_range", names, &start,
                                     &end, &lo, &hi, &w, &d) ||
        parse_parts(start, "start", 3, p) < 0 || parse_parts(end, "end", 3, q) < 0)
        return NULL;
    r = rules(lo, hi, w, d);
    if (!r)
        return NULL;
    int ea = enabled(p, r), eb = enabled(q, r);
    Py_DECREF(r);
    if (ea < 0 || eb < 0)
        return NULL;
    if (!ea || !eb) {
        PyErr_SetString(PyExc_ValueError, "range endpoints must be selectable");
        return NULL;
    }
    a = parts_tuple(compare(p, q, 3) <= 0 ? p : q, 3);
    b = parts_tuple(compare(p, q, 3) <= 0 ? q : p, 3);
    result = a && b ? PyTuple_Pack(2, a, b) : NULL;
    Py_XDECREF(a);
    Py_XDECREF(b);
    return result;
}
static PyObject *clamp_datetime(PyObject *self, PyObject *args, PyObject *kw) {
    static char *names[] = {"value", "minimum", "maximum", NULL};
    PyObject *value, *minimum = NULL, *maximum = NULL;
    int p[6], lo[6] = {1, 1, 1, 0, 0, 0}, hi[6] = {9999, 12, 31, 23, 59, 59};
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kw, "O|OO:calendar_clamp_datetime", names, &value,
                                     &minimum, &maximum) ||
        parse_parts(value, "date", 6, p) < 0 ||
        (minimum && parse_parts(minimum, "minimum", 6, lo) < 0) ||
        (maximum && parse_parts(maximum, "maximum", 6, hi) < 0))
        return NULL;
    if (compare(lo, hi, 6) > 0) {
        PyErr_SetString(PyExc_ValueError, "minimum must not be after maximum");
        return NULL;
    }
    return parts_tuple(compare(p, lo, 6) < 0 ? lo : compare(p, hi, 6) > 0 ? hi : p, 6);
}
static int time_parts(PyObject *hour, PyObject *minute, PyObject *second, PyObject *column, int *p,
                      int *c) {
    return bounded(hour, "hour", 0, 23, &p[0]) < 0 || bounded(minute, "minute", 0, 59, &p[1]) < 0 ||
                   bounded(second, "second", 0, 59, &p[2]) < 0 ||
                   bounded(column, "column", 0, 2, c) < 0
               ? -1
               : 0;
}
static PyObject *step_time(PyObject *self, PyObject *args, PyObject *kw) {
    static char *names[] = {"hour", "minute", "second", "column", "steps", NULL};
    PyObject *h, *m, *s, *col, *steps, *exact, *mod, *rem;
    int p[3], c;
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kw, "OOOOO:calendar_step_time", names, &h, &m, &s, &col,
                                     &steps) ||
        time_parts(h, m, s, col, p, &c) < 0)
        return NULL;
    if (!PyLong_Check(steps) || PyBool_Check(steps)) {
        PyErr_SetString(PyExc_TypeError, "steps must be an int");
        return NULL;
    }
    exact = PyNumber_Index(steps);
    if (!exact)
        return NULL;
    mod = PyLong_FromLong(c == 0 ? 24 : 60);
    if (!mod) {
        Py_DECREF(exact);
        return NULL;
    }
    rem = PyNumber_Remainder(exact, mod);
    Py_DECREF(exact);
    Py_DECREF(mod);
    if (!rem)
        return NULL;
    int amount = (int)PyLong_AsLong(rem);
    Py_DECREF(rem);
    if (PyErr_Occurred())
        return NULL;
    p[c] = (p[c] + amount) % (c == 0 ? 24 : 60);
    return parts_tuple(p, 3);
}
static PyObject *time_values(PyObject *self, PyObject *args, PyObject *kw) {
    static char *names[] = {"hour", "minute", "second", "column", "radius", NULL};
    PyObject *h, *m, *s, *col, *radius = NULL, *result;
    int p[3], c, r = 4;
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kw, "OOOO|O:calendar_time_values", names, &h, &m, &s,
                                     &col, &radius) ||
        time_parts(h, m, s, col, p, &c) < 0 ||
        (radius && bounded(radius, "radius", 0, 100, &r) < 0))
        return NULL;
    result = PyTuple_New(2 * r + 1);
    if (!result)
        return NULL;
    int count = c == 0 ? 24 : 60;
    for (int i = 0; i < 2 * r + 1; ++i) {
        int n = (p[c] + i - r) % count;
        PyObject *v = PyLong_FromLong(n < 0 ? n + count : n);
        if (!v) {
            Py_DECREF(result);
            return NULL;
        }
        PyTuple_SET_ITEM(result, i, v);
    }
    return result;
}
#define METHOD(name)                                                                               \
    {"calendar_" #name, (PyCFunction)(void (*)(void))name, METH_VARARGS | METH_KEYWORDS,           \
     "Validated Gregorian calendar policy."}
static PyMethodDef methods[] = {
    METHOD(validate_rules), METHOD(is_selectable),   METHOD(month_cells),
    METHOD(shift_date),     METHOD(normalize_range), METHOD(clamp_datetime),
    METHOD(step_time),      METHOD(time_values),     {NULL, NULL, 0, NULL}};
int fluentpy_add_calendar_methods(PyObject *module) {
    return PyModule_AddFunctions(module, methods);
}
