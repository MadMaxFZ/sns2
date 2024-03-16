
# x
import math
import logging
import numpy as np
import multiprocessing
# from starsys_data import *
from poliastro.constants import J2000_TDB
from poliastro.ephem import *
from astropy import units as u
from astropy.time import Time, TimeDelta
from vispy.geometry import MeshData
from starsys_data import sys_data
from poliastro.twobody.orbit.scalar import Orbit
from PyQt5.QtCore import pyqtSignal, QObject

logging.basicConfig(filename="logs/sns_defs.log",
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
    epoch0 = J2000_TDB
    system = {}
    # created = pyqtSignal(str)

    def __init__(self, body_data=None):
        # super(SimBody, self).__init__()
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
        self.set_radius()
        self.set_ephem(epoch=self._epoch, t_range=self._t_range)
        self.set_orbit(ephem=self._ephem)
        # SimBody.system[self._name] = self
        # self.created.emit(self.name)

    def set_radius(self):
        if (self._name == 'Sun' or self._type == 'star' or
                (self._body.R_mean.value == 0 and self._body.R_polar.value == 0)):
            R  = self._body.R.to(self._dist_unit).value
            Rm = Rp = R
            self._is_primary = True
        else:
            R  = self._body.R.to(self._dist_unit).value
            Rm = self._body.R_mean.to(self._dist_unit).value
            Rp = self._body.R_polar.to(self._dist_unit).value

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
        print("EPHEM for", self.name, ": ", self._ephem)

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
                self._trajectory = self._orbit.sample(360).xyz.transpose().value
                self._RESAMPLE = False

        elif self._body.parent is None:
            self._orbit = 0
            logging.info(">>> NO PARENT BODY, Orbit set to: %s",
                         str(self._orbit))

    @classmethod
    def _system(cls, _name):
        return cls.system[_name]

    @classmethod
    def update_state(cls, _name, epoch=None):
        simbody = _name
        if epoch:
            if type(epoch) == Time:
                simbody._epoch = epoch

        if type(simbody._orbit) == Orbit:
            new_orbit = simbody._orbit.propagate(simbody._epoch)
            simbody._state = np.array([new_orbit.r.to(simbody._dist_unit).value,
                                       new_orbit.v.to(simbody._dist_unit / u.s).value,
                                       simbody._rot_func(**toTD(simbody._epoch)),
                                       ])
            simbody._orbit = new_orbit
        else:
            simbody._state = np.array([simbody._ephem.rv(simbody._epoch)[0].to(simbody._dist_unit).value,
                                    simbody._ephem.rv(simbody._epoch)[1].to(simbody._dist_unit / u.s).value,
                                    simbody._rot_func(**toTD(simbody._epoch)),
                                    ])

        # self.update_pos(self._state.[0])
        logging.info("Outputting state for\nBODY:%s\nEPOCH:%s\n||POS||:%s\n||VEL||:%s\nROT:%s\n",
                     _name,
                     simbody._epoch,
                     np.linalg.norm(simbody._state[0]),
                     np.linalg.norm(simbody._state[1]),
                     simbody._state[2],
                     )
        return simbody._state

    def rel2pos(self, pos=None):
        if pos is None:
            pos = np.zeros((3,), dtype=vec_type)
        rel_pos = pos.value - self.pos2primary.value
        dist = np.linalg.norm(rel_pos)
        if dist < 1e-09:
            dist = 0.0 * self._dist_unit
            rel_pos = np.zeros((3,), dtype=vec_type)
            fov = MIN_FOV
        else:
            fov = np.float64(1.0 * math.atan(self.body.R.to(self._dist_unit).value / dist))

        return {"rel_pos": rel_pos,
                "dist": dist,
                "fov": fov,
                }

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
        self.sb_parent = new_sb_parent

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
        _pos = self.pos
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
    def t_range(self,
                periods=None,
                spacing=None, ):
        if type(periods) == int:
            self._t_range = time_range(self._epoch,
                                       periods=periods,
                                       # TODO:  spacing = orbital_period / periods
                                       #        reset value once orbital period it known
                                       spacing=spacing,
                                       format='jd',
                                       scale='tdb', )

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
    def pos(self):
        return self._state[0] * self._dist_unit

    @property
    def track(self):
        return self._trajectory

    @property
    def dist2parent(self):
        return np.linalg.norm(self.pos)

    @property
    def vel(self):
        """
        Returns
        -------
        velocity of biody rewlative to its parent body
        """
        return self._state[1] * self._dist_unit

    @epoch.setter
    def epoch(self, e=None):
        if type(e) == Time:
            self._epoch = e

    # @property
    # def texture(self):
    #     return self._tex_data
    #
    # @texture.setter
    # def texture(self, new_tex_data=None):
    #     self._tex_data = new_tex_data

    # @property
    # def colormap(self):
    #     return ColorArray(self._colormap)

    # @colormap.setter
    # def colormap(self, new_cmap=None):
    #     self._colormap = new_cmap
    #
    # @property
    # def periods(self):
    #     return self._periods

    # @property
    # def spacing(self):
    #     return self._spacing

    # @state.setter
    # def state(self, new_state=None):
    #     if (type(new_state)  == np.ndarray) and (new_state.shape == (3, 3)):
    #         self._state = new_state
    #     else:
    #         logging.info("!!!\t>> Incorrect state format. Ignoring...:<%s\n>",
    #                      new_state)
    #         pass

    # @periods.setter
    # def periods(self, p=None):
    #     if p is not None:
    #         self._periods = p
    #
    # @spacing.setter
    # def spacing(self, s=None):
    #     if s is not None:
    #         self._spacing = s
    # @property
    # def base_color(self):
    #     return self._base_color


def main():
    bod_name = "Earth"
    sb = SimBody(body_name=bod_name)


if __name__ == "__main__":

    main()
    print("SimBody doesn't really do much...")
