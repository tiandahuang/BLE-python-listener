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

# bluetooth connection process ################################################

async def device_main(recieve_queue, args):
    d1 = bluetoothclient.BluetoothClient(recieve_queue, 'fitpal', args)
    d2 = bluetoothclient.BluetoothClient(recieve_queue, 'onegaishimasu', args)
    t1 = add_to_background_tasks(d1.run)
    t2 = add_to_background_tasks(d2.run)
    await t1
    await t2

def device_process(recieve_queue, args):
    asyncio.run(device_main(recieve_queue, args))

###############################################################################



# data recieving process ######################################################

def datastream_process(recieve_queue, args):
    datastream = dataprocessing.DataStream(recieve_queue, "imu", "imu.json")
    datastream.run()

###############################################################################


if __name__ == '__main__':
    
    parser = ArgumentParser(description='Connect to a BLE device')
    # parser.add_argument('name')
    parser.add_argument('--timeout', '-t', dest='timeout', default=20.0)
    parser.add_argument('--gatt_char', '-g', dest='gatt_descriptor', default='Nordic UART TX')
    args = parser.parse_args()

    recieve_queue = mp.Queue()
    p1 = mp.Process(target=device_process, args=(recieve_queue, args))
    p1.start()

    reciever = mp.Process(target=datastream_process, args=(recieve_queue, args))
    reciever.start()

    p1.join()
    reciever.join()

    