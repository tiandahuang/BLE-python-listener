
# BLE-python-listener

contains two modules: `bluetoothclient` and `dataprocessing`.

### `bluetoothclient`
This module contains code for connecting via bluetooth using the [BLEAK library](https://github.com/hbldh/bleak); intended usage is for this module to be launched in a separate multiprocessing process.

### `dataprocessing`
This module contains code for parsing received raw bytes and graphing the processed information. Parsing and graphing configuration is performed through `.json` files. Examples for the `.json` configuration file format are stored in `./tests`.

Graphing uses Matplotlib.

### usage

run `python main.py --help` for options (these may be outdated though)

sample device configuration files are stored in `./tests/*.json`

***warning: this code is extremely buggy out-of-the-box***
