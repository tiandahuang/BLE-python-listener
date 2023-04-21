from dataprocessing.dataplotting import DataPlotting

import time
import numpy as np
import matplotlib.pyplot as plt

def graph_frame(arr_l, arr_r, f=None):
    fig, ax = plt.subplots(1, 2, gridspec_kw = {'wspace':-0.2, 'hspace':0})

    ax[0].imshow(arr_l, cmap='plasma', interpolation='None')
    ax[1].imshow(arr_r, cmap='plasma', interpolation='None')

    ax[0].set_axis_off()
    ax[1].set_axis_off()

    if f is not None: fig.savefig(f, bbox_inches='tight')
    fig.show()

def playback(arr_l, arr_r, auto=True):
    amax = max(np.amax(arr_l), np.amax(arr_r))
    frame_buf = [np.zeros((8, 4)) for i in range(2)]
    p = DataPlotting(frame_buf, cols=2, ylims=[(0, amax), (0, amax)])

    for frame in range(len(arr_l)):
        time.sleep(0.01) if auto else input(frame)
        np.copyto(frame_buf[0], arr_l[frame])
        np.copyto(frame_buf[1], arr_r[frame])
        p.update()

    p.stop()

def main():
    def read(f):
        raw = np.loadtxt(f)
        return np.reshape(raw, (raw.shape[0]//8, 8, 4))
    
    vl = read('velostat_left.txt')
    vr = read('velostat_right.txt')
    conductance = lambda v: (v) / (2 * (65535 - v))
    cl = conductance(vl)
    cr = conductance(vr)

    # playback(vl, vr)
    playback(cl, cr)
    return

    keypoints = {
        'center':70,
        'front':275,
        'back':290,
        'right':330,
        'left':350
    }

    for k in keypoints:
        graph_frame(cl[keypoints[k]], cr[keypoints[k]], 'images\\'+k+'.svg')

if __name__ == '__main__':
    main()

