# fortio
A Python IO for Fortran Unformatted Binary File with Variable-Length Records.

## Features:
- support subrecord (which is necessary for record size larger than
          4GB with 4 bytes header)
- endianess auto-detection
- able to read data into pre-allocated buffers

