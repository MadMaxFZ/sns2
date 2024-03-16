# starsystem.py
import psygnal
from starsys_data import *
from src.simbody_list import SimBodyList
from sysbody_model import SimBody
from astropy.coordinates import solar_system_ephemeris
from astropy.time import Time


class SimSystem(SimBodyList):
    """
    """
    _body_count: int = 0
    initialized = psygnal.Signal(list)
    updating    = psygnal.Signal(Time)
    ready       = psygnal.Signal(float)
    data_return = psygnal.Signal(list, list)

    def __init__(self, body_names=None, multi=False):
        """

        Parameters
        ----------
        body_names :
        """
        if not body_names:
            self._current_body_names = sys_data.body_names
        else:
            self._current_body_names = [n for n in body_names if n in sys_data.body_names]

        super(SimSystem, self).__init__([])   # iterable=self._body_names)
        self._IS_POPULATED    = False
        self._HAS_INIT        = False
        self._IS_UPDATING     = False
        self._USE_LOCAL_TIMER = False
        self._USE_MULTIPROC   = multi
        self._USE_AUTO_UPDATE_STATE = False
        self._sys_epoch = Time(sys_data.default_epoch, format='jd', scale='tdb')
        print(f'BODY_NAMES: {self._current_body_names}')
        self.load_from_names(self._current_body_names)

        self._sys_rel_pos = np.zeros((self._body_count, self._body_count),
                                     dtype=vec_type)
        self._sys_rel_vel = np.zeros((self._body_count, self._body_count),
                                     dtype=vec_type)
        self._bod_tot_acc = np.zeros((self._body_count,),
                                     dtype=vec_type)
        
        self.update(self._sys_epoch)

    def load_from_names(self, _body_names):
        """

        Parameters
        ----------
        _body_names :

        Returns
        -------

        """
        solar_system_ephemeris.set("jpl")
        _valid_names = sys_data.body_names
        if _body_names is None:
            _body_names = self._current_body_names

        # print(f'body_names: {body_names}\n_valid_names: {_valid_names}')
        # populate the list with SimBody objects
        [self.data.append(SimBody(body_data=sys_data.body_data(body_name)))
         for body_name in (_body_names and _valid_names)]
        for n in self._current_body_names:
            assert (n in _body_names)
        self._current_body_names = tuple([sb.name for sb in self.data])
        self._body_count = len(self.data)

        [self._set_parentage(sb) for sb in self.data if sb.body.parent]
        self._IS_POPULATED = True

        self.update(epoch=self._sys_epoch)
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
                sb.sb_parent = self.data[self._current_body_names.index(this_parent.name)]
                if sb.sb_parent.type == 'star':
                    sb.type = 'planet'
                elif sb.sb_parent.type == 'planet':
                    sb.type = 'moon'
                    if this_parent.name == "Earth":
                        sb.plane = Planes.EARTH_EQUATOR

    def update(self, epoch=None):
        if epoch:
            if type(epoch) == Time:
                self._sys_epoch = epoch
        else:
            epoch = self._sys_epoch

        for sb in self.data:
            sb.epoch = epoch
            sb.update_state(sb, epoch)

    @property
    def body_names(self):
        return self._current_body_names


if __name__ == "__main__":
    model = SimSystem()
