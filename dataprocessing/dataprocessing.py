import multiprocessing as mp
import time

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from scipy import signal
from collections import deque
from collections import OrderedDict

PLOT_REFRESH_FPS = 60  # fps

QUEUE_BASE_LEN = 100
unsigned = lambda b: int.from_bytes(b, byteorder='little', signed=False)
signed = lambda b: int.from_bytes(b, byteorder='little', signed=True)
# DATA_SPLIT = OrderedDict({
#                 'num':{'len':2, 'convert':unsigned},
#                 'resistance':{'len':4, 'convert':signed},
#                 'reactance':{'len':4, 'convert':signed},
#                 'temp 1':{'len':2, 'convert':unsigned},
#                 'temp 2':{'len':2, 'convert':unsigned}
#             })
# DATA_SPLIT = OrderedDict({
#                 'num':{'len':2, 'convert':unsigned, 'color':(80/256,0,0)},
#                 'scg':{'len':3, 'convert':signed, 'multi':20, 'color':(80/256,0,0)},
#                 'ecg':{'len':3, 'convert':signed, 'multi':20, 'color':(80/256,0,0)},
#                 'ppg':{'len':4, 'convert':signed, 'multi':5, 'color':(80/256,0,0)},
#                 'tmp':{'len':2, 'convert':unsigned, 'color':(80/256,0,0)}
#             })
DATA_SPLIT = OrderedDict({
                'accel_x':{'len':2, 'convert':signed, 'color':(80/256,0,0)},
                'accel_y':{'len':2, 'convert':signed, 'color':(80/256,0,0)},
                'accel_z':{'len':2, 'convert':signed, 'color':(80/256,0,0)},
                'gyro_x':{'len':2, 'convert':signed, 'color':(80/256,0,0)},
                'gyro_y':{'len':2, 'convert':signed, 'color':(80/256,0,0)},
                'gyro_z':{'len':2, 'convert':signed, 'color':(80/256,0,0)},
            })
EXPECTED_LEN = sum(map(lambda x: x['len']*x.get('multi', 1), DATA_SPLIT.values()))
maxlen = lambda key : QUEUE_BASE_LEN*DATA_SPLIT[key].get('multi', 1)
DATA_RANGES = {key:np.linspace(0, 1, maxlen(key)) for key in DATA_SPLIT}



class DataStream():
    """
    Recieves and filters data
    Also responsible for plotting recieved data

    Data is recieved through a multiprocessing queue from a sender process

    TODO: index-based instead of key-based, should be faster
    TODO: data logging
    TODO: update plotting at interval
    TODO: globals -> class constants
    TODO: multidevice
    """
    
    def __init__(self, config_fname : str, queue : mp.Queue, **kwargs) -> None:
        self.config_fname = config_fname
        self.q = queue
        
        self.graphics_queues = {key:deque([0.0 for _ in range(maxlen(key))], maxlen(key)) 
                                for key in DATA_SPLIT}
        self.plot = DataPlotting(self.graphics_queues)
        self.refresh_period_ns = 1e9 / PLOT_REFRESH_FPS

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
            return 'DataStream disconnected'

    def parse_data(self) -> None:
        byte_array = self.q.get(block=True)
        if len(byte_array) == 0: raise self.DisconnectedError()

        if len(byte_array) != EXPECTED_LEN: raise self.WrongMSGLenError(byte_array, EXPECTED_LEN)

        idx = 0
        for key in DATA_SPLIT:
            for _ in range(DATA_SPLIT[key].get('multi', 1)):
                data = DATA_SPLIT[key]['convert'](byte_array[idx:(idx := idx+DATA_SPLIT[key]['len'])])
                self.graphics_queues[key].append(data)
                # print(f'{key}:{data}', end='|')
        # print('')

    def run(self) -> None:
        while True:
            self.plot.update()
            try:
                self.parse_data()
            except self.WrongMSGLenError as e:
                print(e)
            except self.DisconnectedError as e:
                print(e)
                self.plot.stop()
                return



class DataPlotting:
    """
    Plots streamed data using Matplotlib
    Uses blitting for responsive graph updates
    """

    def __init__(self, graphics_queues : dict[deque], id=0, *args, **kwargs) -> None:
        self.queues = graphics_queues

        SUBPLOT_ROWS = len(graphics_queues)
        SUBPLOT_COLS = 1

        self.fig = plt.figure()
        self.resize_event = self.fig.canvas.mpl_connect('resize_event', self.redraw)

        self.axes = {key:self.fig.add_subplot(SUBPLOT_ROWS, SUBPLOT_COLS, i+1) 
                     for i, key in enumerate(graphics_queues)}
        self.clear = {key:[20000 for _ in range(maxlen(key))]
                      for key in self.axes}
        
        self._reset_axes()
        plt.show(block=False)
        plt.pause(0.5)
        self._update_background()

    def update(self):
        for key in self.lines:
            self.lines[key].set_ydata(self.queues[key])
            self.fig.canvas.restore_region(self.backgrounds[key])
            self.axes[key].draw_artist(self.lines[key])
            self.fig.canvas.blit(self.axes[key].bbox)
        
        self.fig.canvas.flush_events()

    def redraw(self, event):
        for key in self.axes: self.axes[key].cla()
        self._reset_axes()
        self._update_background()
        self.update()

    def stop(self):
        plt.show()

    def _reset_axes(self):
        self.lines = {key:(self.axes[key].plot(self.clear[key],
                           color=DATA_SPLIT[key]['color'])[0]) 
                      for key in self.axes}

        # plot title, label, and color config
        for key in self.axes:
            self.axes[key].set_ylabel(key)
            self.axes[key].set_ylim((-10000, 10000))
            self.axes[key].xaxis.set_visible(False)
        
        self.fig.canvas.draw()

    def _update_background(self):
        self.backgrounds = {key:self.fig.canvas.copy_from_bbox(self.axes[key].bbox) 
                            for key in self.axes}

    
    