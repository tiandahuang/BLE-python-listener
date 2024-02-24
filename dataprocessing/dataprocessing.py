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

    TODO: filter
    TODO: data logging
    TODO: tidy up init function
    """
    
    QUEUE_BASE_LEN = 20
    PLOT_REFRESH_FPS = 20
    PLOT_COLUMNS = 1
    SAVE_BUFFER_SIZE = 1000

    def __init__(self, queue : mp.Queue, dev_name : str, config_file : str, **kwargs) -> None:
        self._q = queue
        self.name = dev_name
        self.config_file = config_file

        # data parsing
        data_config = ConfigParser().read(config_file)

        # rotate config dictionary into series of lists
        def _config_fetch_field(key, **kwargs):
            def fetch(d, key): return (
                (d.get(key, kwargs['default']) if 'default' in kwargs else d[key]) 
                if d else None)
            return [fetch(sig, key) for sig in data_config['Signals Information']]

        # required fields
        names = _config_fetch_field('name')
        data_lengths = _config_fetch_field('bytes-per-data')
        datatypes = _config_fetch_field('datatype')
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
        self._offsets = [0] + np.cumsum(np.sort(self._aligned_data_lengths)).tolist()[:-1]
        reorder = np.zeros(len(expanded_packet_structure), dtype=int)
        reorder[np.argsort(expanded_packet_structure)] = np.arange(len(expanded_packet_structure))
        self._reorder = reorder.tolist()

        self.expected_len = sum(self._data_lengths)

        # parameters for parsing aligned/ordered bytearray into separate fields
        multiples = np.bincount(expanded_packet_structure).tolist()
        offsets = np.cumsum([0] + [m*self._round_up_int(data_lengths[idx], 4) for idx, m in enumerate(multiples)][:-1])
        self._type_conversions = self._create_conversions([
                (datatypes[i], offsets[i], multiples[i]) 
                for i in range(len(names))])
        
        print(expanded_packet_structure)
        print(self._data_lengths)
        print(self._aligned_data_lengths)
        print(self._signextend)
        print(self._offsets)
        print(self._reorder)

        print(names, data_lengths, datatypes, self.expected_len)
        print(offsets, multiples)
        
        # setup for plotting
        graphing_configs = _config_fetch_field('graphable', default=None)
        plot_mask = [type(cfg) is dict for cfg in graphing_configs]
        print(graphing_configs)

        map_graphing_to_data_idx = [i for i, graphable in enumerate(plot_mask) if graphable]
        self._map_data_to_graphing_idx = [(idx if plot_mask[i] else None) 
                                          for i, idx in enumerate(np.cumsum(plot_mask, dtype=int) - 1)]
        
        plot_buffer_types = [cfg.get('type', 'line') for cfg in graphing_configs if cfg is not None]
        plot_heatmap_dims = [cfg.get('heatmap-dimensions') for cfg in graphing_configs if cfg is not None]
        # validate plotting settings
        for i, plot_type in enumerate(plot_buffer_types): 
            if plot_type not in ('line', 'heatmap'): 
                raise ValueError(f'Invalid plot type: {plot_type}')
            if plot_type == 'heatmap' and not (
                    type(plot_heatmap_dims[i]) is list 
                    and len(plot_heatmap_dims[i]) == 2
                    and plot_heatmap_dims[i][0] * plot_heatmap_dims[i][1] == multiples[map_graphing_to_data_idx[i]]):
                raise ValueError(f'Heatmap must have valid dimensions: {plot_heatmap_dims[i]}')
        self._buffers = [(np.zeros(plot_heatmap_dims[i])
                          if plot_type == 'heatmap' 
                          else CircularBuffer(self.QUEUE_BASE_LEN * map_graphing_to_data_idx[i]))
                         for i, plot_type in enumerate(plot_buffer_types)]

        plot_labels = [names[map_graphing_to_data_idx[i]] for i in range(len(self._buffers))]
        plot_colors = [cfg.get('color') for cfg in graphing_configs if cfg is not None]
        plot_ranges = [cfg.get('yrange') for cfg in graphing_configs if cfg is not None]
        
        print(map_graphing_to_data_idx)
        print(self._map_data_to_graphing_idx)
        print(plot_buffer_types)
        print(plot_heatmap_dims)
        print(plot_colors)
        print(plot_ranges)
        print(plot_labels)
        print('')

        # initialize plotting
        self.figure = DataPlotting(self._buffers, 
                                   labels=plot_labels,
                                   colors=plot_colors,
                                   ylims=plot_ranges,
                                   cols=self.PLOT_COLUMNS)

    def parse_data(self) -> None:
        byte_array = self._q.get(block=True)

        if len(byte_array) == 0: raise self.DisconnectedError()
        if len(byte_array) != self.expected_len: raise self.WrongMSGLenError(byte_array, self.expected_len)
        
        aligned_barray = self._align_byte_buffer(byte_array)
        parsed_data = [convert(aligned_barray) for convert in self._type_conversions]
        # print('parse', parsed_data)

        # update graph
        for i, data_field in enumerate(parsed_data):
            if (idx := self._map_data_to_graphing_idx[i]) is not None:
                if type(self._buffers[idx]) is CircularBuffer:
                    for d in data_field: self._buffers[idx].put(d)
                else: # 2d ndarray buffer
                    self._buffers[idx][:] = np.reshape(data_field, self._buffers[idx].shape)

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
    
    def _align_byte_buffer(self, unaligned_buffer : bytearray | bytes):
        aligned_array = bytearray(sum(self._aligned_data_lengths))
        buffer_offset = 0

        for i, length in enumerate(self._data_lengths):
            # copy over existing bytes
            aligned_length = self._aligned_data_lengths[i]
            offset = self._offsets[self._reorder[i]]
            aligned_array[offset : offset + length] = (
                    unaligned_buffer[buffer_offset : buffer_offset + length])

            # sign extend
            sign_ext_bytes = bytes([(0xFF 
                                     if (aligned_array[offset + length - 1] >= 0x80) and self._signextend[i]
                                     else 0x00) for _ in range(aligned_length - length)])
            aligned_array[offset + length : offset + aligned_length] = (
                    sign_ext_bytes)

            buffer_offset += length

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
            if not isinstance(dtype, np.dtype): raise TypeError(f'Invalid datatype for conversion: {requested_dtype}')
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
    


