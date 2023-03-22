import sys

import matplotlib.pyplot as plt
import time
import math

if __name__ == '__main__':
    from plottingutils import CircularBuffer, PlottingColor
else:
    from .plottingutils import CircularBuffer, PlottingColor

class DataPlotting:
    """
    Plots streamed data from a single device using Matplotlib
    Uses blitting for responsive graph updates
    """

    def __init__(self, data_buffers : list[CircularBuffer], colors : list = None, *args, **kwargs) -> None:
        self.num_fields = len(data_buffers)
        self.buffers = data_buffers
        self.colors = list(map(PlottingColor.auto_normalize, colors)) if colors is not None else (
                      list(PlottingColor(self.num_fields)))
        self.labels = ["" for i in range(self.num_fields)]      # TODO:
        self.ylims = [(-1, 1) for i in range(self.num_fields)]  # TODO:
        self.cols = 1                                           # TODO:

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

    def update(self):
        for i in range(self.num_fields):
            self.fig.canvas.restore_region(self.backgrounds[i])
            self.lines[i].set_ydata(self.buffers[i].get_view())
            self.axes[i].draw_artist(self.lines[i])
            self.fig.canvas.blit(self.axes[i].bbox)
        
        self.fig.canvas.flush_events()

    def redraw(self, event=None):
        for i in range(self.num_fields): self.axes[i].cla()
        self._reset_axes()
        self._update_background()
        self.update()

    def stop(self):
        print('displaying last output. close figure to continue')
        self.fig.show()

    def _reset_axes(self):
        self.lines = [self.axes[i].plot(self.clear[i],
                      color=self.colors[i])[0]
                      for i in range(self.num_fields)]

        # plot title, label, and color config
        for i in range(self.num_fields):
            self.axes[i].set_ylabel(self.labels[i])
            self.axes[i].set_ylim(self.ylims[i])
            self.axes[i].xaxis.set_visible(False)
        
        self.fig.canvas.draw()

    def _update_background(self):
        self.backgrounds = [self.fig.canvas.copy_from_bbox(self.axes[i].bbox) 
                            for i in range(self.num_fields)]

if __name__ == '__main__':
    # test/benchmark
    
    t = 0

    NUM_SUBPLOTS = 1
    LEN_BUFFER = 200

    p_data = [CircularBuffer(LEN_BUFFER) for _ in range(NUM_SUBPLOTS)]
    p = DataPlotting(p_data)

    t_arr = [0 for _ in range(200)]
    t_total = 0
    while True:
        val = 0.75 * math.sin(t/100)
        for i in range(NUM_SUBPLOTS):
            p_data[i].put(val * (1 if i % 2 == 0 else -1))
            p_data[i].increment_view()

        start = time.time()

        p.update()

        elapsed = time.time() - start
        t_total = t_total - t_arr[t % len(t_arr)] + elapsed
        t_arr[t % len(t_arr)] = elapsed
        t += 1

        print('fps', '%.2f                                    ' % (len(t_arr)/(t_total if t_total > 0 else 1e-9)), end='\r')
