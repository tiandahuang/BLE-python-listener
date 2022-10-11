import asyncio
import sys

from collections import OrderedDict
from collections import deque

import numpy as np
import matplotlib.pyplot as plt

from bleak import BleakScanner
from bleak import BleakClient

class BluetoothClient:
    """
    Class containing a bluetooth client's connection details
    Contains a BleakClient, a parsing method, a data processing method,
    and a plotting method

    Uses async
    """

    def __init__(self, id : str, **kwargs):
        self.name = id
        self.gatt_descriptor = kwargs['descriptor']
        await self.__find()
        await self.__connect()

    async def __find(self):
        found_event = asyncio.Event()

        def detection_callback(dev, advert):
            nonlocal self
            if dev.name == self.name:
                found_event.set()
                self.device = device

        async with BleakScanner(detection_callback) as scanner:
            # TODO: handle device not found
            await found_event.wait()


    async def __connect(self):
        self.disconnect_event = asyncio.Event()

        def disconnect_callback(dev):
            self.disconnect_event.set()
            print(f'disconnected: {dev}')

        def recieve_callback(gatt_char, data):
            print(data)

        try:
            async with BleakClient(self.device, disconnect_callback, timeout=20.0) as client:
                characteristics = client.services.characteristics.copy()

                if any((gatt_char := gatt).description == self.gatt_descriptor 
                    for gatt in characteristics.values()):
                    print(gatt_nordic_uart_tx)

                await client.start_notify(gatt_char, recieve_callback)
                await self.disconnect_event.wait()

        except asyncio.exceptions.CancelledError:
            print('connection cancelled')
        except asyncio.exceptions.TimeoutError:
            print('connection timeout')

        
