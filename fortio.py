"""
# Fortio
A Python IO for Fortran Unformatted Binary Files with Variable-Length Records.

## Features
- read and write Fortran unformatted file
- auto-detect endianness(byteorder)
- allow reading data into pre-allocated buffers
- allow skipping over records or jumping to wanted record directly without reading data
- support subrecords (which is necessary for long record whose size larger than
  4GB with signed 4 bytes integer header)
- support numpy.memmap array for fast loading

## Usage
```
from fortio import FortranFile
with FortranFile(filename) as f:
    a = f.read_record('i4')
    f.skip_record()
    b = f.read_record('f8')
```
"""

__author__ = 'Syrtis Major <styr.py@gmail.com>'
__version__ = '0.4'

import warnings
import numpy as np
import os

__all__ = ['FortranFile']


def _assert_header_equal(head, tail):
    if (head != tail):
        raise ValueError("inconsistent record headers: %d != %d." % (head, tail))


def _assert_header_abs_equal(head, tail):
    if (head != tail) and (head != -tail):
        raise ValueError("inconsistent record headers: |%d| != |%d|." % (head, tail))


class FortranFile(object):
    """Fortran Unformatted Binary file with Variable-Length Records.
    """

    def __init__(self, filename, mode='r', header_dtype='uint32',
                 auto_endian=True, check_file=True):
        """
        Parameters
        ----------
        filename : str
            File to open.
        mode : str
            The mode can be 'r' or 'w' for reading (default) or writing. 
        header_dtype : data-type
            Data type of the record header, default is 'uint32'.
            If signed integer type is used, the file will be assumed to contain 
            subrecords (ie. long records).
        auto_endian: bool
            If True, file byteorder will be auto detected, otherwise
            byteorder of given header_dtype will be used.
        check_file: bool
            If True, header consistency of every record in the file will be checked.
            This may take a while when the file contains a large number of records.
            Once checking is finished, record jumping will be faster.
        """
        filename = os.path.abspath(filename)

        if mode not in ['r', 'w']:
            raise ValueError("mode must be 'r' or 'w'")

        header_dtype = np.dtype(header_dtype)
        if header_dtype.kind == 'u':
            long_records = False
        elif header_dtype.kind == 'i':
            long_records = True
        else:
            raise TypeError('header_dtype should be integer type.')

        self.file = filename
        self.filesize = os.path.getsize(filename)
        self.mode = mode
        self.header_dtype = header_dtype
        self.long_records = long_records
        self._fp = open(filename, '%sb' % mode)

        if self.mode != 'w':
            if auto_endian:
                self._check_byteorder()
            if check_file:
                self._check_file()
        self._fp.seek(0)  # restore the pos indicator after checking

    @property
    def closed(self):
        return self._fp.closed

    @property
    def byteorder(self):
        return self.header_dtype.byteorder

    def _read_header(self):
        '''Read the number of bytes of record data.
        '''
        head, = np.fromfile(self._fp, dtype=self.header_dtype, count=1)
        return head

    def _check_byteorder(self):
        '''Determinate the byteorder of header_dtype by checking the 
        header consistency of the first record.
        '''
        try:
            # use goto_record in case the current pos indicator is not 0
            self.goto_record(1)
        except ValueError:
            self.header_dtype = self.header_dtype.newbyteorder()
            try:
                self.goto_record(1)
                msg = ("byteorder of the file is set to '%s' by auto-detection."
                       % self.header_dtype.byteorder)
                warnings.warn(msg)
            except ValueError:
                self.close()
                raise ValueError("Invalid fortran file '%s'." % self.file)

    def _check_file(self):
        try:
            self._fp.seek(0)
            offsets, lengths = [], []
            while True:
                offset = self._fp.tell()
                if offset == self.filesize:
                    break
                length = self.skip_record()
                offsets.append(offset)
                lengths.append(length)
            self.nrec = len(offsets)
            self._offsets = offsets
            self._lengths = lengths
        except ValueError:
            self.close()
            raise ValueError("Invalid fortran file '%s'." % self.file)

    def write_record(self, data):
        '''Write a data record to file.
        '''
        if self.mode != 'w':
            raise IOError('File not open for writing.')
        if self.long_records:
            raise NotImplementedError('not support writing with signed header yet.')

        data = np.asarray(data)
        head = np.array(data.nbytes).astype(self.header_dtype)
        if data.nbytes > np.iinfo(self.header_dtype).max:
            raise ValueError('input data is too long for header_dtype: %s.'
                             % self.header_dtype.name)

        head.tofile(self._fp)
        data.tofile(self._fp)
        head.tofile(self._fp)
        return data.nbytes

    def skip_record(self, nrec=1):
        '''Skip over the next `nrec` records.
        Parameters
        ----------
        nrec : int

        Returns
        -------
        total : int
            nbytes of skipped data. 
            Note the size of headers is not included.
        '''
        total = 0
        if self.long_records:
            for i in range(nrec):
                while True:
                    head = self._read_header()
                    self._fp.seek(abs(head), 1)
                    tail = self._read_header()
                    _assert_header_abs_equal(head, tail)
                    total += abs(int(head))
                    if head >= 0:
                        break
        else:
            for i in range(nrec):
                head = self._read_header()
                self._fp.seek(head, 1)
                tail = self._read_header()
                _assert_header_equal(head, tail)
                total += int(head)
        return total

    def _read_record_data(self, data):
        '''data should be array with type `byte`'''
        total = 0
        if self.long_records:
            while True:
                head = self._read_header()
                nread = self._fp.readinto(data[total:total + abs(head)])
                tail = self._read_header()
                _assert_header_abs_equal(head, tail)
                total += nread
                if head >= 0:
                    break
        else:
            head = self._read_header()
            nread = self._fp.readinto(data[:head])
            tail = self._read_header()
            _assert_header_equal(head, tail)
            total += nread
        return total

    def goto_record(self, rec=None):
        '''Skip the first `rec` records from the beginning of the file.
        Parameters
        ----------
        rec : int or None
            The wanted record. 0 is the first record,
            Do nothing if `rec` is None.
        '''
        if rec is not None:
            if hasattr(self, '_offsets'):
                self._fp.seek(self._offsets[rec])
            else:
                self._fp.seek(0)
                self.skip_record(rec)
        return

    def get_record_size(self, rec=None):
        '''Get the data size of the record.
        Parameters
        ----------
        rec : int or None
            The wanted record. 0 is the first record,
            `None` means the current record.

        Returns
        -------
        size : int
            nbytes of the record data.
            Note the size of headers is not included.
        '''
        if (rec is not None) and hasattr(self, '_lengths'):
            size = self._lengths[rec]
        else:
            pos = self._fp.tell()
            self.goto_record(rec)
            if self.long_records:
                size = self.skip_record()
            else:
                size = self._read_header()
            self._fp.seek(pos)
        return size

    def mmap_record(self, dtype='byte', shape=None, rec=None):
        '''Read a record with given dtype from the file, using memmap
        when possible.
        Parameters
        ----------
        dtype : data type
            Data type. The endianess of record header will be used.
        rec : int or None
            The record to read. 0 is the first record,
            `None` means the current record.

        Returns
        -------
        result : memmap array
            Data stored in the record.
        '''
        return self.read_record(dtype=dtype, shape=shape, rec=rec, memmap=True)

    def read_record(self, dtype='byte', shape=None, rec=None, memmap=False):
        '''Read a record with given dtype from the file.
        Parameters
        ----------
        dtype : data type
            Data type. The endianess of record header will be used.
        shape : int or tuple
            The wanted shape of the record array.
        rec : int or None
            The record to read. 0 is the first record,
            `None` means the current record.
        memmap : bool
            If true, a memmap of the record will be created and
            returned when possible.

        Returns
        -------
        result : ndarr
            Data stored in the record.
        '''
        dtype = np.dtype(dtype).newbyteorder(self.byteorder)

        if self.long_records and memmap:
            raise ValueError('memmap does not support subrecords.')

        self.goto_record(rec)

        size = self.get_record_size()
        if size % dtype.itemsize:
            raise ValueError("record size is not multiple of itemsize.")
        if (shape is not None) and (size != dtype.itemsize * np.prod(shape)):
            raise ValueError("record size does not match the wanted shape.")

        if memmap:
            data = np.memmap(self.file, dtype='byte', shape=size, mode='r',
                             offset=self._fp.tell() + self.header_dtype.itemsize)
            self.skip_record()
        else:
            data = np.empty(size, dtype='byte')
            self._read_record_data(data)
        return data.view(dtype).reshape(shape)

    def read_record_into(self, into, offset=None, rec=None):
        '''Read a record from the file into given array.
        Parameters
        ----------
        into : ndarray
            The array to store the record data.
        offset : int
            The offset *bytes*, ie. data is read into `into.view('byte')[offset:]`.
        rec : int or None
            The record to read. 0 is the first record,
            `None` means the current record.

        Returns
        -------
        nread : int
            nbytes of read data.

        Notes
        -----
        This function does nothing with endianess, you may want
        to check endianess of data read in by yourself if necessary.
        '''
        if into.dtype.byteorder != self.byteorder:
            raise TypeError('endianess of the input array does not match the file.')

        data = into.reshape(-1).view('byte')
        if offset is not None:
            data = data[offset:]

        self.goto_record(rec)

        size = self.get_record_size()
        if size > data.nbytes:
            raise ValueError("record size is larger than given array.")

        nread = self._read_record_data(data)
        return nread

    def close(self):
        '''Close file.'''
        self._fp.close()

    def flush(self):
        '''Flush the buffer.'''
        self._fp.flush()

    def __enter__(self):
        return self

    def __exit__(self, type, value, trace):
        self.close()

    def __repr__(self):
        return "<FortranFile '{}', mode '{}', header_dtype '{}' at {}>".format(
            self.file, self.mode, self.header_dtype.str, hex(id(self)))
