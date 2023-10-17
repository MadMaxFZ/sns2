# -*- coding: utf-8 -*-

from vispy.app.timer import *
from astropy.time import TimeDelta
from astropy.coordinates import solar_system_ephemeris
from poliastro.util import time_range
from data_functs import *
from simbody import SimBody
from astropy import units as u
from astropy.constants.codata2014 import G
from vispy.scene.visuals import Markers

logging.basicConfig(filename="logs/sb_viewer.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )


class StarSystem:
    def __init__(self, cam=None):
        self.INIT = False
        self.DATASET = setup_datastore()
        self.body_count = self.DATASET["BODY_COUNT"]
        self.body_names = self.DATASET["BODY_NAMES"]    # cast this to a tuple?
        self.body_data  = self.DATASET["BODY_DATA"]
        self.skymap     = self.DATASET["SKYMAP"]
        self.sim_params = self.DATASET["SYS_PARAMS"]
        self.w_last = 0
        self.d_epoch = None
        self.avg_d_epoch = None
        self.end_epoch = None
        self._sys_epoch = Time(self.DATASET["DEF_EPOCH"],
                               format='jd',
                               scale='tdb',
                               )
        self.wclock = Timer(interval='auto',
                            connect=self.update_bodies,  # change this
                            iterations=-1,
                            )
        print("Target FPS:", 1 / self.wclock.interval)
        self.simbods = self.init_simbodies(body_names=self.body_names)
        self.sb_list = list(self.simbods.values())
        self.vec_type = type(np.zeros((3,), dtype=np.float64))
        self.sys_rel_pos = np.zeros((self.body_count, self.body_count), dtype=self.vec_type)
        self.sys_rel_vel = np.zeros((self.body_count, self.body_count), dtype=self.vec_type)
        self.body_accel = np.zeros((self.body_count,), dtype=self.vec_type)
        self.cam = cam
        self.cam_rel_pos = np.zeros((self.body_count,), dtype=self.vec_type)
        self.cam_rel_vel = None
        self._bods_viz = Markers(edge_color=(0, 1, 0, 1))
        self.b_states = None
        self.b_symbs = ['star', 'o', 'o', 'o',
                        '+',
                        'o', 'o', 'o', 'o', 'o', 'o', ]     # could base this on body type
        self.t_warp = 100000            # multiple to apply to real time in simulation
        self.set_wide_ephems()
        # self.wclock.start()

    def set_wide_ephems(self, epoch=None, span=None):
        year_span = self.simbods["Earth"].orbit.period
        if epoch is None:
            epoch = self._sys_epoch

        if span is None:
            span = year_span

        full_t_range = time_range(epoch,
                                  periods=365,
                                  spacing=span,
                                  format="jd",
                                  scale="tdb",
                                  )
        for sb_name in self.body_names:
            sb = self.simbods[sb_name]
            sb.set_ephem(t_range=full_t_range)

        self.end_epoch = full_t_range[-1]
        print("END_EPOCH:", self.end_epoch)

    def update_bodies(self, event=None):
        if self.INIT:
            w_now = self.wclock.elapsed     # not the first call
            dt = w_now - self.w_last
            self.w_last = w_now
        else:
            w_now = 0                       # the first call sets up self.w_last
            dt = 0
            self.w_last = w_now - dt
            self.INIT = True

        d_epoch = TimeDelta(dt * u.s * self.t_warp)
        if self.avg_d_epoch is None:
            self.avg_d_epoch = d_epoch

        new_epoch = self._sys_epoch + d_epoch
        self.avg_d_epoch = (self.avg_d_epoch + d_epoch) / 2
        self.do_updates(new_epoch=new_epoch)

        if (self.end_epoch - new_epoch) < 2 * self.avg_d_epoch:
            logging.debug("RELOAD EPOCHS/EPHEM SETS...")
            self.set_wide_ephems(epoch=new_epoch)               # reset ephem range

        self._sys_epoch = new_epoch

        logging.debug("AVG_dt: %s\n\t>>> NEW EPOCH: %s\n",
                      self.avg_d_epoch,
                      new_epoch.jd)

    def init_simbodies(self, body_names=None):
        solar_system_ephemeris.set("jpl")
        sb_dict = {}
        for name in self.body_names:
            sb_dict.update({name: SimBody(body_name=name,
                                          epoch=self._sys_epoch,
                                          sim_param=self.sim_params,
                                          body_data=self.body_data[name],
                                          # add marker symbol and marker size to body_data
                                          )})
        logging.info("\t>>> SimBody objects created....\n")
        return sb_dict

    def do_updates(self, new_epoch=None):
        for sb in self.sb_list:
            sb.update_state(epoch=new_epoch)

        self.b_states = []
        self.b_states.extend([sb.state[0] for sb in self.sb_list])
        self.b_states[4] += self.simbods['Earth'].state[0, :]       # add Earth pos to Moon pos
        self.b_states = np.array(self.b_states)
        self._bods_viz.set_data(pos=self.b_states,
                                face_color=self.DATASET["COLOR_SET"],
                                edge_color=(0, 1, 0, .2),
                                symbol=self.b_symbs,
                                )

        i = 0
        for sb1 in self.sb_list:
            j = 0
            self.cam_rel_pos[i] = sb1.state[0] - self.cam.center
            # self.cam_rel_vel[i] = sb1.state[1] - self.view.camera.
            for sb2 in self.sb_list:
                self.sys_rel_pos[i][j] = sb2.state[0] - sb1.state[0]
                self.sys_rel_vel[i][j] = sb2.state[1] - sb1.state[1]
                if i != j:
                    # TODO: all body positions must be in same reference system!! Moon orbit is rel to Earth!
                    self.body_accel[i] += (G * sb2.body.mass) / (
                                self.sys_rel_pos[i][j] * self.sys_rel_pos[i][j] * u.m * u.m)
                j += 1
            i += 1
        logging.info("\nCAM_REL_POS :\n%s", self.cam_rel_pos)
        logging.debug("\nREL_POS :\n%s\nREL_VEL :\n%s\nACCEL :\n%s",
                      self.sys_rel_pos, self.sys_rel_vel, self.body_accel)

    def run(self):
        self.wclock.start()

    @property
    def bods_viz(self):
        return self._bods_viz

def main():
    my_starsys = StarSystem()
    my_starsys.run()


if __name__ == "__main__":
    main()
