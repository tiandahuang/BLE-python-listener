import asyncio
import sys
from argparse import ArgumentParser
from unittest.mock import NonCallableMagicMock

from bleak import BleakScanner
from bleak import BleakClient

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

async def main():

    parser = ArgumentParser(description='Connect to a BLE device')
    parser.add_argument('name')
    parser.add_argument('--timeout', '-t', dest='timeout', default=5)
    parser.add_argument('--gatt_char', '-g', dest='gatt_descriptor', default='Nordic UART TX')
    args = parser.parse_args()

    device, _ =  await find_device(args.name)
    try:
        async with BleakClient(device) as client:
            characteristics = client.services.characteristics.copy()

            if any((gatt_nordic_uart_tx := gatt).description == args.gatt_descriptor 
                   for gatt in characteristics.values()):
                print(gatt_nordic_uart_tx)
            print(await client.read_gatt_char(gatt_nordic_uart_tx))
            print(client)
    except asyncio.exceptions.CancelledError:
        print('cancelled')
    except asyncio.exceptions.TimeoutError:
        print('timeout')

    # TODO: is 'Nordic UART TX' always the last GATT handle
    # TODO: handle for incoming messages
    # TODO: longer timeout, handle timeout


if __name__ == '__main__':
    asyncio.run(main())
    