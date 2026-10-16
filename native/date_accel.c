/* Gregorian date arithmetic for FluentPy. SPDX-License-Identifier: MIT
 *
 * All calendar decisions live here. Dates use years 1..9999; bounds are
 * complete inclusive dates. Wheel columns are independent: years clamp,
 * months and days wrap inside the current column's permitted interval.
 */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "date_accel.h"

typedef struct {
    int year;
    int month;
    int day;
} Date;

typedef struct {
    Date minimum;
    Date maximum;
} DateRange;

static int
month_length(int year, int month)
{
    static const int lengths[] = {31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31};
    return lengths[month - 1] +
        (month == 2 && year % 4 == 0 && (year % 100 != 0 || year % 400 == 0));
}

static int
compare_dates(Date left, Date right)
{
    if (left.year != right.year) {
        return left.year < right.year ? -1 : 1;
    }
    if (left.month != right.month) {
        return left.month < right.month ? -1 : 1;
    }
    return (left.day > right.day) - (left.day < right.day);
}

static int
require_integer(PyObject *value, const char *name)
{
    if (!PyLong_Check(value) || PyBool_Check(value)) {
        PyErr_Format(PyExc_TypeError, "%s must be an int, not bool or another type", name);
        return -1;
    }
    return 0;
}

static int
bounded_integer(PyObject *value, const char *name, int minimum, int maximum, int *result)
{
    int overflow = 0;
    long number;
    if (require_integer(value, name) < 0) {
        return -1;
    }
    number = PyLong_AsLongAndOverflow(value, &overflow);
    if (PyErr_Occurred()) {
        return -1;
    }
    if (overflow || number < minimum || number > maximum) {
        PyErr_Format(PyExc_ValueError, "%s must be between %d and %d", name, minimum, maximum);
        return -1;
    }
    *result = (int)number;
    return 0;
}

static int
clamped_day(PyObject *value, int maximum, int *result)
{
    int overflow = 0;
    long number;
    if (require_integer(value, "day") < 0) {
        return -1;
    }
    number = PyLong_AsLongAndOverflow(value, &overflow);
    if (PyErr_Occurred()) {
        return -1;
    }
    if (overflow < 0 || (!overflow && number < 1)) {
        *result = 1;
    } else if (overflow > 0 || number > maximum) {
        *result = maximum;
    } else {
        *result = (int)number;
    }
    return 0;
}

static int
parse_bound(PyObject *value, const char *name, Date *result)
{
    PyObject *sequence = PySequence_Fast(value, "date bounds must contain year, month, and day");
    int status = -1;
    if (sequence == NULL) {
        return -1;
    }
    if (PySequence_Fast_GET_SIZE(sequence) != 3) {
        PyErr_Format(PyExc_ValueError, "%s must contain exactly three date integers", name);
        goto done;
    }
    if (bounded_integer(PySequence_Fast_GET_ITEM(sequence, 0), "bound year", 1, 9999, &result->year) < 0 ||
            bounded_integer(PySequence_Fast_GET_ITEM(sequence, 1), "bound month", 1, 12, &result->month) < 0 ||
            bounded_integer(PySequence_Fast_GET_ITEM(sequence, 2), "bound day", 1,
                month_length(result->year, result->month), &result->day) < 0) {
        goto done;
    }
    status = 0;
done:
    Py_DECREF(sequence);
    return status;
}

static int
parse_range(PyObject *minimum, PyObject *maximum, DateRange *range)
{
    range->minimum = (Date){1, 1, 1};
    range->maximum = (Date){9999, 12, 31};
    if ((minimum != NULL && parse_bound(minimum, "minimum", &range->minimum) < 0) ||
            (maximum != NULL && parse_bound(maximum, "maximum", &range->maximum) < 0)) {
        return -1;
    }
    if (compare_dates(range->minimum, range->maximum) > 0) {
        PyErr_SetString(PyExc_ValueError, "minimum date must not be after maximum date");
        return -1;
    }
    return 0;
}

