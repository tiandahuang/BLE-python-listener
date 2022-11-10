import asyncio
import sys
import multiprocessing as mp
import time

from argparse import ArgumentParser

from bleak import BleakScanner
from bleak import BleakClient

import dataprocessing

background_tasks = set()

async def find_device(name):
    stop_event = asyncio.Event()
    device = None
    advertising_data = None

    def detection_callback(dev, advert):
        if dev.name == name:
            stop_event.set()
            nonlocal device
            nonlocal advertising_data
            device = dev
            advertising_data = advert

    async with BleakScanner(detection_callback) as scanner:
        await stop_event.wait()

    print(f'Found device: {device}')
    print(advertising_data)
    return device, advertising_data


async def device_connect(device, recieve_queue, args):
    disconnect_event = asyncio.Event()

    def disconnect_callback(dev):
        nonlocal recieve_queue
        disconnect_event.set()
        recieve_queue.put(bytearray())
        print(f'disconnected: {dev}')

    def recieve_callback(gatt_char, data):
        nonlocal recieve_queue
        recieve_queue.put(data)

    try:
        async with BleakClient(device, disconnect_callback, timeout=args.timeout) as client:
            characteristics = client.services.characteristics.copy()
            if any((gatt_char := gatt).description == args.gatt_descriptor 
                   for gatt in characteristics.values()):
                print(gatt_char)

                await client.start_notify(gatt_char, recieve_callback)
                await disconnect_event.wait()

    except asyncio.exceptions.CancelledError:
        print('connection cancelled')
    except asyncio.exceptions.TimeoutError:
        print('connection timeout')

async def dloop(recieve_queue, args):
    device, _ =  await find_device(args.name)
    await device_connect(device, recieve_queue, args)

def add_to_background_tasks(coroutine, *args, **kwargs):
    task = asyncio.create_task(coroutine(*args, **kwargs))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)
    return task

async def device_main(recieve_queue, args):
    await add_to_background_tasks(dloop, recieve_queue, args)


def device_process(recieve_queue, args):
    asyncio.run(device_main(recieve_queue, args))
    


if __name__ == '__main__':
    
    parser = ArgumentParser(description='Connect to a BLE device')
    parser.add_argument('name')
    parser.add_argument('--timeout', '-t', dest='timeout', default=20.0)
    parser.add_argument('--gatt_char', '-g', dest='gatt_descriptor', default='Nordic UART TX')
    args = parser.parse_args()

    recieve_queue = mp.Queue()
    reciever = dataprocessing.DataStream("", recieve_queue)
    p1 = mp.Process(target=device_process, args=(recieve_queue, args))

    p1.start()
    reciever.start()

    p1.join()
    reciever.join()

    