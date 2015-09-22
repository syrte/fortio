# Compilers and linkers
# ---------------------
CC          =   icc
LD          =   icc

# Optimisation and Debugging
CWARNINGS   =   -w1
OPTIM       =   -O2
DEBUG       =   #-g -DDEBUG=0
FPIC        =   -fPIC
SHARED      =   -shared
OMP         =   -openmp

# Baisc compile and link flags
CFLAGS      =   $(OPTIM) $(DEBUG) $(CWARNINGS) $(FPIC) $(OMP)
LFLAGS      =   -lm $(OMP)

# Flags for Cython
PYTHON_INC  =  ~/local/include/python2.7
NUMPY_INC   =  ~/local/lib/python2.7/site-packages/numpy/core/include
CYCFLAGS    =   $(OPTIM) -DNDEBUG $(FPIC) $(CWARNINGS) \
      	  			-I$(NUMPY_INC) -I$(PYTHON_INC) \
			        	-fno-strict-aliasing -Wstrict-prototypes
CYLFLAGS    =   -pthread $(SHARED)


all: fortio.so

fortio.so: fortio.o utils.o
	$(CC) $^ $(CYLFLAGS) $(LFLAGS) $(SHARED) -o $@

%.o: %.c 
	$(CC) $< $(CYCFLAGS) $(CFLAGS) -c -o $@

fortio.c: fortio.pyx
	cython -t fortio.pyx

clean:
	rm *.o fortio.c 
