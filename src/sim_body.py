
import logging

logging.basicConfig(filename="../logs/sns_simbod.log",
                    level=logging.ERROR,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )

from sim_object import *
from vispy.color import Color
from poliastro.twobody.orbit.scalar import Orbit

MIN_FOV = 1 / 3600      # I think this would be arc-seconds


def toTD(epoch=None):
    d = (epoch - J2000_TDB).jd
    T = d / 36525
    return dict(T=T, d=d)


class SimBody(SimObject):
    """
        TODO: Provide a class method to create a SimBody based upon
              a provided Body object.
    """
    def __init__(self, body_data=None, vizz_data=None):
        super(SimBody, self).__init__()
        self._body_data     = body_data
        self._vizz_data     = vizz_data
        self._name          = self._body_data['body_name']
        self._body          = self._body_data['body_obj']
        self._rot_func      = self._body_data['rot_func']
        self._o_period      = self._body_data['o_period']

        self.set_dimensions()
        self.set_ephem(epoch=self._epoch)
        self.set_orbit(ephem=self._ephem)
        # self._field_dict = None
        # SimBody.system[self._name] = self
        # self.created.emit(self.name)

    def set_dimensions(self, **kwargs):
        if (self._name == 'Sun' or self._type == 'star' or
                (self._body.R_mean.value == 0 and self._body.R_polar.value == 0)):
            R  = self._body.R.to(self._dist_unit)
            Rm = Rp = R
            self._is_primary = True
        else:
            R  = self._body.R.to(self._dist_unit)
            Rm = self._body.R_mean.to(self._dist_unit)
            Rp = self._body.R_polar.to(self._dist_unit)

        self._rad_set = [R, Rm, Rp]
        self._body_data.update({'rad_set': self._rad_set})
        logging.info("RADIUS SET: %s", self._rad_set)

    def set_ephem(self, epoch=None, t_range=None):
        if epoch is None:
            epoch = self._epoch
        if t_range is None:                                         # sets t_range from epoch to epoch + orbital period
            t_range = time_range(epoch,
                                 periods=self._periods,
                                 spacing=self._spacing,
                                 format='jd',
                                 scale='tdb',
                                 )
            self._end_epoch += self._periods * self._spacing

        if self._orbit is None:                                     # first time through
            self._ephem = Ephem.from_body(self._body,
                                          epochs=t_range,
                                          attractor=self.body.parent,
                                          plane=self._plane,
                                          )
        elif self._orbit != 0:                                      # this body has a parent
            self._ephem = Ephem.from_orbit(orbit=self._orbit,
                                           epochs=t_range,
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
                self._trajectory = self._orbit.sample(720)
                self._RESAMPLE = False

        elif self._body.parent is None:
            self._orbit = 0
            logging.info(">>> NO PARENT BODY, Orbit set to: %s",
                         str(self._orbit))

    def update_state(self, epoch=None):
        """

        Parameters
        ----------
        epoch           :   Time            The epoch to which the state is to be set

        Returns
        -------
        simbody._state  : np.ndarray(3, 3)  The state matrix for the new Simbody state
        """
        new_state = None
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

        # return self._state

    @property
    def body(self):
        return self._body

    @property
    def radius(self):
        return self._rad_set

    @property
    def parent(self):
        return self._sim_parent

    @parent.setter
    def parent(self, new_sb_parent=None):
        if self.body.parent:
            if self.body.parent.name == new_sb_parent.name:
                self._sim_parent = new_sb_parent

    def set_parent(self, sb=None):
        if type(sb) == Body:
            self._sim_parent = sb
            sb.plane = Planes.EARTH_ECLIPTIC
            this_parent = sb.parent
            if this_parent is None:
                sb.type = 'star'
                sb.sb_parent = None
                sb.is_primary = True
            else:
                sb.sb_parent = this_parent
                if sb.sb_parent.type == 'star':
                    sb.type = 'planet'
                elif sb.sb_parent.type == 'planet':
                    sb.type = 'moon'
                    if this_parent.name == "Earth":
                        sb.plane = Planes.EARTH_EQUATOR

    @property
    def sys_primary(self):
        if self.body.parent:
            if self._sim_parent:
                return self.sys_primary(self._sim_parent)
            else:
                print("Error: SimSystem parentage not set...")
        else:
            return self

    @property
    def is_primary(self):
        if self.body.parent:
            return False
        else:
            return True

    @property
    def type(self):
        return self._type

    @type.setter
    def type(self, new_type=None):
        self._type = new_type

    @property
    def pos(self):
        return self.pos2primary

    @property
    def RA(self):
        return self._state[2, 0]

    @property
    def DEC(self):
        return 90 - self._state[2, 1]

    @property
    def W(self):
        return self._state[2, 2]

    @property                   # this returns the position of a body plus the position of the primary
    def pos2primary(self):
        _pos = self._state[0] * self._dist_unit
        if self._sim_parent is None:
            return np.zeros((3,), dtype=np.float64) * self._dist_unit
        else:
            return _pos + self._sim_parent.pos2primary

    @property
    def attr(self):
        res = []
        for a in self.body:
            if type(a) == Body:
                a = a.name
            res.append(a)
        return res

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
    def state_matrix(self):
        return self._state

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

    @property
    def track_color(self):
        res = Color(self._vizz_data['body_color'])
        res.alpha = self._vizz_data['track_alpha']

        return res


if __name__ == "__main__":

    def main():
        pass
        #     sb = SimBody(body_data=sys_data.body_data(bod_name))
        #     sb.update_state(sb)
        # print(sb.orbit)


    main()
    print("SimBody doesn't really do much...")
