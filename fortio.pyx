'''
A module for accessing fortran unformatted binary file.
Author: styr.py@gmail.com
'''

import os
cimport cython
from cython.parallel cimport parallel, prange
import numpy as np
cimport numpy as np
np.import_array()
__all__ = ["FortranFile"]

from libc.stdlib cimport malloc, free
from libc.math cimport abs
from libc.stdio cimport FILE, fopen, fclose, fread, \
        fgetpos, fsetpos, fseek, fpos_t
from libc.stdint cimport uint8_t, uint16_t, uint32_t, uint64_t, \
        int8_t, int16_t, int32_t, int64_t

cdef extern from "stdio.h":
    ctypedef struct fpos_t:
        pass

cdef extern from "utils.h":
    void bswap_uint32 (uint32_t *)
    void bswap_uint32_array (uint32_t *, size_t)
    void adjust_float32_arr(float *, size_t, float, float)
    void adjust_int32_arr(int *, size_t, int, int)

cdef pointer_to_numpy_array(void * ptr, np.npy_intp size):
    '''Convert c pointer to numpy array.
    The memory will be freed as soon as the ndarray is deallocated.
    author: Kynan & Stefan (http://stackoverflow.com/questions/23872946/)
    '''
    cdef extern from "numpy/arrayobject.h":
        void PyArray_ENABLEFLAGS(np.ndarray arr, int flags)
    cdef np.ndarray[np.npy_byte, ndim=1] arr = np.PyArray_SimpleNewFromData(1, &size, np.NPY_BYTE, ptr)
    PyArray_ENABLEFLAGS(arr, np.NPY_OWNDATA)
    return arr


