/* XLPS2-Alpha CFW — minimal host test harness (no framework deps) */
#ifndef CFW_TEST_H
#define CFW_TEST_H

#include <stdio.h>
#include <stdint.h>
#include <string.h>

extern int g_tests;
extern int g_fail;

#define TASSERT(cond) do {                                              \
    g_tests++;                                                         \
    if (!(cond)) { g_fail++;                                           \
        printf("  FAIL %s:%d  %s\n", __FILE__, __LINE__, #cond); }     \
} while (0)

#define TASSERT_EQ(a, b) do {                                          \
    g_tests++;                                                         \
    long _a = (long)(a); long _b = (long)(b);                          \
    if (_a != _b) { g_fail++;                                          \
        printf("  FAIL %s:%d  %s (%ld != %ld)\n",                     \
               __FILE__, __LINE__, #a "==" #b, _a, _b); }              \
} while (0)

#endif /* CFW_TEST_H */
