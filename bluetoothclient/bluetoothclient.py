import asyncio
import multiprocessing as mp

from bleak import BleakScanner
from bleak import BleakClient

class BluetoothClient:
    """
    Class containing a bluetooth client's connection details
    Runs entirely asynchronously, await the run method to start

    TODO: reconnect
    TODO: add debugging methods (discover)
    """

    def __init__(self, queue : mp.Queue, device_name : str, args) -> None:
        self.queue = queue
        self.name = device_name
        self.device = None
        self.advertising_data = None
        self.args = args

    async def run(self):
        await self._find()
        await self._connect()

    async def _find(self):
        stop_event = asyncio.Event()

        def detection_callback(dev, advert):
            if dev.name == self.name:
                stop_event.set()
                self.device = dev
                self.advertising_data = advert

        async with BleakScanner(detection_callback) as scanner:
            # TODO: add timeout
            await stop_event.wait()

        print(f'Found device: {self.device}')
        print(self.advertising_data)


    async def _connect(self):
        disconnect_event = asyncio.Event()

        def disconnect_callback(dev):
            disconnect_event.set()
            self.queue.put(bytearray())
            print(f'disconnected: {dev}')

        def recieve_callback(gatt_char, data):
            self.queue.put(data)

        try:
            async with BleakClient(self.device, disconnect_callback, timeout=self.args.timeout) as client:
                characteristics = client.services.characteristics.copy()
                if any((gatt_char := gatt).description == self.args.gatt_descriptor 
                    for gatt in characteristics.values()):
                    print(gatt_char)

                    await client.start_notify(gatt_char, recieve_callback)
                    await disconnect_event.wait()

        except asyncio.exceptions.CancelledError:
            print('connection cancelled')
        except asyncio.exceptions.TimeoutError:
            print('connection timeout')




        
