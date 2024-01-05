import numpy as np

from starsys_data import *
from poliastro.ephem import *
from astropy import units as u
from astropy.time import Time, TimeDelta
from poliastro.twobody.orbit.scalar import Orbit

logging.basicConfig(filename="logs/sns_defs.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )

MIN_FOV = 1 / 3600      # I think this would be arc-seconds


class SimBody:
    """
        TODO: Provide a class method to create a SimBody based upon
              a provided Body object.
    """
    epoch0 = J2000_TDB
    simbodies = {}

    def __init__(self,
                 epoch=None,
                 body_data=None,
                 sim_param=None,
                 ):
        self._is_primary    = False
        self._RESAMPLE      = False
        self._sb_parent     = None
        self._body_data     = body_data
        self._name          = body_data['body_name']
        self._body          = body_data['body_obj']
        self._rot_func      = body_data['rot_func']
        self._o_period      = body_data['o_period']
        self._tex_data      = body_data['tex_data']
        self._dist_unit     = sim_param['dist_unit']
        self._periods       = sim_param['periods']
        self._spacing       = self._o_period / self._periods
        self._trajectory    = None
        self._type          = None
        self._ephem: Ephem  = None
        self._orbit: Orbit  = None
        self._t_range: time_range = None
        self._plane         = Planes.EARTH_ECLIPTIC
        self._state         = np.zeros((3,), dtype=vec_type)
        self.x_ax           = vec_type([1, 0, 0])
        self.y_ax           = vec_type([0, 1, 0])
        self.z_ax           = vec_type([0, 0, 1])
        if epoch is None:
            epoch = SimBody.epoch0

        self._epoch         = Time(epoch, format='jd', scale='tdb')
        # self._base_color    = np.array(self._body_data['body_color'])
        # self._body_alpha    = 1.0
        self._track_alpha   = 0.6
        self._mark = None

        # TODO: Fix and/or move this section elsewhere
        #  <<<
        # if self._body.parent is None:
        #     self._type          = "star"
        #     self._body_symbol   = 'o'
        #     self._sb_parent     = None
        #     self._is_primary    = True
        # else:
        #     self._type          = "planet"
        #     self._body_symbol   = 'o'
        #
        # if self._name == "Moon":
        #     self._plane         = Planes.EARTH_EQUATOR
        #     self._body_symbol   = 'o'
        #     self._type          = "moon"
        # else:
        #     self._plane         = Planes.EARTH_ECLIPTIC

        if (self._name == 'Sun' or self._type == 'star' or
                (self._body.R_mean.value == 0 and self._body.R_polar.value == 0)):
            R  = self._body.R.value
            Rm = Rp = R
        else:
            R  = self._body.R.value
            Rm = self._body.R_mean.value
            Rp = self._body.R_polar.value

        self._rad_set = [R, Rm, Rp,]
        self._body_data.update({'rad_set' : self._rad_set})
        # >>>

        self._t_range = time_range(epoch,
                                   periods=sim_param['periods'],
                                   # TODO:  spacing = orbital_period / periods
                                   #        reset value once orbital period it known
                                   spacing=sim_param['spacing'],
                                   format='jd',
                                   scale='tdb', )
        self.set_ephem(t_range=self._t_range)
        self.set_orbit(self._ephem)

    def set_epoch(self, epoch=None):
        if epoch is None:
            epoch = self._epoch
        self._epoch = Time(epoch,
                           format='jd',
                           scale='tdb',
                           )

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

        else:
            self._orbit = 0
            logging.info(">>> NO PARENT BODY, Orbit set to: %s",
                         str(self._orbit))

    def update_state(self, epoch=None):
        if epoch is not None:
            self.set_epoch(epoch)

        if type(self._orbit) == Orbit:
            new_orbit = self._orbit.propagate(self._epoch)
            self._state = np.array([new_orbit.r.to(self._dist_unit).value,
                                    new_orbit.v.to(self._dist_unit / u.s).value,
                                    self._rot_func(**toTD(self._epoch)),
                                    ])
            self._orbit = new_orbit
        else:
            self._state = np.array([self._ephem.rv(self._epoch)[0].to(self._dist_unit).value,
                                    self._ephem.rv(self._epoch)[1].to(self._dist_unit / u.s).value,
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

    def rel2pos(self, pos=None):
        if pos is None:
            pos = self.pos2primary()

        rel_pos = pos - self._state[0]
        dist = np.linalg.norm(rel_pos)
        if dist < 1e-09:
            dist = 0.0
            rel_pos = vec_type([0, 0, 0])
            fov = MIN_FOV
        else:
            fov = np.float64(1.0 * math.atan(self.body.R.value / dist))
        return {"rel_pos": rel_pos,
                "dist": dist,
                "fov": fov,
                }

    def pos2primary(self):
        # TODO: Consider making a SimBody.rel2cam method, that takes
        #       a View as an argument, so the cam from any view can be referenced
        _pos = self.pos
        if self.body.parent is None:
            return _pos
        else:
            return _pos + self.sb_parent.pos2primary()

    @property
    def name(self):
        return self._name

    @property
    def body(self):
        return self._body

    @property
    def sb_parent(self):
        return self._sb_parent

    @sb_parent.setter
    def sb_parent(self, new_sb_parent=None):
        if type(new_sb_parent) is SimBody:
            self._sb_parent = new_sb_parent

    @property
    def is_primary(self):
        return self._is_primary

    @is_primary.setter
    def is_primary(self, is_pri=None):
        self._is_primary = is_pri

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, new_type=None):
        self._type = new_type

    @property
    def base_color(self):
        return self._body_data['body_color']

    @base_color.setter
    def base_color(self, new_color=(1, 1, 1, 1)):
        self._base_color = np.array(new_color)

    @property
    def mark(self):
        return self._body_data['body_mark']

    @mark.setter
    def mark(self, new_symbol='o'):
        self._mark = new_symbol

    @property
    def track_alpha(self):
        return self._track_alpha

    @track_alpha.setter
    def track_alpha(self, new_alpha=1):
        self._track_alpha = 0.6

    @property
    def plane(self):
        return self._plane

    @plane.setter
    def plane(self, new_plane=None):
        self._plane = new_plane

    @property
    def symbol(self):
        return self._body_symbol

    @symbol.setter
    def symbol(self, new_symbol='o'):
        self._body_symbol = new_symbol

    # @property
    # def trk_poly(self):
    #     return self._trk_poly
    #
    # @trk_poly.setter
    # def trk_poly(self, new_trk=None):
    #     assert type(new_trk) is Polygon
    #     self._trk_poly = new_trk

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
        if type(new_epoch) == Time:
            self._epoch = Time(new_epoch,
                               format='jd',
                               scale='tdb',
                               )

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
    def state(self):
        return self._state

    @property
    def pos(self):
        return self._state[0]

    @property
    def vel(self):
        return self._state[1]

    @property
    def track(self):
        return self._trajectory

    @property
    def texture(self):
        return self._tex_data

    @texture.setter
    def texture(self, new_tex_data=None):
        self._tex_data = new_tex_data

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

    @property
    def o_track(self):
        return self._trajectory

    # @property
    # def spacing(self):
    #     return self._spacing

    @state.setter
    def state(self, new_state=None):
        if (type(new_state)  == np.ndarray) and (new_state.shape == (3, 3)):
            self._state = new_state
        else:
            logging.info("!!!\t>> Incorrect state format. Ignoring...:<%s\n>",
                         new_state)
            pass

    # @periods.setter
    # def periods(self, p=None):
    #     if p is not None:
    #         self._periods = p
    #
    # @spacing.setter
    # def spacing(self, s=None):
    #     if s is not None:
    #         self._spacing = s

    @epoch.setter
    def epoch(self, e=None):
        self._epoch = e

    # @property
    # def base_color(self):
    #     return self._base_color


if __name__ == "__main__":

    print("SimBody doesn't really do much...")
