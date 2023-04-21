# from dataprocessing.dataprocessing import DataStream
from dataprocessing.config_parse import ConfigParser

import time
import math
import numpy as np
import multiprocessing as mp

# def datastream_process(recieve_queue, *args):
#     datastream = DataStream(recieve_queue, "test_device", "test_config.json")
#     datastream.run()

def main():
    # recieve_queue = mp.Queue()
    # reciever = mp.Process(target=datastream_process, args=(recieve_queue,))
    # reciever.start()

    print(cfg := ConfigParser().read("test_config.json"), '\n\n')
    for e in cfg['Signals Information']:
        print(e)

    # for i in range(10):
    #     recieve_queue.put(bytearray([i, 0, 2*i, 2*i+1, 2*i+2, 2*i+3, 2*i+4]))

    # recieve_queue.put(bytearray())

    # reciever.join()

if __name__ == '__main__':
    main()

