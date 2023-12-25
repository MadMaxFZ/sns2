# -*- coding: utf-8 -*-

from vispy.app.timer import *
from astropy.time import TimeDelta
from astropy.coordinates import solar_system_ephemeris
from poliastro.util import time_range
from starsys_data import *
from simbody import SimBody
from astropy import units as u
from astropy.constants.codata2014 import G

logging.basicConfig(filename="logs/sb_viewer.log",
                    level=logging.DEBUG,
                    format='%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s',
                    )

SYS_DATA = SystemDataStore()


class StarSystemModel:
    """
    """
    sim_params = SYS_DATA.system_params

    def __init__(self, bod_names=SYS_DATA.body_names, view=None):
        self._INIT        = False
        self._ephem_span  = (StarSystemModel.sim_params['periods']
                             * StarSystemModel.sim_params['spacing'])
        self._body_count  = 0
        self._body_names  = []
        self._body_data   = {}
        for name in bod_names:
            if name in SYS_DATA.body_names:
                self._body_count += 1
                self._body_names.append(name)
                self._body_data.update({name: SYS_DATA.get_body_data(name)})

        self._simbodies   = self.init_simbodies()
        self._sbod_list   = [self._simbodies[name] for name in self._body_names]
        self._sys_epoch   = Time(SYS_DATA.def_epoch,
                                 format='jd',
                                 scale='tdb')
        self._end_epoch   = self._sys_epoch + self._ephem_span
        self._w_last      = 0
        self._d_epoch     = None
        self._avg_d_epoch = 0 * u.s
        self._w_clock     = Timer(interval='auto',
                                  connect=self.update_epochs,  # change this
                                  iterations=-1)
        self._t_warp      = 1.0             # multiple to apply to real time in simulation
        self._sys_rel_pos = np.zeros((self._body_count, self._body_count), dtype=vec_type)
        self._sys_rel_vel = np.zeros((self._body_count, self._body_count), dtype=vec_type)
        self._body_accel = np.zeros((self._body_count,), dtype=vec_type)
        self.set_ephems()

    def init_simbodies(self, names=None):
        solar_system_ephemeris.set("jpl")
        sb_dict = {}
        for name in self._body_names:
            sb_dict.update({name: SimBody(body_name=name,
                                          epoch=self._sys_epoch,
                                          body_data=self._body_data[name],
                                          sim_param=StarSystemModel.sim_params,
                                          )})
        for sb in sb_dict.values():
            if sb.body.parent is not None:
                sb.sb_parent = sb_dict[sb.body.parent.name]
        logging.info("\t>>> SimBody objects created....\n")
        return sb_dict

    def set_ephems(self,
                   epoch=None,
                   periods=365,
                   spacing=86400 * u.s,
                   ):
        if epoch is None:
            epoch = self._sys_epoch

        _t_range = time_range(epoch,
                              periods=periods,
                              spacing=spacing,
                              format="jd",
                              scale="tdb",
                              )
        [sb.set_ephem(t_range=_t_range) for sb in self._sbod_list]
        self._end_epoch = _t_range[-1]
        logging.info("END_EPOCH:\n%s\n", self._end_epoch)

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
        if self._sys_epoch > self._end_epoch:
            self.set_ephems(epoch=self._sys_epoch)  # reset ephem range
            logging.debug("RELOAD EPOCHS/EPHEM SETS...")

        if self._avg_d_epoch.value == 0:
            self._avg_d_epoch = d_epoch

        self._avg_d_epoch = (self._avg_d_epoch + d_epoch) / 2
        self.update_states(new_epoch=self._sys_epoch)
        logging.debug("AVG_dt: %s\n\t>>> NEW EPOCH: %s\n",
                      self._avg_d_epoch,
                      self._sys_epoch.jd)

    def update_states(self, new_epoch=None):
        for sb in self._sbod_list:
            sb.update_state(epoch=new_epoch)

        # self._system_viz.update_sysviz()
        i = 0
        for sb1 in self._sbod_list:
            j = 0
            # collect the relative position and velocity to the other bodies
            for sb2 in self._sbod_list:
                self._sys_rel_pos[i][j] = sb2.rel2pos(pos=sb1.pos)['rel_pos']
                self._sys_rel_vel[i][j] = sb2.vel - sb1.vel
                if i != j:
                    # accumulate the acceleration from the other bodies
                    self._body_accel[i] += (G * sb1.body.mass * sb2.body.mass) / (
                            self._sys_rel_pos[i][j] * self._sys_rel_pos[i][j] * u.m * u.m)
                j += 1
            i += 1

        logging.debug("\nREL_POS :\n%s\nREL_VEL :\n%s\nACCEL :\n%s",
                      self._sys_rel_pos, self._sys_rel_vel, self._body_accel)

    def run(self):
        self._w_clock.start()

    @property
    def sys_viz(self):
        return self._system_viz

    @property
    def t_warp(self):
        return self._t_warp

    @t_warp.setter
    def t_warp(self, new_twarp):
        self._t_warp = new_twarp

    @property
    def simbodies(self):
        return self._simbodies


def main():
    my_starsys = StarSystemModel()
    my_starsys.run()


if __name__ == "__main__":
    main()
