from abc import abstractmethod
from collections import UserDict
from simbody_model import SimBody


class SimBodyDict(dict):

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

    @abstractmethod
    def _set_parentage(self, simbody):
        pass

    @property
    def body(self):
        return [sb.body for sb in self.data.values()]

    def radius(self):
        return [sb.rad_set for sb in self.data.values()]

    def rad(self):
        return [sb.rad_set[0] for sb in self.data.values()]

    def parent(self):
        return [sb.parent for sb in self.data.values()]

    def type(self):
        return [sb.type for sb in self.data.values()]

    def pos(self):
        return [sb.pos for sb in self.data.values()]

    def vel(self):
        return [sb.vel for sb in self.data.values()]

    def rot(self):
        return [sb.rot for sb in self.data.values()]

    def state(self):
        return [sb.state_matrix for sb in self.data.values()]

    def body_mark(self):
        return [sb.body_mark for sb in self.data.values()]

    def body_color(self):
        return [sb.body_color for sb in self.data.values()]

    def body_alpha(self):
        return [sb.body_alpha for sb in self.data.values()]

    def track_color(self):
        return [sb.track_color for sb in self.data.values()]

    def track_alpha(self):
        return [sb.track_alpha for sb in self.data.values()]

    def track_data(self):
        return [sb.track_data for sb in self.data.values()]

    def elem_coe(self):
        return [sb.elem_coe for sb in self.data.values()]

    def elem_pqw(self):
        return [sb.elem_pqw for sb in self.data.values()]

    def elem_rv(self):
        return [sb.elem_rv for sb in self.data.values()]


if __name__ == "__main__":
    bodies = {"Earth": SimBody(), "Mars": SimBody()}

    simbody_dict = SimBodyDict(bodies)

    print(simbody_dict["Earth"])