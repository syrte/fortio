from setuptools import setup

with open('README.md', 'r') as fp:
    long_description = fp.read()

setup(
    name='fortio',
    version='0.4',
    description='A Python IO for Fortran unformatted binary files with variable-length records.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/syrte/fortio/',
    keywords=['Fortran', 'Numpy'],
    author='Syrtis Major',
    author_email='styr.py@gmail.com',
    py_modules=['fortio'],
    install_requires=['numpy'],
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Topic :: Scientific/Engineering',
        'License :: OSI Approved :: GNU General Public License v2 (GPLv2)',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
    ],
)
