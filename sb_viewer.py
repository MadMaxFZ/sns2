# -*- coding: utf-8 -*-

# import functiontrace
import numpy as np
import math
import subprocess
import vispy.visuals.transforms as tr
from vispy.util.transforms import *
from vispy.scene.visuals import Markers, Compound, Polygon
from vispy.color import Color
from viz_functs import get_tex_data, get_viz_data
from vispy import app, scene
from vispy.app.timer import *
from astropy.time import TimeDelta
from astropy.coordinates import solar_system_ephemeris
from poliastro.util import time_range
from data_functs import *
from simbody import SimBody
from astropy import units as u
from astropy.constants.codata2014 import G
from astropy.units import Quantity
from multiprocessing import Process
import threading

# print(subprocess.run(["cp", "logs/sb_viewer.log", "logs/OLD_sb_viewer.log"]))
# print(subprocess.run(["rm", "logs/sb_viewer.log"]))
# print(subprocess.run(["touch","logs/sb_viewer.log",]))
logging.basicConfig(filename="logs/sb_viewer.log",
                    level=logging.DEBUG,
                    format="%(funcName)s:\t\t%(levelname)s:%(asctime)s:\t%(message)s",
                    )


class SBViewer(scene.SceneCanvas):
    def __init__(self):
        self.INIT = False
        self.dat_store = setup_datastore()
        self.bod_count = self.dat_store["BODY_COUNT"]
        self.b_names = self.dat_store["BODY_NAMES"]
        self.body_data = self.dat_store["BODY_DATA"]
        self.skymap = self.dat_store["SKYMAP"]
        self.sim_params = self.dat_store["SYS_PARAMS"]
        self.w_last = 0
        # self.viz_dicts = {}
        # self.batches = {}
        # self.viz_tr = {}
        self.end_epoch = None
        self.d_epoch = None
        self.avg_d_epoch = None
        self._sys_epoch = Time(self.dat_store["DEF_EPOCH"],
                               format='jd',
                               scale='tdb',
                               )
        self.wclock = Timer(interval='auto',
                            connect=self.update_bodies,     # change this
                            iterations=-1,
                            )
        print("Target FPS:", 1 / self.wclock.interval)
        self.simbods = self.init_simbodies(body_names=self.b_names)
        self.sb_set = list(self.simbods.values())
        self.t_warp = 100000
        self.vec_type = type(np.zeros((3,), dtype=np.float64))
        self.sys_rel_pos = np.zeros((self.bod_count, self.bod_count), dtype=self.vec_type)
        self.sys_rel_vel = np.zeros((self.bod_count, self.bod_count), dtype=self.vec_type)
        self.cam_rel_pos = np.zeros((self.bod_count, ), dtype=self.vec_type)
        self.cam_rel_vel = None
        self.body_accel = np.zeros((self.bod_count, ), dtype=self.vec_type)
        super(SBViewer, self).__init__(keys="interactive",
                                       size=(1024, 768),
                                       show=False,
                                       bgcolor=Color("black"),
                                       )
        self.unfreeze()
        self.view = self.central_widget.add_view()
        self.view.camera = scene.cameras.FlyCamera(fov=30)
        self.view.camera.scale_factor = 0.01
        self.view.camera.zoom_factor = 0.001
        self.b_states = None
        self.b_symbs = ['star', 'o', 'o', 'o',
                        '+',
                        'o', 'o', 'o', 'o', 'o', 'o', ]
        self.bods_viz = None
        self.sys_viz = None
        self.freeze()
        self.sys_viz = self.init_sysviz()
        self.set_wide_ephems()
        self.skymap.parent = self.view.scene
        self.view.add(self.sys_viz)
        self.view.add(self.skymap)
        self.view.camera.set_range((-1e+09, 1e+09),
                                   (-1e+09, 1e+09),
                                   (-1e+09, 1e+09),
                                   )
        # self.init_vizuals()
        # self.run_cycle()
        # self.skymap.visible = False
        # functiontrace.trace()
        self.wclock.start()

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
        for sb_name in self.b_names:
            sb = self.simbods[sb_name]
            sb.set_ephem(t_range=full_t_range)

        self.end_epoch = full_t_range[-1]
        print("END_EPOCH:", self.end_epoch)

    def init_sysviz(self):
        frame = scene.visuals.XYZAxis(parent=self.view.scene)
        # frame.transform = tr.STTransform(scale=(1e+08, 1e+08, 1e+08))
        self.bods_viz = Markers(edge_color=(0, 1, 0, 1))
        orb_vizz = Compound([Polygon(pos=self.simbods[name].o_track,
                                     border_color=self.simbods[name].base_color,
                                     triangulate=False)
                             for name in self.b_names])
        viz = Compound([frame, self.bods_viz, orb_vizz])
        viz.parent = self.view.scene

        return viz

    def update_bodies(self, event=None):
        if self.INIT:
            w_now = self.wclock.elapsed
            dt = w_now - self.w_last
            self.w_last = w_now
        else:
            w_now = 0
            dt = 0
            self.w_last = w_now - dt
            self.INIT = True

        d_epoch = TimeDelta(dt * u.s * self.t_warp)
        if self.avg_d_epoch is None:
            self.avg_d_epoch = d_epoch

        new_epoch = self._sys_epoch + d_epoch
        self.avg_d_epoch = (self.avg_d_epoch + d_epoch) / 2
        self.do_updates(new_epoch=new_epoch)

        # the anomaly most likely resides here
        self.b_states = []
        self.b_states.extend([sb.state[0] for sb in self.sb_set])
        self.b_states[4] += self.simbods['Earth'].state[0, :]
        self.b_states = np.array(self.b_states)
        self.bods_viz.set_data(pos=self.b_states,
                               face_color=self.dat_store["COLOR_SET"],
                               edge_color=(0, 1, 0, .2),
                               symbol=self.b_symbs,
                               )
        if (self.end_epoch - new_epoch) < 2 * self.avg_d_epoch:
            logging.debug("RELOAD EPOCHS/EPHEM SETS...")
            self.set_wide_ephems(epoch=new_epoch)

        self._sys_epoch = new_epoch

        logging.debug("AVG_dt: %s\n\t>>> NEW EPOCH: %s\n",
                      self.avg_d_epoch,
                      new_epoch.jd)
        # print("\n\t>>> NEW EPOCH:", new_epoch.jd)

    def init_simbodies(self, body_names=None):
        solar_system_ephemeris.set("jpl")
        sb_dict = {}
        for name in self.b_names:
            sb_dict.update({name: SimBody(body_name=name,
                                          epoch=self._sys_epoch,
                                          sim_param=self.sim_params,
                                          body_data=self.body_data[name],
                                          )})
        logging.info("\t>>> SimBody objects created....\n")
        return sb_dict
        # self.simbods = sb_dict
        # self.sb_list = list(sb_dict.values())

    def do_updates(self, new_epoch=None):
        for sb in self.sb_set:
            sb.update_state(epoch=new_epoch)
        # self.sys_rel_pos = np.zeros((self.bod_count, self.bod_count), dtype=type(np.zeros((3,), dtype=np.float64)))
        # self.sys_rel_vel = np.zeros((self.bod_count, self.bod_count), dtype=type(np.zeros((3,), dtype=np.float64)))
        # self.body_accel = np.zeros((self.bod_count,), dtype=type(np.zeros((3,), dtype=np.float64)))
        i = 0
        for sb1 in self.sb_set:
            j = 0
            self.cam_rel_pos[i] = sb1.state[0] - self.view.camera.center
            # self.cam_rel_vel[i] = sb1.state[1] - self.view.camera.
            for sb2 in self.sb_set:
                self.sys_rel_pos[i][j] = sb2.state[0] - sb1.state[0]
                self.sys_rel_vel[i][j] = sb2.state[1] - sb1.state[1]
                if i != j:
                    # TODO: all body positions must be in same reference system!! Moon orbit is rel to Earth!
                    self.body_accel[i] += (G * sb2.body.mass) / (self.sys_rel_pos[i][j] * self.sys_rel_pos[i][j] * u.m * u.m)
                j += 1
            i += 1
        logging.info("\nCAM_REL_POS :\n%s", self.cam_rel_pos)
        logging.debug("\nREL_POS :\n%s\nREL_VEL :\n%s\nACCEL :\n%s",
                     self.sys_rel_pos, self.sys_rel_vel, self.body_accel)

    def run(self):
        self.wclock.start()
        self.show()
        app.run()

    def stop(self):
        app.quit()


def main():
    my_can = SBViewer()
    my_can.run()


if __name__ == "__main__":

    main()
