from .dataplotting import DataPlotting

import multiprocessing as mp
from functools import partial

import numpy as np
from scipy import signal
from collections import deque

# DATA_SPLIT = {
#                 'num':{'len':2, 'convert':unsigned},
#                 'resistance':{'len':4, 'convert':signed},
#                 'reactance':{'len':4, 'convert':signed},
#                 'temp 1':{'len':2, 'convert':unsigned},
#                 'temp 2':{'len':2, 'convert':unsigned}
#             }
# DATA_SPLIT = {
#                 'num':{'len':2, 'convert':unsigned, 'color':(80/256,0,0)},
#                 'scg':{'len':3, 'convert':signed, 'multi':20, 'color':(80/256,0,0)},
#                 'ecg':{'len':3, 'convert':signed, 'multi':20, 'color':(80/256,0,0)},
#                 'ppg':{'len':4, 'convert':signed, 'multi':5, 'color':(80/256,0,0)},
#                 'tmp':{'len':2, 'convert':unsigned, 'color':(80/256,0,0)}
#             }




class DataStream():
    """
    Recieves and filters data from multiple devices
    Also responsible for plotting recieved data

    Data is recieved through a multiprocessing queue from a sender process

    TODO: input config parsing
    TODO: signal processing
    TODO: data logging
    TODO: test multidevice
    """
    
    QUEUE_BASE_LEN = 100
    PLOT_REFRESH_FPS = 60

    @staticmethod
    def _bytes_to_int(byte_array : bytearray, signed : bool, bit_length=None):
        bit_length = 8*len(byte_array) if bit_length is None else bit_length
        return int.from_bytes(byte_array, byteorder='little', signed=signed)
    
    @staticmethod
    def _max_deque_len(data_config, key):
        return DataStream.QUEUE_BASE_LEN * data_config[key].get('multi', 1)

    DATA_SPLIT = {
        'accel_x':{'len':2, 'convert':partial(_bytes_to_int, signed=True), 'color':(80,0,0)},
        'accel_y':{'len':2, 'convert':partial(_bytes_to_int, signed=True), 'color':(80,0,0)},
        'accel_z':{'len':2, 'convert':partial(_bytes_to_int, signed=True), 'color':(80,0,0)},
        'gyro_x':{'len':2, 'convert':partial(_bytes_to_int, signed=True), 'color':(80,0,0)},
        'gyro_y':{'len':2, 'convert':partial(_bytes_to_int, signed=True), 'color':(80,0,0)},
        'gyro_z':{'len':2, 'convert':partial(_bytes_to_int, signed=True), 'color':(80,0,0)},
    }
    EXPECTED_LEN = sum(map(lambda x: x['len']*x.get('multi', 1), DATA_SPLIT.values()))

    def __init__(self, queue : mp.Queue, **kwargs) -> None:
        self.q = queue
        self.current_id = 0
        self.devices = {}           # dict of (device : id)

        # per-device fields, indexed with device id
        self.data_config = []       # list of data parsing configs
        self.expected_lens = []     # list of expected message lengths  # TODO: embed in data_config json
        self.graphics_queues = []   # list of deques for plotting
        self.figures = []           # list of figure references
        
        self.refresh_period_ns = 1e9 / self.PLOT_REFRESH_FPS

    def add_device(self, dev_name : str, config_file : str):
        self.devices[dev_name] = self.current_id
        self.current_id += 1

        self.data_config.append(self.DATA_SPLIT)
        self.graphics_queues.append({key:deque([0.0 for _ in range(DataStream._max_deque_len(self.data_config[-1], key))], 
                                               DataStream._max_deque_len(self.data_config[-1], key)) 
                                     for key in self.data_config[-1]})
        self.figures.append(DataPlotting(self.graphics_queues[-1], 
                            {key:np.divide(self.data_config[-1][key]['color'], 256) 
                             for key in self.data_config[-1]}))
        

    def parse_data(self) -> None:
        byte_array = self.q.get(block=True)

        if len(byte_array) == 0: raise self.DisconnectedError()
        if len(byte_array) != self.EXPECTED_LEN: raise self.WrongMSGLenError(byte_array, self.EXPECTED_LEN)

        id = 0

        curr_config = self.data_config[id]
        idx = 0
        for key in curr_config:
            for _ in range(curr_config[key].get('multi', 1)):
                data = curr_config[key]['convert'](byte_array[idx:(idx := idx+curr_config[key]['len'])])
                self.graphics_queues[id][key].append(data)
                # print(f'{key}:{data}', end='|')
        # print('')

    def run(self) -> None:
        while True:
            self.figures[0].update()
            try:
                self.parse_data()
            except self.WrongMSGLenError as e:
                print(e)
            except self.DisconnectedError as e:
                print(e)
                self.figures[0].stop()
                return

    class WrongMSGLenError(Exception): 
        """ Raised when recieved byte array is of an incorrect length """
        def __init__(self, byte_array, len_expected):
            self.byte_array = byte_array
            self.len_expected = len_expected
        def __str__(self):
            return f'error {len(self.byte_array)} bytes recieved, {self.len_expected} bytes expected: {self.byte_array}'
        
    class DisconnectedError(Exception):
        """ Raised when a disconnect message is recieved from the queue """
        def __str__(self):
            return 'disconnected: DataStream'
    
    
    