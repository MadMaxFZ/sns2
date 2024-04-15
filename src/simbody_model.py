
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


logging.basicConfig(filename="../logs/sns_defs.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )

MIN_FOV = 1 / 3600      # I think this would be arc-seconds
vec_type = type(np.zeros((3,), dtype=np.float64))


def toTD(epoch=None):
    d = (epoch - J2000_TDB).jd
    T = d / 36525
    return dict(T=T, d=d)


class SimBody:
    """
        TODO: Provide a class method to create a SimBody based upon
              a provided Body object.
    """
    #
    # curr_camera = None
    epoch0 = J2000_TDB
    system = {}
    # created = pyqtSignal(str)
    _fields = ('attr',
               'pos',
               'rot',
               'elem',
               )

    def __init__(self, body_data=None, vizz_data=None,):
        self._is_primary    = False
        self._prev_update   = None
        self._RESAMPLE      = False
        self._sb_parent     = None
        self._sys_primary   = None
        self._body_data     = body_data
        self._name          = self._body_data['body_name']
        self._body          = self._body_data['body_obj']
        self._rot_func      = self._body_data['rot_func']
        self._o_period      = self._body_data['o_period']
        self.x_ax           = np.array([1, 0, 0])
        self.y_ax           = np.array([0, 1, 0])
        self.z_ax           = np.array([0, 0, 1])
        self._dist_unit     = u.km
        self._plane         = Planes.EARTH_ECLIPTIC
        self._epoch         = Time(SimBody.epoch0, format='jd', scale='tdb')
        self._state         = np.zeros((3,), dtype=vec_type)
        self._periods       = 365
        self._spacing       = self._o_period.to(u.d) / self._periods
        self._t_range       = None
        self._end_epoch     = self._epoch + self._periods * self._spacing
        self._ephem: Ephem  = None
        self._orbit: Orbit  = None
        self._trajectory    = None
        self._rad_set       = None
        self._type          = None
        self._curr_cam_id   = None
        self._vizz_data     = vizz_data
        self.set_radius()
        self.set_ephem(epoch=self._epoch, t_range=self._t_range)
        self.set_orbit(ephem=self._ephem)
        self._field_dict = None
        # SimBody.system[self._name] = self
        # self.created.emit(self.name)

    def set_field_dict(self):
        self._field_dict = {'attr_': [self.body[i] for i in range(len(self.body._fields))],
                            'pos': self.pos.value.round(4) * u.km,
                            'rot': self.rot,
                            'rad': self.body.R,
                            'radii': self._rad_set,
                            }
        if self.body.parent:
            # _orb = self._orbit.classical()
            # _orb.extend(self._orbit.pqw())
            # _orb.extend(self._orbit.rv())
            # _elem = self.elems
            self._field_dict.update({'elem_coe_': self.elem_coe})
            self._field_dict.update({'elem_pqw_': self.elem_pqw})
            self._field_dict.update({'elem_rv_': self.elem_rv})

    def field(self, field_key):
        if field_key in self._field_dict.keys():
            return self._field_dict[field_key]
        else:
            print(f'No field with name: <{field_key}>')
            return None

    def set_radius(self):
        if (self._name == 'Sun' or self._type == 'star' or
                (self._body.R_mean.value == 0 and self._body.R_polar.value == 0)):
            R  = self._body.R.to(self._dist_unit)
            Rm = Rp = R
            self._is_primary = True
        else:
            R  = self._body.R.to(self._dist_unit)
            Rm = self._body.R_mean.to(self._dist_unit)
            Rp = self._body.R_polar.to(self._dist_unit)

        self._rad_set = [R, Rm, Rp,]
        self._body_data.update({'rad_set': self._rad_set})
        logging.info("RADIUS SET: %s", self._rad_set)

    def set_ephem(self, epoch=None, t_range=None):
        if epoch is None:
            epoch = self._epoch
        if t_range is None:
            self._t_range = time_range(epoch,
                                       periods=self._periods,
                                       spacing=self._spacing,
                                       format='jd',
                                       scale='tdb',
                                       )
            self._end_epoch += self._periods * self._spacing

        if self._orbit is None:
            self._ephem = Ephem.from_body(self._body,
                                          epochs=self._t_range,
                                          attractor=self.body.parent,
                                          plane=self._plane,
                                          )
        elif self._orbit != 0:
            self._ephem = Ephem.from_orbit(orbit=self._orbit,
                                           epochs=self._t_range,
                                           plane=self._plane,
                                           )

        logging.info("EPHEM for %s: %s", self.name, str(self._ephem))
        print(f'EPHEM for {self.name:^9}: {self._ephem}')

    def set_orbit(self, ephem=None):
        if ephem is None:
            ephem = self._ephem

        if self.body.parent is not None:
            self._orbit = Orbit.from_ephem(self.body.parent,
                                           ephem,
                                           self._epoch,
                                           )
            # print(self._orbit)
            logging.info(">>> COMPUTING ORBIT: %s",
                         str(self._orbit))
            if (self._trajectory is None) or (self._RESAMPLE is True):
                self._trajectory = self._orbit.sample(360)
                self._RESAMPLE = False

        elif self._body.parent is None:
            self._orbit = 0
            logging.info(">>> NO PARENT BODY, Orbit set to: %s",
                         str(self._orbit))

    @classmethod
    def _system(cls, _name):
        return cls.system[_name]

    def update_state(self, epoch=None):
        """

        Parameters
        ----------
        simbody         :   SimBody         An instance of a SimBody object
        epoch           :   Time            The epoch to which the state is to be set

        Returns
        -------
        simbody._state  : np.ndarray(3, 3)  The state matrix for the new Simbody state
        """
        if epoch:
            if type(epoch) == Time:
                self._epoch = epoch

            if type(self._orbit) == Orbit:
                new_orbit = self._orbit.propagate(self._epoch)
                new_state = np.array([new_orbit.r.to(self._dist_unit).value,
                                      new_orbit.v.to(self._dist_unit / u.s).value,
                                      self._rot_func(**toTD(self._epoch)),
                                      ])
                self._orbit = new_orbit
            else:
                new_state = np.array([self._ephem.rv(self._epoch)[0].to(self._dist_unit).value,
                                      self._ephem.rv(self._epoch)[1].to(self._dist_unit / u.s).value,
                                      self._rot_func(**toTD(self._epoch)),
                                      ])

        # self.update_pos(self._state.[0])
        logging.info("Outputting state for\nBODY:%s\nEPOCH:%s\n||POS||:%s\n||VEL||:%s\nROT:%s\n",
                     self,
                     self._epoch,
                     np.linalg.norm(new_state[0]),
                     np.linalg.norm(new_state[1]),
                     new_state[2],
                     )
        self._state = new_state

        return self._state

    def get_field(self, f):
        match f:
            case 'rel2cam':
                return self.rel2cam
            case 'pos':
                return self.pos
            case 'rot':
                return self._state[2]
            case 'track':
                return self.track

    @property
    def name(self):
        return self._name

    @property
    def body(self):
        return self._body

    @property
    def radius(self):
        return self._rad_set

    @property
    def dist_unit(self):
        return self._dist_unit

    @property
    def sb_parent(self):
        return self._sb_parent

    @sb_parent.setter
    def sb_parent(self, new_sb_parent=None):
        if type(new_sb_parent) is SimBody:
            self._sb_parent = new_sb_parent

    def set_parent(self, new_sb_parent=None):
        self._sb_parent = new_sb_parent

    @property
    def sys_primary(self):
        return self._sys_primary

    @sys_primary.setter
    def sys_primary(self, new_primary):
        self._sys_primary = new_primary

    @property
    def is_primary(self):
        return self._is_primary

    @is_primary.setter
    def is_primary(self, is_pri):
        if type(is_pri) == bool:
            self._is_primary = is_pri

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, new_type=None):
        self._type = new_type

    @property
    def r(self):
        return self._state[0]

    @property
    def v(self):
        return self._state[1]

    @property
    def pos(self):
        return self.pos2primary

    @property
    def rot(self):
        return self._state[2]

    @property
    def axes(self):
        return self.x_ax, self.y_ax, self.z_ax, self.z_ax

    @property
    def track(self):
        if self._trajectory:
            return self._trajectory.xyz.transpose().value

    @property
    def RA(self):
        return self._state[2, 0]

    @property
    def DEC(self):
        return 90 - self._state[2, 1]

    @property
    def W(self):
        return self._state[2, 2]

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

    @property                   # this returns the position of a body plus the position of the primary
    def pos2primary(self):
        _pos = self._state[0] * self._dist_unit
        if self.body.parent is None:
            return _pos
        else:
            return _pos + self.sb_parent.pos2primary

    @property                   # this returns the position of a body relative to system barycenter
    def pos2bary(self):
        _pos = self._state[0] * self._dist_unit
        if self.is_primary:
            return _pos
        else:
            return _pos + self._sys_primary.pos

    @property
    def epoch(self):
        return self._epoch

    @epoch.setter
    def epoch(self, new_epoch=None):
        if new_epoch is None:
            new_epoch = SimBody.epoch0
        if type(new_epoch) == Time:
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
    def t_range(self):
        return self._t_range

    @t_range.setter
    def t_range(self, periods=None, spacing=None, ):
        if type(periods) == int:
            self._t_range = time_range(self._epoch,
                                       periods=periods,
                                       # TODO:  spacing = orbital_period / periods
                                       #        reset value once orbital period it known
                                       spacing=spacing,
                                       format='jd',
                                       scale='tdb', )

    @property
    def elem_coe(self):
        if self._is_primary:
            res = np.zeros((6,), dtype=np.float64)
        else:
            res = list(self._orbit.classical())

        return res

    @property
    def elem_pqw(self):
        if self._is_primary:
            res = np.zeros((3, 3), dtype=np.float64)
        else:
            res = list(self._orbit.pqw())

        return res

    @property
    def elem_rv(self):
        res = list(self._orbit.rv())

        return res

    @property
    def ephem(self):
        return self._ephem

    @property
    def orbit(self):
        return self._orbit

    @property
    def state_matrix(self):
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

    @property
    def body_alpha(self):
        return self._vizz_data['body_alpha']

    @property
    def track_alpha(self):
        return self._vizz_data['track_alpha']

    @property
    def body_mark(self):
        return self._vizz_data['body_mark']

    @property
    def body_color(self):
        res = Color(self._vizz_data['body_color'])
        res.alpha = self._vizz_data['body_alpha']

        return res


if __name__ == "__main__":

    def main():
        pass
        #     sb = SimBody(body_data=sys_data.body_data(bod_name))
        #     sb.update_state(sb)
        # print(sb.orbit)


    main()
    print("SimBody doesn't really do much...")