static Date
clamp_to_range(Date date, const DateRange *range)
{
    int last_day = month_length(date.year, date.month);
    if (date.day > last_day) {
        date.day = last_day;
    }
    if (compare_dates(date, range->minimum) < 0) {
        return range->minimum;
    }
    if (compare_dates(date, range->maximum) > 0) {
        return range->maximum;
    }
    return date;
}

static int
parse_date(PyObject *year, PyObject *month, PyObject *day,
        PyObject *minimum, PyObject *maximum, Date *date, DateRange *range)
{
    if (bounded_integer(year, "year", 1, 9999, &date->year) < 0 ||
            bounded_integer(month, "month", 1, 12, &date->month) < 0 ||
            clamped_day(day, month_length(date->year, date->month), &date->day) < 0 ||
            parse_range(minimum, maximum, range) < 0) {
        return -1;
    }
    *date = clamp_to_range(*date, range);
    return 0;
}

static void
column_interval(Date date, const DateRange *range, int column, int *minimum, int *maximum)
{
    if (column == 0) {
        *minimum = range->minimum.year;
        *maximum = range->maximum.year;
    } else if (column == 1) {
        *minimum = date.year == range->minimum.year ? range->minimum.month : 1;
        *maximum = date.year == range->maximum.year ? range->maximum.month : 12;
    } else {
        *minimum = date.year == range->minimum.year && date.month == range->minimum.month
            ? range->minimum.day : 1;
        *maximum = date.year == range->maximum.year && date.month == range->maximum.month
            ? range->maximum.day : month_length(date.year, date.month);
    }
}

static int
column_value(Date date, int column)
{
    return column == 0 ? date.year : column == 1 ? date.month : date.day;
}

static int
wrapped_value(int value, int offset, int minimum, int maximum)
{
    int width = maximum - minimum + 1;
    int position = (value - minimum + offset) % width;
    return minimum + (position < 0 ? position + width : position);
}

static PyObject *
date_days_in_month(PyObject *module, PyObject *args, PyObject *kwargs)
{
    static char *keywords[] = {"year", "month", NULL};
    PyObject *year_object, *month_object;
    int year, month;
    (void)module;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OO:date_days_in_month", keywords,
            &year_object, &month_object) ||
            bounded_integer(year_object, "year", 1, 9999, &year) < 0 ||
            bounded_integer(month_object, "month", 1, 12, &month) < 0) {
        return NULL;
    }
    return PyLong_FromLong(month_length(year, month));
}

static PyObject *
date_clamp_date(PyObject *module, PyObject *args, PyObject *kwargs)
{
    static char *keywords[] = {"year", "month", "day", "minimum", "maximum", NULL};
    PyObject *year, *month, *day, *minimum = NULL, *maximum = NULL;
    Date date;
    DateRange range;
    (void)module;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OOO|OO:date_clamp_date", keywords,
            &year, &month, &day, &minimum, &maximum) ||
            parse_date(year, month, day, minimum, maximum, &date, &range) < 0) {
        return NULL;
    }
    return Py_BuildValue("(iii)", date.year, date.month, date.day);
}

