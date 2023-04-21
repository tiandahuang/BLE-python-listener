from .dataplotting import DataPlotting
from .config_parse import ConfigParser
from .plottingutils import CircularBuffer, MovingAverage

import multiprocessing as mp
import functools
import numpy as np


class DataStream():
    """
    Recieves and filters data for a single device
    Also responsible for plotting recieved data

    Data is recieved through a multiprocessing queue from a sender process

    TODO: input config parsing
    TODO: data logging
    TODO: add skip/ignore field
    TODO: interleaved data
    """
    
    QUEUE_BASE_LEN = 20
    PLOT_REFRESH_FPS = 20
    SAVE_BUFFER_SIZE = 1000

    def __init__(self, queue : mp.Queue, dev_name : str, config_file : str, **kwargs) -> None:
        self._q = queue
        self.name = dev_name
        self.config_file = config_file

        # data parsing
        data_config = ConfigParser().read(config_file)

        # rotate config dictionary into series of lists
        def _config_fetch_field(dlist, key, default=None):
            return [(sig.get(key, default) 
                    if default is not None 
                    else sig[key]) for sig in dlist]

        # required fields
        names = _config_fetch_field(data_config['Signals Information'], 'name')
        data_lengths = _config_fetch_field(data_config['Signals Information'], 'bytes-per-data')
        datatypes = _config_fetch_field(data_config['Signals Information'], 'datatype')
        name_to_idx = lambda n: {name:i for i, name in enumerate(names)}[n]

        # setup for parsing
        expanded_packet_structure = []
        for pkt in data_config['Packet Structure']:
            if type(pkt) is str:                                # single data
                fmt_pkt = [pkt, 1]
            elif type(pkt) is list and type(pkt[-1]) is int:    # repeated data
                fmt_pkt = pkt
            else: raise TypeError
            expanded_packet_structure.extend(map(name_to_idx, fmt_pkt[:-1]*fmt_pkt[-1]))
        
        # for parsing incoming bytearrays:
        # parameters for word aligning and reordering
        self._data_lengths = [data_lengths[idx] for idx in expanded_packet_structure]
        self._aligned_data_lengths = [self._round_up_int(blen, 4) for blen in self._data_lengths]
        self._signextend = [(datatypes[idx] == 'int') for idx in expanded_packet_structure]
        self._offsets = np.cumsum(np.sort(np.array(self._aligned_data_lengths))).tolist()
        self._reorder = np.argsort(expanded_packet_structure).tolist()
        self.expected_len = sum(self._data_lengths)

        # parameters for parsing aligned/ordered bytearray into separate fields
        multiples = np.bincount(expanded_packet_structure).tolist()
        offsets = np.cumsum(np.array([m*self._round_up_int(data_lengths[idx], 4) for idx, m in enumerate(multiples)]))
        self._type_conversions = self._create_conversions([
            (datatypes[i], offsets[i], multiples[i]) 
            for i in range(len(names))])
        
        # setup for plotting


        # per-data-field initialization
        self.keys = list(self.DATA_SPLIT.keys())
        self.keys_to_idx = {key:i for i, key in enumerate(self.keys)}
        self.ranges = [self.DATA_SPLIT[key]['range'] for key in self.keys]
        # self.buffers = [CircularBuffer(DataStream._max_buffer_len(self.data_config, key)) for key in self.keys]
        self.buffers = [np.zeros((8, 4)) for _ in self.keys]
        self.cols = 2

        # initialize plotting
        self.figure = DataPlotting(self.buffers, labels=self.keys, ylims=self.ranges, cols=self.cols)

    def parse_data(self) -> None:
        byte_array = self._q.get(block=True)

        if len(byte_array) == 0: raise self.DisconnectedError()
        if len(byte_array) != self.expected_len: raise self.WrongMSGLenError(byte_array, self.expected_len)
        
        aligned_barray = self._align_byte_buffer(byte_array)
        parsed_data = [convert(aligned_barray) for convert in self._type_conversions]

        # with open('velostat_left.txt', 'a') as f:
        #     np.savetxt(f, self.buffers[0])
        # with open('velostat_right.txt', 'a') as f:
        #     np.savetxt(f, self.buffers[1])

    def run(self) -> None:
        self.figure.run(self.PLOT_REFRESH_FPS, self._update_func)

    def _update_func(self) -> None:
        try:
            self.parse_data()
        except self.WrongMSGLenError as e:
            print(e)
            return False
        except self.DisconnectedError as e:
            print(e)
            return False
        return True
    
    # TODO: shift for interlaced data
    def _align_byte_buffer(self, unaligned_buffer : bytearray | bytes):
        aligned_array = bytearray(sum(self._aligned_data_lengths))
        aligned_idx, unaligned_idx = 0, 0

        for i, length in enumerate(self._data_lengths):
            # copy over existing bytes
            aligned_length = self._aligned_data_lengths[i]
            offset = self._offsets[self._reorder[i]]
            aligned_array[aligned_idx + offset : aligned_idx + length] = (
                    unaligned_buffer[unaligned_idx : unaligned_idx + length])

            # sign extend
            sign_ext_bytes = bytes([(0xFF 
                                     if (aligned_array[aligned_idx + length - 1] >= 0x80) and self._signextend[i]
                                     else 0x00) for _ in range(aligned_length - length)])
            aligned_array[aligned_idx + length + offset : aligned_idx + aligned_length + offset] = (
                    sign_ext_bytes)

        return aligned_array

    """
    creates a list of conversion functions from an input list
    input list contains tuples of
              type: ('float', 'int', 'unsigned')
              start byte / bytearray offset
              array count / repeats
    note conversions require the input array to be 32b word aligned
    """
    @staticmethod
    def _create_conversions(types : list[tuple[str | np.dtype, int, int]]):
        string_to_npdtype = {'float'     : np.dtype(np.float32).newbyteorder('<'),  # default to little endian
                             'int'       : np.dtype(np.int32).newbyteorder('<'),
                             'unsigned'  : np.dtype(np.uint32).newbyteorder('<')}

        def convert_to_npdtype(requested_dtype : str | np.dtype):
            dtype = (string_to_npdtype.get(requested_dtype, None) 
                     if type(requested_dtype) is str 
                     else requested_dtype)
            if type(dtype) is not np.dtype: raise TypeError('Invalid datatype for conversion')
            return dtype

        return [functools.partial(np.frombuffer,
                                  dtype=convert_to_npdtype(e[0]),
                                  offset=e[1],
                                  count=e[2]) for e in types]

    @staticmethod
    def _max_buffer_len(data_config, key):
        return DataStream.QUEUE_BASE_LEN * data_config[key].get('multi', 1)
    
    @staticmethod
    def _round_up_int(n, base):
        return((n + base - 1) // base) * base

    class WrongMSGLenError(Exception): 
        """ Raised when recieved byte array is of an incorrect length """
        def __init__(self, byte_array, len_expected):
            self.byte_array = byte_array
            self.len_expected = len_expected
        def __str__(self):
            return f'error {len(self.byte_array)} bytes recieved, {self.len_expected} bytes expected: {self.byte_array}'
        
    class DisconnectedError(Exception):
        """ Raised when a disconnect message is recieved from the queue """
        def __str__(self):
            return 'disconnected: DataStream'
    


