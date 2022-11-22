import asyncio
import multiprocessing as mp

from argparse import ArgumentParser

import dataprocessing
import bluetoothclient

background_tasks = set()

def add_to_background_tasks(coroutine, *args, **kwargs):
    task = asyncio.create_task(coroutine(*args, **kwargs))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return task

async def dloop(recieve_queue, args):
    await bluetoothclient.BluetoothClient(recieve_queue, args.name, args).run()

# bluetooth connection process ################################################

async def device_main(recieve_queue, args):
    await add_to_background_tasks(dloop, recieve_queue, args)

def device_process(recieve_queue, args):
    asyncio.run(device_main(recieve_queue, args))

###############################################################################



# data recieving process ######################################################

def datastream_process(recieve_queue, args):
    datastream = dataprocessing.DataStream(recieve_queue)
    datastream.add_device("test_device", "test_config")
    datastream.run()

###############################################################################


if __name__ == '__main__':
    
    parser = ArgumentParser(description='Connect to a BLE device')
    parser.add_argument('name')
    parser.add_argument('--timeout', '-t', dest='timeout', default=20.0)
    parser.add_argument('--gatt_char', '-g', dest='gatt_descriptor', default='Nordic UART TX')
    args = parser.parse_args()

    recieve_queue = mp.Queue()
    p1 = mp.Process(target=device_process, args=(recieve_queue, args))
    p1.start()

    reciever = mp.Process(target=datastream_process, args=(recieve_queue, args))
    # reciever = dataprocessing.DataStream("", recieve_queue)
    reciever.start()

    p1.join()
    reciever.join()

    