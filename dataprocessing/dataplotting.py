import sys

import matplotlib
matplotlib.use('QtAgg', force=True)
import matplotlib.pyplot as plt
import numpy as np
from typing import Union
import time
import threading
from .plottingutils import CircularBuffer, PlottingColor, MovingAverage

class DataPlotting:
    """
    Plots streamed data from a single device using Matplotlib
    Uses blitting for responsive graph updates

    For 1d live-plotting use CircularBuffer
    For 2d live-plotting use np.ndarray

    TODO: multiple data per plot
    """

    def __init__(self, 
                 data_buffers : list[Union[CircularBuffer, np.ndarray]], # required
                 labels       : list[str] = None,
                 colors       : list[Union[str, tuple[int, int, int], tuple[float, float, float]]] = None,
                 ylims        : list[tuple[float, float]] = None,
                 cols         : int = None,
                 *args, **kwargs) -> None:

        self.data_2d = [(type(buf) is not CircularBuffer) for buf in data_buffers]
        self.num_fields = len(data_buffers)
        self.buffers = data_buffers

        self.colors = list(map(PlottingColor.auto_normalize, 
                               self._check_arg(colors, 
                                               list(PlottingColor(self.num_fields)))))
        self.labels = self._check_arg(labels, 
                                      ['' for i in range(self.num_fields)])
        self.ylims = self._check_arg(ylims,
                                     [(-1, 1) for i in range(self.num_fields)])
        self.cols = self._check_arg(cols, 1, scalar=True)

        SUBPLOT_ROWS = -(self.num_fields // -self.cols)     # ceiling integer divide
        SUBPLOT_COLS = self.cols

        self.fig = plt.figure()
        self.resize_event = self.fig.canvas.mpl_connect('resize_event', self.redraw)

        self.axes = [self.fig.add_subplot(SUBPLOT_ROWS, SUBPLOT_COLS, i+1) 
                     for i in range(self.num_fields)]
        self.clear = [[sys.float_info.max for _ in data_buffers[i]]
                      for i in range(self.num_fields)]
        
        self.fig.show()
        self.redraw()

    def update(self) -> None:
        for i, is_2d in enumerate(self.data_2d):
            self._update_2d(i) if is_2d else self._update_1d(i)

        self.fig.canvas.flush_events()

    def redraw(self, event=None) -> None:
        for i in range(self.num_fields): self.axes[i].cla()
        self._reset_axes()
        self._update_background()
        self.update()

    # callable should return True if valid, False to stop
    def run(self, fps : int, update : callable) -> None:
        end_flag = threading.Event()
        self.autoupdate_func = update

        update_thread = threading.Thread(target=self._update, args=(end_flag,))
        plot_thread = threading.Thread(target=self._plot, args=(fps, end_flag))

        update_thread.start()
        plot_thread.run()

        update_thread.join()

    def _plot(self, fps : int, end : threading.Event) -> None:
        self.autoupdate_period = 1/fps
        end_flag = end

        # funny little function to sleep for (period - execution time)
        def get_sleep_time():
            t = time.time()
            while True:
                t += self.autoupdate_period
                yield max(t - time.time(), 0)

        sleep_time = get_sleep_time()
        while not end_flag.is_set():
            time.sleep(next(sleep_time))
            self.update()

    def _update(self, end : threading.Event) -> None:
        while self.autoupdate_func(): pass
        end.set()

    def stop(self) -> None:
        print('displaying last output. close figure to continue')
        self.fig.show()

    def _update_1d(self, i):
        self.fig.canvas.restore_region(self.backgrounds[i])
        self.artist[i].set_ydata(self.buffers[i].get_view())
        self.axes[i].draw_artist(self.artist[i])
        self.fig.canvas.blit(self.axes[i].bbox)

    def _update_2d(self, i):
        self.artist[i].set_data(self.buffers[i])
        self.axes[i].draw_artist(self.artist[i])
        self.fig.canvas.blit(self.axes[i].bbox)

    def _reset_axes(self):
        self.artist = [self.axes[i].imshow(self.buffers[i], 
                                           vmin=self.ylims[i][0], 
                                           vmax=self.ylims[i][1], 
                                           interpolation='None', cmap='plasma') 
                       if self.data_2d[i] else (
                       self.axes[i].plot(self.clear[i],
                                         color=self.colors[i])[0])
                       for i in range(self.num_fields)]

        # plot title, label, and color config
        for i in range(self.num_fields):
            self.axes[i].set_ylabel(self.labels[i])
            if not self.data_2d[i]:
                self.axes[i].set_ylim(self.ylims[i])
                self.axes[i].xaxis.set_visible(False)
        
        self.fig.canvas.draw()

    def _update_background(self):
        self.backgrounds = [self.fig.canvas.copy_from_bbox(self.axes[i].bbox) 
                            for i in range(self.num_fields)]

    def _check_arg(self, arg, default, scalar=False):
        if arg is None: return default
        if scalar:
            return arg
        else:
            if len(arg) != self.num_fields: raise ValueError
            return [(a if a is not None else default[i]) for i, a in enumerate(arg)]
