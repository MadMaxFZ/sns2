# simbody_list.py

from collections import UserList
from sysbody_model import SimBody

obj_type = SimBody


class SimBodyList(UserList):
    def __init__(self, iterable):
        super(SimBodyList, self).__init__(self._validate_simbody(item) for item in iterable)

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
        """
            This method returns value if and only of it is of type SimBody,
            otherwise raises TypeError
        Returns
        -------
        value if value is of type SimBody
        """
        if isinstance(value, obj_type):
            return value
        raise TypeError(f"SimBody object expected, got {type(value).__name__}")

    def for_each(self, func):
        for item in self:
            func(item)


if __name__ == "__main__":
    sb_list = SimBodyList([])
    print(sb_list)
