import numpy as np

from starsys_data import *
from poliastro.ephem import *
from astropy import units as u
from astropy.time import Time, TimeDelta
from poliastro.twobody.orbit.scalar import Orbit
from vispy.scene.visuals import Polygon

logging.basicConfig(filename="logs/sns_defs.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )


class SimBody:
    """
        TODO: Provide a class method to create a SimBody based upon
              a provided Body object.
    """
    epoch0 = J2000_TDB
    # R_set = {}
    # simbods = {}

    # TODO: trim down extraneous arguments here:
    def __init__(self,
                 body_name=None,
                 epoch=None,
                 dist_unit=u.km,
                 body_data=None,
                 sim_param=None,
                 ):
        if epoch is None:
            epoch = J2000_TDB
        self._is_primary    = False
        self._sb_parent     = None
        self._name          = body_name
        self._body_data     = body_data
        self._body          = self._body_data['body_obj']
        self._rot_func      = self._body_data['rot_func']
        self._tex_data      = self._body_data['tex_data']
        self._dist_unit     = dist_unit
        self._periods       = sim_param['periods']
        self._spacing       = sim_param['spacing']
        self._t_range       = None
        self._ephem         = None
        self._orbit         = None
        self._track         = None
        self._type          = None
        self._state         = np.zeros((3,), dtype=vec_type)
        self._base_color    = np.array(self._body_data['body_color'])
        self._body_alpha    = 1.0
        self._track_alpha   = 0.6
        self.x_ax           = vec_type([1, 0, 0])
        self.y_ax           = vec_type([0, 1, 0])
        self.z_ax           = vec_type([0, 0, 1])
        self._epoch         = Time(epoch, format='jd', scale='tdb')
        self._RESAMPLE      = False

        # TODO: Fix and/or move this section elsewhere
        #  <<<
        if self._body.parent is None:
            self._type          = "star"
            self._body_symbol   = 'o'
            self._sb_parent     = None
        else:
            self._type          = "planet"
            self._body_symbol   = 'o'

        if self._name == "Moon":
            self._plane         = Planes.EARTH_EQUATOR
            self._body_symbol   = 'o'
            self._type          = "moon"
        else:
            self._plane         = Planes.EARTH_ECLIPTIC

        if self._name == 'Sun' or self._type == 'star':
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
            self._orbit = Orbit.from_ephem(self._sb_parent,
                                           ephem,
                                           self._epoch,
                                           )
            print(self._orbit)
            logging.info(">>> COMPUTING ORBIT: %s",
                         str(self._orbit))
            if (self._track is None) or (self._RESAMPLE is True):
                self._track = self._orbit.sample(360).xyz.transpose().value
                self._RESAMPLE = False

        else:
            self._orbit = 0
            logging.info(">>> NO PARENT BODY, Orbit set to: %s",
                         str(self._orbit))

    def update_state(self, epoch=None):
        self.set_epoch(epoch)
        logging.debug("\n\t\t\tBODY:\t%s\n\t\t\tEPOCH:\t%s\n\t\t\tEPHEM:\t%s",
                      self._name,
                      str(self._epoch),
                      self._ephem
                      )
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

    def rel2pos(self, pos=np.zeros((3,), dtype=np.float64)):
        rel_pos = pos - self._state[0]
        dist = np.linalg.norm(rel_pos)
        if dist < 1e-09:
            dist = 0.0
            rel_pos = vec_type([0, 0, 0])
            fov = -1
        else:
            fov = np.float64(1.0 * math.atan(self.body.R.value / dist))
        return {"rel_pos": rel_pos,
                "dist": dist,
                "fov": fov,
                }

    def pos2primary(self):
        # TODO: Move this method into SimBody module
        #       Consider making a SimBody.rel2cam method, that takes
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
    def type(self):
        return self._type

    @property
    def base_color(self):
        return self._base_color

    @base_color.setter
    def base_color(self, new_color=(1, 1, 1, 1)):
        self._base_color = np.array(new_color)

    @property
    def body_symbol(self):
        return self._body_symbol

    @body_symbol.setter
    def body_symbol(self, new_symbol='o'):
        self._body_symbol = new_symbol

    @property
    def track_alpha(self):
        return self._track_alpha

    @track_alpha.setter
    def track_alpha(self, new_alpha=1):
        self._track_alpha = new_alpha

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
    def t_range(self, new_t_range=None):
        if type(new_t_range) == Time:
            self._t_range = new_t_range

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
        return self._track

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
        return self._track

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
