from dataprocessing.dataplotting import DataPlotting
from dataprocessing.plottingutils import CircularBuffer, PlottingColor, MovingAverage

import time
import math
import numpy as np

def main():
    # test/benchmark
    
    t = 0

    COLS = 2
    LEN_BUFFER = 200
    DIMS_2D = (16, 4)
    TEST_2D = [True, False, False, True]
    TEST_AUTO_REFRESH = False
    FPS = 60

    p_data = [np.zeros(DIMS_2D) if is_2d else CircularBuffer(LEN_BUFFER) for is_2d in TEST_2D]
    p = DataPlotting(p_data, cols=COLS)
    num_subplots = len(TEST_2D)

    if TEST_AUTO_REFRESH:
        def update_func():
            nonlocal t

            for i in range(num_subplots):
                if TEST_2D[i]:
                    for j in range(DIMS_2D[0]):
                        for k in range(DIMS_2D[1]):
                            p_data[i][j][k] = math.sin((j+k+t)/6*math.pi)
                else:
                    val = 0.75 * math.sin(t/100)
                    p_data[i].put(val * (1 if i % 2 == 0 else -1))
                    p_data[i].increment_view()
        
            t += 1
            MEAN = 1/FPS
            STD_DEV = 0.2*MEAN
            MIN, MAX = MEAN-1.5*STD_DEV, MEAN+1.5*STD_DEV
            time.sleep(np.clip(np.random.normal(1/FPS, 1/(5*FPS)), MIN, MAX))
            return True

        p.run(FPS, update_func)

    else:
        fps_avg = MovingAverage(200)
        while True:
            
            for i in range(num_subplots):
                if TEST_2D[i]:
                    for j in range(DIMS_2D[0]):
                        for k in range(DIMS_2D[1]):
                            p_data[i][j][k] = math.sin((j+k+t)/6*math.pi)
                else:
                    val = 0.75 * math.sin(t/100)
                    p_data[i].put(val * (1 if i % 2 == 0 else -1))
                    p_data[i].increment_view()

            start = time.time()

            p.update()

            elapsed = time.time() - start
            fps_avg.put(elapsed)
            t += 1

            print('fps', '%.2f                                    ' % (1/(fps_avg.get() if fps_avg.get() > 0 else 1e-9)), end='\r')

if __name__ == '__main__':
    main()

