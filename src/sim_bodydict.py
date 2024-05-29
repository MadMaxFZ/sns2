import time
import numpy as np
from psygnal import Signal
from astropy.coordinates import solar_system_ephemeris
from astropy.time import Time
from sim_body import SimBody
from datastore import vec_type, SystemDataStore
from concurrent.futures import ThreadPoolExecutor


class SimBodyDict(dict):

    has_updated = Signal()

    def __init__(self, epoch=None, data=None, ref_data=None, body_names=None, use_multi=False, auto_up=False):
        super().__init__()
        solar_system_ephemeris.set("jpl")
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
        self._sys_primary = None
        self._dist_unit = self.ref_data.dist_unit
        self._vec_type = self.ref_data.vec_type
        self._valid_body_names = self.ref_data.body_names

        if body_names:
            self._current_body_names = tuple([n for n in body_names if n in self._valid_body_names])
        else:
            self._current_body_names = tuple(self._valid_body_names)

        self._body_count = len(self._current_body_names)
        self._sys_rel_pos = np.zeros((self._body_count, self._body_count),
                                     dtype=vec_type)
        self._sys_rel_vel = np.zeros((self._body_count, self._body_count),
                                     dtype=vec_type)
        self._bod_tot_acc = np.zeros((self._body_count,),
                                     dtype=vec_type)
        if epoch:
            self._sys_epoch = epoch
        else:
            self._sys_epoch = Time(self.ref_data.default_epoch, format='jd', scale='tdb')

        self._base_t = 0
        self._t1 = 0
        self.USE_AUTO_UPDATE_STATE = auto_up
        self._IS_POPULATED = False
        self._HAS_INIT = False
        self._IS_UPDATING = False
        self._USE_LOCAL_TIMER = False
        self._USE_MULTIPROC = use_multi
        self.executor = ThreadPoolExecutor(max_workers=6)

    def __setitem__(self, name, simbody):
        self.data[name] = self._validate_simbody(simbody)

    def __getitem__(self, name):
        return self.data[name]

    '''===== METHODS ==========================================================================================='''

    @staticmethod
    def _validate_simbody(simbody):
        if not isinstance(simbody, SimBody):
            raise TypeError("SimBody object expected")
        return simbody

    def load_from_names(self, _body_names: list = None) -> None:
        """
            This method creates one or more SimBody objects based upon the provided list of names.
            CONSIDER: Should this be a class method that returns a SimSystem() when given names?

        Parameters
        ----------
        _body_names :

        Returns
        -------
        nothing     : Leaves the model usable with SimBody objects loaded
        """
        if _body_names is None:
            self._current_body_names = self._valid_body_names
        else:
            self._current_body_names = [n for n in _body_names if n in self._valid_body_names]

        # populate the list with SimBody objects
        self.data.clear()
        [self.data.update({body_name: SimBody(body_data=self.ref_data.body_data[body_name],
                                              vizz_data=self.ref_data.vizz_data()[body_name])})
         for body_name in self._current_body_names]

        self._body_count = len(self.data)
        # self._sys_primary = [sb for sb in self.data.values() if sb.body.parent is None][0]
        self.set_parentage()
        self._IS_POPULATED = True

        self.update_state(epoch=self._sys_epoch)
        self._HAS_INIT = True
        # self.set_field_dict()

    def update_state(self, epoch):
        self._base_t = self._t1
        _tx = time.perf_counter()

        if self._USE_MULTIPROC:
            futures = [self.executor.submit(sb.update_state, epoch=epoch) for sb in self.data.values()]
            for future in futures:
                future.result()
        else:
            [sb.update_state(epoch) for sb in self.data.values()]

        self._t1 = time.perf_counter()
        update_time = self._t1 - self._base_t
        print(f'\n\t\t> Frame Rate: {1 / update_time:.4f} FPS (1/{update_time:.4f})\n'
              f'  Model updated in {self._t1 - _tx:.4f} seconds...')
        self.has_updated.emit(update_time)

    def set_parentage(self):
        self._sys_primary = None
        for sb in self.data.values():
            if sb.body.parent:
                sb.parent = self.data[sb.body.parent.name]
            else:
                self._sys_primary = sb

    '''===== PROPERTIES ==========================================================================================='''

    @property
    def primary(self):
        return self._sys_primary

    @property
    def body(self):
        return [sb.body for sb in self.data.values()]

    @property
    def radius(self):
        return [sb.rad_set for sb in self.data.values()]

    @property
    def rad(self):
        return [sb.rad_set[0] for sb in self.data.values()]

    @property
    def parent(self):
        return [sb.parent for sb in self.data.values()]

    @property
    def type(self):
        return [sb.type for sb in self.data.values()]

    @property
    def pos(self):
        return [sb.pos for sb in self.data.values()]

    @property
    def vel(self):
        return [sb.vel for sb in self.data.values()]

    @property
    def rot(self):
        return [sb.rot for sb in self.data.values()]

    @property
    def state(self):
        return [sb.state_matrix for sb in self.data.values()]

    @property
    def track_data(self):
        return [sb.track_data for sb in self.data.values()]

    @property
    def elem_coe(self):
        return [sb.elem_coe for sb in self.data.values()]

    @property
    def elem_pqw(self):
        return [sb.elem_pqw for sb in self.data.values()]

    @property
    def elem_rv(self):
        return [sb.elem_rv for sb in self.data.values()]

    # The following properties should me relocated into the StarSysVisual class
    # since they do not apply to the SimSystem itself, only the rendering
    @property
    def body_mark(self):
        return [sb.body_mark for sb in self.data.values()]

    @property
    def body_color(self):
        return [sb.body_color for sb in self.data.values()]

    @property
    def body_alpha(self):
        return [sb.body_alpha for sb in self.data.values()]

    @property
    def track_color(self):
        return [sb.track_color for sb in self.data.values()]

    @property
    def track_alpha(self):
        return [sb.track_alpha for sb in self.data.values()]


if __name__ == "__main__":
    bodies = {"Earth": SimBody(), "Mars": SimBody()}

    simbody_dict = SimBodyDict(bodies)

    print(simbody_dict["Earth"])