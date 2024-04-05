# simbody_list.py

from collections import UserList
from src.simbody_model import SimBody

DEFAULT_TYPE = SimBody


class SimBodyList(UserList):
    def __init__(self, iterable=[], obj=None, obj_type=None):
        """
            Initialize a UserList object of type 'obj'.
        Parameters
        ----------
        iterable    :   an existing iterable to convert into a UserList.
        obj         :   an object of type 'obj_type' to use as the type of the UserList elements
        obj_type    :   the type of object to use as the type of the UserList.
                        If not provided, defaults to DEFAULT_TYPE.
        """
        super(SimBodyList, self).__init__(self._validate_simbody(item) for item in iterable)
        if obj:
            self._obj_type = type(obj)
            if obj_type:
                try:
                    assert(self._obj_type == obj_type)
                except:
                    print(f"Ignoring mismatched obj: {type(obj).__name__} and type: {obj_type.__name__}")
                    print(f"{self._obj_type.__name__} taking precedence...")
        elif obj_type:
            self._obj_type = obj_type
            if obj:
                try:
                    assert(self._obj_type == type(obj))
                except:
                    print(f"Ignoring mismatched obj: {type(obj).__name__} and type: {obj_type.__name__}")
                    print(f"{self._obj_type.__name__} taking precedence...")
        else:
            self._obj_type = SimBody
            print(f"Defaulting to type: {DEFAULT_TYPE}...")

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
        if isinstance(value, self._obj_type):
            return value
        raise TypeError(f"Type {self._obj_type.__name__} expected, got {type(value).__name__}")

    def for_each(self, func):
        for item in self:
            func(item)


if __name__ == "__main__":
    obj = "whatever"
    sb_list = SimBodyList([], obj)
    print(sb_list)
