import multiprocessing as mp
import time

import numpy as np
import matplotlib.pyplot as plt
from collections import deque
from collections import OrderedDict

PLOT_REFRESH_RATE = 100

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
                'num':{'len':2, 'convert':unsigned},
                'scg':{'len':3, 'convert':signed, 'multi':20},
                'ecg':{'len':3, 'convert':signed, 'multi':20},
                'ppg':{'len':4, 'convert':signed, 'multi':5},
                'tmp':{'len':2, 'convert':unsigned}
            })
EXPECTED_LEN = sum(map(lambda x: x['len']*x.get('multi', 1), DATA_SPLIT.values()))
maxlen = lambda key : QUEUE_BASE_LEN*DATA_SPLIT[key].get('multi', 1)
DATA_RANGES = {key:np.linspace(0, 1, maxlen(key)) for key in DATA_SPLIT}



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
    # def parse_data(self) -> None:
    #     data = self.q.get(block=True)
    #     print(data)

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
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(1,1,1)
        plt.ion()

    def update(self):
        self.fig.gca().cla()
        for key in DATA_SPLIT:
            self.ax.plot(DATA_RANGES[key], self.queues[key])
        plt.draw()
        plt.pause(1/PLOT_REFRESH_RATE)
        pass

    def stop(self):
        plt.ioff()
        plt.show()
    