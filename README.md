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

## Installation

```bash
pip install fortio
```

## Usage
```
from fortio import FortranFile
with FortranFile(filename) as f:
    a = f.read_record('i4')
    f.skip_record()
    b = f.read_record('f8')
```

## Functions
- FortranFile(filename, mode='r', header_dtype='uint32',
              auto_endian=True, check_file=True)

- methods
    * write_record(data)
    * read_record(dtype='byte', shape=None, rec=None, memmap=False)
    * mmap_record(dtype='byte', shape=None, rec=None)
    * read_record_into(into, offset=None, rec=None)
    * get_record_size(rec=None)
    * skip_record(nrec=1)
    * goto_record(rec=None)
    * close()
    * flush()

- properties
    * file
    * filesize
    * mode
    * header_dtype
    * long_records
    * closed
    * byteorder

- internal properties and methods
    * _fp
    * _offsets
    * _lengths
    * _read_header()
    * _check_byteorder()
    * _check_file()
    * _read_record_data(data)
