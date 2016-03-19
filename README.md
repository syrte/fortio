# Fortio
A Python IO for Fortran Unformatted Binary File with Variable-Length Records.

## Features:
- endianess auto-detection
- able to read data into pre-allocated buffers
- able to skip over records or jump to wanted record directly without reading data
- support subrecords (which is necessary for long record whose size larger than 
  4GB with signed 4 bytes integer header)
