from dataprocessing.dataprocessing import DataStream
from dataprocessing.config_parse import ConfigParser

import time
import math
import numpy as np
import multiprocessing as mp

def datastream_process(recieve_queue, *args):
    datastream = DataStream(recieve_queue, "test_device", "simple_test_config.json")
    datastream.run()

def main():
    recieve_queue = mp.Queue()
    reciever = mp.Process(target=datastream_process, args=(recieve_queue,))
    reciever.start()

    print(cfg := ConfigParser().read("simple_test_config.json"), '\n\n')
    for e in cfg['Signals Information']:
        print(e)
    print(cfg['Packet Structure'])
    print('\n\n')

    for i in range(10):
        recieve_queue.put(bytearray(
              [i]
            + [0 for _ in range(5)]
            + [(2*i+j) if (j%2==0) else ((~(2*i+j)+1)&0xFF) for j in range(6)]))
        time.sleep(0.5)

    recieve_queue.put(bytearray())

    reciever.join()

if __name__ == '__main__':
    main()

