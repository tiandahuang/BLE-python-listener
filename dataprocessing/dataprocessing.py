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
    Recieves and filters data for a single device
    Also responsible for plotting recieved data

    Data is recieved through a multiprocessing queue from a sender process

    TODO: input config parsing
    TODO: data logging
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

    B_COEFS = [0.81587532, -4.0793766, 8.1587532, -8.1587532,  4.0793766, -0.81587532]
    A_COEFS = [1.0, -4.5934214, 8.45511522, -7.79491832, 3.59890277, -0.66565254]
    DATA_SPLIT = {
        'accel_x':{'len':2, 'convert':partial(_bytes_to_int, signed=True), 'color':(80,0,0)},
        'accel_y':{'len':2, 'convert':partial(_bytes_to_int, signed=True), 'color':(80,0,0)},
        'accel_z':{'len':2, 'convert':partial(_bytes_to_int, signed=True), 'color':(80,0,0)},
            # 'filt':{'b':B_COEFS, 'a':A_COEFS, 'gain':5}},
        'gyro_x':{'len':2, 'convert':partial(_bytes_to_int, signed=True), 'color':(80,0,0)},
        'gyro_y':{'len':2, 'convert':partial(_bytes_to_int, signed=True), 'color':(80,0,0)},
        'gyro_z':{'len':2, 'convert':partial(_bytes_to_int, signed=True), 'color':(80,0,0)},
    }
    # DATA_SPLIT = {
    #     'num':{'len':2, 'convert':partial(_bytes_to_int, signed=False), 'color':(0,256,0)},
    #     'ppg-r':{'len':4, 'convert':partial(_bytes_to_int, signed=False), 'multi':5, 'color':(256,0,0),
    #         'filt':{'b':B_COEFS, 'a':A_COEFS, 'gain':50}},
    #     'ppg-ir':{'len':4, 'convert':partial(_bytes_to_int, signed=False), 'multi':5, 'color':(256,0,256),
    #         'filt':{'b':B_COEFS, 'a':A_COEFS, 'gain':50}},
    #     'temp':{'len':2, 'convert':partial(_bytes_to_int, signed=False), 'color':(0,256,0)}
    # }
    EXPECTED_LEN = sum(map(lambda x: x['len']*x.get('multi', 1), DATA_SPLIT.values()))


    def __init__(self, queue : mp.Queue, dev_name : str, config_file : str, **kwargs) -> None:
        self.q = queue
        self.name = None

        # data parsing config
        self.data_config = self.DATA_SPLIT

        # per-data-field initialization
        self.lfilt_a = {}; self.lfilt_b = {}; self.lfilt_gain = {}; self.lfilt_zi = {}
        self.graphics_queues = {}
        
        for key in self.data_config:
            self.graphics_queues[key] = deque(
                    [0.0 for _ in range(DataStream._max_deque_len(self.data_config, key))], 
                    DataStream._max_deque_len(self.data_config, key))
            
            # filter initial condition and parameters
            if 'filt' in self.data_config[key]:
                self.lfilt_b[key] = self.data_config[key]['filt']['b']
                self.lfilt_a[key] = self.data_config[key]['filt'].get('a', [1.0])
                self.lfilt_gain[key] = self.data_config[key]['filt'].get('gain', 1.0)
                self.lfilt_zi[key] = signal.lfiltic(self.lfilt_b[key], self.lfilt_a[key], 0, 0)

        # initialize plotting
        self.figure = DataPlotting(
            self.graphics_queues, 
            {key:np.divide(self.data_config[key]['color'], 256) 
                for key in self.data_config})
        
        self.refresh_period_ns = 1e9 / self.PLOT_REFRESH_FPS

    def parse_data(self) -> None:
        byte_array = self.q.get(block=True)

        if len(byte_array) == 0: raise self.DisconnectedError()
        if len(byte_array) != self.EXPECTED_LEN: raise self.WrongMSGLenError(byte_array, self.EXPECTED_LEN)

        idx = 0
        for key in self.data_config:
            for _ in range(self.data_config[key].get('multi', 1)):
                rawdata = self.data_config[key]['convert'](byte_array[idx:(idx := idx+self.data_config[key]['len'])])
                
                if 'filt' in self.data_config[key]:
                    filtdata, self.lfilt_zi[key] = signal.lfilter(
                            self.lfilt_b[key], 
                            self.lfilt_a[key], 
                            (rawdata,), 
                            zi=self.lfilt_zi[key])
                    data = self.lfilt_gain[key]*filtdata
                    self.graphics_queues[key].append(data)
                else:
                    self.graphics_queues[key].append(rawdata)
                
                # print(f'{key}:{data}', end='|')
        # print('')

    def run(self) -> None:
        while True:
            self.figure.update()
            try:
                self.parse_data()
            except self.WrongMSGLenError as e:
                print(e)
            except self.DisconnectedError as e:
                print(e)
                self.figure.stop()
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
    
    
    