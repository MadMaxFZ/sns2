from abc import abstractmethod
from collections import UserDict
import numpy as np
from simbody_model import SimBody
from starsys_data import vec_type, SystemDataStore, Planes


class SimBodyDict(dict):

    def __init__(self, data=None, ref_data=None, use_multi=False, auto_up=False):
        super().__init__()
        if data:
            self.data = {name: self._validate_simbody(simbody)
                         for name, simbody in data.items()}
        else:
            self.data = {}

        if ref_data:
            if isinstance(ref_data, SystemDataStore):
                print('<sys_date> input is valid...')
            else:
                print('Bad <sys_data> input... Reverting to defaults...')
                ref_data = SystemDataStore()

        else:
            ref_data = SystemDataStore()

        self.ref_data = ref_data
        self._dist_unit = self.ref_data.dist_unit
        self._vec_type = self.ref_data.vec_type
        self._body_count = self.ref_data.body_count
        self._USE_AUTO_UPDATE_STATE = auto_up
        self._IS_POPULATED = False
        self._HAS_INIT = False
        self._IS_UPDATING = False
        self._USE_LOCAL_TIMER = False
        self._USE_MULTIPROC = use_multi
        self._sys_primary = None
        self._sys_rel_pos = np.zeros((self._body_count, self._body_count),
                                     dtype=vec_type)
        self._sys_rel_vel = np.zeros((self._body_count, self._body_count),
                                     dtype=vec_type)
        self._bod_tot_acc = np.zeros((self._body_count,),
                                     dtype=vec_type)

    def __setitem__(self, name, simbody):
        self.data[name] = self._validate_simbody(simbody)

    def __getitem__(self, name):
        return self.data[name]

    def _validate_simbody(self, simbody):
        if not isinstance(simbody, SimBody):
            raise TypeError("SimBody object expected")
        return simbody

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