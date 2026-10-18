/* Independent bounded sRGB/HSV conversion and Qt-order hexadecimal parsing. MIT. */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <math.h>
#include "color_accel.h"

static int channel(PyObject *object, const char *name, int *result) {
    long value;
    if (!PyLong_Check(object) || PyBool_Check(object)) {
        PyErr_Format(PyExc_TypeError, "%s must be an int", name); return -1;
    }
    value = PyLong_AsLong(object);
    if (PyErr_Occurred()) { PyErr_Clear(); value = -1; }
    if (value < 0 || value > 255) {
        PyErr_Format(PyExc_ValueError, "%s must be between 0 and 255", name); return -1;
    }
    *result = (int)value;
    return 0;
}

static int number(PyObject *object, const char *name, double low, double high, double *out) {
    if (PyBool_Check(object) || (!PyFloat_Check(object) && !PyLong_Check(object))) {
        PyErr_Format(PyExc_TypeError, "%s must be a number", name); return -1;
    }
    *out = PyFloat_AsDouble(object);
    if (PyErr_Occurred()) { PyErr_Clear(); *out = -HUGE_VAL; }
    if (!isfinite(*out) || *out < low || *out > high) {
        PyErr_Format(PyExc_ValueError, "%s is outside its valid range", name); return -1;
    }
    return 0;
}

static PyObject *parse_hex(PyObject *self, PyObject *args, PyObject *kwargs) {
    static char *names[] = {"text", NULL};
    PyObject *object;
    const char *text;
    Py_ssize_t length, i;
    unsigned int value = 0;
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O:color_parse_hex", names, &object)) return NULL;
    if (!PyUnicode_Check(object)) { PyErr_SetString(PyExc_TypeError, "text must be a string"); return NULL; }
    text = PyUnicode_AsUTF8AndSize(object, &length);
    if (!text) { PyErr_Clear(); goto invalid; }
    if (length && text[0] == '#') { text++; length--; }
    if (length != 3 && length != 6 && length != 8) goto invalid;
    for (i = 0; i < length; ++i) {
        int digit = text[i] >= '0' && text[i] <= '9' ? text[i] - '0' :
                    text[i] >= 'a' && text[i] <= 'f' ? text[i] - 'a' + 10 :
                    text[i] >= 'A' && text[i] <= 'F' ? text[i] - 'A' + 10 : -1;
        if (digit < 0) goto invalid;
        value = (value << (length == 3 ? 8 : 4)) | (unsigned int)(length == 3 ? digit * 17 : digit);
    }
    return Py_BuildValue("(iiii)", (value >> 16) & 255, (value >> 8) & 255, value & 255,
                         length == 8 ? (value >> 24) & 255 : 255);
invalid:
    PyErr_SetString(PyExc_ValueError, "expected #RGB, #RRGGBB or #AARRGGBB");
    return NULL;
}

static PyObject *format_hex(PyObject *self, PyObject *args, PyObject *kwargs) {
    static char *names[] = {"red", "green", "blue", "alpha", "include_alpha", NULL};
    PyObject *r, *g, *b, *a = NULL, *include = Py_False;
    int red, green, blue, alpha = 255;
    char text[10];
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OOO|OO:color_format_hex", names, &r, &g, &b, &a, &include) ||
        channel(r, "red", &red) < 0 || channel(g, "green", &green) < 0 || channel(b, "blue", &blue) < 0 ||
        (a && channel(a, "alpha", &alpha) < 0)) return NULL;
    if (!PyBool_Check(include)) { PyErr_SetString(PyExc_TypeError, "include_alpha must be a bool"); return NULL; }
    if (include == Py_True) PyOS_snprintf(text, sizeof(text), "#%02x%02x%02x%02x", alpha, red, green, blue);
    else PyOS_snprintf(text, sizeof(text), "#%02x%02x%02x", red, green, blue);
    return PyUnicode_FromString(text);
}

static PyObject *rgb_to_hsv(PyObject *self, PyObject *args, PyObject *kwargs) {
    static char *names[] = {"red", "green", "blue", NULL};
    PyObject *r, *g, *b;
    int ri, gi, bi;
    double red, green, blue, maximum, minimum, delta, hue;
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OOO:color_rgb_to_hsv", names, &r, &g, &b) ||
        channel(r, "red", &ri) < 0 || channel(g, "green", &gi) < 0 || channel(b, "blue", &bi) < 0) return NULL;
    red = ri / 255.0; green = gi / 255.0; blue = bi / 255.0;
    maximum = fmax(red, fmax(green, blue)); minimum = fmin(red, fmin(green, blue)); delta = maximum - minimum;
    if (delta == 0) hue = -1.0;
    else if (maximum == red) { hue = fmod((green - blue) / delta, 6.0) * 60; if (hue < 0) hue += 360; }
    else if (maximum == green) hue = ((blue - red) / delta + 2) * 60;
    else hue = ((red - green) / delta + 4) * 60;
    return Py_BuildValue("(ddd)", hue, maximum ? delta / maximum : 0.0, maximum);
}

static PyObject *hsv_to_rgba(PyObject *self, PyObject *args, PyObject *kwargs) {
    static char *names[] = {"hue", "saturation", "value", "alpha", NULL};
    PyObject *h, *s, *v, *a = NULL;
    int alpha = 255, sector, red, green, blue;
    double hue, saturation, value, c, x, m, channels[3];
    (void)self;
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "OOO|O:color_hsv_to_rgba", names, &h, &s, &v, &a) ||
        number(h, "hue", 0, 360, &hue) < 0 || number(s, "saturation", 0, 1, &saturation) < 0 ||
        number(v, "value", 0, 1, &value) < 0 || (a && channel(a, "alpha", &alpha) < 0)) return NULL;
    hue /= 60; c = value * saturation; x = c * (1 - fabs(fmod(hue, 2) - 1)); m = value - c;
    sector = (int)hue % 6;
    switch (sector) {
        case 0: channels[0]=c; channels[1]=x; channels[2]=0; break;
        case 1: channels[0]=x; channels[1]=c; channels[2]=0; break;
        case 2: channels[0]=0; channels[1]=c; channels[2]=x; break;
        case 3: channels[0]=0; channels[1]=x; channels[2]=c; break;
        case 4: channels[0]=x; channels[1]=0; channels[2]=c; break;
        default: channels[0]=c; channels[1]=0; channels[2]=x; break;
    }
    red = (int)floor((channels[0] + m) * 255 + .5);
    green = (int)floor((channels[1] + m) * 255 + .5);
    blue = (int)floor((channels[2] + m) * 255 + .5);
    return Py_BuildValue("(iiii)", red, green, blue, alpha);
}

#define COLOR_METHOD(name) {"color_" #name, (PyCFunction)(void(*)(void))name, METH_VARARGS | METH_KEYWORDS, "Validated color policy."}
static PyMethodDef methods[] = {
    COLOR_METHOD(parse_hex), COLOR_METHOD(format_hex), COLOR_METHOD(rgb_to_hsv), COLOR_METHOD(hsv_to_rgba),
    {NULL, NULL, 0, NULL}
};
int fluentpy_add_color_methods(PyObject *module) { return PyModule_AddFunctions(module, methods); }