static PyObject *
date_step_date(PyObject *module, PyObject *args, PyObject *kwargs)
{
    static char *keywords[] = {"year", "month", "day", "column", "steps", "minimum", "maximum", NULL};
    PyObject *year, *month, *day, *column_object, *steps_object;
    PyObject *minimum_object = NULL, *maximum_object = NULL;
    Date date;
    DateRange range;
    int column, minimum, maximum;
    (void)module;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OOOOO|OO:date_step_date", keywords,
            &year, &month, &day, &column_object, &steps_object, &minimum_object, &maximum_object) ||
            bounded_integer(column_object, "column", 0, 2, &column) < 0 ||
            require_integer(steps_object, "steps") < 0 ||
            parse_date(year, month, day, minimum_object, maximum_object, &date, &range) < 0) {
        return NULL;
    }
    column_interval(date, &range, column, &minimum, &maximum);
    if (column == 0) {
        int overflow = 0;
        long steps = PyLong_AsLongAndOverflow(steps_object, &overflow);
        if (PyErr_Occurred()) {
            return NULL;
        }
        /* Compare before adding so even a machine-sized extreme cannot overflow. */
        if (overflow < 0 || (!overflow && steps < minimum - date.year)) {
            date.year = minimum;
        } else if (overflow > 0 || steps > maximum - date.year) {
            date.year = maximum;
        } else {
            date.year += (int)steps;
        }
    } else {
        PyObject *width = PyLong_FromLong(maximum - minimum + 1);
        PyObject *integer = NULL, *remainder = NULL;
        int offset;
        if (width == NULL) {
            return NULL;
        }
        /* PyNumber_Index normalizes int subclasses before modulo, preventing
         * subclass arithmetic overrides from entering calendar calculations. */
        integer = PyNumber_Index(steps_object);
        if (integer != NULL) {
            remainder = PyNumber_Remainder(integer, width);
        }
        Py_XDECREF(integer);
        Py_DECREF(width);
        if (remainder == NULL) {
            return NULL;
        }
        offset = (int)PyLong_AsLong(remainder);
        Py_DECREF(remainder);
        if (PyErr_Occurred()) {
            return NULL;
        }
        if (column == 1) {
            date.month = wrapped_value(date.month, offset, minimum, maximum);
        } else {
            date.day = wrapped_value(date.day, offset, minimum, maximum);
        }
    }
    date = clamp_to_range(date, &range);
    return Py_BuildValue("(iii)", date.year, date.month, date.day);
}

static PyObject *
date_column_values(PyObject *module, PyObject *args, PyObject *kwargs)
{
    static char *keywords[] = {"year", "month", "day", "column", "radius", "minimum", "maximum", NULL};
    PyObject *year, *month, *day, *column_object, *radius_object = NULL;
    PyObject *minimum_object = NULL, *maximum_object = NULL, *values;
    Date date;
    DateRange range;
    int column, radius = 4, minimum, maximum, current, index;
    (void)module;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OOOO|OOO:date_column_values", keywords,
            &year, &month, &day, &column_object, &radius_object, &minimum_object, &maximum_object) ||
            bounded_integer(column_object, "column", 0, 2, &column) < 0 ||
            (radius_object != NULL && bounded_integer(radius_object, "radius", 0, 100, &radius) < 0) ||
            parse_date(year, month, day, minimum_object, maximum_object, &date, &range) < 0) {
        return NULL;
    }
    column_interval(date, &range, column, &minimum, &maximum);
    current = column_value(date, column);
    values = PyTuple_New(2 * radius + 1);
    if (values == NULL) {
        return NULL;
    }
    for (index = 0; index < 2 * radius + 1; ++index) {
        int offset = index - radius;
        PyObject *value;
        if ((column == 0 && (current + offset < minimum || current + offset > maximum)) ||
                (minimum == maximum && offset != 0)) {
            value = Py_None;
            Py_INCREF(value);
        } else {
            value = PyLong_FromLong(column == 0 ? current + offset :
                wrapped_value(current, offset, minimum, maximum));
            if (value == NULL) {
                Py_DECREF(values);
                return NULL;
            }
        }
        PyTuple_SET_ITEM(values, index, value);
    }
    return values;
}

static PyMethodDef date_methods[] = {
    {"date_days_in_month", (PyCFunction)(void (*)(void))date_days_in_month,
        METH_VARARGS | METH_KEYWORDS, "Return the Gregorian month length for years 1..9999."},
    {"date_clamp_date", (PyCFunction)(void (*)(void))date_clamp_date,
        METH_VARARGS | METH_KEYWORDS, "Clamp a Gregorian date to an inclusive date range."},
    {"date_step_date", (PyCFunction)(void (*)(void))date_step_date,
        METH_VARARGS | METH_KEYWORDS, "Step one independent year, month, or day wheel column."},
    {"date_column_values", (PyCFunction)(void (*)(void))date_column_values,
        METH_VARARGS | METH_KEYWORDS, "Return centered date-wheel values and empty boundary rows."},
    {NULL, NULL, 0, NULL}
};

int
fluentpy_add_date_methods(PyObject *module)
{
    return PyModule_AddFunctions(module, date_methods);
}
