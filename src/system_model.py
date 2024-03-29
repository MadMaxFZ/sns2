# system_model.py
import time
import urllib.parse

import psygnal
import src.starsys_data as data_store
from src.starsys_data import *
from src.simbody_dict import SimBodyDict        #   TODO::
from src.sysbody_model import SimBody
from vispy.color import *
from astropy.coordinates import solar_system_ephemeris
from astropy.time import Time


class SimSystem(SimBodyDict):
    """
    """
    initialized = psygnal.Signal(list)
    has_updated = psygnal.Signal(Time)
    panel_data = psygnal.Signal(list, list)
    _body_count: int = 0

    def __init__(self, sys_data=None, epoch=None, body_names=None, use_multi=False):
        """
            Initialize a star system model to include SimBody objects indicated by a list of names.
            If no list of names is provided, the complete default star system will be loaded.
            The 'multi' argument indicates if the multiprocessing routines should be used or not.

        Parameters
        ----------
        epoch        : Time     #   Epoch of the system.
        body_names   : list     #   List of names of bodies to include in the model.
        use_multi    : bool     #   If True, use multiprocessing to speed up calculations.
        """
        t0 = time.perf_counter()
        super(SimSystem, self).__init__([])
        self._IS_POPULATED = False
        self._HAS_INIT = False
        self._IS_UPDATING = False
        self._USE_LOCAL_TIMER = False
        self._USE_MULTIPROC = use_multi
        self._USE_AUTO_UPDATE_STATE = False
        self._sys_primary = None
        self._sys_rel_pos = None
        self._sys_rel_vel = None
        self._bod_tot_acc = None
        if sys_data:
            if isinstance(sys_data, SystemDataStore):
                print('<sys_date> input is valid...')
            else:
                print('Bad <sys_data> input... Reverting to defaults...')
                sys_data = SystemDataStore()

        else:
            sys_data = SystemDataStore()

        self.sys_data = sys_data
        self._dist_unit = self.sys_data.dist_unit
        self._vec_type = self.sys_data.vec_type

        if epoch:
            self._sys_epoch = epoch
        else:
            self._sys_epoch = Time(self.sys_data.default_epoch, format='jd', scale='tdb')

        self._valid_body_names = self.sys_data.body_names
        if body_names:
            self._current_body_names = tuple([n for n in body_names if n in self._valid_body_names])
        else:
            self._current_body_names = tuple(self._valid_body_names)

        self.load_from_names(self._current_body_names)
        t1 = time.perf_counter()
        print(f'SimSystem initialization took {t1 - t0:.6f} seconds...')

    def load_from_names(self, _body_names):
        """
            This method creates one or more SimBody objects based upon the provided list of names.
        Parameters
        ----------
        _body_names :

        Returns
        -------

        """
        solar_system_ephemeris.set("jpl")
        if _body_names is None:
            self._current_body_names = self._valid_body_names
        else:
            self._current_body_names = [n for n in _body_names if n in self._valid_body_names]

        # populate the list with SimBody objects
        self.data.clear()
        [self.data.update({body_name : SimBody(body_data=self.sys_data.body_data[body_name])})
         for body_name in self._current_body_names]
        self._body_count = len(self.data)
        self._sys_primary = [sb for sb in self.data.values() if sb.body.parent is None][0]
        [self._set_parentage(sb) for sb in self.data.values() if sb.body.parent]
        self._IS_POPULATED = True
        self._sys_rel_pos = np.zeros((self._body_count, self._body_count),
                                     dtype=self._vec_type)
        self._sys_rel_vel = np.zeros((self._body_count, self._body_count),
                                     dtype=self._vec_type)
        self._bod_tot_acc = np.zeros((self._body_count,),
                                     dtype=self._vec_type)
        self.update_state(epoch=self._sys_epoch)
        self._HAS_INIT = True

    def _set_parentage(self, sb):
        sb.plane = Planes.EARTH_ECLIPTIC
        this_parent = sb.body.parent
        if this_parent is None:
            sb.type = 'star'
            sb.sb_parent = None
            sb.is_primary = True
        else:
            if this_parent.name in self._current_body_names:
                sb.sb_parent = self.data[this_parent.name]
                if sb.sb_parent.type == 'star':
                    sb.type = 'planet'
                elif sb.sb_parent.type == 'planet':
                    sb.type = 'moon'
                    if this_parent.name == "Earth":
                        sb.plane = Planes.EARTH_EQUATOR

    def update_state(self, epoch=None):
        t0 = time.perf_counter()
        if epoch:
            if type(epoch) == Time:
                self._sys_epoch = epoch
        else:
            epoch = self._sys_epoch

        for sb in self.data.values():
            sb.epoch = epoch
            sb.update_state(sb, epoch)
        t1 = time.perf_counter()

        return (t1 - t0) * u.s

    # @pyqtSlot(list)
    @property
    def positions(self):
        """
        Returns
        -------
        dict    :   a dictionary of the positions of the bodies in the system keyed by name.
        """
        return dict.fromkeys([(sb.name, sb.r) for sb in self.data.values()])

    @property
    def radii(self):
        """
        Returns
        -------
        dict    :   a dictionary of the mean radius of the bodies in the system keyed by name.
        """
        return dict.fromkeys([(sb.name, sb.body.R) for sb in self.data.values()])

    @property
    def body_names(self):
        return tuple(self.data.keys())

    @property
    def system_primary(self):
        return self._sys_primary

    @property
    def tracks_data(self):
        """
        Returns
        -------
        dict    :   a dictionary of the orbit tracks of the bodies in the system keyed by name.
        """
        return dict.fromkeys(list(self.data.keys()),
                             [sb.track for sb in self.data.values()])

    def data_group(self, sb_name, tgt_key):
        """
            This method returns the data group associated with the provided body name and key.
        Parameters
        ----------
        sb_name :   the name of the SimBody object targeted
        tgt_key :   the key associated with the data group requested

        Returns
        -------
        data_list : a list containing the data associated with the provided body name and key.
        """
        return self.data[sb_name].field_dict[tgt_key]


if __name__ == "__main__":
    ref_time = time.time()
    model = SimSystem({})
    init_time = time.time() - ref_time
    model.update_state()
    done_time = time.time() - ref_time
    print(f"Setup time: {(init_time / 1e+09):0.4f} seconds")
    print(f'Update time: {(done_time / 1e+09):0.4f} seconds')
