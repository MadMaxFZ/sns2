# simbody_list.py

from collections import UserList
from sysbody_model import SimBody


class SimBodyList(UserList):
    def __init__(self, iterable):
        super().__init__(self._validate_simbody(item) for item in iterable)

    def __setitem__(self, index, item):
        self.data[index] = self._validate_simbody(item)

    def insert(self, index, item):
        self.data.insert(index, self._validate_simbody(item))

    def append(self, item):
        self.data.append(self._validate_simbody(item))

    def extend(self, other):
        if isinstance(other, type(self)):
            self.data.extend(other)
        else:
            self.data.extend(self._validate_simbody(item) for item in other)

    def _validate_simbody(self, value):
        if isinstance(value, (int, float, complex)):
            return value
        raise TypeError(f"numeric value expected, got {type(value).__name__}")

    def for_each(self, func):
        for item in self:
            func(item)
