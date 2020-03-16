Tormenta
========

Measurement control and analysis for optical microscopy

.. image:: tormenta_screen.png

Installation
~~~~~~~~~~~~

Ubuntu
^^^^^^

Run in terminal:

::

    ```
    $ sudo apt-get install python3-pip python3-h5py git
    $ sudo pip3 install comtypes lantz 

    $ sudo apt-get install build-essential python3-dev cython3 python3-setuptools python3-pip python3-wheel python3-numpy   python3-pytest python3-blosc python3-brotli python3-snappy python3-lz4 libz-dev libblosc-dev liblzma-dev liblz4-dev libzstd-dev libpng-dev libwebp-dev libbz2-dev libopenjp2-7-dev libjpeg-turbo8-dev libjxr-dev liblcms2-dev libcharls-dev libaec-dev libbrotli-dev libsnappy-dev libzopfli-dev libgif-dev libtiff-dev

    $ pip3 install imagecodecs
    $ pip3 install tifffile pyqtgraph
    $ git clone https://github.com/fedebarabas/
    ```

Windows
^^^^^^^

-  Install `WinPython
   3.4 <https://sourceforge.net/projects/winpython/files/>`__.
-  Browse to `Laboratory for Fluorescence
   Dynamics <http://www.lfd.uci.edu/~gohlke/pythonlibs/>`__ and download
   tifffile for Python 3.4 to
   ``$PATH\WinPython-64bit-3.4.4.1\python-3.4.4.amd64\``.
-  Open WinPython Command Prompt and run:

   ::

       $ pip install comtypes lantz tifffile-2016.4.19-cp34-cp34m-win_amd64.whl

-  Clone Repository by running:

```
$ git clone https://github.com/marcnol/tormenta.git
```

Optional dependencies
^^^^^^^^^^^^^^^^^^^^^

Don't install these libraries if you have different equipment or you
just want to test the software without instruments (offline mode). -
Support for Labjack's T7 DAQ - `LJM
Library <https://labjack.com/support/software/installers/ljm>`__ - `LJM
Library Python
wrapper <https://labjack.com/support/software/examples/ljm/python>`__ -
Support for webcam image acquisition - Pygame

Launch Tormenta
~~~~~~~~~~~~~~~

-  Open WinPython Command Prompt, go to tormenta's repository directory
   and run:

   ::

       $ python -m tormenta

Documentation
~~~~~~~~~~~~~

The documentation is under construction in
`http://fedebarabas.github.io/tormenta/ <http://fedebarabas.github.io/tormenta/>`__

How to cite
~~~~~~~~~~~

If you used the code/program for your paper, please cite

Barabas et al., *Note: Tormenta: An open source Python-powered control software for camera based optical microscopy*, Review of Scientific Instruments, 2016.

https://doi.org/10.1063/1.4972392

Contact
~~~~~~~

Feel free to contact me with comments or suggestions. Use any part of
the code that suits your needs.

Federico Barabas fede.barabas[AT]gmail.com
