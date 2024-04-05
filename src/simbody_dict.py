from collections import UserDict
from simbody_model import SimBody


class SimBodyDict(UserDict):

    def __init__(self, data=None):
        super().__init__()
        if data:
            self.data = {name: self._validate_simbody(simbody)
                         for name, simbody in data.items()}
        else:
            self.data = {}

    def __setitem__(self, name, simbody):
        self.data[name] = self._validate_simbody(simbody)

    def __getitem__(self, name):
        return self.data[name]

    def _validate_simbody(self, simbody):
        if not isinstance(simbody, SimBody):
            raise TypeError("SimBody object expected")
        return simbody


if __name__ == "__main__":
    bodies = {"Earth": SimBody(), "Mars": SimBody()}

    simbody_dict = SimBodyDict(bodies)

    print(simbody_dict["Earth"])