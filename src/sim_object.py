
# x
import math
import logging
import numpy as np
import multiprocessing
# from starsys_data import vec_type
from poliastro.constants import J2000_TDB
from poliastro.ephem import *
from astropy import units as u
from astropy.time import Time, TimeDelta
from vispy.color import Color
# from starsys_data import sys_data
from poliastro.twobody.orbit.scalar import Orbit
from PyQt5.QtCore import pyqtSignal, QObject
from abc import ABC, abstractmethod, abstractproperty


logging.basicConfig(filename="../logs/sns_sdimobj.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )

# MIN_FOV = 1 / 3600      # I think this would be arc-seconds
vec_type = type(np.zeros((3,), dtype=np.float64))


# def toTD(epoch=None):
#     d = (epoch - J2000_TDB).jd
#     T = d / 36525
#     return dict(T=T, d=d)


class SimObject(ABC):
    """
        TODO: Provide a base class method to create a SimBody based upon
              a provided Body object.
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
        # self._field_dict = {    # 'attr_': [self.body[i] for i in range(len(self.body._fields))],
        #                     'pos': self.pos.value.round(4) * u.km,
        #                     'rot': self.rot,
        #                     # 'rad': self.body.R,
        #                     # 'radii': self._rad_set,
        #                     }
        # if self._parent:
        #     self._field_dict.update({'elem_coe_': self.elem_coe})
        #     self._field_dict.update({'elem_pqw_': self.elem_pqw})
        #     self._field_dict.update({'elem_rv_': self.elem_rv})

    @abstractmethod
    def field(self, field_key):
        pass
        # if field_key in self._field_dict.keys():
        #     return self._field_dict[field_key]
        # else:
        #     print(f'No field with name: <{field_key}>')
        #     return None

    @abstractmethod
    def set_ephem(self, epoch=None, t_range=None):
        pass
        # if epoch is None:
        #     epoch = self._epoch
        # if t_range is None:                    # sets t_range from epoch to epoch + orbital period
        #     t_range = time_range(epoch,
        #                          periods=self._periods,
        #                          spacing=self._spacing,
        #                          format='jd',
        #                          scale='tdb',
        #                          )
        #     self._end_epoch += self._periods * self._spacing
        #
        # if self._orbit is None:                                     # no orbit defined
        #     # TODO: Define a default Orbit  based upon vectors r and v
        #     # self._ephem = Ephem.from_body(self._body,
        #     #                               epochs=self._t_range,
        #     #                               attractor=self._parent,
        #     #                               plane=self._plane,
        #     #                               )
        #     pass
        # elif self._orbit != 0:                                      # this body has a parent
        #     self._ephem = Ephem.from_orbit(orbit=self._orbit,
        #                                    epochs=t_range,
        #                                    plane=self._plane,
        #                                    )
        #     Ephem.rv()
        # logging.info("EPHEM for %s: %s", self.name, str(self._ephem))
        # print(f'EPHEM for {self.name:^9}: {self._ephem}')

    @abstractmethod
    def set_orbit(self, ephem=None):
        pass
        # if ephem is None:
        #     ephem = self._ephem
        #
        # if self._parent is not None:
        #     self._orbit = Orbit.from_ephem(self._parent,
        #                                    ephem,
        #                                    self._epoch,
        #                                    )
        #     # print(self._orbit)
        #     logging.info(">>> COMPUTING ORBIT: %s",
        #                  str(self._orbit))
        #     if (self._trajectory is None) or (self._RESAMPLE is True):
        #         self._trajectory = self._orbit.sample(720)
        #         self._RESAMPLE = False
        #
        # elif self._parent is None:
        #     self._orbit = 0
        #     logging.info(">>> NO PARENT BODY, Orbit set to: %s",
        #                  str(self._orbit))

    @classmethod
    def _system(cls, _name):
        return cls.system[_name]

    @abstractmethod
    def update_state(self, epoch=None):
        pass
        # """
        #
        # Parameters
        # ----------
        # simbody         :   SimBody         An instance of a SimBody object
        # epoch           :   Time            The epoch to which the state is to be set
        #
        # Returns
        # -------
        # simbody._state  : np.ndarray(3, 3)  The state matrix for the new Simbody state
        # """
        # new_state = None
        # if epoch:
        #     if type(epoch) == Time:
        #         self._epoch = epoch
        #
        #     if type(self._orbit) == Orbit:
        #         new_orbit = self._orbit.propagate(self._epoch)
        #         new_state = np.array([new_orbit.r.to(self._dist_unit).value,
        #                               new_orbit.v.to(self._dist_unit / u.s).value,
        #                               [0.0, 0.0, 0.0],
        #                               ])
        #         self._orbit = new_orbit
        #     else:
        #         new_state = np.array([self._ephem.rv(self._epoch)[0].to(self._dist_unit).value,
        #                               self._ephem.rv(self._epoch)[1].to(self._dist_unit / u.s).value,
        #                               [0.0, 0.0, 0.0],
        #                               ])
        #
        # # self.update_pos(self._state.[0])
        # logging.info("Outputting state for\nBODY:%s\nEPOCH:%s\n||POS||:%s\n||VEL||:%s\nROT:%s\n",
        #              self,
        #              self._epoch,
        #              np.linalg.norm(new_state[0]),
        #              np.linalg.norm(new_state[1]),
        #              new_state[2],
        #              )
        # self._state = new_state
        #
        # return self._state

    @abstractmethod
    def get_field(self, f):
        pass
        # match f:
        #     # case 'rel2cam':
        #     #     return self.rel2cam
        #     case 'pos':
        #         return self.pos
        #     case 'rot':
        #         return self._state[2]
        #     case 'track':
        #         return self.track

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
            # self.update_state()

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

    # @property
    # def body_alpha(self):
    #     return self._vizz_data['body_alpha']
    #
    # @property
    # def track_alpha(self):
    #     return self._vizz_data['track_alpha']
    #
    # @property
    # def body_mark(self):
    #     return self._vizz_data['body_mark']
    #
    # @property
    # def body_color(self):
    #     res = Color(self._vizz_data['body_color'])
    #     res.alpha = self._vizz_data['body_alpha']
    #
    #     return res


if __name__ == "__main__":

    def main():
        pass
        #     sb = SimBody(body_data=sys_data.body_data(bod_name))
        #     sb.update_state(sb)
        # print(sb.orbit)


    main()
    print("SimBody doesn't really do much...")
