import asyncio
import sys
from argparse import ArgumentParser
from collections import OrderedDict

from bleak import BleakScanner
from bleak import BleakClient

# temporary print function for core-hydration system
# replace with generic
def hydration_print_data(byte_array):
    unsigned = lambda b: int.from_bytes(b, byteorder='little', signed=False)
    signed = lambda b: int.from_bytes(b, byteorder='little', signed=True)

    DATA_SPLIT = OrderedDict({
                    'num':{'len':2, 'convert':unsigned},
                    'resistance':{'len':4, 'convert':signed},
                    'reactance':{'len':4, 'convert':signed},
                    'temp 1':{'len':2, 'convert':unsigned},
                    'temp 2':{'len':2, 'convert':unsigned}
                })
    EXPECTED_LEN = sum(map(lambda x: x['len'], DATA_SPLIT.values()))

    if len(byte_array) != EXPECTED_LEN:
        print(f'error {len(byte_array)} bytes recieved, {EXPECTED_LEN} bytes expected')
        print(byte_array)
        return
    idx = 0
    for key in DATA_SPLIT:
        data = DATA_SPLIT[key]['convert'](byte_array[idx:idx+DATA_SPLIT[key]['len']])
        print(f'{key}: {data}', end=' | ')
        idx += DATA_SPLIT[key]['len']
    print('')

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


async def device_connect(device, args):

    disconnect_event = asyncio.Event()

    def disconnect_callback(dev):
        disconnect_event.set()
        print(f'disconnected: {dev}')

    def recieve_callback(gatt_char, data):
        hydration_print_data(data)

    try:
        async with BleakClient(device, disconnect_callback, timeout=args.timeout) as client:
            characteristics = client.services.characteristics.copy()

            if any((gatt_nordic_uart_tx := gatt).description == args.gatt_descriptor 
                   for gatt in characteristics.values()):
                print(gatt_nordic_uart_tx)

            await client.start_notify(gatt_nordic_uart_tx, recieve_callback)
            await disconnect_event.wait()

    except asyncio.exceptions.CancelledError:
        print('connection cancelled')
    except asyncio.exceptions.TimeoutError:
        print('connection timeout')


async def main():

    parser = ArgumentParser(description='Connect to a BLE device')
    parser.add_argument('name')
    parser.add_argument('--timeout', '-t', dest='timeout', default=20.0)
    parser.add_argument('--gatt_char', '-g', dest='gatt_descriptor', default='Nordic UART TX')
    args = parser.parse_args()

    device, _ =  await find_device(args.name)
    await device_connect(device, args)


if __name__ == '__main__':
    asyncio.run(main())
    