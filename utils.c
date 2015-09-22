#include "utils.h"

void bswap_uint32 (uint32_t *u){
    *u = ( ((*u & 0x000000ffu)<<24) | ((*u & 0x0000ff00u)<< 8) |
           ((*u & 0x00ff0000u)>> 8) | ((*u & 0xff000000u)>>24) );
}

void bswap_uint32_array (uint32_t *value, size_t size){
    size_t i;
#pragma omp parallel for default(shared) private(i)
    for (i = 0; i < size; i++){
        bswap_uint32 (value+i);
    }
}


void adjust_float32_arr(float *value, size_t size, float scale, float shift)
{
    size_t i;
    if (scale != 1.){
        if (shift != 0.){
#pragma omp parallel for default(shared) private(i)
            for (i = 0; i < size; i++)
                value[i] = value[i] * scale + shift;
        } else {
#pragma omp parallel for default(shared) private(i)
            for (i = 0; i < size; i++)
                value[i] *= scale;
        }
    }
    else {
        if (shift != 0.){
#pragma omp parallel for default(shared) private(i)
            for (i = 0; i < size; i++)
                value[i] += shift;
        }
    }
}

void adjust_int32_arr(int *value, size_t size, int scale, int shift)
{
    size_t i;
    if (scale != 1){
        if (shift != 0){
#pragma omp parallel for default(shared) private(i)
            for (i = 0; i < size; i++)
                value[i] = value[i] * scale + shift;
        } else {
#pragma omp parallel for default(shared) private(i)
            for (i = 0; i < size; i++)
                value[i] *= scale;
        }
    }
    else {
        if (shift != 0){
#pragma omp parallel for default(shared) private(i)
            for (i = 0; i < size; i++)
                value[i] += shift;
        }
    }
}

