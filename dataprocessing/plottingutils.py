import numpy as np
import random
import re
import threading

class CircularBuffer:

    def __init__(self, length, dtype=np.float32):
        self.buffer = np.array([0 for _ in range(2*(length+1))], dtype=dtype)
        self.length = length
        self.putidx = length
        self.view = 0

    def put(self, x):
        self.buffer[self.putidx] = self.buffer[self.putidx + self.length + 1] = x
        self.putidx += 1
        if self.putidx == self.length + 1: self.putidx = 0

    def get_view(self):
        return self.buffer[self.view:(self.view+self.length)]

    def increment_view(self):
        self.view += 1
        if self.view == self.length + 1: self.view = 0

    def __len__(self):
        return self.length

    def __iter__(self):
        i = self.view
        while i < self.view + self.length:
            yield self.buffer[i]
            i += 1

class PlottingColor:
    """
    Assigns lists of default colors and contains helper functions for color conversion
    """
    _colors_rgb = []
    _initialized = False
    _initialized_lock = threading.Lock()

    def __init__(self, len):
        PlottingColor.init()
        self.len = len

    def __iter__(self):
        i = 0
        while i < self.len:
            yield self._colors_rgb[i % len(self._colors_rgb)]
            i += 1

    @staticmethod
    def hex_string_to_rgb_tuple(hexstr : str) -> tuple[int, int, int]:
        if re.match(r'#[0-9a-fA-F]{6}$', hexstr) is None: raise ValueError
        return tuple(map(lambda b: int(b, 16), [hexstr[i:i+2] for i in range(1, len(hexstr), 2)]))

    @staticmethod
    def hex_string_to_normalized(hexstr : str) -> tuple[float, float, float]:
        return PlottingColor.normalize_rgb_tuple(PlottingColor.hex_string_to_rgb_tuple(hexstr))

    @staticmethod
    def normalize_rgb_tuple(rgbtup : tuple[int, int, int]) -> tuple[float, float, float]:
        if any(map(lambda c: c not in range(0, 256), rgbtup)): raise ValueError
        return tuple(map(lambda c: c/256, rgbtup))
    
    @staticmethod
    def auto_normalize(color) -> tuple[float, float, float]:
        convert = PlottingColor.hex_string_to_normalized if type(color) is str else (
                  PlottingColor.normalize_rgb_tuple if type(color[0]) is int else (
                  lambda x: x))
        return convert(color)
    
    @classmethod
    def init(cls):
        with cls._initialized_lock:
            if not cls._initialized: 
                random.Random(16).shuffle(colors := '#bf5700 #f8971f #ffd600 #a6cd57 #579d42 #00a9b7 #005f86 #9cadb7 #333f48'.split(' '))
                cls._colors_rgb = list(map(PlottingColor.hex_string_to_normalized, colors))
                cls._initialized = True
