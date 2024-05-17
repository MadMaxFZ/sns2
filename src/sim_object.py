
import logging
import numpy as np
from poliastro.constants import J2000_TDB
from poliastro.ephem import *
from astropy import units as u
from astropy.time import Time
from abc import ABC, abstractmethod, abstractproperty


logging.basicConfig(filename="../logs/sns_simobj.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )

vec_type = type(np.zeros((3,), dtype=np.float64))


class SimObject(ABC):
    """
        This is a base class for SimBody, SimShip and any other gravitationally affected objects in the sim.
    """
    #
    # curr_camera = None
    epoch0 = J2000_TDB.jd
    system = {}
    # created = pyqtSignal(str)
    _fields = ('attr',
               'pos',
               'rot',
               'elem',
               )

    def __init__(self, *args, **kwargs):
        super(SimObject, self).__init__(*args, **kwargs)
        self._is_primary    = False
        self._RESAMPLE      = False
        self._parent        = None
        self._name          = ""
        self.x_ax           = np.array([1, 0, 0])
        self.y_ax           = np.array([0, 1, 0])
        self.z_ax           = np.array([0, 0, 1])
        self._dist_unit     = u.km
        self._plane         = Planes.EARTH_ECLIPTIC
        self._epoch         = Time(SimObject.epoch0, format='jd', scale='tdb')
        self._state         = np.zeros((3,), dtype=vec_type)
        self._periods       = 365
        self._o_period      = 1.0 * u.year
        self._spacing       = self._o_period.to(u.d) / self._periods
        self._end_epoch     = self._epoch + self._periods * self._spacing
        self._ephem         = None
        self._orbit         = None
        self._trajectory    = None
        self._field_dict    = None

    @abstractmethod
    def set_field_dict(self):
        pass

    @abstractmethod
    def field(self, field_key):
        pass

    @abstractmethod
    def set_ephem(self, epoch=None, t_range=None):
        pass

    @abstractmethod
    def set_orbit(self, ephem=None):
        pass

    @classmethod
    def _system(cls, _name):
        return cls.system[_name]

    @abstractmethod
    def update_state(self, epoch=None):
        pass

    @abstractmethod
    def get_field(self, f):
        pass

    @property
    def name(self):
        return self._name

    @property
    def dist_unit(self):
        return self._dist_unit
    
    @dist_unit.setter
    def dist_unit(self, new_du):
        if type(new_du) == u.Unit:
            self._dist_unit = new_du

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, new_parent=None):
        if type(new_parent) is SimObject:
            self._parent = new_parent

    def set_parent(self, new_parent=None):
        self._parent = new_parent

    @property
    def r(self):
        return self._state[0] * self._dist_unit

    @property
    def v(self):
        return self._state[1] * self._dist_unit / u.s

    @property
    def pos(self):
        return self._state[0] * self._dist_unit

    @property
    def rot(self):
        return self._state[2]

    @property
    def axes(self):
        return self.x_ax, self.y_ax, self.z_ax, self.z_ax       # what's up with this?

    @property
    def track(self):
        if self._trajectory:
            return self._trajectory.xyz.transpose().value

    @property
    def plane(self):
        return self._plane

    @plane.setter
    def plane(self, new_plane=None):
        self._plane = new_plane

    @property
    def spacing(self):
        return self._spacing

    @property
    def RESAMPLE(self):
        return self._RESAMPLE

    @RESAMPLE.setter
    def RESAMPLE(self, new_sample=True):
        self._RESAMPLE = True

    @property
    def epoch(self):
        return self._epoch

    @epoch.setter
    def epoch(self, new_epoch=None):
        if new_epoch is None:
            new_epoch = SimObject.epoch0
        if type(new_epoch) == Time:
            if new_epoch > self._end_epoch:
                self.set_ephem(new_epoch)
            self._epoch = Time(new_epoch,
                               format='jd',
                               scale='tdb',
                               )

    @property
    def end_epoch(self):
        return self._end_epoch

    @end_epoch.setter
    def end_epoch(self, new_end=None):
        if type(new_end) == Time:
            self._end_epoch = new_end

    @property
    @abstractproperty
    def elem_coe(self):
        pass

    @property
    @abstractproperty
    def elem_pqw(self):
        pass

    @property
    @abstractproperty
    def elem_rv(self):
        pass

    @property
    def ephem(self):
        return self._ephem

    @property
    def orbit(self):
        return self._orbit

    @property
    def state(self):
        return self._state

    @property
    def dist2parent(self):
        return np.linalg.norm(self.pos)

    @property
    def vel(self):
        """
        TODO:  make this a property that returns the velocity of the body relative to system primary
        Returns
        -------
        velocity of biody relative to its parent body
        """
        return self._state[1] * self._dist_unit

    @epoch.setter
    def epoch(self, e=None):
        if type(e) == Time:
            self._epoch = e


if __name__ == "__main__":

    def main():
        pass
        #     sb = SimBody(body_data=sys_data.body_data(bod_name))
        #     sb.update_state(sb)
        # print(sb.orbit)


    main()
    print("SimBody doesn't really do much...")
