/* Gregorian date arithmetic for FluentPy. SPDX-License-Identifier: MIT */
#ifndef FLUENTPY_DATE_ACCEL_H
#define FLUENTPY_DATE_ACCEL_H

#include <Python.h>

/* Add the date functions to the existing fluentpy._native module. */
int fluentpy_add_date_methods(PyObject *module);

#endif
