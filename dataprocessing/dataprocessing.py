import multiprocessing as mp

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from collections import deque
from collections import OrderedDict

PLOT_REFRESH_RATE = 200

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
DATA_SPLIT = OrderedDict({
                'num':{'len':2, 'convert':unsigned, 'color':(80/256,0,0)},
                'scg':{'len':3, 'convert':signed, 'multi':20, 'color':(80/256,0,0)},
                'ecg':{'len':3, 'convert':signed, 'multi':20, 'color':(80/256,0,0)},
                'ppg':{'len':4, 'convert':signed, 'multi':5, 'color':(80/256,0,0)},
                'tmp':{'len':2, 'convert':unsigned, 'color':(80/256,0,0)}
            })
EXPECTED_LEN = sum(map(lambda x: x['len']*x.get('multi', 1), DATA_SPLIT.values()))
maxlen = lambda key : QUEUE_BASE_LEN*DATA_SPLIT[key].get('multi', 1)
# DATA_RANGES = {key:np.linspace(0, 1, maxlen(key)) for key in DATA_SPLIT}



class DataStream(mp.Process):
    """
    Recieves and filters data
    Also responsible for plotting recieved data

    Data is recieved through a multiprocessing queue from a sender process
    """
    
    def __init__(self, config_fname : str, queue : mp.Queue, **kwargs) -> None:
        super(DataStream, self).__init__()
        self.config_fname = config_fname
        self.q = queue
        
        self.graphics_queues = {key:deque([0.0 for _ in range(maxlen(key))], maxlen(key)) 
                                for key in DATA_SPLIT}
        self.plot = DataPlotting(self.graphics_queues)

    class WrongMSGLenError(Exception): 
        """ Raised when recieved byte array is of an incorrect length """
        pass
    class DisconnectedError(Exception):
        """ Raised when a disconnect message is recieved from the queue """
        pass

    def parse_data(self) -> None:
        byte_array = self.q.get(block=True)
        if len(byte_array) == 0: raise self.DisconnectedError()

        if len(byte_array) != EXPECTED_LEN:
            print(f'error {len(byte_array)} bytes recieved, {EXPECTED_LEN} bytes expected')
            print(byte_array)
            raise self.WrongMSGLenError()
        idx = 0
        for key in DATA_SPLIT:
            for _ in range(DATA_SPLIT[key].get('multi', 1)):
                data = DATA_SPLIT[key]['convert'](byte_array[idx:(idx := idx+DATA_SPLIT[key]['len'])])
                self.graphics_queues[key].append(data)
                # print(f'{key}:{data}', end='|')
        # print('')

    def run(self) -> None:
        while True:
            try:
                self.parse_data()
            except self.WrongMSGLenError:
                pass
            except self.DisconnectedError:
                self.plot.stop()
                return
            self.plot.update()



class DataPlotting:
    """
    Plots streamed data using Matplotlib
    """

    def __init__(self, graphics_queues : dict[deque], *args, **kwargs) -> None:
        self.queues = graphics_queues

        SUBPLOT_ROWS = len(graphics_queues)
        SUBPLOT_COLS = 1

        self.fig = plt.figure()
        self.axes = {key:self.fig.add_subplot(SUBPLOT_ROWS, SUBPLOT_COLS, i+1) 
                     for i, key in enumerate(graphics_queues)}
        # plot title, label, and color config
        for key in self.axes:
            self.axes[key].set_ylabel(key)
            self.axes[key].xaxis.set_visible(False)
            self.axes[key].plot(self.queues[key], color=DATA_SPLIT[key]['color'])
        plt.ion()

    def update(self):
        for key in self.axes:
            self.axes[key].lines.pop()
            self.axes[key].plot(self.queues[key], color=DATA_SPLIT[key]['color'])
        plt.draw()
        plt.pause(1/PLOT_REFRESH_RATE)
        pass

    def stop(self):
        plt.ioff()
        plt.show()
    