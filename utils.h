#ifndef _UTILS_H
#define _UTILS_H

#include <stdlib.h>
#include <stdint.h>

void bswap_uint32 (uint32_t *u);
void bswap_uint32_array (uint32_t *value, size_t size);
void adjust_float32_arr(float *value, size_t size, float scale, float shift);
void adjust_int32_arr(int *value, size_t size, int scale, int shift);

#endif
