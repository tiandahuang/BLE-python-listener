import numpy as np

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

