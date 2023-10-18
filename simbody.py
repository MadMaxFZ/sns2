import logging
import unittest.mock
import numpy as np

# from astropy.time import Time
# from poliastro.util import time_range
# from poliastro.constants import J2000_TDB
# from poliastro.constants import J2000_TDB
# from vispy.app.timer import *
# from data_functs import setup_datastore
# from multiprocessing import get_logger
# from astropy.coordinates import solar_system_ephemeris
# from astropy.coordinates.solar_system import get_body_barycentric_posvel
# import subprocess
from data_functs import *
from poliastro.ephem import *
from astropy.time import TimeDelta, Time
from poliastro.twobody.orbit.scalar import Orbit


# print(subprocess.run(["cp", "logs/sim_body.log", "logs/OLD_sim_body.log"]))
# print(subprocess.run(["rm", "logs/sim_body.log"]))
# print(subprocess.run(["touch", "logs/sim_body.log", ]))
logging.basicConfig(filename="logs/sim_body.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )


class SimBody:
    epoch0 = J2000_TDB
    # R_set = {}
    # simbods = {}

    # TODO: trim down extraneous arguments here:
    def __init__(self,
                 body_name=None,
                 epoch=None,
                 sim_param=None,
                 body_data=None,
                 ):

        if epoch is None:
            epoch = J2000_TDB
        self._sb_parent     = None
        self._name          = body_name
        self._body_data     = body_data
        self._body          = self._body_data['body_obj']
        self._rot_func      = self._body_data['rot_func']

        # self._tex_data      = self._body_data['tex_data']
        # self._viz_names     = self._body_data['viz_names']
        self._dist_unit     = sim_param["dist_unit"]
        self._periods       = sim_param["periods"]
        self._spacing       = sim_param["spacing"]
        self._FPS           = sim_param["fps"]
        self._t_span        = self._periods * self._spacing
        self._t_range       = None
        self._ephem         = None
        self._orbit         = None
        self._track         = None
        self._type          = None
        self._state         = None
        self._base_color    = self._body_data['body_color']
        self._body_symb     = None
        # self._vizuals      = {}
        # self._v_mult        = 2
        # self._xyz_mult      = 2
        self.x_ax           = np.array([1, 0, 0])
        self.y_ax           = np.array([0, 1, 0])
        self.z_ax           = np.array([0, 0, 1])
        self._epoch         = Time(epoch, format='jd', scale='tdb')
        self.RESAMPLE       = False

        if self._body.parent is None:
            self._type = "star"
            self._body_symb = 'star'
            self._sb_parent = None
        else:
            self._type = "planet"
            self._body_symb = 'o'
            self._sb_parent = self._body.parent

        if self._name == "Moon":
            self._plane = Planes.EARTH_EQUATOR
            self._body_symb = '+'
            self._type = "moon"
        else:
            self._plane = Planes.EARTH_ECLIPTIC
            self._body_symb = 'diamond'

        if self._name == 'Sun' or self._type == 'star':
            R = self._body.R.value
            Rm = Rp = R
        else:
            R = self._body.R.value
            Rm = self._body.R_mean.value
            Rp = self._body.R_polar.value

        r_set = [R, Rm, Rp,]
        self._body_data.update({'r_set' : r_set})
        # SimBody.simbods.update({self._name : self})
        self.set_time_range(epoch=self._epoch,
                            periods=self._periods,
                            spacing=self._spacing,
                            )
        self.set_ephem(t_range=self._t_range)
        if self._body.parent is not None:
            self.set_orbit(self._ephem)

    def update_state(self, epoch=None):
        self.set_epoch(epoch)
        logging.debug("\n\t\t\tBODY:\t%s\n\t\t\tEPOCH:\t%s\n\t\t\tEPHEM:\t%s",
                      self._name,
                      str(self._epoch),
                      self._ephem
                      )
        if self._orbit is not None:
            neworbit = self._orbit.propagate(self._epoch)
            self._state = np.array([neworbit.r.value,
                                    neworbit.v.value,
                                    self._rot_func(**toTD(self._epoch)),
                                    ])
            self._orbit = neworbit
        else:
            self._state = np.array([self._ephem.rv(self._epoch)[0].to(self._dist_unit),
                                    self._ephem.rv(self._epoch)[1].to(self._dist_unit / u.s),
                                    self._rot_func(**toTD(self._epoch)),
                                    ])
        # self.update_pos(self._state.[0])
        logging.debug("Outputting state for\nBODY:%s\nEPOCH:%s\nPOS:%s\n",  # VEL:%s\nROT:%s\n,
                      self._name,
                      self._epoch,
                      self._state[0],
                      # self._state[1],
                      # self._state[2],
                      )

    def set_epoch(self, epoch=None):
        if epoch is None:
            epoch = self._epoch
        self._epoch = Time(epoch,
                           format='jd',
                           scale='tdb',
                           )

    # def update_pos(self, pos=None):     # this doesn't get called
    #     pass

    def set_time_range(self,
                       epoch=None,
                       periods=None,
                       spacing=None,
                       ):
        logging.debug("set_time_range() at " + str(epoch.jd / 86400))
        if epoch is None:
            epoch = self._epoch

        self._epoch = epoch
        if periods is None:
            periods = self._periods

        if spacing is None:
            spacing = self._spacing

        self._t_range = time_range(epoch,
                                   periods=periods,
                                   spacing=spacing,
                                   format='jd',
                                   scale='tdb',)

    def set_ephem(self, t_range=None):
        logging.debug("get_ephem()")
        if t_range is None:
            t_range = self._epoch
        if self._orbit is None:
            self._ephem = Ephem.from_body(self._body,
                                          epochs=t_range,
                                          attractor=self._sb_parent,
                                          plane=self._plane,
                                          )
        elif self._orbit != 0:
            self._ephem = Ephem.from_orbit(orbit=self._orbit,
                                           epochs=t_range,
                                           plane=self._plane,
                                           )

        logging.debug("EPHEM : %s", str(self._ephem))
        print("EPHEM : ", self._ephem)

    def set_orbit(self, ephem=None):
        logging.debug("get_orbit()")
        if ephem is None:
            ephem = self._ephem

        if self._sb_parent is not None:
            self._orbit = Orbit.from_ephem(self._sb_parent,
                                           ephem,
                                           self._epoch,
                                           )
            print(self._orbit)
            logging.info(">>> COMPUTING ORBIT: %s",
                         str(self._orbit))
            if (self._track is None) or (self.RESAMPLE is True):
                self._track = self._orbit.sample(360).xyz.transpose().value
                self.RESAMPLE = False

        else:
            self._orbit = 0

    @property
    def name(self):
        return self._name

    @property
    def body(self):
        return self._body

    @property
    def type(self):
        return self._type

    @property
    def body_symb(self):
        return self._body_symb

    @property
    def epoch(self):
        return self._epoch

    @property
    def t_range(self):
        return self._t_range

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
    def rad_pos(self):
        return self._state[0]

    @property
    def track(self):
        return self._track

    # @property
    # def viz_names(self):
    #     return self._viz_names

    @property
    def t_span(self):
        return self._t_span

    @property
    def periods(self):
        return self._periods

    @property
    def o_track(self):
        return self._track

    @property
    def spacing(self):
        return self._spacing

    @state.setter
    def state(self, new_state=None):
        if (type(new_state)  == np.ndarray) and (new_state.shape == (3, 3)):
            self._state = new_state
        else:
            logging.info("!!!\t>> Incorrect state format. Ignoring...:<%s\n>",
                         new_state)
            pass

    @periods.setter
    def periods(self, p=None):
        if p is not None:
            self._periods = p

    @spacing.setter
    def spacing(self, s=None):
        if s is not None:
            self._spacing = s

    @epoch.setter
    def epoch(self, e=None):
        self._epoch = e

    @property
    def base_color(self):
        return self._base_color

    # @property
    # def xyz_mult(self):
    #     return self._xyz_mult

    # @property
    # def v_mult(self):
    #     return self._v_mult

    # @property
    # def tex_data(self):
    #     return self._tex_data

    # @property
    # def vizuals(self):
    #     return self._vizuals

    # @viz_names.setter
    # def viz_names(self, vn=None):
    #     self._viz_names = vn

    # @vizuals.setter
    # def vizuals(self, new_vd=None):
    #     if type(new_vd) == dict and len(new_vd) == len(self.viz_names):
    #         self._vizuals = new_vd


if __name__ == "__main__":

    print("SimBody doesn't really do much...")
