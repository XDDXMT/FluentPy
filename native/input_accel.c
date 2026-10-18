/* Bounded printable-code segmentation; compatible Python fallback is maintained. */
#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "input_accel.h"

static PyObject *split_code(PyObject *self,PyObject *args,PyObject *kwargs) {
    static char *names[]={"text","length","digits_only","truncate",NULL};
    PyObject *text,*length,*digits=Py_True,*truncate=Py_False,*result;
    Py_ssize_t count,i,n;
    (void)self;
    if(!PyArg_ParseTupleAndKeywords(args,kwargs,"OO|OO:input_split_code",names,&text,&length,&digits,&truncate))return NULL;
    if(!PyUnicode_Check(text)){PyErr_SetString(PyExc_TypeError,"text must be a string");return NULL;}
    if(!PyLong_Check(length)||PyBool_Check(length)){PyErr_SetString(PyExc_TypeError,"length must be an int");return NULL;}
    n=PyLong_AsSsize_t(length);
    if(PyErr_Occurred()){PyErr_Clear();n=-1;}
    if(n<1||n>32){PyErr_SetString(PyExc_ValueError,"length must be between 1 and 32");return NULL;}
    if(!PyBool_Check(digits)||!PyBool_Check(truncate)){PyErr_SetString(PyExc_TypeError,"digits_only and truncate must be bools");return NULL;}
    count=PyUnicode_GetLength(text);
    if(count>n&&truncate==Py_False){PyErr_SetString(PyExc_ValueError,"code is longer than length");return NULL;}
    for(i=0;i<count;i++){
        Py_UCS4 ch=PyUnicode_ReadChar(text,i);
        if((digits==Py_True&&(ch<'0'||ch>'9'))||(digits==Py_False&&!Py_UNICODE_ISPRINTABLE(ch))){
            PyErr_SetString(PyExc_ValueError,"code contains an invalid character");return NULL;
        }
    }
    result=PyTuple_New(n);if(!result)return NULL;
    for(i=0;i<n;i++){
        PyObject *cell=i<count?PyUnicode_Substring(text,i,i+1):PyUnicode_New(0,0);
        if(!cell){Py_DECREF(result);return NULL;}
        PyTuple_SET_ITEM(result,i,cell);
    }
    return result;
}
static PyMethodDef methods[]={
    {"input_split_code",(PyCFunction)(void(*)(void))split_code,METH_VARARGS|METH_KEYWORDS,"Validate and segment a bounded PIN/password."},
    {NULL,NULL,0,NULL}
};
int fluentpy_add_input_methods(PyObject *module){return PyModule_AddFunctions(module,methods);}
