import sys

import matplotlib.pyplot as plt
from collections import deque
import time
import math

class DataPlotting:
    """
    Plots streamed data from a single device using Matplotlib
    Uses blitting for responsive graph updates
    """

    def __init__(self, graphics_queues : dict[deque], colors : dict[tuple], *args, **kwargs) -> None:
        self.queues = graphics_queues
        self.colors = colors

        SUBPLOT_ROWS = len(graphics_queues)
        SUBPLOT_COLS = 1

        self.fig = plt.figure()
        self.resize_event = self.fig.canvas.mpl_connect('resize_event', self.redraw)

        self.axes = {key:self.fig.add_subplot(SUBPLOT_ROWS, SUBPLOT_COLS, i+1) 
                     for i, key in enumerate(graphics_queues)}
        self.clear = {key:[sys.float_info.max for _ in graphics_queues[key]]
                      for key in self.axes}
        
        self.fig.show()
        self.redraw()

    def update(self):
        for key in self.lines:
            self.lines[key].set_ydata(self.queues[key])
            self.fig.canvas.restore_region(self.backgrounds[key])
            self.axes[key].draw_artist(self.lines[key])
            self.fig.canvas.blit(self.axes[key].bbox)
        
        self.fig.canvas.flush_events()

    def redraw(self, event=None):
        for key in self.axes: self.axes[key].cla()
        self._reset_axes()
        self._update_background()
        self.update()

    def stop(self):
        print('displaying last output. close figure to continue')
        self.fig.show()

    def _reset_axes(self):
        self.lines = {key:(self.axes[key].plot(self.clear[key],
                           color=self.colors[key])[0]) 
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

    @staticmethod
    def _dummy_event(event):
        return

if __name__ == '__main__':
    # test/benchmark

    t = 0

    p_data = deque([0.0 for _ in range(200)], 200)
    graph_color = tuple(map(lambda x: x/256, (191,87,0)))
    p = DataPlotting({'plot':p_data}, {'plot':graph_color})

    t_arr = [0 for _ in range(200)]
    t_total = 0
    while True:
        val = 7500 * math.sin(t/100)
        p_data.append(val)

        start = time.time()

        p.update()

        elapsed = time.time() - start
        t_total = t_total - t_arr[t % len(t_arr)] + elapsed
        t_arr[t % len(t_arr)] = elapsed
        t += 1

        print('fps', '%.4f                                    ' % (len(t_arr)/(t_total if t_total > 0 else 1e-9)), end='\r')
