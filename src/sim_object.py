import logging

logging.basicConfig(filename="../logs/sns_simobj.log",
                    level=logging.ERROR,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )

import numpy as np
from poliastro.constants import J2000_TDB
from poliastro.ephem import *
from astropy import units as u
from astropy.time import Time
from poliastro.bodies import Body
from abc import ABC, abstractmethod

VEC_TYPE = type(np.zeros((3,), dtype=np.float64))
MIN_SIZE = 0.001 # * u.km
BASE_DIMS = np.ndarray((3,), dtype=np.float64)


class SimObject(ABC):
    """
        This is a base class for SimBody, SimShip and any
        other gravitationally affected objects in the sim.
        This base class exists to contain the necessary data to
        define an object's orbital state about a parent attractor object.
        This will allow for celestial bodies and maneuverable spacecraft to
        operate within a common model while allowing for subclasses that can
        have differing behaviors and specific attributes.

    """
    epoch0 = J2000_TDB.jd
    system = {}
    dist_unit = u.km
    # created = pyqtSignal(str)
    _fields = ('attr',
               'pos',
               'rot',
               'elem',
               )

    def __init__(self, *args, **kwargs):
        self._name       = ""
        self._dist_unit  = u.km
        super(SimObject, self).__init__(*args, **kwargs)
        self._epoch      = Time(SimObject.epoch0, format='jd', scale='tdb')
        self._state      = np.zeros((3,), dtype=VEC_TYPE)
        self._rad_set    = [MIN_SIZE, ] * 3
        self._plane      = Planes.EARTH_ECLIPTIC
        self._body       = None
        self._rank       = False
        self._RESAMPLE   = False
        self._parent     = None
        self._sim_parent = None
        self._rot_func   = None
        self._type       = None
        self._ephem      = None
        self._orbit      = None
        self._trajectory = None
        self._field_dict = None
        self._periods    = 365
        self._o_period   = 1.0 * u.year
        self._spacing    = self._o_period.to(u.d) / self._periods
        self._end_epoch  = self._epoch + self._periods * self._spacing
        self._axes       = np.identity(4, dtype=np.float64)
        # for some reason this slowed things down a lot
        self.x_ax        = self._axes[0:3, 0]
        self.y_ax        = self._axes[0:3, 1]
        self.z_ax        = self._axes[0:3, 2]
        pass

    if __name__ != "__main__":
        @abstractmethod
        def set_dimensions(self, dims=BASE_DIMS):
            if dims.shape == BASE_DIMS.shape:
                self._rad_set = dims
            else:
                self._rad_set = BASE_DIMS

        @abstractmethod
        def set_ephem(self, epoch=None, t_range=None):
            pass

        @abstractmethod
        def set_orbit(self, ephem=None):
            pass

        @abstractmethod
        def update_state(self, epoch=None):
            pass

    @property
    def name(self):
        return self._name

    @property
    def dist_unit(self):
        return self._dist_unit

    # @dist_unit.setter
    # def dist_unit(self, new_du):
    #     if type(new_du) == u.Unit:
    #         self._dist_unit = new_du

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
        return self.x_ax, self.y_ax, self.z_ax, self.z_ax  # what's up with this?

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
    def elem_coe(self):
        pass

    @property
    def elem_pqw(self):
        pass

    @property
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
        return np.linalg.norm(self.pos)         # dist unit here??

    @property
    def vel(self):
        """
        TODO:  make this a property that returns the velocity of the body relative to system primary
        Returns
        -------
        velocity of body relative to its parent body
        """
        return self._state[1] * self._dist_unit / u.s

    @epoch.setter
    def epoch(self, e=None):
        if type(e) == Time:
            self._epoch = e


if __name__ == "__main__":
    def main():
        simobj = SimObject()
        for k, v in simobj.__dict__.items():
            print(f"{k} :\t\t\t{v}")
        pass

    main()
    print("SimObject.__main__ complete...")