cdef class FortranFile:
    '''FortranFile(filename, mode="r", bswap=None)
    Fortran Unformatted Binary file with Variable-Length Records.
    Necessarity of byteswap could be specified or auto-detected.
    For the moment only 4 bytes byteswap is supported.
    keyword `bswap` can be set to be
        None:  auto byteswap
        True:  force byteswap
        False: no byteswap
    `bswap` only work for reading record header.
    '''
    cdef:
        FILE *fp
        public str file
        public str mode
        public size_t size
        public bint byteswap
        public int nrecords
            
    def __cinit__(self, str filename, str mode="r", bswap=None, check=True):
        self.size = os.path.getsize(filename)
        self.fp = fopen(filename, "r")
        if NULL == self.fp:
            raise IOError("failed to open file '%s'." %filename)
        self.file = filename
        self.mode = mode

        if bswap is None:
            try:
                self.byteswap = False
                self.check_file()
            except IOError:
                self.byteswap = True
        else:
            self.byteswap = bswap

        if check:
            try:
                self.nrecords = self.check_file()
            except IOError:
                self.close()
                raise IOError("invalid fortran file '%s'." %filename)
        fseek(self.fp, 0, 0)
        #print("file %s opened." %filename)
            
    def __dealloc__(self):
        self.close()
        
    def __enter__(self):
        return self

    def __exit__(self, type, value, trace):
        self.close()

    def close(self):
        '''close()
        close file.
        '''
        if self.fp:
            fclose(self.fp)
            self.fp = NULL
            #print("file %s closed." %self.file)

    cdef check_file(self):
        '''check_file()
        Check the consistency of prefix and suffix of each record.
        Return the number of records.
        '''
        cdef size_t size=self.size, total = 0
        cdef fpos_t pos
        cdef int prefix, n=0
        fgetpos(self.fp, &pos)
        fseek(self.fp, 0, 0)
        while total < size:
            prefix = self.skip_subrecord()
            total = total + abs(prefix) + 8
            if prefix >= 0:
                n += 1
        fsetpos(self.fp, &pos)
        if total != size:
            raise IOError("%d byte expected, but got %d instead"
                    %(size, total))
        return n
    
    cdef read_record_data(self, void *data, size_t size):
        cdef int prefix
        cdef size_t total = 0
        
        while True:
            prefix = self.read_subrecord(<char *>data + total)
            total += abs(prefix)
            if prefix >=0:
                break
        if total != size:
            raise IOError("%d byte expected, but got %d instead"
                    %(size, total))
        return

    def read_record_float(self, n=None, float scale=1, float shift=0, bswap=None):
        '''read_record_float(n=None, scale=1, shift=0)
        Read a record of float type from the file.
        Simple manipulation scale and shift are avilble,
        return value = data * scale + shift
        '''
        cdef np.ndarray[np.npy_float32, ndim=1] ndarr
        ndarr = self.read_record(dtype='f4', n=n, bswap=bswap)
        adjust_float32_arr(<float *>&ndarr[0], ndarr.size, scale, shift)
        return ndarr

    def read_record_int(self, n=None, int scale=1, int shift=0, bswap=None):
        '''read_record_int(n=None, scale=1, shift=0)
        Read a record of int type from the file.
        Simple manipulation scale and shift are avilble,
        return value = data * scale + shift
        '''
        cdef np.ndarray[np.npy_int32, ndim=1] ndarr
        ndarr = self.read_record(dtype='i4', n=n, bswap=bswap)
        adjust_int32_arr(<int *>&ndarr[0], ndarr.size, scale, shift)
        return ndarr

    def read_record(self, dtype='i4', n=None, bswap=None):
        '''read_record(self, dtype='i4', n=None, bswap=None)
        Read a record of given type from the file.
        keyword `bswap` can be set to be
            None:  auto byteswap.
            True:  force byteswap.
            False: no byteswap.
        '''
        cdef void *data
        cdef size_t size
        cdef np.ndarray[np.npy_byte, ndim=1] ndarr
        
        if n is not None:
            self.goto_record(n)

        size = self.get_record_size()
        data = malloc(size)
        if (NULL == data):
            raise MemoryError("failed to allocate memory for %u bytes.\n", 
                    size)
        try:
            self.read_record_data(data, size)
        except Exception:
            free(data)
            raise

        if bswap is None:
            bswap = self.byteswap
        if bswap:
            if size % 4 != 0:
                free(data)
                raise ValueError("length of record is not multiple of 4.")
                #for the moment only 4 bytes byteswap is supported.
            bswap_uint32_array(<uint32_t *>data, size//4)

        ndarr = pointer_to_numpy_array(data, size)
        ndarr.dtype = dtype
        return ndarr

    def get_record_size(self):
        '''get_record_size()
        Get the currunt record size.
        '''
        cdef fpos_t pos
        cdef size_t total
        if NULL == self.fp:
            raise IOError("file closed.")
        fgetpos(self.fp, &pos)
        total = self.skip_record()
        fsetpos(self.fp, &pos)
        return total

    def check_record_size(self, size_t size):
        '''check_record_size(size)
        Check if the record size equal to given value.
        '''
        if size != self.get_record_size():
            return False
        else:
            return True
        
    def skip_record(self, int n=1):
        '''skip_record(n=1)
        Skip over n records.
        '''
        cdef int i, prefix
        cdef size_t total = 0
        for i in range(n):
            while True:
                prefix = self.skip_subrecord()
                total += abs(prefix)
                if prefix >=0:
                    break
        return total

    def goto_record(self, int n=0):
        '''goto_record(n=0)
        Goto the nth record. Note the first record is 0th.
        '''
        if NULL == self.fp:
            raise IOError("file closed.")
        fseek(self.fp, 0, 0)
        self.skip_record(n)
        return

    cdef read_header(self):
        cdef int header
        if 1 != fread (&header, sizeof (int), 1, self.fp):
            raise IOError("end of file.")
        if self.byteswap:
            bswap_uint32(<uint32_t *>&header)
        return header

    cdef skip_subrecord(self):
        cdef int prefix, suffix
        if NULL == self.fp:
            raise IOError("file closed.")
        prefix = self.read_header()
        if 0 != fseek(self.fp, abs(prefix), 1):
            raise IOError("fseek error. (likely end of file reached.)")
        suffix = self.read_header()
        if abs(suffix) != abs(prefix):
            raise IOError("inconsistent record headers: %d != %d." 
                    %(prefix, suffix))
        return prefix

    cdef read_subrecord(self, void *data):
        cdef int prefix, suffix, nread
        if NULL == self.fp:
            raise IOError("file closed.")
        prefix = self.read_header()
        nread = fread (data, 1, abs(prefix), self.fp)
        if abs(prefix) != nread:
            raise IOError("%d bytes expected but got %d instead."
                    %(prefix, nread))
        suffix = self.read_header()
        if abs(suffix) != abs(prefix):
            raise IOError("inconsistent record headers: %d != %d." 
                    %(prefix, suffix))
        return prefix


from cpython cimport PyObject, Py_INCREF
cdef class ArrayWrap:
    cdef void *data
    cdef np.npy_intp size
    def __cinit__(self, np.npy_intp size):
        self.size = size
        self.data = malloc(size)
    def __dealloc__(self):
        free(self.data)
        self.data = NULL
    def asarray(self, dtype='i4'):
        cdef np.ndarray ndarray
        ndarray = np.PyArray_SimpleNewFromData(1, &self.size,
                np.NPY_BYTE, self.data)
        ndarray.base = <PyObject*>self
        Py_INCREF(self)
        ndarray.dtype = dtype
        return ndarray

cdef class ArrayWrap2:
    '''use: ArrayWrap2().asarray(data, n, dtype='i4')
    '''
    cdef void *data
    def __cinit__(self):
        self.data = NULL
    def __dealloc__(self):
        free(self.data)
    cdef asarray(self, void *data, np.npy_intp nbytes, dtype='i4'):
        cdef np.ndarray ndarray
        if self.data:
            raise Exception("only allow once!")
        else:
            self.data = data
            ndarray = np.PyArray_SimpleNewFromData(1, &nbytes,
                    np.NPY_BYTE, data)
            ndarray.base = <PyObject*>self
            Py_INCREF(self)
            ndarray.dtype = dtype
        return ndarray

