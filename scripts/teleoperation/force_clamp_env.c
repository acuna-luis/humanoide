#define _GNU_SOURCE

#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
 * Work around a ubt-controller 5.3.0 defect: when PICO teleoperation starts
 * without gloves, websocket_server.collect() overwrites arm=clamp with
 * arm=gripper and then PicoPublisher reloads the wrong kinematic matrices.
 *
 * This preload is deliberately narrow.  It changes only the exact attempted
 * assignment arm=gripper to arm=clamp and leaves every other environment
 * operation untouched.
 */

typedef int (*setenv_fn)(const char *, const char *, int);
typedef int (*putenv_fn)(char *);
typedef struct _object PyObject;
typedef int (*pyobject_setitem_fn)(PyObject *, PyObject *, PyObject *);
typedef const char *(*pyunicode_asutf8_fn)(PyObject *);
typedef PyObject *(*pyunicode_fromstring_fn)(const char *);
typedef void (*py_decref_fn)(PyObject *);

struct pyobject_head {
    long ob_refcnt;
    void *ob_type;
};

static setenv_fn real_setenv(void)
{
    static setenv_fn fn;
    if (fn == NULL) {
        fn = (setenv_fn)dlsym(RTLD_NEXT, "setenv");
    }
    return fn;
}

static putenv_fn real_putenv(void)
{
    static putenv_fn fn;
    if (fn == NULL) {
        fn = (putenv_fn)dlsym(RTLD_NEXT, "putenv");
    }
    return fn;
}

int setenv(const char *name, const char *value, int overwrite)
{
    setenv_fn fn = real_setenv();
    if (fn == NULL) {
        return -1;
    }

    if (strcmp(name, "arm") == 0 && strcmp(value, "gripper") == 0) {
        fputs("CRUZR_CLAMP_GUARD: remapped arm=gripper to arm=clamp\n", stderr);
        return fn(name, "clamp", overwrite);
    }
    return fn(name, value, overwrite);
}

int putenv(char *string)
{
    putenv_fn fn = real_putenv();
    static char clamp_assignment[] = "arm=clamp";
    if (fn == NULL) {
        return -1;
    }

    if (strcmp(string, "arm=gripper") == 0) {
        fputs("CRUZR_CLAMP_GUARD: remapped arm=gripper to arm=clamp\n", stderr);
        return fn(clamp_assignment);
    }
    return fn(string);
}

/*
 * CPython mirrors os.environ in a Python dictionary before calling setenv().
 * Therefore libc interposition alone fixes the process environment but not
 * the value later read by os.getenv().  Intercept the exact Python assignment
 * too.  No robot API, heartbeat or watchdog behavior is changed.
 */
int PyObject_SetItem(PyObject *object, PyObject *key, PyObject *value)
{
    static pyobject_setitem_fn real_fn;
    static pyunicode_asutf8_fn as_utf8;
    static pyunicode_fromstring_fn from_string;
    static py_decref_fn decref;
    void *unicode_type;
    struct pyobject_head *key_head = (struct pyobject_head *)key;
    struct pyobject_head *value_head = (struct pyobject_head *)value;

    if (real_fn == NULL) {
        real_fn = (pyobject_setitem_fn)dlsym(RTLD_NEXT, "PyObject_SetItem");
        as_utf8 = (pyunicode_asutf8_fn)dlsym(RTLD_NEXT, "PyUnicode_AsUTF8");
        from_string =
            (pyunicode_fromstring_fn)dlsym(RTLD_NEXT, "PyUnicode_FromString");
        decref = (py_decref_fn)dlsym(RTLD_NEXT, "Py_DecRef");
    }
    if (real_fn == NULL) {
        return -1;
    }

    unicode_type = dlsym(RTLD_DEFAULT, "PyUnicode_Type");
    if (unicode_type != NULL && as_utf8 != NULL && from_string != NULL &&
        key_head != NULL && value_head != NULL &&
        key_head->ob_type == unicode_type && value_head->ob_type == unicode_type) {
        const char *key_text = as_utf8(key);
        const char *value_text = as_utf8(value);
        if (key_text != NULL && value_text != NULL &&
            strcmp(key_text, "arm") == 0 && strcmp(value_text, "gripper") == 0) {
            PyObject *replacement = from_string("clamp");
            int result;
            if (replacement == NULL) {
                return -1;
            }
            fputs("CRUZR_CLAMP_GUARD: remapped Python arm=gripper to arm=clamp\n",
                  stderr);
            result = real_fn(object, key, replacement);
            if (decref != NULL) {
                decref(replacement);
            }
            return result;
        }
    }

    return real_fn(object, key, value);
}
