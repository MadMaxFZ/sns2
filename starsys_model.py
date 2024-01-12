# -*- coding: utf-8 -*-

from astropy.time import TimeDelta
from astropy.coordinates import solar_system_ephemeris
from poliastro.util import time_range
from starsys_data import *
from sysbody_model import SimBody
from astropy import units as u
from astropy.constants.codata2014 import G

logging.basicConfig(filename="logs/sb_viewer.log",
                    level=logging.DEBUG,
                    format='%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s',
                    )

# SYS_DATA = SystemDataStore()


class StarSystemModel:
    """
    """
    # sim_params = SYS_DATA.system_params

    def __init__(self, body_names=None):
        self._data        = SystemDataStore()
        self._INIT        = False
        self._w_last      = 0
        self._d_epoch     = None
        self._avg_d_epoch = 0 * u.s
        self._w_clock     = None
        self._t_warp      = 1.0             # multiple to apply to real time in simulation
        self._sys_epoch   = Time(self._data.def_epoch,
                                 format='jd',
                                 scale='tdb')
        self._ephem_span  = (self._data.system_params['periods']
                             * self._data.system_params['spacing'])
        self._end_epoch   = self._sys_epoch + self._ephem_span

        solar_system_ephemeris.set("jpl")
        self._body_count  = 0
        self._body_names  = []
        self._simbod_dict = {}
        if body_names is None:
            body_names = self._data.body_names
        for _name in body_names:
            if _name in self._data.body_names:
                self._body_count += 1
                self._body_names.append(_name)
                self.add_simbody(body_name=_name)

        for sb in self._simbod_dict.values():
            parent = sb.body.parent
            sb.plane = Planes.EARTH_ECLIPTIC
            if parent is not None:
                if parent.name in self._body_names:
                    sb.sb_parent = self._simbod_dict[sb.body.parent.name]
                    if sb.sb_parent.type == 'star':
                        sb.type = 'planet'
                    elif sb.sb_parent.type == 'planet':
                        sb.type = 'moon'
                        if parent.name == "Earth":
                            sb.plane = Planes.EARTH_EQUATOR
            else:
                sb.type       = 'star'
                sb.sb_parent  = None
                sb.is_primary = True

        SimBody.simbodies = self._simbod_dict

        # self.set_ephems()

        self._sys_rel_pos = np.zeros((self._body_count, self._body_count),
                                     dtype=vec_type)
        self._sys_rel_vel = np.zeros((self._body_count, self._body_count),
                                     dtype=vec_type)
        self._bod_tot_acc = np.zeros((self._body_count,),
                                     dtype=vec_type)

    def assign_timer(self, clock):
        self._w_clock = clock
        self.run()

    def add_simbody(self, body_name=None):
        if body_name is not None:
            if body_name in self._body_names:
                self._simbod_dict.update({body_name: SimBody(body_data=self._data.body_data(name=body_name),
                                                             epoch=self._sys_epoch,
                                                             sim_param=self._data.system_params,
                                                             )
                                          })
            logging.info("\t>>> SimBody object %s created....\n", body_name)

    def set_ephems(self,
                   epoch=None,
                   periods=365,
                   spacing=86400 * u.s,
                   ):
        if epoch is None:
            epoch = self._sys_epoch

        for sb in self.simbod_list:
            _t_range = time_range(epoch,
                                  periods=periods,
                                  spacing=sb.spacing,
                                  format="jd",
                                  scale="tdb",
                                  )
            sb.set_ephem(t_range=_t_range)
            sb.end_epoch = epoch + periods * spacing
            logging.info("END_EPOCH:\n%s\n", self._end_epoch)

    def set_orbits(self):
        [sb.orbit(ephem=sb.ephem) for sb in self.simbod_list]

    def update_epochs(self, event=None):
        if self._INIT:
            w_now = self._w_clock.elapsed     # not the first call
            dt = w_now - self._w_last
            self._w_last = w_now
        else:
            w_now = 0                       # the first call sets up self.w_last
            dt = 0
            self._w_last = w_now - dt
            self._INIT = True

        d_epoch = TimeDelta(dt * u.s * self._t_warp)
        self._sys_epoch += d_epoch
        for sb in self.simbod_list:
            if self._sys_epoch > sb.end_epoch:
                sb.ephem = self._sys_epoch  # reset ephem range
                sb.RESAMPLE = True
                logging.debug("RELOAD EPOCHS/EPHEM SETS...")

        if self._avg_d_epoch.value == 0:
            self._avg_d_epoch = d_epoch

        self._avg_d_epoch = (self._avg_d_epoch + d_epoch) / 2
        self.update_states(new_epoch=self._sys_epoch)
        logging.debug("AVG_dt: %s\n\t>>> NEW EPOCH: %s\n",
                      self._avg_d_epoch,
                      self._sys_epoch.jd)

    def update_states(self, new_epoch=None):
        for sb in self.simbod_list:
            sb.update_state(epoch=new_epoch)

        # self._system_viz.update_sysviz()
        i = 0
        for sb1 in self.simbod_list:
            j = 0
            # collect the relative position and velocity to the other bodies
            for sb2 in self.simbod_list:
                self._sys_rel_pos[i][j] = sb2.rel2pos(pos=sb1.pos2primary)['rel_pos']
                self._sys_rel_vel[i][j] = sb2.vel - sb1.vel
                if i != j:
                    # accumulate the acceleration from the other bodies
                    self.body_accel[i] += (G * sb2.body.mass) / (
                            self._sys_rel_pos[i][j] * self._sys_rel_pos[i][j] * u.m * u.m)
                j += 1
            i += 1


        logging.debug("\nREL_POS :\n%s\nREL_VEL :\n%s\nACCEL :\n%s",
                      self._sys_rel_pos,
                      self._sys_rel_vel,
                      self.body_accel)

    def run(self):
        self._w_clock.start()

    @property
    def simbod_list(self):
        return [self._simbod_dict[name] for name in self._body_names]

    @property
    def body_accel(self):
        return self._bod_tot_acc

    @property
    def t_warp(self):
        return self._t_warp

    @t_warp.setter
    def t_warp(self, new_twarp):
        self._t_warp = new_twarp

    @property
    def model_clock(self):
        return self._w_clock

    @property
    def simbodies(self):
        return self._simbod_dict


def main():
    my_starsys = StarSystemModel()
    my_starsys.run()


if __name__ == "__main__":
    main()
