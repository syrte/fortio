"""
Fortio is a package for reading and writing Fortran Unformatted Records.

Some features:
- support subrecord (which is necessary for record size larger than 
  4GB with 4 bytes header)
- endianess auto-detection
- able to read data into pre-allocated buffers
"""

__author__ = 'styr <styr.py@gmail.com>'
__version__ = '0.2'

import warnings
import numpy as np
import os

__all__ = ['FortranFile']


def _assert_head_equal(head, tail):
    if head != tail:
        raise IOError("inconsistent record headers: %d != %d." %(head, tail))


def _assert_head_abs_equal(head, tail):
    if abs(head) != abs(tail):
        raise IOError("inconsistent record headers: %d != %d." %(head, tail))


class FortranFile(object):
    """Fortran Unformatted Binary file with Variable-Length Records.
    """
    def __init__(self, filename, mode='r', header_dtype='uint32', 
        auto_endian=True):
        """
        Parameters
        ----------
        filename : str
            File to open.
        mode : str
            The mode can be 'r', 'w' or 'a' for reading (default),
            writing or appending. 
        header_dtype : data-type
            Data type of the record header, default is 'uint32'.
        auto_endian: bool
            If true file byteorder will be auto detected, otherwise
            byteorder of given header_dtype will be used.
        """
        if mode not in ['r', 'w', 'a']:
            raise ValueError("mode must be one of 'r', 'w' or 'a'")
        self._header_dtype = np.dtype(header_dtype)

        self.file = filename
        self.filesize = os.path.getsize(filename)
        self.mode = mode
        self._fp = open(filename, '%sb' % mode)

        if self._header_dtype.kind != 'u':   
            if self._header_dtype.kind == 'i':
                self.skip_record = self._skip_long_record
                self._read_record_data = self._read_long_record_data
            else:
                raise ValueError('header_dtype should be integer.')
        if auto_endian:
            self._check_byteorder()


    @property
    def header_dtype(self):
        '''Data type of record header.
        '''
        return self._header_dtype


    @property
    def byteorder(self):
        '''Byteorder of record header.
        '''
        return self._header_dtype.byteorder


    def _read_header(self):
        '''Read the number of bytes of record data.
        '''
        head, = np.fromfile(self._fp, dtype=self._header_dtype, count=1)
        return head


    def _check_byteorder(self):
        '''Determinate the byteorder of header_dtype by checking the 
        header consistency of the first record.
        '''
        try:
            self.goto_record(1)
        except IOError:
            self._header_dtype = self._header_dtype.newbyteorder()
            try:
                self.goto_record(1)
                warnings.warn("byteorder is changed to '%s' by auto detection." 
                % self._header_dtype.byteorder)
            except IOError:
                raise IOError("Invalid fortran file '%s'." %filename)
        self.goto_record(0)
        return self._header_dtype.byteorder


    def write_record(self, data):
        '''Write a data record to file.
        '''
        data = np.asarray(data)
        head = self._header_dtype(data.nbytes)
        if data.nbytes > np.iinfo(self._header_dtype).max:
            raise ValueError('input data is too big for header_dtype.')
        head.tofile(self._fp)
        data.tofile(self._fp)
        head.tofile(self._fp)
        return


    def skip_record(self, nrec=1):
        '''Skip over the next `nrec` records.
        Parameters
        ----------
        nrec : int or None
            Do nothing if nrec is None

        Returns
        -------
        total : int
            nbytes of skipped data. 
            Note the size of headers is not included.
        '''
        total = 0
        for i in range(nrec):
            head = self._read_header()
            self._fp.seek(head, 1)
            tail = self._read_header()
            _assert_head_equal(head, tail)
            total += head
        return total


    def _skip_long_record(self, nrec=1):
        '''Skip over the next `nrec` records.
        Parameters
        ----------
        nrec : int or None
            Do nothing if nrec is None

        Returns
        -------
        total : int
            nbytes of skipped data. 
            Note the size of headers is not included.
        '''
        total = 0
        for i in range(nrec):
            while True:
                head = self._read_header()
                self._fp.seek(abs(head), 1)
                tail = self._read_header()
                _assert_head_abs_equal(head, tail)
                total += abs(head)
                if head >= 0: 
                    break
        return total


    def _read_record_data(self, data):
        head = self._read_header()
        nread = self._fp.readinto(data[:head])
        #_assert_head_equal(head, nread)
        tail = self._read_header()
        _assert_head_equal(head, tail)
        return nread


    def _read_long_record_data(self, data):
        total = 0
        while True:
            head = self._read_header()
            nread = self._fp.readinto(data[total:total+abs(head)])
            #_assert_head_abs_equal(head, nread)
            tail = self._read_header()
            _assert_head_abs_equal(head, tail)
            total += abs(head)
            if head >= 0: 
                break
        return total


    def goto_record(self, nrec=None):
        '''Skip the first `nrec` records from the beginning 
        of the file.
        Parameters
        ----------
        nrec : int or None
            The wanted record. 0 is the first record,
            `None` means the current record.
        '''
        if nrec is not None:
            self._fp.seek(0, 0)
            self.skip_record(nrec)
        return


    def get_record_size(self, nrec=None):
        '''Get the size of the nrec-th record.
        Parameters
        ----------
        nrec : int or None
            The wanted record. 0 is the first record,
            `None` means the current record.
        '''
        pos = self._fp.tell()
        self.goto_record(nrec)
        size = self.skip_record()
        self._fp.seek(pos, 0)
        return size


    def read_record(self, dtype='byte', nrec=None):
        '''Read a record with given dtype from the file.
        Parameters
        ----------
        dtype : data type
            Data type.
        nrec : int or None
            The record to read. 0 is the first record,
            `None` means the current record.

        Returns
        -------
        result : ndarr
            Data stored in the record.
        '''
        dtype = np.dtype(dtype).newbyteorder(self.byteorder)
        
        self.goto_record(nrec)
        size = self.get_record_size()
        if size % dtype.itemsize:
            raise ValueError("record size is not multiple of itemsize")
        data = np.empty(size, dtype='byte')
        nread = self._read_record_data(data)
        return data.view(dtype)


    def read_record_into(self, into, nrec=None):
        '''Read a record from the file into given array.
        Parameters
        ----------
        into : ndarray
            The array to store the record data.
        nrec : int or None
            The record to read. 0 is the first record,
            `None` means the current record.
        
        Returns
        -------
        nread : int
            nbytes of the record.
        '''
        self.goto_record(nrec)
        size = self.get_record_size()
        if size > data.nbytes:
            raise ValueError("record size is larger than gien array")
        data = into.view('byte')  
        nread = self._read_record_data(data)
        return nread


    def close(self):
        '''Close file'''
        self._fp.close()

    def __enter__(self):
        return self

    def __exit__(self, type, value, trace):
        self.close()
        