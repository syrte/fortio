# Fortio
A Python IO for Fortran Unformatted Binary File with Variable-Length Records.

## Features:
- endianness autodetection
- able to read data into pre-allocated buffers
- able to skip over records or jump to wanted record directly without reading data
- support subrecords (which is necessary for long record whose size larger than 
  4GB with signed 4 bytes integer header)
- support numpy memmap array

## Usage
```
from fortio import FortranFile
f = FortranFile(filename)
a = f.read_record('i4')
b = f.read_record('f4')
```

## Functions
FortranFile
__init__(filename, mode='r', header_dtype='uint32',
         auto_endian=True, check_file=True)

### properties
mode
file
closed
filesize
_fp

header_dtype
byteorder
nrec
_offsets
_lengths

### internal methods
_read_header
_check_byteorder
_check_file
_read_record_data(data)
__enter__
__exit__
__repr__

### methods
write_record(data)
skip_record(nrec=1)
goto_record(rec=None)
get_record_size(rec=None)
read_record_into(into, offset=None, rec=None)
read_record(dtype='byte', shape=None, rec=None, mmap=False)
close
flush



close
closed
mode
readinto
seek
tell
write
